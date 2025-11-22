# Libraries

- modelcontextprotocol/python‑sdk (≈20k stars)	This is the official MCP SDK.  It provides FastMCP wrappers for exposing resources (like state://active) and tools (like runner.chat or custom tuner methods) so your Runner/Tuner servers speak MCP out of the box.
- FastAPI (≈92 k stars) + Uvicorn (ASGI server, ≈10k stars)	FastAPI offers easy declaration of REST endpoints with automatic OpenAPI docs, while Uvicorn is a high‑performance ASGI server.  Together they’re a battle‑tested combination for serving HTTP endpoints and can wrap the MCP server if desired.
- jsonschema (≈4.9k stars)	Implements the JSON Schema specification, letting you validate state files and tuner inputs; supports multiple drafts and programmatic error inspection.
- pydantic (≈25.8k stars)	Creates Python classes that enforce type hints and validate incoming data.  Useful for building Runner/Tuner request/response models and for state representation.
- python‑semver (≈508 stars)	Provides proper SemVer parsing and comparison, making it easy to increment patch/minor/major versions in git tags.
- GitPython (≈5k stars)	Provides high‑level access to git repositories, allowing the Architect and Tuner to create commits, read tags, and manage branches programmatically.
- pytest (≈13.3k stars)	Widely‑used test runner with powerful fixtures and detailed assertion introspection; scales from simple unit tests to complex integration tests.
- OpenTelemetry Python (≈2.2k stars)	Supplies unified APIs and SDKs for traces, metrics and logs.  Using this library allows you to instrument the Runner and Tuner, emit spans and structured logs and export them to backends via OTLP.
- watchdog (≈7.2k stars)	Monitors file system events.  You can integrate it to watch state files or logs and feed events into the Architect‑wake trigger.

These libraries should be available for the implementations (Tuner, Tests, Runner)

- Optuna (≈13.1k stars)	Provides efficient algorithms for hyperparameter optimization.  For a Tuner that performs RLHF‑style or bandit tuning, Optuna’s sampler and study APIs can be repurposed to adjust Runner parameters and policies.
- pycma (≈1.3k stars)	Implements the Covariance Matrix Adaptation evolution strategy.  Ideal when the Architect selects CMA‑ES as the optimization strategy for the Tuner.
- scikit‑learn (≈64.1k stars)	Provides logistic regression and other models that can be used for pairwise preference fitting or contextual bandits in the Tuner.  Although scikit‑learn isn’t a bandit library per se, its algorithms are foundational for implementing custom bandit strategies.
- SMPyBandits (≈413 stars)	Although smaller, it implements dozens of single‑ and multi‑player bandit algorithms and can serve as a reference for bandit‑style Tuner strategies.
- langchain for using LLM agents
