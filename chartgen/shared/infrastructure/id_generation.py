"""
id_generation.py
Base-36 id helper. Issues short, permanent, never-reused ids from a
persisted, monotonically increasing counter.

Each id store keeps its own counter under its own settings key. Only the
digit encoding and the uniqueness check are shared.

An id can arrive from the user as well as from the system. Every id space
here has an Excel round trip, and a person editing that spreadsheet may
type whatever ids suit them -- "AB1, AB2, AB3" then "AC1, AC2, AC3" is a
natural way to number tabular material. So the counter cannot be assumed
to know about every id in use, and the system's job when issuing a new one
is to avoid what is already there rather than to predict it.

next_unique_id does that by checking, not by inferring. It parses nothing,
so a hand-typed id in any form at all is respected.
"""

TAG_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


def to_base36(n: int) -> str:
    if n == 0:
        return "0"
    digits = []
    while n:
        n, rem = divmod(n, 36)
        digits.append(TAG_ALPHABET[rem])
    return "".join(reversed(digits))


def next_id(settings: dict, counter_key: str) -> str:
    """
    Issue and persist the next base-36 id under the given settings counter
    key. Mutates settings in place — caller is responsible for marking the
    workfile dirty.

    Takes no account of what is already in use. Callers issuing an id that
    has to be unique want next_unique_id instead.
    """
    n = int(settings.get(counter_key, "0") or "0") + 1
    settings[counter_key] = str(n)
    return to_base36(n)


def next_unique_id(settings: dict, counter_key: str, prefix: str, ids_in_use) -> str:
    """
    Issue and persist the next id under counter_key, prefixed, skipping any
    candidate already in ids_in_use.

    Uniqueness is checked rather than inferred. Nothing here parses an id,
    so an id typed by hand in any form is honoured — including one that is
    not base-36 at all, which an approach based on decoding ids would have
    to ignore.

    Compared case-insensitively. A Stat Tag is matched in a template by its
    exact literal text, so issuing "ab1" alongside a user's "AB1" would
    create two ids a person reads as one.

    The counter only ever advances, so it is never recomputed from
    surviving rows and an id is never reissued after its row is deleted.
    A candidate that is already taken still consumes its counter value.

    ids_in_use is required, with no default. A caller that cannot say what
    is in use cannot be given a guaranteed-unique id, and should fail here
    rather than silently skip the check.

    The loop is bounded by len(ids_in_use) + 1: each iteration either
    returns or rules out one of the ids in use, so it cannot run away.
    """
    taken = {str(i or "").strip().casefold() for i in ids_in_use}
    while True:
        candidate = prefix + next_id(settings, counter_key)
        if candidate.casefold() not in taken:
            return candidate
