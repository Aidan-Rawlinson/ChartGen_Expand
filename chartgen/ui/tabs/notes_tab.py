"""
notes_tab.py
"Notes" tab (page header: "Project/Workfile Notes") — a shared, free-form
scratchpad for the team, stacked vertically, reorderable, each note
editable and deletable in place.

Each note is a heading (optional, bold) plus a main text (required), shown
as plain text — st.text_area only appears for the note currently being
edited (toggled by its edit button) — with an attribution line directly
underneath in a smaller, grey font.

The view-mode action buttons (edit/up/down/delete) are pinned to the
bottom-right corner of the note's text block with CSS position:absolute,
not aligned via st.columns(vertical_alignment=...). That was tried first
and measured — via getBoundingClientRect in a throwaway repro, not guessed
— to consistently misalign by exactly the height of the attribution line:
Streamlit's column cross-alignment did not account for the final rendered
height of the raw-HTML markdown block. Absolute positioning against a
position:relative wrapper only depends on that wrapper's own computed
height, which doesn't have that problem, and was verified pixel-perfect
(0px difference, both bottom- and top-anchored) before landing here. Edit
mode doesn't need any of this: there's no attribution line to align
against, so its Done button just sits in ordinary flow, right-aligned.

Two nested containers do two separate spacing jobs that used to share one
gap=0 container and fought each other: the outer keeps the title tight
against the (collapsed-by-default) add-note expander; the inner gives the
notes list its own small gap plus a real tight_divider() between notes, so
notes read as visually separate rather than one run-together block.

Spacing otherwise uses st.container's/st.columns' own gap= parameter rather
than injected CSS wherever that reaches, per chartgen/ui/CLAUDE.md's
preference for native Streamlit controls over custom styling. Button size
and the view-mode button positioning are the two exceptions: Streamlit has
no built-in "small button" parameter, nor a native way to pin one element
to another's corner, so the whole tab body sits in a keyed container
(st.container(key=...) gives it a stable "st-key-<key>" class — Streamlit's
own documented mechanism) and small CSS rules scoped to that class handle
both. Same narrow exception chartgen/ui/common/layout_css.py documents for
the sidebar, applied here for the same reason: no native parameter reaches
it.

Notes live on the workfile (WorkfileState.notes_rows) and travel and save
the same way as everything else in it: only on explicit Save, and
last-write-wins if two people have the workfile open at once.
"""

import html
from datetime import datetime, timezone

import streamlit as st

from chartgen.shared.infrastructure.id_generation import next_id
from chartgen.ui.common.formatting import format_uk_time
from chartgen.ui.common.guidance import render_tab_header
from chartgen.workfile.state.session_state import notes, settings, ws

# Reserved as padding-right on the note-text block so it wraps clear of the
# absolutely-positioned button group rather than running under it. A bit
# more than the measured 4-button group width (~129px at the CSS below).
_ACTIONS_WIDTH_PX = 145

_TAB_CSS = f"""
<style>
.st-key-notes_tab_root button {{
    padding: 0.1rem 0.35rem !important;
    min-height: 1.4rem !important;
    font-size: 0.8rem !important;
}}
.st-key-notes_tab_root [class*="st-key-nt_wrap_"] {{
    position: relative;
}}
.st-key-notes_tab_root [class*="st-key-nt_actions_"] {{
    position: absolute !important;
    right: 0;
    bottom: 0;
    width: max-content !important;
}}
</style>
"""


def render_notes_tab():
    with st.container(key="notes_tab_root", gap=0):
        st.markdown(_TAB_CSS, unsafe_allow_html=True)
        render_tab_header("Project/Workfile Notes", "notes")

        workfile_state = ws()
        username = st.session_state.get("username", "")

        _render_add_note(workfile_state, username)

        # The outer container's gap=0 is for the title-to-box gap above;
        # a dedicated spacer here, rather than touching that shared gap
        # again, so this space is independent of it.
        st.markdown('<div style="height:40px;"></div>', unsafe_allow_html=True)

        note_rows = notes()
        if not note_rows:
            st.caption("No notes yet.")
            return

        with st.container(gap=0):
            for i, note in enumerate(note_rows):
                _render_note(workfile_state, note, i, len(note_rows), username)
                if i < len(note_rows) - 1:
                    # Local one-off, not the shared tight_divider(): the two
                    # sides need different margins (tighter above, next to
                    # the buttons; a bit more below, before the next
                    # heading), which a single shared default can't give.
                    st.markdown(
                        '<hr style="border:none;border-top:1px solid #ddd;margin:3px 0 22px 0;">',
                        unsafe_allow_html=True,
                    )


