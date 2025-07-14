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
R1 = Rotor("YM8GQIA/36TNCO4WH51FK7#RELPJVBSDU29Z0X", "", alphabet=Alpha38)
R2 = Rotor("YNVRZ62U1AF4PT/E395QC#GKLHOBXJ807MDSIW", "", alphabet=Alpha38)
R3 = Rotor("ZJIUWTGBEOL5SK0V3X796A4DN8CQHRMP/1Y2#F", "", alphabet=Alpha38)
R4 = Rotor("KVC5Y3TD4N1PRLB#HW8GZIQJ/EO02U7X9MA6SF", "", alphabet=Alpha38)
R5 = Rotor("O5MTPFDY/WUJKRABGCXN38E4#1Q2L9V7HSIZ06", "", alphabet=Alpha38)
R6 = Rotor("X/ER5Z21#PQFAUGCN4HMSJK09VY8WLI36BDO7T", "", alphabet=Alpha38)
R7 = Rotor("G0JTXY2M6/P8Z7DEA54K91WBS#QVUFH3LCRION", "", alphabet=Alpha38)
R8 = Rotor("ZKH4F8Y2C13J96RLA0XSV5Q7DNMWBIT/UPE#GO", "", alphabet=Alpha38)
R9 = Rotor("MTLIX/J164SY320ABRCQN5KP8WDF7#GVOEUHZ9", "", alphabet=Alpha38)
R10 = Rotor("4ZYF3LCODUWG2VTB09ER61Q8SJ7XK5APN/#MIH", "", alphabet=Alpha38)

D = Reflector("UFM15BIZG3SQCV9#LYK/AN62RH4DXJ0EW87OPT", alphabet=Alpha38)
E = Reflector("5YXNQSORZ/9P3DGLEHF86#7CBI104M2AUWTKVJ", alphabet=Alpha38)
F = Reflector("0UJW64X53C72SYPO/ZM1B9DGNRATLIFHEK#V8Q", alphabet=Alpha38)
G = Reflector("VU69JW5YNE2R1I073L4#BAF/H8OMKQSGCPZDTX", alphabet=Alpha38)
H = Reflector("JTSR27NUYA/V6G49ZDCBHL1#IQ5WE8O0MF3PXK", alphabet=Alpha38)

