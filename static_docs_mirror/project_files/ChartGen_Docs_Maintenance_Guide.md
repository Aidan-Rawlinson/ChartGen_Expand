# ChartGen — Documentation Maintenance Guide

*TBN Internal · Process instructions for Claude, governing edits to the other six documents during refactoring. Not a domain document — contains no facts about ChartGen.*

---

## 1. Purpose

The six reference documents are ground truth for the refactor, edited across many sessions and Claude instances. Read this before editing any of them.

---

## 2. The Code/Documentation Relationship

Not every code change requires a documentation change. Deleting dead code, removing unused paths, or internal tidying with no visible change in behaviour, structure, or naming needs no doc update — there was nothing documented there. Exception: if the change resolves an entry in `Refactoring_issues_known.md`, update or remove that entry.

Any change that alters documented behaviour, structure, or naming needs a documentation update eventually — a renamed class, a changed schema, a resolved gap, a newly-built feature. Test: does this change touch a fact one of the six documents currently states.

Documentation updates happen in discrete steps, on the user's command — not continuously alongside code changes. Sequence: code change → test if needed → documentation update as its own requested step.

If a round of code changes is finishing, or the session appears to be ending, and a documentation-relevant change hasn't been written up yet, say so explicitly before moving to new work or closing out.

---

## 3. Before Writing Anything

**Step 1 — Route it.** Name the one document that owns the fact:

| If the change is about... | It belongs in... |
|---|---|
| Runtime behaviour | Functional Spec |
| Storage, structure, package boundaries | Architecture |
| Scope and readiness (built / partial / not built) | Feature List |
| Naming and taxonomy | Glossary |
| Domain rationale, design intent | Primer |
| A deferred problem or known gap | Refactoring Issues |

If a change seems to need a sentence in two documents, find the single right home instead of writing it twice.

**Step 2 — Check what's already there.** Before adding new text, check whether the owning document already covers this nearby. Edit in place rather than adding a new paragraph next to existing coverage.

**Step 3 — Cross-reference, don't restate.** Other documents touching the same fact get a pointer (e.g. `See Functional Spec §10.4`), never a restatement. If explaining the fact seems necessary to make a point land elsewhere, move the fact to that document instead of duplicating it.

---

## 4. Ground Truth Discipline

- Check the actual code before editing a document for any refactor-driven update. Never update a document based on what an earlier document-editing session said should happen.
- Present tense, current state only. If a refactor step hasn't landed in code, it stays in Refactoring Issues, not in the other five documents.
- Test for inclusion: is this a fact about ChartGen, or a fact about the documents/process. The latter doesn't belong in the six documents — raise it in chat instead.

---

## 5. Primer Is Edit-Locked

Never modify `ChartGen_Primer.md` without explicit permission for that specific change, even when a rename or refactor step elsewhere seems to imply it should follow suit. Propose changes to it separately and wait for approval.

---

## 6. Style Discipline

- No examples unless the user asks for one.
- Definitions state what a term is; justification/rationale belongs in Architecture (decision) or Primer (rationale), not folded into the definition.
- Match surrounding density — a one-line change gets a one-line edit.
- No explanation of how normal software works generally (ZIP archives, lock files) — ChartGen-specific behaviour only.
- Tables over prose for repeating-shape content (features, columns, decisions); extend the Notes column rather than converting a row to prose.
- Declarative, present tense, no roadmap language — except in Refactoring Issues, which is entirely future work by design.

---

## 7. Change Hygiene

- Show every proposed change as a diff or clear summary and wait for explicit approval before applying it.
- Edit one document per pass where possible. Flag unrelated issues noticed in a document rather than fixing them unasked.
- If content is uncertain or belongs elsewhere, delete it and flag the gap rather than leaving a hedged version in place.

---

## 8. Mid-Session Writes (MCP Environment)

- Once a proposed change to any of the six documents is approved (Section 7), write it immediately to the mirror copy in `static_docs_mirror/project_files` — don't hold approved edits in conversation memory pending session Close-down.
- Once a document's mirror copy has been written to mid-session, it is ahead of the Project Files version visible in Claude Desktop, which only updates when the user re-uploads it at Close-down. Diff any further edit to that document later in the same session against the current mirror copy, not the version originally supplied in context.
- This section governs writes that happen during a session's work. It does not alter the Session Start or Close-down protocols — Close-down's mirror step remains a verification pass, confirming the mirror matches what was approved, not the first point of writing.
