# MCP + REST Interfaces for the System

This spec defines **two MCP servers** and **two REST APIs** exposed under a single agent namespace. Each MCP server uses **commit scoping**, but has an associated **semver tag**. For example, commit `eda3322` may be the parent of `982daa`, and a minor bump (`1.5.3 → 1.6.0`) indicates that changes were limited in scope. Note that multiple branches can thus have the same version tag: this represents the possibility to have multiple evolutions of the system.

* `/agent/{versions}/runner`
  Architect-defined MCP server for execution.
* `/agent/{versions}/tuner`
  Architect-defined MCP server for structured optimization.
* `/agent/{versions}/architect`
  **REST API** for textual feedback and governance; runs tests and commits to git on green; bumps semver. Note: the underlying code is always the same for the Architect (since there's actually only one instance of the Architect running), but this helps conceptually to specify which version the agent should look at
* `/versions`
  **REST API** for listing versions and metadata.

> **Note**: Runner and Tuner are intentionally broad. The **Architect owns the Runner and Tuner APIs** and may evolve their internal state models across versions. Clients should always perform MCP discovery at session start.

---

## Common MCP Conventions (Runner & Tuner)

These apply to `/runner` and `/tuner` servers:

* **Transport**: HTTP (JSON)
* **Initialization**: Clients MUST perform an MCP handshake and discovery (list tools/resources/prompts) per connection.
* **Auth**: Bearer or OAuth2 (as configured).
* **Version scope**: Each MCP server URL is immutable for that `version`.
* **Resources**: URIs may reference object store artifacts (e.g., `s3://…`) or local virtual schemes like:

  * `state://…`
  * `logs://…`
  * `session://{session_id}`

---

## 1) `/runner` — Execution Surface (Architect-Defined MCP Server)

Completely Architect-defined. Below are two concrete examples: a **stateless** tool and a **stateful** tool.

One invariant: **every call returns a server-generated UUID** (`conversation_id`). For stateful tools, the `conversation_id` can be passed back to continue the session; for stateless tools, it can be used to attach feedback and logs.

### Discovery

* **Tools**:

  * `runner.get_weather` (stateless)
  * `runner.chat` (stateful)
* **Resources**:

  * `state://active`
  * `state://assets`
  * `session://{conversation_id}`
  * `session://index?limit=N`
  * `logs://recent?limit=N`
  * `compat://manifest`

### Tools

#### `runner.get_weather` (stateless)

**Purpose**: Demonstration tool without server-side conversational state (but still producing a `conversation_id` for logging/feedback).

**Input JSON Schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://specs/runner.get_weather.input.json",
  "type": "object",
  "required": ["location"],
  "properties": {
    "location": {
      "type": "string",
      "description": "City name or 'lat,long' coordinates."
    },
    "units": {
      "type": "string",
      "enum": ["metric", "imperial"],
      "default": "metric"
    },
    "when": {
      "type": "string",
      "description": "RFC3339 datetime or 'now'.",
      "default": "now"
    }
  },
  "additionalProperties": false
}
```

**Output JSON Schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://specs/runner.get_weather.output.json",
  "type": "object",
  "required": ["forecast", "conversation_id"],
  "properties": {
    "forecast": {
      "type": "object",
      "description": "Structured forecast payload."
    },
    "conversation_id": {
      "type": "string",
      "description": "Server-generated UUID associated with this invocation."
    },
    "logs_uri": {
      "type": "string",
      "format": "uri",
      "description": "Optional URI for debug logs related to this invocation."
    }
  },
  "additionalProperties": false
}
```

#### `runner.chat` (stateful)

**Purpose**: Maintains **per-session conversational state** keyed by `conversation_id`. The server stores ephemeral context (turns, summaries, flags) and surfaces it via `session://{conversation_id}` resources.

**Input JSON Schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://specs/runner.chat.input.json",
  "type": "object",
  "required": ["message"],
  "properties": {
    "conversation_id": {
      "type": "string",
      "description": "Server-provided identifier; reuse to continue the session."
    },
    "message": {
      "type": "string",
      "description": "User input for this turn."
    },
    "metadata": {
      "type": "object",
      "description": "Optional per-turn metadata (tool prefs, routing hints)."
    }
  },
  "additionalProperties": false
}
```

**Output JSON Schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://specs/runner.chat.output.json",
  "type": "object",
  "required": ["reply", "conversation_id"],
  "properties": {
    "reply": {
      "type": "object",
      "description": "Model or pipeline response for this turn, possibly structured."
    },
    "conversation_id": {
      "type": "string",
      "description": "Server-generated or reused conversation UUID."
    },
    "logs_uri": {
      "type": "string",
      "format": "uri",
      "description": "Optional URI for server logs or trace for this turn."
    }
  },
  "additionalProperties": false
}
```

