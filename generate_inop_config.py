# ── generate_inop_config.py ───────────────────────────────────────
import json, random, sys, string
from itertools import islice

# ── alphabet families ────────────────────────────────────────────
ALPHA26 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ALPHA38 = ALPHA26 + "0123456789#/"
ALPHA60 = ALPHA38 + "+-*=()[]{}<>!?@&^%$£€_"

SUITES = {
    "1": {           # Legacy
        "name"         : "Legacy",
        "alphabet"     : ALPHA26,
        "rotors"       : ["I", "II", "III", "IV", "V", "VI", "VII"],
        "reflectors"   : ["A", "B", "C"],
        "n_rot"        : 3,
        "max_pairs"    : 10,
        "max_notches"  : 0,    # no user-set notches
    },
    "2": {           # INOP-38
        "name"         : "INOP-38",
        "alphabet"     : ALPHA38,
        "rotors"       : [f"R{i}" for i in range(1, 11)],
        "reflectors"   : list("DEFGH"),
        "n_rot"        : 5,
        "max_pairs"    : 15,
        "max_notches"  : 3,
    },
    "3": {           # INOP-60
        "name"         : "INOP-60",
        "alphabet"     : ALPHA60,
        "rotors"       : [f"S{i}" for i in range(1, 21)],
        "reflectors"   : list("AIJKLMNOPQR"),
        "n_rot"        : 10,
        "max_pairs"    : 25,
        "max_notches"  : 5,
    },
}

def ask_suite() -> dict:
    print("Select suite:")
    for key, cfg in SUITES.items():
        print(f" [{key}] {cfg['name']}")
    choice = input("> ").strip()
    return SUITES.get(choice)

def rand_plugboard(alpha: str, max_pairs: int) -> list[str]:
    """Generate up to max_pairs random disjoint pairs from alpha."""
    pool = list(alpha)
    random.shuffle(pool)
    pairs = []
    for a, b in zip(islice(pool, 0, None, 2), islice(pool, 1, None, 2)):
        if len(pairs) >= max_pairs:
            break
        pairs.append(a + b)
    return pairs

def rand_notches(rotors: list[str], alpha: str, max_notches: int) -> dict[str, str]:
    """For each rotor, pick 0–max_notches random notch positions from alpha."""
    if max_notches <= 0:
        return {}
    out = {}
    for r in rotors:
        k = random.randint(0, max_notches)
        out[r] = "".join(random.sample(alpha, k))
    return out

def main() -> None:
    suite_cfg = ask_suite()
    if not suite_cfg:
        sys.exit("Aborted.")

    alphabet    = suite_cfg["alphabet"]
    rotor_names = random.sample(suite_cfg["rotors"], suite_cfg["n_rot"])
    reflector   = random.choice(suite_cfg["reflectors"])
    ring_set    = [random.randint(1, len(alphabet)) for _ in rotor_names]
    plugs       = rand_plugboard(alphabet, suite_cfg["max_pairs"])
    notch_map   = rand_notches(rotor_names, alphabet, suite_cfg["max_notches"])
    # master_key length = n_rot + 1
    master_key  = "".join(random.choices(alphabet, k=len(rotor_names) + 1))

    cfg = {
        "suite"        : suite_cfg["name"],
        "rotors"       : rotor_names,
        "reflector"    : reflector,
        "ring_set"     : ring_set,
        "notch_map"    : notch_map,
        "plugs"        : plugs,
        "master_key"   : master_key,
    }

    with open("inop_config.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    print("✅  Configuration written to inop_config.json")

if __name__ == "__main__":
    main()