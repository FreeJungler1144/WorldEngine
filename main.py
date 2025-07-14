# main.py
from __future__ import annotations

import argparse, json
from pathlib import Path
from copy import deepcopy
from dataclasses import dataclass
from secrets import choice as secure_choice, randbelow
from typing import Dict, List, Tuple

from debug import Debug
from inop import Inop
from keyboard_and_plugboard import Keyboard, Plugboard
from rotor_and_reflector import Rotor, Reflector
from utilities import (
    get_inop_settings,
    preprocess_message,
    reflector_dict,
    rotor_dict,
    CURRENT
)

# ────────────────────────────────────────────────────────────────────────
#  0. Configuration & logging
# ────────────────────────────────────────────────────────────────────────


debug = Debug()
debug.toggle_global(False)


@dataclass(slots=True)
class Config:
    """Runtime switches that influence the crypto pipeline."""

    double_pass: bool = True        # encrypt‑reverse‑encrypt if True
    do_padding: bool = True         # wrap msg with marker + cover traffic
    step_reflector: bool = True    # step reflector on every keypress 
    block: int = 5                  # display / padding block size
    base_noise: int = 8             # minimum random chars added when padding
    marker_len: int = 5             # hidden delimiter length


# ────────────────────────────────────────────────────────────────────────
#  1. Suite and JSON loading helpers
# ────────────────────────────────────────────────────────────────────────


def load_suite() -> tuple[str, str, Dict[str, "Rotor"], Dict[str, "Reflector"]]:
    """Return `(suite_name, alphabet, rotor_pool, reflector_pool)` for the
    *CURRENT* suite, duplicating wheels so we never mutate originals."""

    suite_name: str = CURRENT["name"]
    alphabet: str = CURRENT["alphabet"]
    alpha_len: int = len(alphabet)

    rotor_pool = {
        name: deepcopy(r)
        for name, r in rotor_dict.items()
        if len(r.alphabet) == alpha_len
    }
    refl_pool = {
        name: deepcopy(r)
        for name, r in reflector_dict.items()
        if len(r.alphabet) == alpha_len
    }

    if not rotor_pool or not refl_pool:
        raise SystemExit("❌  No wheels compatible with this suite.")

    return suite_name, alphabet, rotor_pool, refl_pool


def load_config(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"suite", "rotors", "reflector", "ring_set",
                "plugs", "master_key"}
    missing = required - data.keys()
    if missing:
        raise ValueError(f"Missing keys in config: {', '.join(missing)}")
    return data


# ────────────────────────────────────────────────────────────────────────
#  2. MachineContext – wraps an Inop machine & reset logic
# ────────────────────────────────────────────────────────────────────────