**Session lifecycle (informative)**

1. Client calls `runner.chat` without `conversation_id` → server creates a session and returns `conversation_id`.
2. Subsequent calls reuse the same `conversation_id` to maintain context and share state via `session://{conversation_id}`.

---

## 2) `/tuner` — Structured Optimization (Architect-Defined MCP Server)

The **Architect defines every aspect** of `/tuner`: tool names, input/output schemas, semantics, and how they map into internal optimization pipelines.

### Discovery

* **Tools**:

  * `tuner.bandit_reward`
  * (and optional strategy-specific tools per version)
* **Resources**:

  * `state://active`
  * `state://staging`
  * `eval://micro_results.jsonl`
  * optional `assets://*`
* **Prompts** (optional):

  * `tuner/explain` (e.g., “explain current tuning state”)

### Example tool archetypes (illustrative)

#### `tuner.bandit_reward`

**Purpose**: Apply a numeric bandit reward for a given conversation ID.

**Input JSON Schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://specs/tuner.bandit_reward.input.json",
  "type": "object",
  "required": ["conversation_id", "reward"],
  "properties": {
    "conversation_id": {
      "type": "string",
      "description": "ID of the referenced conversation."
    },
    "reward": {
      "type": "number",
      "description": "Bandit reward signal (e.g., scalar in [-1,1] or [0,1])."
    }
  },
  "additionalProperties": false
}
```

**Output JSON Schema**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://specs/tuner.bandit_reward.output.json",
  "type": "object",
  "required": ["status"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["success", "failure"],
      "description": "Whether the reward was recorded and propagated."
    },
    "details": {
      "type": "string",
      "description": "Optional human-readable details on what was updated."
    }
  },
  "additionalProperties": false
}
```

#### Strategy-specific tools (examples; Architect may add/remove per version)

* `tuner.ucb_step(batch)` → adjust discrete/continuous params using UCB bandit step.
* `tuner.cma_es_iter(population)` → evolve continuous parameters with CMA-ES.
* `tuner.pref_fit(pairs)` → fit a preference model and emit thresholds / updated weights.

These tool names, signatures, and semantics are **version-scoped** and may change between versions.

---

## 3) `/architect` — REST API for Textual Feedback → Commit

The Architect is now **REST**, not MCP. There is no MCP discovery for this surface; instead, clients interact with a standard HTTP endpoint.

### Endpoint

* **URL**: `/agent/{versions}/architect/chat`
* **Method**: `POST`
* **Auth**: Same as MCP servers (Bearer or OAuth2).
* **Semantics**:

  * Accepts free-text feedback and optional attachments.
  * May inspect logs, state, and evaluations (e.g., via internal access to `logs://`, `state://`, `eval://`).
  * May:

    * ignore the feedback and keep the current version,
    * adjust internal state of Runner/Tuner without code changes, or
    * commit code/config changes, bump semver, and update `/versions`.

The Architect is allowed to be conservative: **“reject”** is a normal outcome.

### Request Body JSON Schema

Identical payload semantics as previous MCP tool, but now documented as the HTTP request body:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://specs/architect.chat.input.json",
  "type": "object",
  "required": ["message"],
  "properties": {
    "message": {
      "type": "string",
      "description": "Free-text critique, request, or high-level governance instruction."
    },
    "attachments": {
      "type": "array",
      "description": "URIs to logs, eval diffs, or artifacts relevant to the feedback.",
      "items": {
        "type": "string",
        "format": "uri"
      }
    },
    "dry_run": {
      "type": "boolean",
      "description": "If true, Architect should simulate changes and report what *would* happen without committing.",
      "default": false
    }
  },
  "additionalProperties": false
}
```

### Response Body JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://specs/architect.chat.output.json",
  "type": "object",
  "required": ["result"],
  "properties": {
    "result": {
      "type": "string",
      "enum": ["committed", "tuned", "rejected"],
      "description": "'committed' = code/config change + semver bump; 'tuned' = internal state updated only; 'rejected' = no change."
    },
    "new_version": {
      "type": "string",
      "pattern": "^\\d+\\.\\d+\\.\\d+$",
      "description": "New semantic version tag, if a bump occurred. Absent or null if unchanged."
    },
    "commit_hash": {
      "type": "string",
      "description": "Git commit hash associated with the change, if any."
    },
    "notes": {
      "type": "string",
      "description": "Human-readable explanation of what happened and why."
    }
  },
  "additionalProperties": false
}
```

---

## 4) `/versions` — Version Manager (REST API)

The Version Manager is a **REST read API** that exposes information about available versions. It is independent of any particular version (no `{version}` path segment).

### Endpoint

