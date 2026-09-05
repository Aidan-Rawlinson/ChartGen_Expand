"""
render_memo.py
A single-entry memo for a preview surface's rendered image, so a redraw
happens when something that determines the picture changes and not
otherwise.

Streamlit reruns the whole script on every interaction. A preview that
calls its Base Chart or Base Table function unconditionally therefore
redraws for things that cannot change the picture at all: picking a Save
target row, changing Zoom, opening an expander, saving to the Running
Order. Each of those costs a full render -- 110-170ms for a table, 70-110ms
for a chart, and about another 100ms for every {Cn} chart cell a table
carries.

The signature is the whole of the correctness argument. A caller builds it
from the arguments the render is about to be given, never from something
that stands in for them, because a missed input shows a stale picture with
no error -- the opposite of the standing fail-visibly rule.

Invalidation needs no code here. Both cache keys carry a per-tab prefix
("cs_", "ots_"), and Reset, Open and Close already delete every session key
under those prefixes.
"""

import hashlib

import streamlit as st


def render_signature(*parts) -> str:
    """
    Hash the render's own arguments into a signature string. repr() is
    used deliberately: it is complete and deterministic across the plain
    containers and dataclasses these arguments are made of, and it costs
    a fraction of the render it guards.
    """
    return hashlib.sha256(repr(parts).encode("utf-8")).hexdigest()


def remember_render(cache_key: str, signature: str, produce, identity=None):
    """
    Return the remembered value when both the signature and identity match
    what produced it; otherwise call produce(), remember its result and
    return that.

    identity is the built-in registry function this render will call, or
    None when the code being rendered is compiled from source text. It is
    compared with `is`, not by value, and it exists for one case the
    signature cannot cover: Streamlit's watcher evicts and re-imports a
    changed local module, so editing a built-in Base Chart or Base Table
    under a running app produces a new function object under the same
    name, with every signature input unchanged. Holding the object keeps
    that comparison meaningful, which comparing id() would not.

    Compiled custom code needs no identity, and must not use one: it
    compiles to a new function object on every run, which would never
    match. Its source text is in the signature instead, and that is what
    determines the compiled result.

    A failing produce() is not remembered, so the error surfaces on this
    run and on every run after it until the cause is fixed.
    """
    memo = st.session_state.get(cache_key)
    if (
        memo is not None
        and memo["signature"] == signature
        and memo["identity"] is identity
    ):
        return memo["value"]

    value = produce()
    st.session_state[cache_key] = {
        "signature": signature, "identity": identity, "value": value,
    }
    return value