class MachineContext:
    """A thin wrapper so we do not pass six objects around."""

    def __init__(
        self,
        alphabet: str,
        rotor_pool: Dict[str, "Rotor"],
        reflector_pool: Dict[str, "Reflector"],
    ) -> None:
        (
            self.rotor_names,
            reflector_choice,
            self.ring_set,
            self.notch_map,
            self.plugs,
            self.master_key,
        ) = get_inop_settings(CURRENT["name"], alphabet, rotor_pool, reflector_pool)

        # apply per‑run notch overrides
        for name, notch_chars in self.notch_map.items():
            rotor_pool[name].set_notches(notch_chars)

        # instantiate wheels in chosen order
        rotor_objs = [rotor_pool[name] for name in self.rotor_names]

        # reflector may be object or name
        refl_obj = (
            reflector_choice
            if isinstance(reflector_choice, Reflector)
            else deepcopy(reflector_pool[reflector_choice])
        )

        self.machine: Inop = Inop(
            Keyboard(alphabet),
            Plugboard(self.plugs, alphabet),
            rotor_objs,
            refl_obj,
            self.ring_set,
            self.master_key,
        )
        
        self.alphabet: str = alphabet

    @classmethod
    def from_config(cls, cfg: dict) -> "MachineContext":
        """Build a MachineContext from a saved JSON dictionary."""
        rotor_labels = cfg["rotors"]

        # recreate fresh wheel objects
        rotor_objs = [deepcopy(rotor_dict[label]) for label in rotor_labels]
        refl_obj   = deepcopy(reflector_dict[cfg["reflector"]])

        # alphabet is the one baked into any rotor
        alphabet = rotor_objs[0].alphabet

        # apply notch overrides (if present)
        notch_map = cfg.get("notch_map", {})
        for obj, label in zip(rotor_objs, rotor_labels):
            obj.set_notches(notch_map.get(label, ""))

        # build the actual machine
        inst = object.__new__(cls)          # bypass __init__
        inst.alphabet    = alphabet
        inst.rotor_names = rotor_labels
        inst.plugs       = cfg["plugs"]
        inst.ring_set    = cfg["ring_set"]
        inst.notch_map   = notch_map
        inst.master_key  = cfg["master_key"]

        inst.machine = Inop(
            Keyboard(alphabet),
            Plugboard(cfg["plugs"], alphabet),
            rotor_objs,
            refl_obj,
            cfg["ring_set"],
            cfg["master_key"],
        )
        return inst

    # ––– helpers ––––––––––––––––––––––––––––––––––––––––––––––––

    def rewind(self) -> None:
        """Reset the machine to the daily *master_key*."""
        self.machine.set_key(self.master_key[:-1])
        self.machine.reflector.rotate_to_letter(self.master_key[-1])

    def encipher_block(self, text: str) -> str:
        """Encipher *text* once, assuming it already maps into alphabet."""
        self.rewind()
        return "".join(self.machine.encypher(ch) for ch in text)


    # ────────────────────────────────────────────────────────────────────────
    #  3. Padding & marker helpers
    # ────────────────────────────────────────────────────────────────────────


def make_marker(alpha: str, length: int, choice=secure_choice) -> str:
    return "".join(choice(alpha) for _ in range(length))


def pad_message(
    msg: str,
    alpha: str,
    *,
    base_noise: int,
    block: int,
    target_residue: int = 1,
) -> str:

    scaled_noise = max(base_noise, int(len(msg) * 0.35))
    residue = (len(msg) + scaled_noise) % block
    extra = (target_residue - residue) % block
    n = scaled_noise + extra

    front_len = randbelow(n + 1)  # 0‥n inclusive
    suffix_len = n - front_len

    prefix = "".join(secure_choice(alpha) for _ in range(front_len))
    suffix = "".join(secure_choice(alpha) for _ in range(suffix_len))
    return prefix + msg + suffix


def extract_message(full: str, marker: str) -> str:
    i, j = full.find(marker), full.rfind(marker)
    if i == -1 or j == -1 or i == j:
        raise ValueError("Markers not found - padding removal failed")
    return full[i + len(marker) : j]


# ────────────────────────────────────────────────────────────────────────
#  4. CipherPipeline – the high‑level encrypt/decrypt API
# ────────────────────────────────────────────────────────────────────────


class CipherPipeline:
    """Encrypt / decrypt using the configured pipeline."""

    def __init__(self, ctx: MachineContext, cfg: Config) -> None:
        self.ctx = ctx
        self.cfg = cfg

        self.ctx.machine._step_reflector_flag = cfg.step_reflector
    # ––– public API ––––––––––––––––––––––––––––––––––––––––––––

    def encrypt(self, msg: str) -> tuple[str, str | None]:
        """Return `(ciphertext, marker)`; marker is None when padding is off."""

        if self.cfg.do_padding:
            marker = make_marker(self.ctx.alphabet, self.cfg.marker_len)
            wrapped = marker + msg + marker
            working = pad_message(
            wrapped, self.ctx.alphabet,
            base_noise=self.cfg.base_noise,
            block=self.cfg.block,
            )
        else:
            marker = None
            working = msg

        clean = preprocess_message(working, self.ctx.alphabet)

        if self.cfg.double_pass:
            # Double-pass encryption
            stage1 = self.ctx.encipher_block(clean)
            stage2_input = stage1[::-1]
            cipher = self.ctx.encipher_block(stage2_input)
        else:
            # Single-pass encryption
            cipher = self.ctx.encipher_block(clean)

        return cipher, marker

    def decrypt(self, cipher: str, marker: str | None = None) -> str:
        if self.cfg.double_pass:
            # Double-pass decryption
            stage1 = self.ctx.encipher_block(cipher)
            stage2_input = stage1[::-1]
            full_plain = self.ctx.encipher_block(stage2_input)
        else:
            # Single-pass decryption
            full_plain = self.ctx.encipher_block(cipher)

        if self.cfg.do_padding and marker is not None:
            real = extract_message(full_plain, marker)
        else:
            real = full_plain

        return real.replace("#", " ")


