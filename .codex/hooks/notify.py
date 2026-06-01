"""notify-программа (Codex) — тост/звук при завершении хода агента.

Codex вызывает её на событии agent-turn-complete и передаёт JSON одним
аргументом (sys.argv[1]). Аналог Notification-хука Claude Code.

Кросс-платформенно: на Windows — звук + всплывающее уведомление (если есть
win10toast), иначе — терминальный bell. Никогда не падает.
"""

from __future__ import annotations

import json
import sys


def _payload() -> dict:
    if len(sys.argv) > 1:
        try:
            return json.loads(sys.argv[1])
        except Exception:
            return {}
    try:
        return json.loads(sys.stdin.read() or "{}")
    except Exception:
        return {}


def main() -> int:
    data = _payload()
    msg = data.get("last-assistant-message") or data.get("message") or "Codex: ход завершён"
    title = "Codex"

    try:
        if sys.platform.startswith("win"):
            import winsound
            winsound.MessageBeep()
            try:
                from win10toast import ToastNotifier  # опционально: pip install win10toast
                ToastNotifier().show_toast(title, str(msg)[:200], duration=5, threaded=True)
            except Exception:
                pass
        else:
            sys.stdout.write("\a")  # терминальный bell
            sys.stdout.flush()
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
