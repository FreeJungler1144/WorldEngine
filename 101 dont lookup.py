# wheel_gen.py  – prints 10×38-rotor, 5×38-refl, 20×60-rotor, 10×60-refl
import random, textwrap
from rotor_and_reflector import Rotor, Reflector   # import your classes

# ───── alphabets ───────────────────────────────────────────────────
ALPHA26 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ALPHA38 = ALPHA26 + "0123456789#/"
ALPHA60 = ALPHA38 + "+-*=()[]{}<>!?@&^%$£€_"
assert len(ALPHA38) == 38 and len(ALPHA60) == 60

# ───── wheel-builder helpers ───────────────────────────────────────
def make_rotor(alpha: str, seed) -> str:
    rng = random.Random(seed)
    lst = list(alpha); rng.shuffle(lst)
    return "".join(lst)

def make_reflector(alpha: str, seed) -> str:
    rng = random.Random(seed)
    symbols = list(alpha); rng.shuffle(symbols)
    wiring = [''] * len(alpha)
    while symbols:
        a, b = symbols.pop(), symbols.pop()
        ia, ib = alpha.index(a), alpha.index(b)
        wiring[ia] = b; wiring[ib] = a
    return "".join(wiring)

# ───── build families ──────────────────────────────────────────────
rot38_seeds = range(58, 68)
refl38_seeds = range(94, 99)    
rot60_seeds = range(614, 634)  
refl60_seeds = range(97205, 97215)   

rot38  = [make_rotor(ALPHA38,  s) for s in rot38_seeds]
refl38 = [make_reflector(ALPHA38, s) for s in refl38_seeds]
rot60  = [make_rotor(ALPHA60,  s) for s in rot60_seeds]
refl60 = [make_reflector(ALPHA60, s) for s in refl60_seeds]

# ───── print code you can paste into rotor_and_reflector.py ────────
print("# === 38-symbol ROTORS (R1–R10) ===")
for idx, wiring in enumerate(rot38, 1):
    name = f"R{idx}"
    print(f'{name} = Rotor("{wiring}", "")')

print("\n# === 38-symbol REFLECTORS (D–H) ===")
for idx, wiring in enumerate(refl38):
    name = chr(ord('D') + idx)           # D, E, F, G, H
    print(f'{name} = Reflector("{wiring}")')

print("\n# === 60-symbol ROTORS (S1–S20) ===")
for idx, wiring in enumerate(rot60, 1):
    name = f"S{idx}"
    print(f'{name} = Rotor("{wiring}", "")')

print("\n# === 60-symbol REFLECTORS (I–R) ===")
for idx, wiring in enumerate(refl60):
    name = chr(ord('I') + idx)           # I … R
    print(f'{name} = Reflector("{wiring}")')
