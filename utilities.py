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

Alpha26 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
Alpha38 = Alpha26 + "0123456789#/"
Alpha60 = Alpha38 + "+-*=()[]{}<>!?@&^%$£€_"

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
R1 = Rotor("EUXQ1W3BYF4RK0H7VGPADS59TOIZJL628C#NM/", "", alphabet=Alpha38)
R2 = Rotor("HCWGN7LYZ5E/29UXDQ4KS#JR1MP0A6V8TIB3FO", "", alphabet=Alpha38)
R3 = Rotor("UD8L/G7#RI0Y59PWXNAH1MEFVCZB6K234OQJST", "", alphabet=Alpha38)
R4 = Rotor("8BHJDT3IEX4RG61/YQ2VFKOMC0#PAWZ7SUN9L5", "", alphabet=Alpha38)
R5 = Rotor("JSMGCN9RHZ6BO5/XKV7Y80D1UIA24QFWT3PEL#", "", alphabet=Alpha38)
R6 = Rotor("7L98N6P0D5OMARWI1KEHBTZU#JGV3CXYF4QS/2", "", alphabet=Alpha38)
R7 = Rotor("TFDIS#JVMLP7QK5XA0O6CE1/GY2U93WRNB8ZH4", "", alphabet=Alpha38)
R8 = Rotor("DAXJ9EMF1ZYLVW4TBPGI58CHNU/KR7Q32O6#S0", "", alphabet=Alpha38)
R9 = Rotor("WM#7VHK4J36UGBIA0NYLC/5OF8XDRZ9QS2P1TE", "", alphabet=Alpha38)
R10 = Rotor("N2SK8#YCMAWL5Q/46D7OXZJFVBUGITP1R930HE", "", alphabet=Alpha38)

D = Reflector("/VEYCXKR7NG86JS#UHO1QB0FD5WT492ZMIL3PA", alphabet=Alpha38)
E = Reflector("T5UYKM7V/WE4F1R02O#ACHJ3D9PNQXLB8G6ZSI", alphabet=Alpha38)
F = Reflector("27W148V05R#YSZ9T3JMPXGCULNHDAQEI/BFOK6", alphabet=Alpha38)
G = Reflector("6CBXSJVKLFHI1WU8RQEZOGND3T9M7Y54A2P0/#", alphabet=Alpha38)
H = Reflector("LU/015MT642AGQ39NV8HBR#7ZYDEKOJFIXSPWC", alphabet=Alpha38)

