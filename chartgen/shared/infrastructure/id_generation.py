"""
id_generation.py
Base-36 id helper. Issues short, permanent, never-reused ids from a
persisted, monotonically increasing counter.

Each id store keeps its own counter under its own settings key. Only the
digit encoding is shared.
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
    """Inverse of to_base36. Used to resync a counter against ids already in
    use, since a row imported with its id already filled in never advances
    the counter."""
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
