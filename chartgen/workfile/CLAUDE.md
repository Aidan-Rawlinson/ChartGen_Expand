# workfile

`state/workfile_file.py` owns the `.cgw` format and is the only module that reads or writes the ZIP. Nothing else opens it.

`WorkfileState` is the only real state in the system. `AssemblyContext`, `ReportContext` and population-filtered shape lists are rebuilt from it on every run and are never sources of truth.

Anything mutating `WorkfileState` sets `dirty` itself. Helpers that mutate `settings` in place, such as id issuing, leave that to the caller.

`dirty` and `read_only` are session-only and are not persisted.

## Creation and population are separate

`setup/new_workfile.py` makes a blank `.cgw`: file, description, settings scaffold. It has no knowledge that population tables exist, that they ever will, or what a toolkit project is. Population tables are built by the toolkit packages, triggered from a chart fetch. Do not couple the two.

## Locking

The lock is advisory. `locked_by` and `locked_at` live inside `workfile_info.json`, written on Open and cleared on Close. A Read-Only session never writes the lock and therefore never clears one.

A lock may be stale after a crash, with no way to tell a live lock from an orphan, so Open always offers a choice rather than blocking. Last write wins if two people both choose Open and both save.

Read-only enforcement is shallow by design: Save is disabled, everything else behaves normally.

## Version compatibility

A workfile whose file version id is not in this build's readable list is refused at Open. No partial read, no migration attempt. See `shared/infrastructure/CLAUDE.md`.
