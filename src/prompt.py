import json

SYSTEM_PROMPT = """\
Ти — асистент AI-юніту в Netpeak. Внутрішні команди (маркетинг, продажі, аналітика, \
PM, HR) надсилають запити у вільній формі. Твоє завдання — класифікувати кожен запит \
і витягнути структуровані поля. Відповідай СТРОГО валідним JSON за наданою схемою.

Правила:
- category: рівно одне з: "автоматизація", "інтеграція", "звіт/аналітика", \
"баг/підтримка", "питання/консультація", "поза скоупом".
  - "поза скоупом" — коли це не задача для AI-юніту (закупівлі, кадрові/побутові \
питання) або взагалі не запит (подяка, флуд).
- target_department: відділ-замовник одним словом ("маркетинг", "продажі", \
"аналітика", "HR", "бухгалтерія", "контент", "SMM"...). null, якщо незрозуміло.
- priority: low / medium / high. Виводь із тону і змісту. \
Слова "ГОРИТЬ", "терміново", "сьогодні до вечора", "дуже потрібно" → high. \
"не горить", "просто цікаво", "колись" → low.
- short_summary: суть одним реченням українською.
- requested_actions: список конкретних дій, кожна пронумерована ("1. ...", "2. ..."). \
Може бути 0, 1 або кілька. Якщо в запиті дві задачі — поверни два елементи.
- needs_clarification: true, якщо запит надто розмитий, щоб брати в роботу як є.
- confidence: 0..1, наскільки ти впевнений у класифікації.
- urgency_signals: слова/фрази з тексту, що вплинули на priority, включно з \
дедлайнами ("сьогодні до вечора", "до кінця місяця"). Можуть бути відсутні.
- is_actionable: false, якщо повідомлення не є задачею (подяка, флуд, FYI).
- estimated_effort: орієнтовні трудовитрати — low (швидко/тривіально), \
medium (помітна робота), high (велика інтеграція/складна задача).
"""

# Compact few-shot examples covering the tricky inbox cases.
FEW_SHOT = [
    {
        "input": "хлопці треба бот",
        "output": {
            "category": "питання/консультація",
            "target_department": None,
            "priority": "low",
            "short_summary": "Запит на якогось бота без деталей.",
            "requested_actions": [],
            "needs_clarification": True,
            "confidence": 0.4,
            "urgency_signals": [],
            "is_actionable": False,
            "estimated_effort": "low",
        },
    },
    {
        "input": "дякую за вчора, все працює супер",
        "output": {
            "category": "поза скоупом",
            "target_department": None,
            "priority": "low",
            "short_summary": "Подяка за виконану раніше роботу.",
            "requested_actions": [],
            "needs_clarification": False,
            "confidence": 0.95,
            "urgency_signals": [],
            "is_actionable": False,
            "estimated_effort": "low",
        },
    },
    {
        "input": "ГОРИТЬ. Сьогодні до вечора треба вивантажити список контрагентів з витратами понад 50к за травень, бухгалтерія просить терміново.",
        "output": {
            "category": "звіт/аналітика",
            "target_department": "бухгалтерія",
            "priority": "high",
            "short_summary": "Терміново вивантажити контрагентів із витратами понад 50к за травень.",
            "requested_actions": [
                "1. Вивантажити список контрагентів із витратами >50к за травень"
            ],
            "needs_clarification": False,
            "confidence": 0.9,
            "urgency_signals": ["ГОРИТЬ", "терміново", "сьогодні до вечора"],
            "is_actionable": True,
            "estimated_effort": "medium",
        },
    },
    {
        "input": "Можна автоматизувати збір згадок про Netpeak в телеграм-каналах і робити дайджест раз на день? І ще окремо — алерт, якщо згадка негативна.",
        "output": {
            "category": "автоматизація",
            "target_department": "маркетинг",
            "priority": "medium",
            "short_summary": "Автоматизувати моніторинг згадок про Netpeak з дайджестом і алертами.",
            "requested_actions": [
                "1. Збирати згадки про Netpeak у Telegram-каналах і робити щоденний дайджест",
                "2. Налаштувати алерт на негативні згадки",
            ],
            "needs_clarification": False,
            "confidence": 0.85,
            "urgency_signals": [],
            "is_actionable": True,
            "estimated_effort": "high",
        },
    },
]


def build_user_prompt(raw_text: str) -> str:
    """Assemble the per-request user message with inline few-shot guidance."""
    lines = ["Приклади:"]
    for shot in FEW_SHOT:
        lines.append(f"Запит: {shot['input']}")
        lines.append(
            "JSON: " + json.dumps(shot["output"], ensure_ascii=False)
        )
    lines.append("")
    lines.append("Класифікуй наступний запит:")
    lines.append(f"Запит: {raw_text}")
    return "\n".join(lines)
