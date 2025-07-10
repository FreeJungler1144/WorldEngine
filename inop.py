# inop.py  ──────────────────────────────────────────────────────────
from debug import Debug

debug = Debug()
debug.disable("encypher")

class Inop:
    """Enigma-like machine with historical stepping (double-step) for 3 rotors, fallback cascade for others."""
    def __init__(self, kb, pb, rotors, reflector, ring_settings, master_key):
        self.kb = kb
        self.pb = pb
        self.rotors = rotors
        self.reflector = reflector

        if len(ring_settings) != len(rotors):
            raise ValueError("Incorrect ring settings length")
        if len(master_key) != len(rotors) + 1:
            raise ValueError("Incorrect master key length")

        # set ring and initial positions
        self.set_rings(ring_settings)
        self.set_key(master_key[:-1])
        self.reflector.rotate_to_letter(master_key[-1])

    def set_rings(self, rings):
        for rotor, ring in zip(self.rotors, rings):
            rotor.set_ring(ring)

    def set_key(self, key_part):
        for rotor, letter in zip(self.rotors, key_part):
            rotor.position = rotor.alphabet.index(letter)

    def _step_rotors(self):
        # If exactly 3 rotors, apply historical double-stepping
        if len(self.rotors) == 3:
            left, middle, right = self.rotors
            # double-step: if middle at notch, step left & middle
            if left.alphabet[middle.position] in middle.notches:
                left.step()
                middle.step()
            # normal step of middle when right rotor at notch
            elif left.alphabet[right.position] in right.notches:
                middle.step()
            # always step rightmost
            right.step()
        else:
            # fallback: simple cascade from rightmost inward
            carry = True
            for rotor in reversed(self.rotors):
                if carry:
                    carry = rotor.step()
                else:
                    break

    def encypher(self, letter: str) -> str:
        try:
            # 1) step rotors according to historical Enigma rules
            self._step_rotors()
            debug.log("stepping", f"Rotor positions {[r.position for r in self.rotors]}")

            # 2) keyboard
            signal = self.kb.forward(letter)
            debug.log("encypher", f"Keyboard: {letter} -> {signal}")

            # 3) plugboard in
            signal = self.pb.forward(signal)
            debug.log("encypher", f"Plugboard in: {signal}")

            # 4) forward through rotors (right-to-left)
            for rotor in reversed(self.rotors):
                signal = rotor.forward(signal)
            debug.log("encypher", f"Rotors forward: {signal}")

            # 5) reflector
            signal = self.reflector.reflect(signal)
            debug.log("encypher", f"Reflector: {signal}")

            # 6) backward through rotors (left-to-right)
            for rotor in self.rotors:
                signal = rotor.backward(signal)
            debug.log("encypher", f"Rotors backward: {signal}")

            # 7) plugboard out
            signal = self.pb.backward(signal)
            debug.log("encypher", f"Plugboard out: {signal}")

            # 8) keyboard back to letter
            decrypted_letter = self.kb.backward(signal)
            debug.log("encypher", f"Output: {decrypted_letter}")

            return decrypted_letter
        except Exception as e:
            debug.log("encypher", f"Error: {e}")
            raise