# INOPv2
S1 = Rotor("21S5WE>P}7@V-A8]{£*D6T![€R(L^_C=N&<40XU9YK3ZI?%J$BG#H/FM)+OQ", "", alphabet=Alpha60)
S2 = Rotor("D^8%*R7AG_{6=#&U[Q!CI)+12HF4/<}Z5NX-]P0TK3@MW9£B€V>S?JL$(EYO", "", alphabet=Alpha60)
S3 = Rotor("&HK/1U}R9(F#6XA£<03WZJD-{QO45G^€_YC)T]P+*%!=E>?SNMI$VL8@72[B", "", alphabet=Alpha60)
S4 = Rotor("Q9+E*^>DVS}1K(P$#LOT{7YC_6GJ€HA&8!)N<WZ-£I]?5M/20BX=F@UR%34[", "", alphabet=Alpha60)
S5 = Rotor("9A86=_R#{/B4MN*-]GF?1P€V+>!XY)C07%5<IWZOSJ^QT}&KDE@$[UH2L£(3", "", alphabet=Alpha60)
S6 = Rotor("-9[C!X0_KM%@N2S+Y5&O>?QZT<^7/(F{*R])UBWV3ED1G$HIP#£8L=4J}A€6", "", alphabet=Alpha60)
S7 = Rotor("8G#€>V[39TXZ=IA*}LNE5-0_%7(Q2U^&K£BR?]W@YHCPJDSM${<F)!/+461O", "", alphabet=Alpha60)
S8 = Rotor("}N]^GBYQ(/KHJFS3=4R1*+C£&@8XIE?PDO9M!A_06V25L)T{[#$<Z%>W7€-U", "", alphabet=Alpha60)
S9 = Rotor("]QHE)4%<WXY8^FMOP/2*3{_@?70I£V6}G(RBNC-L$!€K#9JU[Z&1+AT=5>DS", "", alphabet=Alpha60)
S10 = Rotor("XO8?M0H-2U<&F£LIZ75R$*P6}J13WA{)4B%]+9V=#^@NS![TQ(G_D/€E>KYC", "", alphabet=Alpha60)
S11 = Rotor("8*1X&J3I5Q+}{_E@G0WB!<%LK>FAH92$€()6]ZO^[4-YUD=/7TVR?#SNPC£M", "", alphabet=Alpha60)
S12 = Rotor("1^4{6N*7X$L&_D[@%)BYP}J3TRAMICS#(2?8<=!OE/9WHK>V]G-5UZ€F£+Q0", "", alphabet=Alpha60)
S13 = Rotor("=D}V#C8M7/L1KS@0!$Z^Q%R9GJ)W<[&_24-EF?{£3T+P5]ANY6U€*I(BOH>X", "", alphabet=Alpha60)
S14 = Rotor("L5$W@CF£A?}*D[UJX!3S7(1#)^>&ZY]T4%ER-+<€VM9286=NK0HPBOIG/{Q_", "", alphabet=Alpha60)
S15 = Rotor("P[O?S€5]RN6(£DE>X&)KV8U#CG-}<+A*@MB0TW7!/Q1L^Y42=%IJ3H{_9FZ$", "", alphabet=Alpha60)
S16 = Rotor("_€8!C9@£)K=I<24L>O-RJ*NH(Y1T?G#PXQ[{%}FM]BZ0VE&W637$S+A/^5UD", "", alphabet=Alpha60)
S17 = Rotor("PLGOA#)_(2SI€HV^9U85MR<WE=-47D?*T]0CBZ!@£1}[&$/>%YK{QNX+F6J3", "", alphabet=Alpha60)
S18 = Rotor("743D{E1W?£}ZR5HQU2P0KM)(9</G_A-[BTY$C>F8#OX=J@€]*6%&I+LN^VS!", "", alphabet=Alpha60)
S19 = Rotor("[HB96}QJ)W{7V€5@DS+£(<Y>*4/IU#!G$M2Z1E&PKL]0=?3_RNF-TA^%C8OX", "", alphabet=Alpha60)
S20 = Rotor("SBPR#/V?I=35JKTN4O8E9)17!Y[UH(%Z>*@+_-$]GQ£{026}<LM€^FAWD&XC", "", alphabet=Alpha60)

AI = Reflector("?38^$&@€X%£S60VQP*L(/O<I1{NY>B7-M4C=+U#5R9T_}!Z[W2]AGFDJEKH)", alphabet=Alpha60)
J = Reflector("G#)£-=A20S€[9}&+!^J$ZWV16UIXH@</Y*]MB5PE7F{CL8(N4_Q%3OR?TDK>", alphabet=Alpha60)
K = Reflector("T<G0}-C?VZ[^#ONY%4$A9I7=PJD8(€R65W1UM_*F+X2{K!)EB@]H>£LQS&3/", alphabet=Alpha60)
L = Reflector("{@(R+WY<1M4SJ!X^-DL$56FOG[=I*#KUV€}?3]EQ20C%Z/A8H£N9B_P)T>7&", alphabet=Alpha60)
M = Reflector("DJSAZI£3FB@0)Y%RWPC_?9Q7NEL#=H{[&X*V1<$!82}M5^4(/€-UK6]O+G>T", alphabet=Alpha60)
N = Reflector("){@WVT>8#4=Q*Z?]L</F%ED^&N-£_9J+!(H3IS50MK7A$PB€RG6OCYXU[1}2", alphabet=Alpha60)
O = Reflector("L?&U)4M#<]OAGTK%2(5ND3*0@8X=QVFS-_Z>H€{6W1RE$J+!I9}BYC£P[^/7", alphabet=Alpha60)
P = Reflector("V^P_$?8[9X€T!-WC*6<L&AOJ{()/%43£R+GI=17NQ#Z0H>Y@S]MF}UB2E5KD", alphabet=Alpha60)
Q = Reflector("#%9£FEP6YX&^U+=G}75)MZ_JIV[(@?<SHR€CA{N!$O1T0>/Q4]-32KLB*D8W", alphabet=Alpha60)
R = Reflector("9W-L73!V}N+D2J£8%?#/=HB{5&>)MF6Y4EPASTKC€U^1<$XI[0GR_Z(Q]O*@", alphabet=Alpha60)

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