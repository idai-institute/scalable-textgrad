# Scalable TextGrad Platform

Implements the Architect service described in the design docs. Provides shared helper libraries for state tracking and Codex orchestration.

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
| `STG_WORKSPACE_ROOT` | Root directory that stores agent workspaces | `./agents` |
| `STG_CODEX_COMMAND` | Path to the Codex CLI executable | `codex` |

The Architect exposes `POST /agent/start` to bootstrap a new workspace and `POST /agent/{agent_name}/architect/chat` to apply feedback.
