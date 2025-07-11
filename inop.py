# inop.py  ─────────────────────────────────────────────────────────
from __future__ import annotations

from debug import Debug

debug = Debug()
debug.disable("encypher")


class Inop:
    def __init__(
        self,
        kb, pb,
        rotors: list,
        reflector,
        ring_settings: list[int],
        master_key: str
    ) -> None:
        if len(ring_settings) != len(rotors):
            raise ValueError("ring_settings length mismatch")
        if len(master_key) != len(rotors) + 1:
            raise ValueError("master_key length mismatch")

        self.kb         = kb
        self.pb         = pb
        self.rotors     = rotors
        self.reflector  = reflector

        self.set_rings(ring_settings)
        self.set_key(master_key[:-1])
        self.reflector.rotate_to_letter(master_key[-1])

    # ── key & ring helpers ──────────────────────────────────────

    def set_rings(self, rings: list[int]) -> None:
        """Apply ring-stellung offsets (1-based) to every rotor."""
        for rotor, ring in zip(self.rotors, rings):
            rotor.set_ring(ring)

    def set_key(self, key_part: str) -> None:
        """Rotate each rotor to its visible window letter."""
        for rotor, letter in zip(self.rotors, key_part):
            rotor.position = rotor.alphabet.index(letter)

    # ── stepping logic  ─────────────────────────────────────────

    def _step_rotors(self) -> None:
        """Advance rotors one key-press according to suite rules."""

        if len(self.rotors) == 3:
            # --- historic 3-rotor double-step -------------------
            left, middle, right = self.rotors

            # decide which rotors step (two-phase clarity)
            step_L = middle.alphabet[middle.position] in middle.notches
            step_M = (step_L or right.alphabet[right.position] in right.notches)
            step_R = True

            if step_L:
                left.step()
            if step_M:
                middle.step()
            if step_R:
                right.step()

        else:
            # --- generic cascade for 4+ rotors ------------------
            carry = True
            for rotor in reversed(self.rotors):
                if not carry:
                    break
                carry = rotor.step()        # .step() returns bool rollover

    # ── encipher one symbol  ────────────────────────────────────

    def encypher(self, letter: str) -> str:
        self._step_rotors()
        debug.log("stepping", f"Rotor pos {[r.position for r in self.rotors]}")

        signal = self.kb.forward(letter)
        signal = self.pb.forward(signal)

        for rotor in reversed(self.rotors):
            signal = rotor.forward(signal)

        signal = self.reflector.reflect(signal)

        for rotor in self.rotors:
            signal = rotor.backward(signal)

        signal = self.pb.backward(signal)
        out_ch = self.kb.backward(signal)
        return out_ch