* **URL**: `/versions`
* **Method**: `GET`
* **Auth**: Typically the same as other endpoints (Bearer/OAuth2); can be read-only public if desired.
* **Query parameters** (optional, illustrative):

  * `limit` (integer, default e.g. 50): max number of versions to return.
  * `offset` (integer, default 0): pagination offset.
  * `include_unstable` (boolean): whether to include versions that failed some tests or are marked pre-release.
  * `since` (RFC3339 datetime): filter to versions created after a given timestamp.

### Response Body (Conceptual Shape)

Returns a list of version descriptors plus some metadata about the listing.

**Example JSON (informal)**

```json
{
  "versions": [
    {
      "version": "1.6.0",
      "commit_hash": "982daa",
      "created_at": "2025-06-10T12:34:56Z",
      "changelog_uri": "https://changelogs/1.6.0.md",
      "tests": {
        "status": "pass",
        "last_run": "2025-06-10T12:30:00Z",
        "summary_uri": "s3:/-evals/1.6.0/summary.json"
      },
      "tags": ["stable", "production"]
    },
    {
      "version": "1.5.3",
      "commit_hash": "eda3322",
      "created_at": "2025-05-20T09:15:00Z",
      "changelog_uri": "https://changelogs/1.5.3.md",
      "tests": {
        "status": "pass",
        "last_run": "2025-05-20T09:10:00Z"
      },
      "tags": ["stable", "previous-default"]
    }
  ],
  "pagination": {
    "limit": 50,
    "offset": 0,
    "total_estimate": 12
  }
}
```

### Response JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://specs/version_manager.output.json",
  "type": "object",
  "required": ["versions"],
  "properties": {
    "versions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["version", "commit_hash"],
        "properties": {
          "version": {
            "type": "string",
            "pattern": "^\\d+\\.\\d+\\.\\d+$",
            "description": "Semantic version identifier."
          },
          "commit_hash": {
            "type": "string",
            "description": "Git commit hash backing this version."
          },
          "created_at": {
            "type": "string",
            "format": "date-time",
            "description": "Creation or publish time of this version."
          },
          "changelog_uri": {
            "type": "string",
            "format": "uri",
            "description": "Optional URI to a human-readable changelog for this version."
          },
          "tests": {
            "type": "object",
            "description": "Summary of test status for this version.",
            "properties": {
              "status": {
                "type": "string",
                "enum": ["pass", "fail", "unknown"],
                "description": "Aggregate test result."
              },
              "last_run": {
                "type": "string",
                "format": "date-time",
                "description": "Time when tests were last run."
              },
              "summary_uri": {
                "type": "string",
                "format": "uri",
                "description": "Optional URI to detailed eval or test report."
              }
            },
            "additionalProperties": false
          },
          "tags": {
            "type": "array",
            "description": "Free-form labels (e.g., 'stable', 'canary').",
            "items": {
              "type": "string"
            }
          },
          "runner": {
            "type": "object",
            "description": "Runner MCP endpoint information.",
            "properties": {
              "mcp_endpoint": {
                "type": "string",
                "description": "Path for the Runner MCP server for this version."
              }
            },
            "additionalProperties": false
          },
          "tuner": {
            "type": "object",
            "description": "Tuner MCP endpoint information.",
            "properties": {
              "mcp_endpoint": {
                "type": "string",
                "description": "Path for the Tuner MCP server for this version."
              }
            },
            "additionalProperties": false
          },
          "architect": {
            "type": "object",
            "description": "Architect REST endpoint information.",
            "properties": {
              "rest_endpoint": {
                "type": "string",
                "description": "Path for the Architect REST chat endpoint for this version."
              }
            },
            "additionalProperties": false
          }
        },
        "additionalProperties": false
      }
    },
    "pagination": {
      "type": "object",
      "description": "Pagination metadata for this listing.",
      "properties": {
        "limit": {
          "type": "integer",
          "minimum": 0
        },
        "offset": {
          "type": "integer",
          "minimum": 0
        },
        "total_estimate": {
          "type": "integer",
          "minimum": 0,
          "description": "Estimated total number of versions available."
        }
      },
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

---

## Client Guidance

* For **MCP clients**:

  * Always perform **discovery** on `/runner` and `/tuner` for a given `{version}` before use.
  * Treat Tuner APIs as **private to the version**; do not assume cross-version stability.
  * Prefer `runner` tools (e.g. `runner.chat`, `runner.get_weather`, or `runner.handle_query` if present) for production queries.
  * Use `/tuner` only when you have structured feedback (e.g. bandit rewards, preference pairs).

* For **governance / evolution**:

  * Send high-level feedback to `POST /agent/{versions}/architect/chat`.
  * Use `/versions` to:

    * discover available versions and their test status,
    * decide which `{version}` to pin to,
    * inspect the relationship between semver tags, commit hashes, and stability tags.
