# Agent Workflow

A 3-layer architecture for reliable AI-assisted automation. Separates human intent from deterministic execution to maximize reliability.

## Why This Exists

LLMs are probabilistic. Business logic is deterministic. When you let an LLM do everything, errors compound: 90% accuracy per step = 59% success over 5 steps.

The fix: push complexity into deterministic code. The LLM focuses on decision-making and orchestration.

## Architecture

| Layer | Purpose | Location |
|-------|---------|----------|
| **Directive** | What to do (SOPs) | `directives/` |
| **Orchestration** | Decision-making (the LLM) | — |
| **Execution** | Doing the work | `execution/` |

## Directory Structure

```
├── directives/       # Markdown SOPs - goals, inputs, outputs, edge cases
├── execution/        # Python scripts - API calls, data processing, file ops
├── .tmp/             # Intermediate files (auto-generated, gitignored)
├── .env              # API keys and secrets
├── credentials.json  # Google OAuth (gitignored)
├── token.json        # Google OAuth (gitignored)
└── AGENTS.md         # Full architecture reference
```

## How It Works

1. **Directives** define tasks in natural language (like instructions for a mid-level employee)
2. **Orchestration** (the LLM) reads directives, calls scripts in order, handles errors
3. **Execution** scripts do the actual work—deterministic, testable, fast

## Self-Annealing

When something breaks:
1. Fix it
2. Update the script
3. Test it
4. Update the directive with what you learned
5. System is now stronger

Errors are learning opportunities. Directives are living documents.

## Setup

1. Add API keys to `.env`
2. Place Google OAuth credentials in root (if using Google services)
3. Create directives in `directives/` for your workflows
4. Build execution scripts in `execution/` as needed

## Key Principles

- **Check for tools first** — look in `execution/` before writing new scripts
- **Deliverables live in the cloud** — Google Sheets, Slides, etc. Local files are just for processing.
- **Everything in `.tmp/` is disposable** — can be deleted and regenerated
