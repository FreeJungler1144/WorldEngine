# rotor_and_reflector.py
from __future__ import annotations
from debug import Debug

debug = Debug()
debug.disable("stepping")


class Rotor:
    def __init__(self, wiring: str, notches: str, alphabet: str) -> None:
        if sorted(wiring) != sorted(alphabet):
            raise ValueError("wiring must be a permutation of alphabet")

        self.alphabet = alphabet
        self.size = len(alphabet)

        # integer lookup tables
        self._fwd = [alphabet.index(c) for c in wiring]
        self._rev = [wiring.index(c) for c in alphabet]

        self.notches = set(notches)
        self.position = 0
        self.ring_setting = 0

    # ── ring & notch helpers ──────────────────────────────────────
    def set_ring(self, ring: int) -> "Rotor":
        self.ring_setting = (ring - 1) % self.size
        return self

    def set_notches(self, notches: str) -> "Rotor":
        if not set(notches) <= set(self.alphabet):
            raise ValueError("Notch characters must be in the alphabet")
        self.notches = set(notches)
        return self

    # ── stepping --------------------------------------------------
    def _rotate(self, steps: int = 1) -> None:
        self.position = (self.position + steps) % self.size

    def step(self) -> bool:
        """Advance one and return True on *roll-over* (turnover)."""
        self._rotate(1)
        hit = self.alphabet[self.position] in self.notches
        debug.log("stepping", f"Rotor pos {self.position}, notch_hit={hit}")
        return hit

    # ── signal paths ---------------------------------------------
    def forward(self, sig: int) -> int:
        shift = (sig + self.position - self.ring_setting) % self.size
        mapped = self._fwd[shift]
        return (mapped - self.position + self.ring_setting) % self.size

    def backward(self, sig: int) -> int:
        shift = (sig + self.position - self.ring_setting) % self.size
        mapped = self._rev[shift]
        return (mapped - self.position + self.ring_setting) % self.size

    # ── niceties --------------------------------------------------
    def __repr__(self) -> str:
        return f"<Rotor pos={self.position} ring={self.ring_setting}>"


class Reflector:
    def __init__(self, wiring: str, alphabet: str) -> None:
        if len(wiring) != len(alphabet):
            raise ValueError("Reflector wiring length must match alphabet length")

        # ensure involution property (w[i] = j ⇒ w[j] = i) and no self-maps
        for i, c in enumerate(wiring):
            j = alphabet.index(c)
            if wiring[j] != alphabet[i] or i == j:
                raise ValueError("Reflector wiring must be an involution with no fixed points")

        self.alphabet = alphabet
        self.size = len(alphabet)
        self._map = [alphabet.index(c) for c in wiring]
        self.position = 0  # rotational offset

    def rotate_to_letter(self, L: str) -> None:
        if L not in self.alphabet:
            raise ValueError(f"Reflector cannot rotate to {L!r}: not in alphabet")
        self.position = self.alphabet.index(L)

    def reflect(self, sig: int) -> int:
        adjusted = (sig + self.position) % self.size
        mapped = self._map[adjusted]
        return (mapped - self.position) % self.size

    def __repr__(self) -> str:
        return f"<Reflector pos={self.position}>"