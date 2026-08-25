# text

`update_text` resolves every tag family from one combined token dict, in ordinary text frames and in PowerPoint table cells alike. A table cell exposes the same text-frame interface, so both go through the same paragraph walk.

## Report level tags

`REPORT_TEXT_TAGS` in `report_tags.py` is the definition of these tags, not a description of behaviour implemented elsewhere. One entry per tag, carrying its literal text, the description shown to the user, and how it resolves.

Every surface reads that list: the Text tab's table renders it, `update_text` builds tokens from it, and Output Table cell resolution does too. Nothing else names a tag or a description. **Removing an entry therefore stops that replacement happening anywhere, with no other change, and adding one makes it appear on the Text tab and work in the same edit.** A tag that displays but does nothing, or works but is undiscoverable, is not reachable from here. That is the point of the list, and it is why the Text tab's table has no tag strings in it.

`[code]` is deliberately the same literal `insert_picture` substitutes into an image path, from the same `ReportContext` field. Two separate mechanisms on two different things: `update_text` walks slide text and table cells, `insert_picture` rewrites a Running Order path. Removing the list entry here stops the text replacement and leaves the path token working.

`resolve` returns `None` to mean the tag cannot be resolved for this report, and the token is then omitted so the literal text survives in the deck. Only the unit name does that, when no reporting unit is selected. Values are read at resolution time, so a date resolves per report rather than once per run.

## Stat Tags

A Stat Tag is a short, permanent, system-issued id standing in for one summary-stats value from one chart's own cut of its cached data.

**Anchored on `hex_id`, never `chart_ref`.** `chart_ref` renumbers whenever the manifest table changes and is never a storage key. Nothing rewrites tag text already placed in a template, so an anchor that renumbers would silently start pointing at another chart's data.

**`populations` is a single token, not a populations string.** A tag resolves to exactly one value, so it needs exactly one population. The authoring control is a single select, not a multiselect.

**A dynamic peer token is stored unresolved.** `Region()` means "the selected unit's own group" and resolves fresh, against the current reporting unit, every time. Storing the resolved value would freeze it to whichever unit happened to be selected when the tag was made. `Region(Wales)` is a static explicit value and is a different thing.

Display shows a dynamic token alongside its currently resolved value, and a static one as it stands, because the two behave differently.

Storage is a flat table, one row per tag. Several tags sharing the same underlying cut each repeat those fields independently. There is no shared cut object.

An unresolvable tag resolves to "unresolved" silently. That is deliberate: a tag pointing at a period a report does not have is an expected state, not an error.