# ────────────────────────────────────────────────────────────────────────
#  5. CLI helpers
# ────────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Encrypt or decrypt with Inop")
    p.add_argument("-m", "--message", metavar="TEXT", help="Plaintext to encrypt. If omitted, an interactive REPL starts.")
    p.add_argument("--double-pass", dest="double_pass", choices=["on", "off"], default="on", help="Encrypt, reverse, encrypt (on) or classic single pass (off). Default: on")
    p.add_argument("--padding", dest="padding", choices=["on", "off"], default="on", help="Add random cover traffic and hidden marker. Default: on")
    p.add_argument(
    "--moving-reflector", dest="moving_reflector", choices=["on", "off"], default="on", help="Enable rotating reflector logic. Default: off"
)

    p.add_argument("--config", metavar="FILE", help="Load machine settings from JSON instead of answering prompts.")
    p.add_argument("--interactive", action="store_true", help="Ignore any JSON file and run the interactive prompt chain.")
    return p.parse_args()


# ────────────────────────────────────────────────────────────────────────
#  6. Main entry point
# ────────────────────────────────────────────────────────────────────────


def main() -> None:
    args = parse_args()

    #  Where do we get the machine settings?
    cfg_dict = None
    cfg_path = Path(args.config) if args.config else Path("inop_config.json")

    if not args.interactive and cfg_path.exists():
        if args.config:                        # --config FILE  (no question)
            cfg_dict = load_config(cfg_path)
        else:                                  # automatic file → ask first
            ans = input(f"Found '{cfg_path}'.  Load it? (Y/n) ").strip().lower()
            if ans in {"", "y", "yes"}:
                cfg_dict = load_config(cfg_path)

    #  Build the MachineContext
    if cfg_dict:
        ctx        = MachineContext.from_config(cfg_dict)
        suite_name = cfg_dict["suite"]
        alphabet   = ctx.alphabet
    else:
        # your original interactive path
        suite_name, alphabet, rotor_pool, reflector_pool = load_suite()
        ctx = MachineContext(alphabet, rotor_pool, reflector_pool)

    #  Crypto-pipeline still built exactly the same
    cfg = Config(
        double_pass=(args.double_pass == "on"),
        do_padding=(args.padding == "on"),
        step_reflector = (args.moving_reflector == "on"),
    )
    crypto = CipherPipeline(ctx, cfg)

    # one‑shot mode ------------------------------------------------------
    if args.message is not None:
        cipher, marker = crypto.encrypt(args.message)
        blocks = [cipher[i : i + cfg.block] for i in range(0, len(cipher), cfg.block)]
        print("Encrypted:", "  ".join(blocks))
        plain = crypto.decrypt(cipher, marker)
        print("Decrypted:", plain)
        return

    # interactive REPL ---------------------------------------------------
    print(f"\nLoaded suite '{suite_name}' with alphabet length {len(alphabet)}.")
    print("Type blank line to quit.\n")
    while True:
        txt = input("\nMessage to encrypt: ")
        if not txt.strip():
            break
        cipher, marker = crypto.encrypt(txt)
        blocks = [cipher[i : i + cfg.block] for i in range(0, len(cipher), cfg.block)]
        print("\nEncrypted:", "  ".join(blocks))
        print("\nDecrypted:", crypto.decrypt(cipher, marker))


if __name__ == "__main__":
    main()