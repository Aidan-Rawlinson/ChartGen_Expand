"""
id_generation.py
Shared base-36 id helper — issues short, permanent, never-reused ids from a
persisted, monotonically increasing counter. Used by Stat Tags
(settings["next_stat_tag_id"]) and Output Tables
(settings["next_table_id"]) alike; each store keeps its own counter under
its own settings key — only the digit-encoding is shared, so a deleted row
in one store can never free up an id another store might reissue.
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


def from_base36(s: str) -> int:
    """Inverse of to_base36 -- decodes a base-36 string back to its integer
    value. Used defensively wherever an id's own persisted counter might
    have fallen out of sync with ids actually already in use elsewhere
    (e.g. rows carried in from an external source with their own ids
    already filled in, which never advances the counter itself)."""
    n = 0
    for ch in s.lower():
        n = n * 36 + TAG_ALPHABET.index(ch)
    return n


def next_id(settings: dict, counter_key: str) -> str:
    """
    Issue and persist the next base-36 id under the given settings counter
    key. Mutates settings in place — caller is responsible for marking the
    workfile dirty.
    """
    n = int(settings.get(counter_key, "0") or "0") + 1
    settings[counter_key] = str(n)
    return to_base36(n)
