# keyboard_and_plugboard.py
from debug import Debug
debug = Debug()
debug.disable("plugboard")

class Keyboard:
    def __init__(self, alphabet: str):
        self.alphabet: str = alphabet
        self.alpha_to_index: dict[str, int] = {ch: i for i, ch in enumerate(alphabet)}
        # mirror for index → letter is just alphabet[i]
    
    def forward(self, letter: str) -> int:
        try:
            return self.alpha_to_index[letter]
        except KeyError:
            raise ValueError(f"Invalid character {letter!r} for current alphabet.")

    def backward(self, signal: int) -> str:
        if not (0 <= signal < len(self.alphabet)):
            raise ValueError(f"Signal {signal} out of range 0–{len(self.alphabet)-1}")
        return self.alphabet[signal]


class Plugboard:
    def __init__(self, pairs: list[tuple[str, str]], alphabet: str):
        self.alphabet: str = alphabet
        # identity mapping
        self.mapping: dict[str, str] = {ch: ch for ch in alphabet}
        self.letter_to_index: dict[str, int] = {ch: i for i, ch in enumerate(alphabet)}
        used: set[str] = set()

        for a, b in pairs:
            if a == b:
                raise ValueError(f"Plugboard cannot map a symbol to itself: {a}")
            if a in used or b in used:
                dup = a if a in used else b
                raise ValueError(f"Character {dup!r} already used in plugboard")
            if a not in alphabet or b not in alphabet:
                invalid = a if a not in alphabet else b
                raise ValueError(f"Symbol {invalid!r} not in alphabet")
            # swap
            self.mapping[a], self.mapping[b] = b, a
            used.update((a, b))

    def forward(self, signal: int) -> int:
        letter = self.alphabet[signal]
        mapped = self.mapping[letter]
        debug.log("plugboard", f"{signal}->{letter}->{mapped}")
        return self.letter_to_index[mapped]

    # symmetric wiring
    backward = forward