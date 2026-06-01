"""Stop hook (Codex) — статанализ изменённых файлов перед завершением хода.

Берёт изменённые .php из git, гоняет PHPStan в test-образе. Ошибки → блокирует
завершение (exit 2 + stderr), Codex обязан починить. 1 retry, потом пропускает
с сообщением пользователю. Docker / vendor нет → молча выходит.

АДАПТИРУЙ: команду статанализа под свой стек.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import run_in_docker  # noqa: E402

MARKER = pathlib.Path(__file__).parent / ".lint-retry-count"
MAX_RETRIES = 1
TIMEOUT_SEC = 90


def main() -> int:
    try:
        json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
    except Exception:
        pass

    project_root = pathlib.Path(__file__).resolve().parents[2]
    os.chdir(project_root)

    try:
        changed = subprocess.check_output(
            ["git", "diff", "--name-only", "--diff-filter=AM"], text=True, timeout=5
        )
    except Exception:
        return 0

    files = [ln.strip().replace("\\", "/") for ln in changed.splitlines() if ln.strip().endswith(".php")][:20]
    if not files:
        MARKER.unlink(missing_ok=True)
        return 0

    if not (project_root / "vendor" / "bin" / "phpstan").exists():
        return 0

    result = run_in_docker.run_in_image(
        project_root,
        ["php", "vendor/bin/phpstan", "analyse", "--no-progress", "--no-interaction", "--memory-limit=512M", *files],
        timeout=TIMEOUT_SEC,
    )
    if result is None:
        return 0
    if result.returncode == 0:
        MARKER.unlink(missing_ok=True)
        return 0

    count = int(MARKER.read_text()) if MARKER.exists() else 0
    if count >= MAX_RETRIES:
        MARKER.unlink(missing_ok=True)
        print("PHPStan ошибки остались после попытки починки. Сообщи пользователю — чинить сейчас или принять.", file=sys.stderr)
        return 0

    MARKER.write_text(str(count + 1))
    out = ((result.stdout or "") + (result.stderr or ""))[-2000:]
    print(f"PHPStan нашёл проблемы в изменённых .php:\n{out}\nПочини перед завершением.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
