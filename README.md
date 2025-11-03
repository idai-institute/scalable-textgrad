# Scalable TextGrad Platform

Workspace utilities for Codex-driven agents: directory layout helpers, state tracking, and CI runners you can call from your own orchestration layer.

## Quickstart

```bash
pip install -e .
```

## Usage

```python
from pathlib import Path

from scalable_textgrad.codex_client import CodexRunner
from scalable_textgrad.config import AgentSettings, resolve_workspace
from scalable_textgrad.state_manager import StateManager

settings = AgentSettings()
dirs = resolve_workspace(settings, "demo")
dirs.root.mkdir(parents=True, exist_ok=True)

manager = StateManager(dirs)
manager.ensure_layout()

codex = CodexRunner(settings)
result = codex.run("write a hello world script", dirs.root)
print(result.exit_code, result.stdout)
```

Useful environment variables (prefixed with `STG_`):

| Variable | Description | Default |
| --- | --- | --- |
| `STG_WORKSPACE_ROOT` | Root directory that stores agent workspaces | `./agents` |
| `STG_CODEX_COMMAND` | Path to the Codex CLI executable | `codex` |
