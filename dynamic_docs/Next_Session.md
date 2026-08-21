<!-- Purpose: Claude's handoff note -- what to pick up, open questions, and suggested first steps for the next session. Written by Claude at session end. -->

## Pick up here

**The next session is Stage 1 of the migration, and it runs in Claude Code, not here.** Read `Claude_Code_Migration_Plan.md` in the project root first -- the Scope section, then Stage 1. Do not read ahead into later stages.

Before Claude Code touches anything, the current state needs a clean commit to revert to. That is what this session's own commit provides.

### Stage 1 specifics

- Four structural moves plus one launcher fix, all listed in the plan. The largest is renaming `core/` to `chartgen/`, which updates every import across roughly 100 modules.
- **Change 5 has a gate inside it.** Reconcile `requirements.txt` against the hardcoded package list in `run_chartgen.bat`, show Aidan the result, and wait for confirmation before repointing the `.bat` to read from it. `requirements.txt` has never been read and may be stale or incomplete; repointing blind would break first-run setup for anyone with no venv.
- Changes 4 and 5 are behavioural changes to `run_chartgen.bat`. Permission is granted for those two specifically and nothing else.
- The final step of Stage 1 is updating the paths inside the plan file itself to match the new layout. Stage 3's package `CLAUDE.md` table still uses `core/` paths and will need correcting there.
- Verify by hand at the end: launch the app and confirm it runs. An import rename across 100 files is mechanical but dynamic imports and string-based paths are not always caught.
- Commit Stage 1 on its own, before Stage 2 begins.

### Open items on the plan

1. Whether `.claude/rules/` path-scoped rules are adopted -- deferred, not urgent.
2. What replaces the Wake up, Close-down and Scrap Session protocols. `dynamic_docs/` is deleted at the end of Stage 2, which removes what Wake up currently reads, so this needs settling before then.
3. Lead surface for Stages 2 and 3 is provisional -- confirm after Stage 1 completes.

### Not agreed yet

The five standing rules proposed for the root `CLAUDE.md` (plan, Stage 3) are Claude's extraction from the existing documents, not a list Aidan wrote. They are unreviewed. Their approval gates Stage 4, because the bulk docstring strip is what removes their only current home.

## This session's work, for context

Design only. No code changed, no governed document changed.

Reviewed the codebase and the six governed documents to plan the move to Claude Code, then produced and agreed a five-stage plan. The plan was rewritten once mid-session: the first version carried its own justification and context, which Aidan identified as the same failure mode being migrated away from. Stripped to roughly a third of its length, and a test for keeping a line was added to Stage 4 as a result -- does it change what gets done.
