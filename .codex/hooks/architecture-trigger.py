"""UserPromptSubmit hook (Codex) — детект архитектурных trigger-фраз.

Читает stdin JSON Codex (поле prompt / user_prompt). Если есть совпадение —
печатает SOFT SUGGEST в stdout: при exit 0 Codex трактует plain-text как
дополнительный контекст к ходу. Хук СОВЕТУЕТ, не запускает skills сам.

Отключается переменной окружения CODEX_DISABLE_ARCH_TRIGGER=1.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Final

TRIGGERS: Final[list[tuple[str, str]]] = [
    (r"(?:начн[её]м|стартуем|давай[те]?\s+сделаем|поехали)\s+v\s*\d+\.\d+", "start of new version"),
    (
        r"(?:добавим|построим|сделаем|внедрим|реализуем|разработаем|подключим)\s+(?:новый\s+)?"
        r"(?:layer|слой|алгоритм|сервис|модуль|интеграцию|компонент|архитектуру|подсистему|очередь|воркер|API)",
        "add new architectural component",
    ),
    (r"(?:заменим|переделаем|перепишем|выкинем|откатим|мигрируем)\s+\S+", "replace/rewrite component"),
    (
        r"(?:переедем|смена|перенос)\s+(?:на|с|с\s+\S+\s+на)\s+(?:VPS|сервер|хостинг|Docker|Timeweb|Kubernetes)",
        "infrastructure migration",
    ),
    (
        r"(?:изменим|пересмотрим|переделаем)\s+(?:модель\s+прав|разграничение|OAuth|авторизацию|аутентификацию|multi.?tenant)",
        "auth/permissions model change",
    ),
    (r"(?:bulk|массов(?:ый|ая|ое)|backfill|пересчёт|пере[гн]енераци[яю])\s+\S+", "bulk production operation"),
    (r"(?:подключим|интегрируем)\s+(?:GPT|Claude|OpenAI|Anthropic|LLM|ML)", "external LLM integration"),
]

REMINDER = """\
ARCHITECTURE TRIGGER DETECTED: "{phrase}" -> {reason}

Это может быть архитектурное решение. Рекомендую (но не запускай сам):
1. /premortem — pre-mortem, 10-шаговый workflow с RPN scoring.
2. /contrarian — adversarial review плана.
3. /split-decision — если развилка >= 2 viable подходов.

Предложи пользователю вызвать /premortem явно.
"""


def _extract_prompt(payload: dict) -> str:
    for key in ("prompt", "user_prompt", "message", "text"):
        v = payload.get(key)
        if isinstance(v, str) and v:
            return v
    return ""


def main() -> int:
    if os.environ.get("CODEX_DISABLE_ARCH_TRIGGER") == "1":
        return 0
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, ValueError):
        return 0

    prompt = _extract_prompt(payload if isinstance(payload, dict) else {})
    if not prompt:
        return 0

    for pattern, reason in TRIGGERS:
        m = re.search(pattern, prompt, re.IGNORECASE | re.UNICODE)
        if m:
            sys.stdout.write(REMINDER.format(phrase=m.group(0), reason=reason))
            return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
