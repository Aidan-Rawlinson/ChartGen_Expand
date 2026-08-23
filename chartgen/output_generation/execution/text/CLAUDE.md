# text

`update_text` resolves every tag family from one combined token dict, in ordinary text frames and in PowerPoint table cells alike. A table cell exposes the same text-frame interface, so both go through the same paragraph walk.

## Stat Tags

A Stat Tag is a short, permanent, system-issued id standing in for one summary-stats value from one chart's own cut of its cached data.

**Anchored on `hex_id`, never `chart_ref`.** `chart_ref` renumbers whenever the manifest table changes and is never a storage key. Nothing rewrites tag text already placed in a template, so an anchor that renumbers would silently start pointing at another chart's data.

**`populations` is a single token, not a populations string.** A tag resolves to exactly one value, so it needs exactly one population. The authoring control is a single select, not a multiselect.

**A dynamic peer token is stored unresolved.** `Region()` means "the selected unit's own group" and resolves fresh, against the current reporting unit, every time. Storing the resolved value would freeze it to whichever unit happened to be selected when the tag was made. `Region(Wales)` is a static explicit value and is a different thing.

Display shows a dynamic token alongside its currently resolved value, and a static one as it stands, because the two behave differently.

Storage is a flat table, one row per tag. Several tags sharing the same underlying cut each repeat those fields independently. There is no shared cut object.

An unresolvable tag resolves to "unresolved" silently. That is deliberate: a tag pointing at a period a report does not have is an expected state, not an error.
