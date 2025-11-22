The flows of the execution of scalable-godel is as follows:

## First Run

1. The Architect sets up a git repo in the `{agent_dir}` subfolder (for the first time, this is `ROOT`). This will be the working director for everything. The Architect is not authorized to work outside of it
2. The Architect, which uses Codex under the hood, designs two Python files (which might involve designing helper files): the Runner and the Architect. Both of these are MCP servers
3. The two entrypoints are always in `{agent_dir}/runner.py` and `{agent_dir}/tuner.py`. They can be run by calling, in the workdir, `python runner.py [runner_port]` and `python tuner.py [tuner_port] [architect_port]`
4. The runner also designs the schema (`{agent_dir}/state_schema.json`) of the state file, which is stored in `{agent_dir}/schema.json`
5. The Runner and the Architect have access to a Python helper library that handles stuff like concurrent access to the state and boilerplate/helper code for running well
6. (Optionally) The Architect designs `{agent_dir}/tests.py`, which fundamentally is just a pytest file
7. The Architect makes the first commit and renames `ROOT` to the commit hash
8. The Architect launches the Runner and the Tuner, which can now expose their APIs
9. After this, the Architect is done and becomes idle


Note: you might wanna expose a special method for the Architect which is done for "create from scratch" (this flow).

Note: when initializing, there is a `metadata.json` file that contains a single field: the current version of the agent. ROOTs always start at 0.0.0.

Note: the state is not tracked in git.

Any logs are saved in `{agent_dir}/logs/`.

## Runner

This is done in a straightforward manner and simply involves exposing MCP tools. The specific execution heavily depends on the design of the server.

## Tuner

The Tuner will most likely expose some sort of structured feedback endpoint. Typically, this will involve changing the state, which can be done with the helper library. The helper library also provides a convenience method that sends a message to the Architect. This is useful when the Tuner wants to call the Architect (e.g. due to very negative feedback)

## Architect - Subsequent Steps

If the Architect receives textual feedback, everything is copied in `{agent_dir}-staging` (including the .git). Codex is launched in `{agent_dir}-staging` and it makes whatever updates it thinks are necessary (if any).
If the update only concerns the state, the Architect only updates the state in the original file. The staging dir is then deleted.

If the update concerns code (and potentially the state too) and tests pass, Codex makes a commit and updates metadata.json (with semver). The commit is pushed to the repo. The staging dir is then renamed to the new commit hash. The Architect, like before, launches the new Runner and Tuner.

Important: Architect calls are sequential w.r.t. a certain dir, in the sense that you can't run this process twice at the same time on the same dir.


## Notes

- Old versions will intentionally keep an outdated version of the repo. This is intentional
- It is possible that multiple versions will branch off into variants (each with potentially the same version number). That's ok
