"""PostToolUse hook (Codex, matcher=apply_patch) — автоформат изменённых файлов.

apply_patch не отдаёт один file_path (в tool_input лежит патч), поэтому берём
изменённые файлы из git и форматируем их. Никогда не падает (exit 0 всегда):
если форматтер/php недоступны — молча выходит.

АДАПТИРУЙ: команду форматтера и расширения под свой стек.
"""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import subprocess
import sys

EXTENSIONS = (".php",)  # под свой стек: (".ts", ".tsx") / (".py",) / ...


def _changed_files(project_root: pathlib.Path) -> list[str]:
    try:
        out = subprocess.check_output(
            ["git", "diff", "--name-only", "--diff-filter=AM"], text=True, timeout=5, cwd=str(project_root)
        )
    except Exception:
        return []
    return [
        ln.strip() for ln in out.splitlines()
        if ln.strip().endswith(EXTENSIONS) and (project_root / ln.strip()).exists()
    ][:20]


def main() -> int:
    try:
        json.loads(sys.stdin.buffer.read().decode("utf-8", errors="replace"))
    except Exception:
        pass

    project_root = pathlib.Path(__file__).resolve().parents[2]
    files = _changed_files(project_root)
    if not files:
        return 0

    fixer = next(
        (str(p) for p in (
            project_root / "vendor" / "bin" / "php-cs-fixer.bat",
            project_root / "vendor" / "bin" / "php-cs-fixer",
        ) if p.exists()),
        None,
    )
    php = shutil.which("php")
    if fixer is None or php is None:
        return 0

    for f in files:
        try:
            subprocess.run(
                [php, fixer, "fix", "--quiet", str(project_root / f)],
                capture_output=True, timeout=15, cwd=str(project_root),
            )
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    os.chdir(pathlib.Path(__file__).resolve().parents[2])
    sys.exit(main())
