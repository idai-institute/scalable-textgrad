# System Design

This document describes the **internal design** of the system that exposes two MCP servers (Runner, Tuner) and two REST APIs (Architect, Versions). External interfaces are defined elsewhere; here we focus on **components, data, flows, state, testing, logging, triggers, release, and operations**.

---

## 1. Goals & Non-Goals

**Goals**

* Support **rapid, cheap improvements** via structured feedback through Tuner.
* Allow **infrequent, high-impact changes** via Architect (code/config commits, semver bumps).
* Provide **commit-scoped builds** with **semver tags** backed by **git** as the canonical version store.
* Make behavior **observable and auditable** (standard logs, metrics, evals, and provenance).
* Enable **automatic wake-ups** of the Architect when feedback or SLOs degrade.

**Non-Goals**

* Multi-tenant permissions and quotas beyond basic auth (future work).
* Cross-agent federation protocols (future).

---

## 2. High-Level Architecture


**Core components**

* **Runner (MCP, Python)**: **implemented by the Architect in Python.** Executes tasks using the active state; may maintain conversational sessions.
* **Tuner (MCP, Python)**: **implemented by the Architect in Python.** Applies structured feedback via Architect-defined tools; promotes state after microtests and increments **patch**.
* **Architect (REST)**: ingests textual feedback; edits code/state/tests; runs full CI; on success, commits and **tags in git** (minor/major/patch). Note: the code of the Architect is shared across all versions, since it's static
* **Versions API (REST)**: read-only registry of available versions and metadata (sourced from git and the object store).
* **State Manager (library/sidecar)**: controls staging/active state, version pinning, and migration hooks.
* **Testing System**: tiered test harness (micro/fast/full) authored by the Architect and executed in CI.
* **Logging/Telemetry**: standardized structured logs, metrics, and traces into the object store.

---

---

## 5. Testing System (Architect-Authored)

**Artifacts & Budgets**

* `tests/` contains datasets and golden outputs.
* `ci/budgets.json` controls SLOs (see §8).
* Results persisted at `s3://.../evals/{commit}/summary.json` and linked from the Versions API.

**Runner Invocation**

* Test harness calls Runner MCP tools directly; supports parallel shards.

---

## 6. Tuner (Python, Architect-Implemented)

**Contract**

* Entirely **Architect-defined Python tools and JSON Schemas per version**; examples include bandit steps, CMA-ES iterations, preference fitting, rules mining.

**Lifecycle**

1. Receive structured signals (e.g., bandit rewards with `conversation_id`).
2. Update `state/staging.state.json` (OCC-guarded). No need for git
3. Emit summary event to Triggerer (to keep KPI aggregates fresh).

**Safety Rails**

* Tuner can only modify state files under `state/` (policy-enforced paths); **code changes are reserved for the Architect**.

---

## 7. Runner (Python, Architect-Implemented)

**Responsibilities**

* Provide MCP tools (stateless/stateful) to execute tasks under **active** state.
* Manage conversational sessions; expose `session://{conversation_id}`.
* Emit per-call logs/metrics to the logging pipeline.

**Hot Reload**

* Subscribe to State Manager events; apply new `active` state atomically.

---

---

## 9. Logging & Telemetry (Standardized)

Use OpenTelemetry

**Traceability**

* Correlate by `conversation_id` and `trace_id`.

---


## 10. Security & Governance

For now, allow everything and don't handle security.

---

## 11. Deployment & Topology

* Separate processes/containers per component: `runner`, `tuner`, `architect`, `versions`.
---

---

## 13. Examples

Provide, for the architect, a library of inspirations and templates for the Runner, the Tuner, and so on.
