"""Helper для hook-ов: запустить команду в проектном test-образе.

Docker-first проекты: на хосте обычно нет PHP с нужными extensions
(mbstring/pdo_sqlite/intl). Этот helper держит логику запуска и кэш образа
в одном месте. Используется lint-before-stop.py и test-before-stop.py.

Поведение:
1. Docker недоступен → (None) → хук тихо скипает.
2. Образа нет → собираем из <repo>/.codex/hooks/Dockerfile.test (~30-60с в первый раз).
3. Возвращаем CompletedProcess от `docker run`.

Volume mount: корень репо → /app, рабочая директория контейнера = /app.
АДАПТИРУЙ: IMAGE_TAG, Dockerfile.test и саму команду под свой стек.
"""

from __future__ import annotations

import pathlib
import shutil
import subprocess
from typing import Optional

IMAGE_TAG = "project-test:latest"
BUILD_TIMEOUT_SEC = 180


def _docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        return subprocess.run(["docker", "info"], capture_output=True, timeout=5, text=True).returncode == 0
    except Exception:
        return False


def _image_exists() -> bool:
    try:
        return subprocess.run(
            ["docker", "image", "inspect", IMAGE_TAG], capture_output=True, timeout=10, text=True
        ).returncode == 0
    except Exception:
        return False


def _ensure_image(hook_dir: pathlib.Path) -> bool:
    if _image_exists():
        return True
    dockerfile = hook_dir / "Dockerfile.test"
    if not dockerfile.exists():
        return False
    try:
        return subprocess.run(
            ["docker", "build", "-t", IMAGE_TAG, "-f", str(dockerfile), str(hook_dir)],
            capture_output=True, timeout=BUILD_TIMEOUT_SEC, text=True,
        ).returncode == 0
    except Exception:
        return False


def run_in_image(project_root: pathlib.Path, cmd: list[str], timeout: int) -> Optional[subprocess.CompletedProcess]:
    """Запускает `cmd` в test-образе, монтируя project_root → /app. None если docker/образ недоступны."""
    if not _docker_available():
        return None
    hook_dir = pathlib.Path(__file__).parent
    if not _ensure_image(hook_dir):
        return None
    mount = f"{project_root}:/app"  # Docker Desktop на Windows понимает D:\... формат
    try:
        return subprocess.run(
            ["docker", "run", "--rm", "-v", mount, "-w", "/app", IMAGE_TAG, *cmd],
            capture_output=True, text=True, timeout=timeout,
        )
    except Exception:
        return None
