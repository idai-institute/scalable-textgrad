# Scalable TextGrad Platform

Implements the Architect service described in the design docs. Provides shared helper libraries for state tracking, git-backed versioning, and Codex orchestration.

## Quickstart

```bash
pip install -e .
```

Run the Architect REST API:

```bash
uvicorn scalable_textgrad.architect.service:app --reload
```

Useful environment variables (prefixed with `STG_`):

| Variable | Description | Default |
| --- | --- | --- |
| `STG_WORKSPACE_ROOT` | Root directory that stores version worktrees | `./agents` |
| `STG_CODEX_COMMAND` | Path to the Codex CLI executable | `codex` |

The Architect exposes `POST /agent/start` to bootstrap a new workspace and `POST /agent/{version}/architect/chat` to apply feedback.
