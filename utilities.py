# utilities.py
from __future__ import annotations

import re
from typing import Dict, List, Set, Tuple

from rotor_and_reflector import Rotor, Reflector

# ────────────────────────────────────────────────────────────────────────
#  0. Regex & trivial helpers
# ────────────────────────────────────────────────────────────────────────

_num_re = re.compile(r"^([A-Za-z]+)(\d+)$")
SUITE_ROTOR_COUNT = {"LEGACY": 3, "INOP-38": 5, "INOP-60": 10}


def ask(prompt: str) -> str:
    """Read & normalise an operator’s response (uppercase, trimmed)."""
    return input(prompt).strip().upper()


def _nat_key(name: str):
    """Natural‑sort rotor names so I, II, III, …, X, XI, R1, R2, …"""
    m = _num_re.match(name)
    if m:
        prefix, num = m.groups()
        return (0, prefix, int(num))
    return (1, name, 0)


def _rotor_count_for_suite(suite: str) -> int:
    try:
        return SUITE_ROTOR_COUNT[suite.upper()]
    except KeyError:  # pragma: no cover
        raise ValueError(f"Unknown suite '{suite}'. Expected one of {list(SUITE_ROTOR_COUNT)}")


# ────────────────────────────────────────────────────────────────────────
#  1. Interactive question helpers
# ────────────────────────────────────────────────────────────────────────
Alpha26 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
Alpha38 = Alpha26 + "0123456789#/"
Alpha60 = Alpha38 + "+-*=()[]{}<>!?@&^%$£€_"

SUITES: Dict[int, Dict[str, str]] = {
    1: {"name": "Legacy",  "alphabet": Alpha26},
    2: {"name": "INOP-38", "alphabet": Alpha38},
    3: {"name": "INOP-60", "alphabet": Alpha60},
}

def choose_suite(default: int = 1) -> Dict[str, str]:
    print("\nSelect suite:")
    for idx, suite in SUITES.items():
        print(f" [{idx}] {suite['name']}")
    try:
        sel = int(input("> ").strip())
    except ValueError:
        sel = default
    return SUITES.get(sel, SUITES[default])

CURRENT = choose_suite()


def get_rotor_selection(suite: str, rotor_dict: Dict[str, Rotor], max_label: int) -> List[str]:
    need = _rotor_count_for_suite(suite)
    names = sorted({n for n in rotor_dict if n.isupper()}, key=_nat_key)
    print("\nAvailable Rotors:", " ".join(names))
    while True:
        sel = ask(f"Select {need} rotors in order: ").split()
        if len(sel) == need and all(r in rotor_dict for r in sel):
            return sel
        print(f"❌  Need exactly {need} valid rotor names.")


def get_reflector_selection(refl_dict: Dict[str, Reflector], max_label: int) -> Reflector:
    names = sorted({n for n in refl_dict if n.isupper()})
    print("\nAvailable Reflectors: ", ", ".join(names))
    while True:
        ref = ask("Select reflector: ")
        if ref in refl_dict:
            return refl_dict[ref]
        print("❌  Not a valid reflector.")


# ––– plugboard helpers –––––––––––––––––––––––––––––––––––––––––––

def _validate_pair(pair: str, valid: Set[str], used: Set[str]) -> Tuple[bool, str | None]:
    a, b = pair
    if len(pair) != 2:
        return False, f"❌ Pair '{pair}' must be exactly 2 characters."
    if a == b:
        return False, f"❌ Pair '{pair}' cannot map to itself."
    if {a, b} - valid:
        invalid = ({a, b} - valid).pop()
        return False, f"❌ Invalid char '{invalid}' in pair '{pair}'."
    if {a, b} & used:
        dup = ({a, b} & used).pop()
        return False, f"❌ Char '{dup}' already used."
    return True, None


def get_plugboard(alpha: str, max_label: int) -> List[str]:
    """Return a list of *validated* plugboard pairs (e.g. ["AB", "CD"])."""
    valid = set(alpha)
    max_pairs = {26: 10, 38: 15}.get(len(alpha), 25)

    print(f"\nPlugboard pairs (≤{max_pairs}, e.g. AB CD EF):")
    while True:
        used: Set[str] = set()
        raw = ask("Pairs (Enter for none):")
        if not raw:
            return []

        pairs = raw.split()
        if len(pairs) > max_pairs:
            print(f"❌  Too many pairs (max {max_pairs}).")
            continue

        # validate
        for p in pairs:
            ok, err = _validate_pair(p.upper(), valid, used)
            if not ok:
                print(err)
                break
            used.update(p)
        else:  # only executes if no break occurred
            return pairs


# ––– rings & notches ––––––––––––––––––––––––––––––––––––––––––––

