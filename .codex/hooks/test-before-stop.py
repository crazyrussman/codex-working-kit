"""Stop hook (Codex) — тесты на изменённые модули перед завершением хода.

Берёт изменённые src/*.php из git, ищет соответствующие tests/**/*<Stem>Test.php,
гоняет PHPUnit в test-образе. Падение → блокирует завершение (exit 2 + stderr).
1 retry. Docker / vendor нет → молча выходит.

АДАПТИРУЙ: маппинг файл→тест и команду тестов под свой стек.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import run_in_docker  # noqa: E402

MARKER = pathlib.Path(__file__).parent / ".phpunit-retry-count"
MAX_RETRIES = 1
TIMEOUT_SEC = 120
MAX_FILES = 15
MAX_TESTS = 10


def find_tests_for(stem: str, tests_dir: pathlib.Path) -> list[pathlib.Path]:
    if not tests_dir.exists():
        return []
    out: list[pathlib.Path] = []
    for pattern in (f"{stem}Test.php", f"Test{stem}.php", f"*{stem}*Test.php"):
        for p in tests_dir.rglob(pattern):
            if p not in out:
                out.append(p)
    return out


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

    src_files = [
        ln.strip() for ln in changed.splitlines()
        if ln.strip().endswith(".php") and ln.strip().startswith("src/")
    ][:MAX_FILES]
    if not src_files:
        MARKER.unlink(missing_ok=True)
        return 0

    tests_dir = project_root / "tests"
    matched: list[pathlib.Path] = []
    for f in src_files:
        for t in find_tests_for(pathlib.Path(f).stem, tests_dir):
            if t not in matched:
                matched.append(t)
    if not matched:
        MARKER.unlink(missing_ok=True)
        return 0
    matched = matched[:MAX_TESTS]

    if not (project_root / "vendor" / "bin" / "phpunit").exists():
        return 0

    rel = [str(t.relative_to(project_root)).replace("\\", "/") for t in matched]
    result = run_in_docker.run_in_image(
        project_root,
        ["php", "vendor/bin/phpunit", "--stop-on-failure", "--no-coverage", *rel],
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
        print("Тесты падают после попытки починки. Сообщи пользователю: какой тест, какая ошибка, чинить или принять.", file=sys.stderr)
        return 0

    MARKER.write_text(str(count + 1))
    out = ((result.stdout or "") + (result.stderr or ""))[-3000:]
    print(f"PHPUnit упал на тестах изменённых модулей:\n{out}\nПочини перед завершением. Устаревший тест — обнови, не отключай.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