# INOPv2
S1 = Rotor("IXDRJ2>£W-C$6^Z3)4F1G*N%]8<9&#OHAQU{([T}S5KE+L_7Y0@!V=BP€?M/", "", alphabet=Alpha60)
S2 = Rotor("%QTY0I6<F(CZ9-B$^/EOPW{N#R!X5=G8V+_U@KM1£H&73)?]2*LD}A4S>J[€", "", alphabet=Alpha60)
S3 = Rotor(">BRI6)^W#*9]LQDZ2%-FK5CE!X8€HJOYSUN[$PVT(<}={A7?+03GM_/@&1£4", "", alphabet=Alpha60)
S4 = Rotor("<1&#!_@7BKF/=HM€*Z{5EVT+CQLU0SI})?JN^%[$8G6O>W-£(9XD]23RA4YP", "", alphabet=Alpha60)
S5 = Rotor("POVTE$*[X2NZ+(}]W843/>U5GJC)H7I0Q#<9D-_S!€16A&@%B=RK?YM^£{FL", "", alphabet=Alpha60)
S6 = Rotor("M%B63Y&<NW09S]4UKQZ^}(OXG!7#?J$P=1A*£HVF_+[>R@2D){C/I85LE-T€", "", alphabet=Alpha60)
S7 = Rotor("*6MR/XAU#N39T}_8F!€J-^WC1I(]£ZO%P{0@$+Y>7S&VL[)4BK?EQG2D=<H5", "", alphabet=Alpha60)
S8 = Rotor("ENO?6QITS2D*M4B^>Y#!7<CR%-F£H35}Z)0PW1K(=${€UVA[LX/8G_9@&+J]", "", alphabet=Alpha60)
S9 = Rotor(")TR9$={UA*%/_V2L7OK0^(5&Q?HI[ZDG!M34J8£<€EP6>W]@BS+C1N#FY}-X", "", alphabet=Alpha60)
S10 = Rotor("}6/=&RC4^{HU0V£ZK<@IOLY*-(3GS1%+?NT8]J5EFQ€WD2!P)$7>M9#B[AX_", "", alphabet=Alpha60)
S11 = Rotor("MKEY€DJGF?OWVN18(&!0-S/#3T7{}>CL<[H4^%Q+69=P_]U@XZ*£5IB$R)A2", "", alphabet=Alpha60)
S12 = Rotor("$C%?RNU3@_EXH-YZ*&JG{2W^}=]FQ<K+0[#8/£I)MTAD6(>€P75O9!VL4B1S", "", alphabet=Alpha60)
S13 = Rotor("W!QNJU?8#51G/CT*S$VLA3MF)<27£9R-KD}(YP_]0+^EZ>{X=O%I6€H4[B@&", "", alphabet=Alpha60)
S14 = Rotor("E0/&[G€RY(A3^{+>4UCT]?7N56I9OL<S%#}21@£WX)8KFJ*VHB=MP$D!-_QZ", "", alphabet=Alpha60)
S15 = Rotor("?€-V8T{ZO)2&UFW4N%B+£@X]P[_67Y>EG*A1R0J}$HDQ3S/K5M!#^I9(<L=C", "", alphabet=Alpha60)
S16 = Rotor("U+<€EC@YS}2%F6G7H_DNV[QB>{R?)(M$K5IA1WT83=&]#*4JXLZ-P90!/O^£", "", alphabet=Alpha60)
S17 = Rotor("P€N2/6^]*OCGS%WVZJ4Y>XT[@B1EQ=_£<#$DR!7LAHM&3)0KI{(-859?+}UF", "", alphabet=Alpha60)
S18 = Rotor("/X>[3*K-_2ERMQ<ZN6J%£U^!?AB4+]178)SG{$HO€LD(@}Y&59VT#PCF0=IW", "", alphabet=Alpha60)
S19 = Rotor("B€ZUF&@7L8GI*>%?T1AP2HJ95V{NC[X#OE_S0!^}6$D)/=3]W4K<+R-£MQ(Y", "", alphabet=Alpha60)
S20 = Rotor("7GEHB#^&]!4?NT€5A3_S*0>9O8)VKM-U{L@21+CJWFID(P£/Z=%Y<RX$}[6Q", "", alphabet=Alpha60)

AI = Reflector("-OP1I#9=ENXY[JBCT!7Q8%+KL_€D32&?<SUGF(WA£H/{M})]6$R5^4@V>*0Z", alphabet=Alpha60)
J = Reflector("$5N^*_(2{SM/KCW+9)J%6?O=-8>#H43BU}ZQ1LPYEXGR£€I7&0@V!<DTA[]F", alphabet=Alpha60)
K = Reflector("!<7^MYN3}=X£EG+9?@$€0%4KF[U21HW65C)P]-O/&J>8Z#_IB(AQR*DVSLT{", alphabet=Alpha60)
L = Reflector("X(%V)L}7^]=FS0R8/OMW#DTA4[N!+<Y>€HP*UQ2@9KBEZJ$G351£-_IC{?6&", alphabet=Alpha60)
M = Reflector("L<4F0D$97Y%AV1)X&[£/!M}PJ#EN+-C]{I*HZT238_^OR56WB?U>€Q(KGS@=", alphabet=Alpha60)
N = Reflector("Z2)=&T3K€RH+X{7$VJ9F*Q?M<A[£BG-!>O}S%]L4UD^C0/N8Y65W_E(#P1I@", alphabet=Alpha60)
O = Reflector("M£<^6{1@?L7JA]Q(OY=}&!*8R)/G%+54EKX>-03#WSPZ$NFTC9VIHUD2[B_€", alphabet=Alpha60)
P = Reflector("=V#NL^%<S2OE!DK6]£I@[B4>(738J0W?PZ1{C&$}€AY_UQ9-HXM5T/FG+R*)", alphabet=Alpha60)
Q = Reflector("/E7?BLPU!T%F)Z@G}$6JH#_^4N5+>{Y0SC[&VA1=]-€M8*3Q£2IDO9XKR<(W", alphabet=Alpha60)
R = Reflector("N>K8260&9#CX^A@${%4V/T5L+-G<E7SWF3DIJUYZ)(=*?!Q_1B][OHMRP€£}", alphabet=Alpha60)

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