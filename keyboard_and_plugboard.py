# keyboard_and_plugboard.py
from __future__ import annotations

from collections.abc import Sequence
from debug import Debug

debug = Debug()
debug.disable("plugboard")


# ── Keyboard ──────────────────────────────────────────────────────
class Keyboard:
    def __init__(self, alphabet: str) -> None:
        self.alphabet: str = alphabet
        self.alpha_to_index: dict[str, int] = {
            ch: i for i, ch in enumerate(alphabet)
        }

    # letter → integer signal
    def forward(self, letter: str) -> int:
        try:
            return self.alpha_to_index[letter]
        except KeyError:
            raise ValueError(
                f"Invalid character {letter!r} for current alphabet."
            )

    # integer signal → letter
    def backward(self, signal: int) -> str:
        if not (0 <= signal < len(self.alphabet)):
            hi = len(self.alphabet) - 1
            raise ValueError(f"Signal {signal} out of range 0–{hi}")
        return self.alphabet[signal]


# ── Plugboard ─────────────────────────────────────────────────────
class Plugboard:
    def __init__(
        self,
        pairs: Sequence[str | tuple[str, str]],
        alphabet: str,
    ) -> None:
        self.alphabet: str = alphabet
        self.mapping: dict[str, str] = {ch: ch for ch in alphabet}
        used: set[str] = set()

        for raw in pairs:
            # normalise to (a, b)
            if isinstance(raw, str):
                if len(raw) != 2:
                    raise ValueError(f"Pair {raw!r} must be exactly 2 symbols")
                a, b = raw
            else:
                a, b = raw

            if a == b:
                raise ValueError(f"Plugboard cannot map a symbol to itself: {a}")
            if a in used or b in used:
                dup = a if a in used else b
                raise ValueError(f"Character {dup!r} already used in plugboard")
            if a not in alphabet or b not in alphabet:
                bad = a if a not in alphabet else b
                raise ValueError(f"Symbol {bad!r} not in alphabet")

            # passed validation → commit swap
            self.mapping[a], self.mapping[b] = b, a
            used.update((a, b))

    # one private helper does the job for both directions
    def _map(self, signal: int) -> int:
        letter = self.alphabet[signal]
        mapped = self.mapping[letter]
        debug.log("plugboard", f"{signal}->{letter}->{mapped}")
        return self.alphabet.index(mapped)

    forward = _map        # alias: signal in
    backward = _map       # alias: signal out

    # nicety for debugging
    def __repr__(self) -> str:
        swaps = [f"{a}{b}" for a, b in self.mapping.items() if a < b]
        return f"<Plugboard {' '.join(swaps)}>"