# main.py
from __future__ import annotations

import argparse
from copy import deepcopy
from dataclasses import dataclass
from secrets import choice as secure_choice, randbelow
from typing import Dict, List, Tuple

from debug import Debug
from inop import Inop
from keyboard_and_plugboard import Keyboard, Plugboard
from rotor_and_reflector import Rotor, Reflector
from suites import CURRENT
from utilities import (
    get_inop_settings,
    preprocess_message,
    reflector_dict,
    rotor_dict,
)

# ────────────────────────────────────────────────────────────────────────
#  0. Configuration & logging
# ────────────────────────────────────────────────────────────────────────


debug = Debug()
debug.toggle_global(False)


@dataclass(slots=True)
class Config:
    """Runtime switches that influence the crypto pipeline."""

    double_pass: bool = True    # encrypt‑reverse‑encrypt if True
    do_padding: bool = True     # wrap msg with marker + cover traffic
    block: int = 8              # display / padding block size
    base_noise: int = 8         # minimum random chars added when padding
    marker_len: int = 5         # hidden delimiter length


# ────────────────────────────────────────────────────────────────────────
#  1. Suite loading helpers
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
    """Return *msg* surrounded by cover traffic so that
    `(len(padded_msg) % block) == target_residue`."""

    scaled_noise = max(base_noise, int(len(msg) * 0.25))
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
        raise ValueError("Markers not found – padding removal failed")
    return full[i + len(marker) : j]


# ────────────────────────────────────────────────────────────────────────
#  4. CipherPipeline – the high‑level encrypt/decrypt API
# ────────────────────────────────────────────────────────────────────────


class CipherPipeline:
    """Encrypt / decrypt using the configured pipeline."""

    def __init__(self, ctx: MachineContext, cfg: Config) -> None:
        self.ctx = ctx
        self.cfg = cfg

    # ––– public API ––––––––––––––––––––––––––––––––––––––––––––

    def encrypt(self, msg: str) -> tuple[str, str | None]:
        """Return `(ciphertext, marker)`; marker is None when padding is off."""

        if self.cfg.do_padding:
            marker = make_marker(self.ctx.alphabet, self.cfg.marker_len)
            wrapped = marker + msg + marker
            working = pad_message(
                wrapped,
                self.ctx.alphabet,
                base_noise=self.cfg.base_noise,
                block=self.cfg.block,
            )
        else:
            marker = None
            working = msg

        # normalise input
        clean = preprocess_message(working, self.ctx.alphabet)

        # first pass
        stage1 = self.ctx.encipher_block(clean)

        # optional reverse
        stage2_input = stage1[::-1] if self.cfg.double_pass else stage1

        # second pass (or identical if single‑pass mode)
        cipher = self.ctx.encipher_block(stage2_input)
        return cipher, marker

    def decrypt(self, cipher: str, marker: str | None = None) -> str:
        # first pass
        stage1 = self.ctx.encipher_block(cipher)
        # reverse if we did so during encryption
        stage2_input = stage1[::-1] if self.cfg.double_pass else stage1
        # second / final pass
        full_plain = self.ctx.encipher_block(stage2_input)

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
    p.add_argument("--double-pass", dest="double_pass", choices=["on", "off"], default="on", help="Encrypt‑reverse‑encrypt (on) or classic single pass (off). Default: on")
    p.add_argument("--padding", dest="padding", choices=["on", "off"], default="off", help="Add random cover traffic and hidden marker. Default: off")
    return p.parse_args()


# ────────────────────────────────────────────────────────────────────────
#  6. Main entry point
# ────────────────────────────────────────────────────────────────────────


def main() -> None:
    args = parse_args()

    # build configuration from CLI flags
    cfg = Config(
        double_pass=(args.double_pass == "on"),
        do_padding=(args.padding == "on"),
    )

    # suite‑specific resources
    suite_name, alphabet, rotor_pool, reflector_pool = load_suite()

    # machine + pipeline
    ctx = MachineContext(alphabet, rotor_pool, reflector_pool)
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
    print(f"Loaded suite '{suite_name}' with alphabet length {len(alphabet)}.")
    print("Type blank line to quit.\n")
    while True:
        txt = input("Message to encrypt: ")
        if not txt.strip():
            break
        cipher, marker = crypto.encrypt(txt)
        blocks = [cipher[i : i + cfg.block] for i in range(0, len(cipher), cfg.block)]
        print("Encrypted:", "  ".join(blocks))
        print("Decrypted:", crypto.decrypt(cipher, marker))


if __name__ == "__main__":
    main()