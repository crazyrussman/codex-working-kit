# Codex Working Kit

Перенос рабочего процесса с **Claude Code** на **OpenAI Codex CLI** для PHP/Bitrix24-Marketplace-проектов (multi-tenant, Docker-first).

Это самодостаточный комплект: правила работы, хуки автопроверок, skills (бывшие slash-команды + субагенты) и конфиг разрешений. Кладётся в репозиторий проекта и в домашнюю папку Codex. Не содержит секретов и привязки к конкретному порталу — адаптируется под любой аналогичный проект.

---

## Что Codex понимает «из коробки» (проверено по docs OpenAI, апрель–июнь 2026)

| Возможность Claude Code | Аналог в Codex | Файл/место |
|---|---|---|
| `CLAUDE.md` (auto-loaded brief) | **`AGENTS.md`** (auto-loaded) | корень репо + `~/.codex/AGENTS.md` глобально; вложенные `AGENTS.md` по подпапкам |
| `WORKING_RULES.md` | секция в `AGENTS.md` | здесь влита в `AGENTS.md` |
| `.claude/settings.json` → `permissions` | **`config.toml`**: `approval_policy`, `sandbox_mode`, `[sandbox_workspace_write]`, `[projects.<path>] trust_level` | `~/.codex/config.toml` (+ `<repo>/.codex/config.toml`) |
| `.claude/settings.json` → `hooks` | **lifecycle hooks** (схема почти 1:1) | `<repo>/.codex/hooks.json` или `~/.codex/hooks.json` или inline `[hooks]` в `config.toml` |
| Slash-команды (`/resume`, `/wrap`, …) | **skills** (рекомендуемо) или custom prompts (deprecated, но работают) | `.agents/skills/<имя>/SKILL.md` ; либо `~/.codex/prompts/<имя>.md` |
| Субагенты (`contrarian`, `integration-reviewer`) | **skills** с implicit-вызовом (+ события `SubagentStart/Stop`) | `.agents/skills/<имя>/SKILL.md` |
| MCP `context7` | `[mcp_servers.context7]` | `config.toml` |
| Notification-хук (toast/звук) | **`notify`** (внешняя программа на событие) | `notify = [...]` в `config.toml` |
| `MEMORY.md` + `memory/*` | нет встроенного — повторяем файловой конвенцией | `docs/memory/*` + ссылка из `AGENTS.md` |

**Поддерживаемые события хуков Codex:** `SessionStart`, `SubagentStart`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `UserPromptSubmit`, `SubagentStop`, `Stop`.
Matcher применяется к имени инструмента: `Bash`, `apply_patch` (правка файлов), MCP-инструменты. Блокировка — exit code `2` + текст в stderr (как в Claude Code).

---

## Состав комплекта

```
codex-working-kit/
├── README.md                       ← этот файл
├── AGENTS.md                       ← brief проекта + правила работы (= CLAUDE.md + WORKING_RULES.md)
├── config.toml.example             ← разрешения/sandbox/notify/MCP (= settings.json permissions)
├── .codex/
│   ├── hooks.json                  ← конфиг хуков (= settings.json hooks)
│   └── hooks/
│       ├── architecture-trigger.py ← UserPromptSubmit: soft-suggest premortem
│       ├── command-guard.py        ← PreToolUse(Bash): deny-list деструктива (= permissions.deny)
│       ├── format-after-edit.py    ← PostToolUse(apply_patch): автоформат изменённых файлов
│       ├── lint-before-stop.py     ← Stop: статанализ, блокирует выход при ошибках
│       ├── test-before-stop.py     ← Stop: тесты на изменённые модули, блокирует при падении
│       ├── run_in_docker.py        ← общий helper: запуск тулзы в test-образе
│       └── notify.py               ← notify-программа: тост/звук при завершении хода
└── .agents/skills/                 ← skills (= slash-команды + субагенты)
    ├── resume/SKILL.md
    ├── wrap/SKILL.md
    ├── doc-update/SKILL.md
    ├── premortem/SKILL.md
    ├── contrarian/SKILL.md
    ├── split-decision/SKILL.md
    ├── audit/SKILL.md
    └── integration-reviewer/SKILL.md
```

---

## Установка (для коллеги)

1. **Положить в проект.** Скопировать в корень рабочего репозитория:
   - `AGENTS.md` → корень репо (отредактировать плейсхолдеры `<...>` под свой проект);
   - `.codex/` → `<repo>/.codex/`;
   - `.agents/` → `<repo>/.agents/`.

2. **Глобальный конфиг.** Содержимое `config.toml.example` влить в `~/.codex/config.toml` (или `<repo>/.codex/config.toml`). Поправить `writable_roots`, `[projects."<путь к репо>"] trust_level = "trusted"`, MCP-серверы.

3. **Доверие хукам.** При первом запуске Codex попросит подтвердить незнакомые хуки (trust review) — подтвердить один раз.

4. **Проверка.** Запустить `codex` в репо, набрать `/resume` — должен подтянуться `AGENTS.md` и выдать резюме. Сделать тестовую правку `.php` — должен отработать формат; попытка завершить ход — должны прогнаться lint/тесты.

> **Windows.** Хуки кросс-платформенные (Python). Если на Windows путь к интерпретатору отличается — в `hooks.json` есть поле `command_windows` (переопределяет `command` под Windows). Test-образ запускается через Docker Desktop — пути вида `D:\...` он понимает.

---

## Что НЕ переносится 1:1 и как обходим

- **Память (`MEMORY.md`/`memory/*`).** У Codex нет встроенной системы памяти. Конвенция: держать `docs/memory/*.md` (4 типа: `user_/feedback_/project_/reference_`) и ссылаться на индекс из `AGENTS.md`. Codex прочитает их как обычные файлы.
- **`AskUserQuestion` со структурой.** В Codex нет того же инструмента — skill `split-decision` просит модель задать выбор обычным текстом (нумерованные варианты + ждать ответа).
- **Custom prompts deprecated.** OpenAI рекомендует skills. Здесь всё сделано на skills; если коллега хочет именно `/команды` старого вида — те же файлы можно положить в `~/.codex/prompts/<имя>.md`.

---

## Источники (OpenAI Codex docs, актуальны на июнь 2026)

- Hooks: https://developers.openai.com/codex/hooks
- Config reference: https://developers.openai.com/codex/config-reference
- AGENTS.md: https://developers.openai.com/codex/guides/agents-md
- Skills: https://developers.openai.com/codex/skills
- Custom prompts (deprecated): https://developers.openai.com/codex/custom-prompts
