"""CLI entrypoint: read inbox CSV, classify via LLM, write outputs."""
from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime, timezone

from src.classifier import classify_all
from src.config import load_settings
from src.integrations import sheets, telegram
from src.llm.gemini import GeminiProvider
from src.reader import read_requests
from src.reporter import write_outputs

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("main")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify internal inbox requests.")
    parser.add_argument("--input", help="Path to input_requests.csv")
    parser.add_argument("--output-dir", help="Directory for output.json and report.md")
    parser.add_argument(
        "--no-async", action="store_true", help="Process requests sequentially"
    )
    parser.add_argument(
        "--to-telegram", action="store_true", help="Send digest to Telegram"
    )
    parser.add_argument(
        "--to-sheets", action="store_true", help="Export results to Google Sheet"
    )
    return parser.parse_args()


async def run() -> None:
    args = parse_args()
    settings = load_settings()
    input_path = args.input or settings.input_path
    output_dir = args.output_dir or settings.output_dir

    requests = read_requests(input_path)
    logger.info("Loaded %d requests from %s", len(requests), input_path)

    provider = GeminiProvider(settings.gemini_api_key, settings.llm_model)
    results = await classify_all(
        provider,
        requests,
        concurrency=settings.concurrency,
        use_async=not args.no_async,
    )

    run_date = datetime.now().strftime("%d.%m.%Y")  # local date for digest/sheet
    meta = {
        "model": settings.llm_model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    summary = write_outputs(results, output_dir, meta)
    logger.info(
        "Wrote %s/output.json and %s/report.md (%d fallbacks)",
        output_dir,
        output_dir,
        len(summary["fallbacks"]),
    )

    if args.to_telegram and settings.telegram_enabled:
        ok = telegram.send_digest(
            settings.telegram_bot_token,
            settings.telegram_chat_id,
            summary,
            run_date,
        )
        logger.info("Telegram digest sent: %s", ok)
    elif args.to_telegram:
        logger.warning("Telegram requested but not configured; skipping")

    if args.to_sheets and settings.sheets_enabled:
        ok = sheets.export(
            settings.google_sheet_id,
            settings.google_service_account_json,
            results,
            run_date,
        )
        logger.info("Google Sheets export: %s", ok)
    elif args.to_sheets:
        logger.warning("Sheets requested but not configured; skipping")


if __name__ == "__main__":
    asyncio.run(run())
