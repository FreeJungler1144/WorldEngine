# 101%20dont%20lookup.py
from __future__ import annotations

import argparse
import csv
import json
import secrets
import string
import sys
from pathlib import Path
from random import Random, SystemRandom
from typing import Callable, List, Sequence, Tuple

# ─── helpers ────────────────────────────────────────────────────────────


def build_rng(seed: int | None) -> Random | SystemRandom:
    """Return deterministic RNG when *seed* is given, else CSPRNG."""
    return Random(seed) if seed is not None else SystemRandom()  # CSPRNG


def make_rotor(alpha: str, rng: Random | SystemRandom) -> str:
    """Return a random permutation of *alpha*."""
    chars = list(alpha)
    rng.shuffle(chars)
    return "".join(chars)


def make_reflector(alpha: str, rng: Random | SystemRandom) -> str:
    """Return an involutory reflector wiring for *alpha* (no self-maps)."""
    remaining = list(alpha)
    rng.shuffle(remaining)
    wiring = [""] * len(alpha)

    while remaining:
        a, b = remaining.pop(), remaining.pop()
        if a == b:  # should never happen
            raise ValueError("Self-pair in reflector generation")
        ia, ib = alpha.index(a), alpha.index(b)
        wiring[ia], wiring[ib] = b, a

    result = "".join(wiring)
    assert _is_involution(result, alpha), "Reflector is not an involution"
    return result


def _is_involution(wiring: str, alpha: str) -> bool:
    """True if wiring[wiring[i]] == alpha[i] for all i."""
    for i, ch in enumerate(wiring):
        j = alpha.index(ch)
        if wiring[j] != alpha[i]:
            return False
    return True


def _rotor_label(alpha_len: int, idx: int) -> str:
    """R1–R10 for 38-alpha, S1–S20 for 60-alpha, L1… for 26/custom."""
    if alpha_len == 38:
        return f"R{idx}"
    if alpha_len == 60:
        return f"S{idx}"
    return f"L{idx}"


def _refl_label(alpha_len: int, idx: int) -> str:
    """D… for 38-alpha, I… for 60-alpha, A… for 26/custom."""
    if alpha_len == 38:
        base = ord("D")  # D-H
    elif alpha_len == 60:
        base = ord("I")  # I-R
    else:
        base = ord("A")
    return chr(base + idx)


# ─── output formatters ─────────────────────────────────────────────────


def emit_python(
    rotors: Sequence[Tuple[str, str]],
    reflectors: Sequence[Tuple[str, str]],
    alpha_var: str,
) -> str:
    """Return Python source defining Rotor / Reflector objects."""
    lines: List[str] = []
    lines.append(f'# alphabet constant assumed: {alpha_var}\n')
    for name, wiring in rotors:
        lines.append(f'{name} = Rotor("{wiring}", "", alphabet={alpha_var})')
    lines.append("")  # blank line
    for name, wiring in reflectors:
        lines.append(f'{name} = Reflector("{wiring}", alphabet={alpha_var})')
    lines.append("")  # trailing NL
    return "\n".join(lines)


def emit_json(
    rotors: Sequence[Tuple[str, str]],
    reflectors: Sequence[Tuple[str, str]],
    alphabet: str,
) -> str:
    payload = {
        "alphabet": alphabet,
        "rotors": {name: wiring for name, wiring in rotors},
        "reflectors": {name: wiring for name, wiring in reflectors},
    }
    return json.dumps(payload, indent=2)


def emit_csv(
    rotors: Sequence[Tuple[str, str]],
    reflectors: Sequence[Tuple[str, str]],
    alphabet: str,
) -> str:
    out = csv.StringIO()
    writer = csv.writer(out)
    writer.writerow(["type", "name", "wiring", "alphabet"])
    for name, wiring in rotors:
        writer.writerow(["rotor", name, wiring, alphabet])
    for name, wiring in reflectors:
        writer.writerow(["reflector", name, wiring, alphabet])
    return out.getvalue()


# ─── CLI ───────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate random Enigma wheels.")
    p.add_argument(
        "--alphabet",
        default="38",
        help="26, 38, 60 or a literal string of symbols (default 38)",
    )
    p.add_argument("--rotors", type=int, default=10, help="How many rotors (default 10)")
    p.add_argument(
        "--reflectors", type=int, default=5, help="How many reflectors (default 5)"
    )
    p.add_argument(
        "--seed",
        type=int,
        help="Integer seed for deterministic output "
        "(omit for cryptographically strong randomness)",
    )
    p.add_argument(
        "--format",
        choices=["py", "json", "csv"],
        default="py",
        help="Output format (default py)",
    )
    p.add_argument(
        "--outfile",
        type=Path,
        help="Write to this file (stdout if omitted)",
    )
    return p.parse_args()


# ─── main ──────────────────────────────────────────────────────────────


def main() -> None:
    args = parse_args()
    
    #interactive wizard because why not
    if len(sys.argv) == 1:                # launched without flags
        n_rot = int(input("How many rotors? [10] ") or 10)
        n_ref = int(input("How many reflectors? [5] ") or 5)
        alpha_len = input("Alphabet (26/38/60) [38] ") or "38"
        seed = input("Seed (blank = random): ") or None
        if seed:
            sys.argv += ["--seed", seed]
        sys.argv += ["--alphabet", alpha_len, "--rotors", str(n_rot),
                    "--reflectors", str(n_ref)]
    args = parse_args()              

    # alphabet handling --------------------------------------------------
    if args.alphabet in {"26", "38", "60"}:
        alpha_map = {
            "26": string.ascii_uppercase,
            "38": string.ascii_uppercase + "0123456789#/",
            "60": string.ascii_uppercase + "0123456789#/" + "+-*=()[]{}<>!?@&^%$£€_",
        }
        alphabet = alpha_map[args.alphabet]
    else:
        alphabet = args.alphabet
    alpha_len = len(alphabet)

    rng_rot = build_rng(args.seed)
    rng_ref = build_rng(None if args.seed is None else args.seed + 100_000)

    # generate wheels ----------------------------------------------------
    rotors = [
        (_rotor_label(alpha_len, i + 1), make_rotor(alphabet, rng_rot))
        for i in range(args.rotors)
    ]
    reflectors = [
        (_refl_label(alpha_len, i), make_reflector(alphabet, rng_ref))
        for i in range(args.reflectors)
    ]

    # choose formatter ---------------------------------------------------
    if args.format == "py":
        alpha_var = {26: "Alpha26", 38: "Alpha38", 60: "Alpha60"}.get(
            alpha_len, "ALPHABET"
        )
        text = emit_python(rotors, reflectors, alpha_var)
    elif args.format == "json":
        text = emit_json(rotors, reflectors, alphabet)
    else:  # csv
        text = emit_csv(rotors, reflectors, alphabet)

    # output --------------------------------------------------------------
    if args.outfile:
        args.outfile.write_text(text, encoding="utf-8")
        print(f"Wrote {args.outfile} ({args.format}, {len(text)} bytes)")
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()