def get_ring_settings(count: int, alpha: str, max_label: int) -> List[int]:
    hi = len(alpha)
    prompt = f"{count} ring settings 1-{hi}:"
    while True:
        raw = ask(f"{prompt:<{max_label}} ").split()
        if len(raw) == count and all(item.isdigit() and 1 <= int(item) <= hi for item in raw):
            return [int(item) for item in raw]
        print(f"❌  Need exactly {count} numbers in 1–{hi}.")


def get_notches(rotor_names: List[str], alpha: str, max_label: int) -> Dict[str, str]:
    if len(alpha) == len(Alpha26):  # Legacy rotors already have fixed notches
        return {}

    valid = set(alpha)
    max_notches = 5 if len(alpha) == len(Alpha60) else 3
    result: Dict[str, str] = {}

    for name in rotor_names:
        while True:
            s = ask(f"Notches for {name} (0–{max_notches}): ")
            if len(s) <= max_notches and set(s) <= valid:
                result[name] = s
                break
            print(f"❌  0–{max_notches} symbols from alphabet only.")
    return result


def get_master_key(alpha: str, length: int, max_label: int) -> str:
    valid = set(alpha)
    prompt = f"Master key ({length} chars):"
    while True:
        key = ask(prompt)
        if len(key) == length and set(key) <= valid:
            return key
        print(f"❌ Must be exactly {length} symbols from alphabet.")


# ––– orchestration –––––––––––––––––––––––––––––––––––––––––––––––

def get_inop_settings(suite: str, alpha: str, rotor_dict: Dict[str, Rotor], refl_dict: Dict[str, Reflector]):
    """Collect *interactive* settings from the operator and return them in the
    same tuple format expected by older code. The prompts scale nicely with
    alphabet / rotor count.
    """

    ml = max(
        len("Select reflector:"),
        len("Pairs (Enter for none):"),
        len("10 ring settings 1-60:"),
        len("Master key (7 chars):"),
    )

    need = _rotor_count_for_suite(suite)
    rotors = get_rotor_selection(suite, rotor_dict, ml)
    reflector = get_reflector_selection(refl_dict, ml)
    plugboard = get_plugboard(alpha, ml)
    rings = get_ring_settings(need, alpha, ml)
    notches = get_notches(rotors, alpha, ml)
    master_key = get_master_key(alpha, need + 1, ml)
    return rotors, reflector, rings, notches, plugboard, master_key


# ────────────────────────────────────────────────────────────────────────
#  2. Text preprocessing
# ────────────────────────────────────────────────────────────────────────


def preprocess_message(msg: str, alpha: str) -> str:
    """Upper‑case, replace spaces (→ '#') if supported, and drop non‑alphabet chars."""
    text = msg.upper()
    text = text.replace(" ", "#" if "#" in alpha else "")
    return "".join(ch for ch in text if ch in alpha)


# ────────────────────────────────────────────────────────────────────────
#  3. Wheel database
# ────────────────────────────────────────────────────────────────────────

# Legacy rotors ----------------------------------------------------------
I   = Rotor("EKMFLGDQVZNTOWYHXUSPAIBRCJ", notches="Q",  alphabet=Alpha26)
II  = Rotor("AJDKSIRUXBLHWTMCQGZNPYFVOE", notches="E",  alphabet=Alpha26)
III = Rotor("BDFHJLCPRTXVZNYEIWGAKMUSQO", notches="V",  alphabet=Alpha26)
IV  = Rotor("ESOVPZJAYQUIRHXLNFTGKDCMWB", notches="J",  alphabet=Alpha26)
V   = Rotor("VZBRGITYUPSDNHLXAWMJQOFECK", notches="Z",  alphabet=Alpha26)
VI  = Rotor("JPGVOUMFYQBENHZRDKASXLICTW", notches="ZM", alphabet=Alpha26)
VII = Rotor("NZJHGRCXMYSWBOUFAIVLPEKQDT", notches="ZM", alphabet=Alpha26)

# Legacy reflectors ------------------------------------------------------
A = Reflector("EJMZALYXVBWFCRQUONTSPIKHGD", alphabet=Alpha26)
B = Reflector("YRUHQSLDPXNGOKMIEBFZCWVJAT", alphabet=Alpha26)
C = Reflector("FVPJIAOYEDRZXWGCTKUQSBNMHL", alphabet=Alpha26)

