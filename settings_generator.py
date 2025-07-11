# settings_generator.py
from __future__ import annotations

import argparse
import json
import secrets
import string
import sys
from itertools import islice, pairwise
from pathlib import Path
from random import Random, SystemRandom
from typing import Dict, List

# ── alphabets ─────────────────────────────────────────────────────
ALPHA26 = string.ascii_uppercase
ALPHA38 = ALPHA26 + "0123456789#/"
ALPHA60 = ALPHA38 + "+-*=()[]{}<>!?@&^%$£€_"

SUITES: Dict[str, Dict] = {
    "1": {  # Legacy
        "name": "Legacy",
        "alphabet": ALPHA26,
        "rotors": ["I", "II", "III", "IV", "V", "VI", "VII"],
        "reflectors": ["A", "B", "C"],
        "n_rot": 3,
        "max_pairs": 10,
        "max_notches": 0,
    },
    "2": {  # INOP-38
        "name": "INOP-38",
        "alphabet": ALPHA38,
        "rotors": [f"R{i}" for i in range(1, 11)],
        "reflectors": list("DEFGH"),
        "n_rot": 5,
        "max_pairs": 15,
        "max_notches": 3,
    },
    "3": {  # INOP-60
        "name": "INOP-60",
        "alphabet": ALPHA60,
        "rotors": [f"S{i}" for i in range(1, 21)],
        "reflectors": list("AIJKLMNOPQR"),
        "n_rot": 10,
        "max_pairs": 25,
        "max_notches": 5,
    },
}

# ── helpers ───────────────────────────────────────────────────────


def build_rng(seed: int | None) -> Random | SystemRandom:
    """Deterministic RNG when *seed* given; CSPRNG otherwise."""
    return Random(seed) if seed is not None else SystemRandom()


def choose_pairs(alpha: str, k: int, rng: Random | SystemRandom) -> List[str]:
    """Return *k* disjoint plug pairs."""
    max_possible = len(alpha) // 2
    k = min(k, max_possible)
    pool = list(alpha)
    rng.shuffle(pool)
    return [a + b for a, b in zip(pool[::2], pool[1::2])][:k]


def choose_notches(rotors: List[str], alpha: str, max_n: int, rng) -> Dict[str, str]:
    if max_n == 0:
        return {}
    return {
        r: "".join(rng.sample(alpha, rng.randint(0, max_n))) for r in rotors
    }


def ask_suite() -> Dict:
    print("Select suite:")
    for key, cfg in SUITES.items():
        print(f" [{key}] {cfg['name']}")
    return SUITES.get(input("> ").strip())


def parse_cli() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate INOP daily config")
    p.add_argument("--seed", type=int, help="Deterministic seed (omit for random)")
    p.add_argument(
        "--outfile",
        type=Path,
        default=Path("inop_config.json"),
        help="Destination JSON file (default: inop_config.json)",
    )
    return p.parse_args()


# ── main ─────────────────────────────────────────────────────────


def main() -> None:
    args = parse_cli()
    suite_cfg = ask_suite()
    if not suite_cfg:
        sys.exit("Aborted.")

    rng = build_rng(args.seed)
    α = suite_cfg["alphabet"]

    rotors = rng.sample(suite_cfg["rotors"], suite_cfg["n_rot"])
    reflector = rng.choice(suite_cfg["reflectors"])
    ring_set = [rng.randint(1, len(α)) for _ in rotors]
    plugs = choose_pairs(α, suite_cfg["max_pairs"], rng)
    notch_map = choose_notches(rotors, α, suite_cfg["max_notches"], rng)
    master_key = "".join(rng.choices(α, k=len(rotors) + 1))

    cfg = {
        "suite": suite_cfg["name"],
        "rotors": rotors,
        "reflector": reflector,
        "ring_set": ring_set,
        "notch_map": notch_map,
        "plugs": plugs,
        "master_key": master_key,
    }

    args.outfile.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print(f"✅  Wrote {args.outfile}\n"
        f"   suite       : {cfg['suite']}\n"
        f"   rotors      : {rotors}\n"
        f"   reflector   : {reflector}\n"
        f"   master key  : {master_key}\n"
        f"   plug pairs  : {len(plugs)}")


if __name__ == "__main__":
    main()