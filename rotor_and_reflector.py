# rotor_and_reflector.py
from debug import Debug
debug = Debug()
debug.disable("stepping")

class Rotor:
    def __init__(self, wiring: str, notches: str, alphabet: str):
        if sorted(wiring) != sorted(alphabet):
            raise ValueError("wiring must be a permutation of alphabet")
        self.alphabet: str = alphabet
        self.size: int = len(alphabet)
        # maps input position → output position
        self.forward_map: list[int] = [alphabet.index(c) for c in wiring]
        # inverse map: input from right side → output left side
        self.backward_map: list[int] = [wiring.index(c) for c in alphabet]
        self.notches: set[str] = set(notches)
        self.position: int = 0
        self.ring_setting: int = 0

    def set_ring(self, ring: int) -> None:
        self.ring_setting = (ring - 1) % self.size

    def set_notches(self, notches: str) -> None:
        if not set(notches).issubset(self.alphabet):
            raise ValueError("Notch characters must be in the alphabet")
        self.notches = set(notches)

    def rotate(self, steps: int = 1) -> None:
        self.position = (self.position + steps) % self.size

    def step(self) -> bool:
        self.rotate(1)
        hit = self.alphabet[self.position] in self.notches
        debug.log("stepping", f"Rotor @ pos {self.position}, notch_hit={hit}")
        return hit

    def forward(self, sig: int) -> int:
        shifted = (sig + self.position - self.ring_setting) % self.size
        mapped = self.forward_map[shifted]
        return (mapped - self.position + self.ring_setting) % self.size

    def backward(self, sig: int) -> int:
        shifted = (sig + self.position - self.ring_setting) % self.size
        mapped = self.backward_map[shifted]
        return (mapped - self.position + self.ring_setting) % self.size


class Reflector:
    def __init__(self, wiring: str, alphabet: str):
        if len(wiring) != len(alphabet):
            raise ValueError("Reflector wiring length must match alphabet length")
        self.alphabet: str = alphabet
        self.size: int = len(alphabet)
        self.mapping: list[int] = [alphabet.index(c) for c in wiring]
        self.position: int = 0

    def rotate_to_letter(self, L: str) -> None:
        if L not in self.alphabet:
            raise ValueError(f"Reflector cannot rotate to {L!r}: not in alphabet")
        self.position = self.alphabet.index(L)

    def reflect(self, sig: int) -> int:
        adjusted = (sig + self.position) % self.size
        mapped = self.mapping[adjusted]
        return (mapped - self.position) % self.size