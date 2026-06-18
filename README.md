# Inbox Request Classifier

A service that classifies free-form internal requests (from Slack / Telegram / Email)
with an LLM: it determines the category, owning department, priority, a one-line
summary and the concrete actions asked for, validates the model output against a
strict schema, and produces a structured result plus a short report.

## What it does

1. Reads an inbox CSV (`id, channel, timestamp, raw_text`).
2. For each request, calls **Google Gemini** to extract structured fields.
3. Validates the LLM output against a strict Pydantic schema; invalid output
  degrades safely into a fallback record (the pipeline never crashes).
4. Writes `output/output.json` (full result) and `output/report.md` (aggregates).
5. Sends a formatted **Telegram digest** (`--to-telegram`).
6. Exports all rows to a **Google Sheet** (`--to-sheets`).

Telegram and Sheets are real, working integrations; they are opt-in via CLI flags
and stay disabled until their environment variables are set.

## Architecture

```
src/
├── config.py          # settings from .env (pydantic-settings)
├── models.py          # Pydantic schema, enums, fallback factory
├── reader.py          # CSV reading
├── prompt.py          # system prompt + few-shot examples
├── llm/
│   ├── base.py        # LLMProvider (ABC) — provider-agnostic interface
│   └── gemini.py      # Gemini implementation (native JSON output + backoff)
├── classifier.py      # orchestration: validation, retry, fallback, async semaphore
├── reporter.py        # aggregates, report.md, duplicate heuristic
└── integrations/
    ├── telegram.py    # optional digest via Bot API
    └── sheets.py      # optional export to Google Sheets
main.py                # CLI entrypoint
```

The provider sits behind the `LLMProvider` interface, so adding OpenAI/Anthropic is
a new class with no changes to the rest of the code. The Pydantic `Classification`
model is the single source of truth — it is reused as the Gemini response schema.

## Result schema

Mandatory fields (per the task):


| Field                 | Meaning                                                                                                          |
| --------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `category`            | one of: `автоматизація`, `інтеграція`, `звіт/аналітика`, `баг/підтримка`, `питання/консультація`, `поза скоупом` |
| `target_department`   | requesting department, or `null` if unclear                                                                      |
| `priority`            | `low` / `medium` / `high` (inferred from tone and content)                                                       |
| `short_summary`       | one-sentence essence                                                                                             |
| `requested_actions`   | numbered list of concrete actions (0, 1 or many)                                                                 |
| `needs_clarification` | `true` if too vague to act on as-is                                                                              |


Schema extensions (added deliberately):


| Field                  | Why                                                                                 |
| ---------------------- | ----------------------------------------------------------------------------------- |
| `confidence`           | model confidence (0–1) — surfaces uncertain items for manual review                 |
| `urgency_signals`      | tone/deadline phrases that drove the priority (e.g. "ГОРИТЬ", "сьогодні до вечора") |
| `is_actionable`        | `false` for non-tasks (thank-you notes, FYI, noise)                                 |
| `estimated_effort`     | rough delivery effort: `low` / `medium` / `high`                                    |
| `classification_error` | set only when a fallback record was produced                                        |


The final record also carries the input fields (`id`, `channel`, `timestamp`, `raw_text`).

## Setup & run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # set GEMINI_API_KEY (free tier: https://aistudio.google.com/apikey)
python main.py                # reads samples/input_requests.csv by default
```

Results are written to `output/output.json` and `output/report.md`.

Dependencies are pinned to exact, audited versions (`pip-audit`: no known
vulnerabilities). The current `google-genai` SDK is used (the older
`google-generativeai` package is deprecated).

### CLI flags

```bash
python main.py --input path/to/your_inbox.csv    # custom input file
python main.py --output-dir output               # custom output directory
python main.py --no-async                         # process sequentially
python main.py --to-telegram                      # send Telegram digest
python main.py --to-sheets                        # export to Google Sheet
```

### Environment variables


| Variable                                         | Purpose                   | Default                              |
| ------------------------------------------------ | ------------------------- | ------------------------------------ |
| `GEMINI_API_KEY`                                 | Gemini API key (required) | —                                    |
| `LLM_MODEL`                                      | model id                  | `gemini-2.5-flash`                   |
| `CONCURRENCY`                                    | parallel requests         | `5`                                  |
| `INPUT_PATH` / `OUTPUT_DIR`                      | IO paths                  | `samples/input_requests.csv` / `output` |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`         | Telegram digest           | empty (disabled)                     |
| `GOOGLE_SHEET_ID`, `GOOGLE_SERVICE_ACCOUNT_JSON` | Sheets export             | empty / `keys/service_account.json`  |


Secrets live in `.env` and `keys/` — both are git-ignored and never committed.

### Docker

The sample input ships in the image; the service-account key and outputs are mounted at
runtime (secrets are never baked in):

```bash
docker build -t inbox-classifier .

docker run --rm --env-file .env \
  -v "$PWD/keys:/app/keys" \
  -v "$PWD/output:/app/output" \
  inbox-classifier --to-telegram --to-sheets
```

To run your own file, mount it and pass `--input`:
`-v "$PWD/your.csv:/app/input.csv" inbox-classifier --input input.csv`.

### Tests

```bash
pytest
```

Tests never hit the network — the LLM is replaced with a stub.

## Where it breaks / limitations

- **Invalid LLM output.** Closed at three levels: Gemini native structured output
(`response_schema` + `response_mime_type=application/json`, `temperature=0`) →
strict Pydantic validation → one retry → fallback record with
`needs_clarification=true` and `classification_error`. One bad request never
fails the batch.
- **Rate limits / free tier.** The free tier is capped at **20 requests/day per
model**. Transient `429` and `5xx` responses are retried with exponential backoff;
once the daily quota is gone, requests degrade to fallback records. For real volume
use a paid tier or a queue/worker with throttling.
- **Non-determinism.** `temperature=0` reduces but does not eliminate variation;
borderline phrasings may shift category between runs.
- **Token cost.** Each request is a separate call with few-shot in the prompt; at
scale, batch/compress the prompt or cache results.
- **Duplicate detection** is a best-effort keyword-overlap heuristic on
`short_summary`, not semantic — it catches near-identical requests but may miss
paraphrased duplicates.

## What's next



- **Persistent datastore (Postgres).** Store every classified request for history,
analytics, audit and deduplication — not only `output.json` / Sheets.
- **Service + live ingestion.** Expose as an API/worker that consumes Slack/Telegram
events in real time (or on a schedule) instead of a one-off CSV run, and deploy it.
- **DB-managed prompts + RAG over history.** Externalize and version prompts in the
database; retrieve similar past requests as examples to keep classification
consistent over time.
- **Human-in-the-loop + caching.** Route low-`confidence` / `needs_clarification`
items to a human queue; cache by a hash of `raw_text` to avoid paying tokens for
repeated or duplicate requests.

