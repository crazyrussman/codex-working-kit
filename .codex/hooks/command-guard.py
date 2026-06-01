"""PreToolUse hook (Codex, matcher=Bash) — deny-list деструктивных команд.

Заменяет permissions.deny из .claude/settings.json (у Codex нет встроенного
гранулярного deny-list bash-команд). Читает stdin JSON, достаёт tool_input.command.
Если команда совпала с запрещённым паттерном — блокирует: печатает причину в
stderr и выходит с кодом 2 (Codex трактует exit 2 как deny с сообщением).

Списки ниже — адаптируй под свой проект (имена защищаемых файлов/таблиц).
"""

from __future__ import annotations

import json
import re
import sys
from typing import Final

# Паттерны запрещённых команд (case-insensitive, поиск по подстроке как regex).
DENY: Final[list[str]] = [
    # --- уничтожение файловой системы ---
    r"rm\s+-rf\s+/(?:\s|$|\*)",
    r"rm\s+-rf\s+~(?:/|\s|$)",
    r"rm\s+-rf\s+\.\.(?:/|\s|$)",
    r"rm\s+-rf\s+\.git\b",
    r"rm\s+-rf\s+vendor\b",
    r"rm\s+(?:-rf?\s+)?\.env\b",
    r"\bdel\s+/q\s+/s\b",
    r"\brmdir\s+/s\s+/q\b",
    r"Remove-Item\s+-Recurse\s+-Force\s+[/~]",
    r"Remove-Item\s+.*\b(vendor|\.env|\.git)\b",
    r"Format-Volume\b",
    r"Clear-Disk\b",
    # --- системное ---
    r"\bmkfs(\.\w+)?\b",
    r"\bdd\s+if=.*of=/dev/",
    r"\bsudo\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"Stop-Computer\b",
    r"Restart-Computer\b",
    # --- git деструктив ---
    r"git\s+push\s+.*(--force\b|--force-with-lease\b|\s-f\b)",
    r"git\s+reset\s+--hard\b",
    r"git\s+clean\s+-[a-z]*f[a-z]*d",
    r"git\s+branch\s+-D\b",
    # --- БД деструктив / эскалация прав (адаптируй имена таблиц) ---
    r"DROP\s+TABLE\b",
    r"DROP\s+DATABASE\b",
    r"\bTRUNCATE\b",
    r"DELETE\s+FROM\b",
    r"(UPDATE|INSERT\s+INTO)\s+.*\ballowed_users\b",
    # --- скачать-и-выполнить ---
    r"Invoke-Expression\s+.*(iwr|Invoke-WebRequest|Invoke-RestMethod)",
    r"\biex\s+.*(iwr|curl|wget)",
    r"(curl|wget)\s+.*\|\s*(sh|bash)\b",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in DENY]


def _extract_command(payload: dict) -> str:
    ti = payload.get("tool_input") or {}
    for key in ("command", "cmd", "script"):
        v = ti.get(key)
        if isinstance(v, str):
            return v
        if isinstance(v, list):
            return " ".join(str(x) for x in v)
    return ""


def main() -> int:
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
    except (json.JSONDecodeError, ValueError):
        return 0
    if not isinstance(payload, dict):
        return 0

    command = _extract_command(payload)
    if not command:
        return 0

    for rx in _COMPILED:
        if rx.search(command):
            print(
                f"Команда заблокирована deny-list'ом command-guard: совпадение с '{rx.pattern}'.\n"
                "Если это легитимная операция — выполни её вручную или ослабь правило в "
                ".codex/hooks/command-guard.py.",
                file=sys.stderr,
            )
            return 2  # Codex: exit 2 = deny с сообщением из stderr

    return 0


if __name__ == "__main__":
    sys.exit(main())