def _render_add_note(workfile_state, username):
    if st.session_state.pop("nt_clear_new", False):
        st.session_state["nt_new_heading"] = ""
        st.session_state["nt_new_text"] = ""

    with st.expander("Add a note", expanded=False):
        new_heading = st.text_input("New note heading", key="nt_new_heading",
                                     label_visibility="collapsed", placeholder="Heading (optional)")
        new_text = st.text_area("New note", key="nt_new_text", label_visibility="collapsed",
                                 placeholder="Write a note for the team…", height=68)
        if st.button("Add note", icon=":material/add:", type="primary",
                      disabled=not new_text.strip()):
            now = datetime.now(timezone.utc).isoformat()
            note_id = "N" + next_id(settings(), "next_note_id")
            workfile_state.notes_rows.insert(0, {
                "note_id": note_id,
                "heading": new_heading.strip(),
                "text": new_text,
                "added_by": username,
                "added_at": now,
                "edited_by": "",
                "edited_at": "",
            })
            workfile_state.dirty = True
            st.session_state["nt_clear_new"] = True
            st.rerun()


def _render_note(workfile_state, note, i, count, username):
    note_id = note["note_id"]
    heading = note.get("heading", "")
    editing_key = f"nt_editing_{note_id}"

    if st.session_state.get(editing_key, False):
        _render_note_editing(workfile_state, note, note_id, heading, editing_key, username)
    else:
        _render_note_view(workfile_state, note, note_id, heading, i, count, editing_key)


def _render_note_view(workfile_state, note, note_id, heading, i, count, editing_key):
    attribution = f"Added by {note['added_by']} on {format_uk_time(note['added_at'])}"
    if note["edited_at"]:
        attribution += f"  ·  edited by {note['edited_by']} on {format_uk_time(note['edited_at'])}"
    heading_html = (
        f'<div style="font-weight:600;font-size:1rem;">{html.escape(heading)}</div>'
        if heading else ""
    )

    with st.container(key=f"nt_wrap_{note_id}"):
        st.markdown(
            f'<div style="margin:0;padding-right:{_ACTIONS_WIDTH_PX}px;">'
            f'{heading_html}'
            f'<div style="font-size:0.75rem;white-space:pre-wrap;">{html.escape(note["text"])}</div>'
            f'<div style="color:#888;font-size:0.625rem;margin-top:0;">{html.escape(attribution)}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        with st.container(horizontal=True, gap="xxsmall", key=f"nt_actions_{note_id}"):
            if st.button("", icon=":material/edit:", key=f"nt_edit_{note_id}", help="Edit"):
                st.session_state[editing_key] = True
                st.rerun()

            if st.button("", icon=":material/arrow_upward:", key=f"nt_up_{note_id}",
                          disabled=(i == 0), help="Move up"):
                rows = workfile_state.notes_rows
                rows[i - 1], rows[i] = rows[i], rows[i - 1]
                workfile_state.dirty = True
                st.rerun()

            if st.button("", icon=":material/arrow_downward:", key=f"nt_down_{note_id}",
                          disabled=(i == count - 1), help="Move down"):
                rows = workfile_state.notes_rows
                rows[i + 1], rows[i] = rows[i], rows[i + 1]
                workfile_state.dirty = True
                st.rerun()

            if st.button("", icon=":material/delete:", key=f"nt_del_{note_id}", help="Delete"):
                del workfile_state.notes_rows[i]
                workfile_state.dirty = True
                st.rerun()


def _render_note_editing(workfile_state, note, note_id, heading, editing_key, username):
    edited_heading = st.text_input(
        "Heading", value=heading, key=f"nt_heading_{note_id}",
        label_visibility="collapsed", placeholder="Heading (optional)",
    )
    edited_text = st.text_area(
        "Note", value=note["text"], key=f"nt_text_{note_id}",
        label_visibility="collapsed", height=68,
    )
    with st.container(horizontal=True, horizontal_alignment="right"):
        if st.button("Done", icon=":material/check:", key=f"nt_done_{note_id}"):
            new_heading = edited_heading.strip()
            if edited_text != note["text"] or new_heading != heading:
                note["heading"] = new_heading
                note["text"] = edited_text
                note["edited_by"] = username
                note["edited_at"] = datetime.now(timezone.utc).isoformat()
                workfile_state.dirty = True
            st.session_state[editing_key] = False
            st.rerun()