#INOPv1
R1 = Rotor("PFEYNJ9TOZ3RW5QD87K2SUA04CM1H6ILGX/B#V", "", alphabet=Alpha38)
R2 = Rotor("B/4WX83GJMQI7EAT20U56OLP#ZSRDF91KHNYVC", "", alphabet=Alpha38)
R3 = Rotor("GM27U5HWCKZP0R4OXBVIN813EQDA6FY#9/TJSL", "", alphabet=Alpha38)
R4 = Rotor("SN4ZO75C#8Q6GJFIYPDHVA0/KT2R39ULM1EWXB", "", alphabet=Alpha38)
R5 = Rotor("3JO9ZA0E4GFKI6B1XSDNU82TC5Y/PRM7H#LVWQ", "", alphabet=Alpha38)
R6 = Rotor("09CR1M5K36LJYTSPH7XNI#G2ZV4FEOQ/WAU8DB", "", alphabet=Alpha38)
R7 = Rotor("CZTBSNHJPGAKIE54Q8YFW9LUV2D3#R1M0X6O7/", "", alphabet=Alpha38)
R8 = Rotor("3G/CXWU6BYAK7HD5Z428TEIMVFJN0OPS9R#Q1L", "", alphabet=Alpha38)
R9 = Rotor("IP/69KZSQ05XAD#CR2FVJ3O7Y8TW4NG1BEMHLU", "", alphabet=Alpha38)
R10 = Rotor("ZV85JFPWEDHT6GQ7X40BMRIY/CAON1UL2S#93K", "", alphabet=Alpha38)

D = Reflector("/VEYCXKR7NG86JS#UHO1QB0FD5WT492ZMIL3PA", alphabet=Alpha38)
E = Reflector("T5UYKM7V/WE4F1R02O#ACHJ3D9PNQXLB8G6ZSI", alphabet=Alpha38)
F = Reflector("27W148V05R#YSZ9T3JMPXGCULNHDAQEI/BFOK6", alphabet=Alpha38)
G = Reflector("6CBXSJVKLFHI1WU8RQEZOGND3T9M7Y54A2P0/#", alphabet=Alpha38)
H = Reflector("LU/015MT642AGQ39NV8HBR#7ZYDEKOJFIXSPWC", alphabet=Alpha38)

# INOPv2
S1 = Rotor("X2[IZMGN1=$S{}J*QYC7€0_?R£W%<+V^@#U63K>HAP&4(F9-TOB/D8L!E5)]", "", alphabet=Alpha60)
S2 = Rotor("K3%9?6£5P$LY}#S_>DVZ<MU/BR]=J(-I!0NAT)W4@&+F*7^E2€HXOQ1C8[{G", "", alphabet=Alpha60)
S3 = Rotor(">9/A<$ON7ML_S=K&E#][FG3?2UP*T4}H£0JZ8IR+Q1D€6!Y5{-)%(XWC^BV@", "", alphabet=Alpha60)
S4 = Rotor("$WXCU-*K€9)(6B[1JS7+M/!NQ3@#I><^AGPZ£}D2T_H8R=V{4%E&L5]?Y0OF", "", alphabet=Alpha60)
S5 = Rotor("{0SY)5<U24DG^/?TJ}LIO_R7£P]=W$Q[*8!>X9@Z(1#B63-C&FVAN€%H+MEK", "", alphabet=Alpha60)
S6 = Rotor("(&$-A)V13KDS=>PQ*0W_F8U6T£9!?2BO@€MI%J#/+47R^X5E[{H}LYCN<]GZ", "", alphabet=Alpha60)
S7 = Rotor("&BH]L8%(N2U97/$=€<S?O[>£-JPW4+G5CQF0)K^*!3V_ZYR@{D}#1MTAEIX6", "", alphabet=Alpha60)
S8 = Rotor("-4YFXE}>7L<WP&%(S£)5OV_60Z$1A*J+I9U?T3=^[/N{B€GK#RDM@8Q2C]!H", "", alphabet=Alpha60)
S9 = Rotor("C8YSXIF2}3£]&>€O0!@1H*=DU[BZWNRQP-J)E%4M<GT6+A$^?_7L(V{K9/5#", "", alphabet=Alpha60)
S10 = Rotor("7H=G(/N@8L09?3CY6JT^>[£Q1AFK]U5%)P&OZ$DW€V+MX2I4B{ESR<-!}#_*", "", alphabet=Alpha60)
S11 = Rotor("AONH5[/Y£@ZE92C_{K?$=<&PGV€>#7W(84S0*!-^ULFR%)JI}X6+31MTQB]D", "", alphabet=Alpha60)
S12 = Rotor("QNFV$I15%WX{A8*_62YS9K<R>B]L#^}+Z/=JD@GUP£43[€EM7-OC!H0&(?)T", "", alphabet=Alpha60)
S13 = Rotor("B@(AU1GN£C&9!>JQ/LZ=-43{WRKV[SF5%M$€?E6DH8T^+X}2YIP70O*<])_#", "", alphabet=Alpha60)
S14 = Rotor("Y5$4S[3TW6%7U?V£0IPH{AF<EKRL2=_>GJZ#B!8&}@NODC^1XM]*9/-+Q(€)", "", alphabet=Alpha60)
S15 = Rotor("?*%VO)£=A{/K06FT7G$4Y}89URP5H]EC<>^[JBL_QNS@-M!X1IW€Z+D&2(3#", "", alphabet=Alpha60)
S16 = Rotor("1VB^F7E3>[DL*UZ4%+OCYJ9(_8#)5£X<I&R-{]G}2@N0H?PK/Q!6TS€WMA$=", "", alphabet=Alpha60)
S17 = Rotor("I6Y_OLKC?A#ZQ0GXHBV51@€-}38U*/>SE=&94£)[M{7$PJ%D(T+R<]!^2NWF", "", alphabet=Alpha60)
S18 = Rotor("04*=T^(1£29]_-FRIYCG+78BE?K#<€H[O&X/UWA$VPD>S65Z%JL@Q}3)MN!{", "", alphabet=Alpha60)
S19 = Rotor("J&Z!SYW?G4{KMH0I#TUX]€F2Q/N[D5PV%A9)B^->R_3(7+<L@8=}CO*£61E$", "", alphabet=Alpha60)
S20 = Rotor("}[!BD2]JV9E35A&8NST£O>)F=G#-/HL@QC^+7<X(0R%*ZP€_MU{1W6Y4$KI?", "", alphabet=Alpha60)

AI = Reflector("Z0R9WP]<SOX5^+JF>CI2@7EK3AB)TY6L4V=D_-N/$8?1%G&£HQ€(U{M[*}!#", alphabet=Alpha60)
J = Reflector("W*2{JGFT1ELKX0+_8^%H£?AM[&NIC$54](Q)@<O}B€79Y6D-/!>V#ZRS3U=P", alphabet=Alpha60)
K = Reflector("SD/B@€Z*V)1-?X7}9%AW5ITN<G&K6_>U2O#Q8C$LH]^J!=£PY4[ME0(R+{F3", alphabet=Alpha60)
L = Reflector("G2S_!PAX7{5€93)F@}C&^%[H=<4(BN0K]I/M?8>*-Y1OW6JRZ+E#QTUV£$LD", alphabet=Alpha60)
M = Reflector("}{0L[Y1&%P9D=4^J+*>€$5!@F)CG-/NV8_6K]3Q2RM<ZE#BA(SW£XHOIU?T7", alphabet=Alpha60)
N = Reflector("!WM(3L0{74#FC2=UT+}QP>B^9]G_NEJ?$I[YK&R%)OD*8ZHS£VA5€/X-6<@1", alphabet=Alpha60)
O = Reflector("HI@S>-XABZ3V%7#/8<D5=L£G+J?&)K9T^NQ4OPYF}U{2!€(*RE[0C16M_W]$", alphabet=Alpha60)
P = Reflector("BA=%YZ^T8-&£7*{W31_H}[P#EF<R+Q$@/MI!X62JNC?]V)OU0€9(5KGD4L>S", alphabet=Alpha60)
Q = Reflector("N6LW^0HG}T]C(A/5£!2J%*D@$#F€S<=PB_&{ZO>[V4M?-K9I3+R)X8EUYQ17", alphabet=Alpha60)
R = Reflector("8M(S7!ZKP&H[B%/I=6D<29*+?G@5U>^1REAV-OX#WQC{L_)£T3FY0J4N€}$]", alphabet=Alpha60)

# Build the lookup dicts -------------------------------------------------

base_rotors: Dict[str, Rotor] = {
    "I": I, "II": II, "III": III, "IV": IV, "V": V, "VI": VI, "VII": VII,
    "R1": R1, "R2": R2, "R3": R3, "R4": R4, "R5": R5,
    "R6": R6, "R7": R7, "R8": R8, "R9": R9, "R10": R10,
    "S1": S1, "S2": S2, "S3": S3, "S4": S4, "S5": S5,
    "S6": S6, "S7": S7, "S8": S8, "S9": S9, "S10": S10,
    "S11": S11, "S12": S12, "S13": S13, "S14": S14, "S15": S15,
    "S16": S16, "S17": S17, "S18": S18, "S19": S19, "S20": S20,
}

base_reflectors: Dict[str, Reflector] = {
    "A": A, "B": B, "C": C, "D": D, "E": E, "F": F, "G": G, "H": H,
    "AI": AI, "J": J, "K": K, "L": L, "M": M, "N": N, "O": O, "P": P,
    "Q": Q, "R": R,
}

rotor_dict: Dict[str, Rotor] = {}
for name, obj in base_rotors.items():
    rotor_dict[name] = rotor_dict[name.lower()] = obj  # uppercase + alias

reflector_dict: Dict[str, Reflector] = {}
for name, obj in base_reflectors.items():
    reflector_dict[name] = reflector_dict[name.lower()] = obj

__all__ = [
    "rotor_dict",
    "reflector_dict",
    "get_inop_settings",
    "preprocess_message",
]