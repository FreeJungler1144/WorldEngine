from suites                   import CURRENT
from keyboard_and_plugboard   import Keyboard, Plugboard
from rotor_and_reflector      import Reflector
from utilities                import (
    rotor_dict, reflector_dict,
    get_inop_settings, preprocess_message
)
from copy                     import deepcopy
from debug                    import Debug
from inop                     import Inop

# --- switch to a cryptographically secure RNG -------------------
from secrets                  import choice as secure_choice, randbelow

# ─────────────────────────────────────────────────────────────────
#  Debug & globals
# ─────────────────────────────────────────────────────────────────

debug = Debug()
debug.toggle_global(False)

# ── 0. pick suite & alphabet ────────────────────────────────────
SUITE = CURRENT['name']        # "Legacy", "INOP-38" or "INOP-60"
ALPHA = CURRENT['alphabet']    # your 26/38/60‑symbol alphabet

# ── 1. filter wheel pools to this suite’s alphabet length ───────
alpha_len = len(ALPHA)
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

# ── 2. ask user for daily settings ───────────────────────────────
rotor_names, reflector_choice, ring_set, notch_map, plugs, master_key = \
    get_inop_settings(SUITE, ALPHA, rotor_pool, refl_pool)

# ── 3. build the machine ─────────────────────────────────────────

def build_machine(alpha: str,
                  rotor_pool: dict,
                  rotor_names: list[str],
                  reflector_choice,
                  rings: dict[str, int],
                  notches: dict[str, str],
                  plugs: list[tuple[str, str]],
                  master_key: str) -> Inop:
    """Return a freshly‑rewound Inop machine primed with *master_key*."""

    # apply any per‑run notch overrides
    for name, notch_chars in notches.items():
        rotor_pool[name].set_notches(notch_chars)

    # instantiate rotors in the chosen order
    rotor_objs = [rotor_pool[name] for name in rotor_names]

    # resolve reflector (object or name)
    refl_obj = reflector_choice if isinstance(reflector_choice, Reflector) \
               else deepcopy(reflector_dict[reflector_choice])

    KB = Keyboard(alpha)
    PB = Plugboard(plugs, alpha)
    return Inop(KB, PB, rotor_objs, refl_obj, rings, master_key)

machine = build_machine(
    ALPHA,
    rotor_pool,
    rotor_names,
    reflector_choice,
    ring_set,
    notch_map,
    plugs,
    master_key
)

# ── 4. padding and marker utilities ──────────────────────────────

def pad_message(msg: str, alpha: str, base_noise: int = 6,
                block: int = 8, target_residue: int = 1) -> str:
    """Pad *msg* with random cover traffic so that (len(msg) % block)
    equals *target_residue*. Uses the OS CSPRNG via *secrets*."""

    scaled_noise = max(base_noise, int(len(msg) * 0.25))
    residue      = (len(msg) + scaled_noise) % block
    extra        = (target_residue - residue) % block
    n            = scaled_noise + extra

    front_len  = randbelow(n + 1)  # 0..n inclusive
    suffix_len = n - front_len

    prefix = ''.join(secure_choice(alpha) for _ in range(front_len))
    suffix = ''.join(secure_choice(alpha) for _ in range(suffix_len))
    return prefix + msg + suffix

def make_marker(alpha: str, length: int = 4) -> str:
    """Return a random *length*-symbol marker drawn from *alpha*."""
    return ''.join(secure_choice(alpha) for _ in range(length))

def extract_message(full: str, marker: str) -> str:
    """Strip leading/trailing cover traffic by locating *marker* twice."""
    i, j = full.find(marker), full.rfind(marker)
    if i == -1 or j == -1 or j == i:
        raise ValueError("Markers not found – decryption or padding failed")
    return full[i + len(marker): j]

# ── 5. rotor‑rewind helpers ──────────────────────────────────────

def rewind() -> None:
    """Reset the machine to the daily *master_key*."""
    machine.set_key(master_key[:-1])
    machine.reflector.rotate_to_letter(master_key[-1])

# ── 6. two‑pass cipher pipeline  ─────────────────────────────────

DOUBLE_PASS = True
DO_PADDING  = True  

# ––– atomic encipher pass –––––––––––––––––––––––––––––––––––––––

def _encipher_block(text: str) -> str:
    """Encipher *text* once, assuming ASCII already mapped into *ALPHA*."""
    rewind()
    return ''.join(machine.encypher(ch) for ch in text)

# ––– public API ––––––––––––––––––––––––––––––––––––––––––––––––

def encrypt(msg: str) -> str:
    """Return ciphertext produced by *encrypt‑reverse‑encrypt* pipeline."""
    # 0) optional padding & marker wrap
    if DO_PADDING:
        marker      = make_marker(ALPHA, 4)
        wrapped_msg = marker + msg + marker
        padded_msg  = pad_message(wrapped_msg, ALPHA)
    else:
        marker     = None
        padded_msg = msg

    # 1) normalise into alphabet
    clean = preprocess_message(padded_msg, ALPHA)

    # 2) first pass
    stage1 = _encipher_block(clean)

    # 3) reverse
    stage2_input = stage1[::-1]

    # 4) second pass
    cipher = _encipher_block(stage2_input)
    return cipher, marker  # marker needed for later stripping


def decrypt(cipher: str, marker: str | None = None) -> str:
    """Invert the two‑pass pipeline and remove padding if used."""
    # 1) first pass (same direction)
    stage1 = _encipher_block(cipher)
    # 2) reverse
    stage2_input = stage1[::-1]
    # 3) second / final pass
    full_plain = _encipher_block(stage2_input)

    if DO_PADDING and marker is not None:
        try:
            real = extract_message(full_plain, marker)
        except ValueError:
            return "<ERROR: marker not found>"
        return real.replace('#', ' ')
    else:
        return full_plain.replace('#', ' ')

# ── 7. REPL driver ───────────────────────────────────────────────

if __name__ == "__main__":
    while True:
        txt = input("\nMessage to encrypt (blank = quit): ")
        if not txt.strip():
            break

        cipher, marker = encrypt(txt)
        # pretty‑print cipher blocks
        blocks = [cipher[i:i + 8] for i in range(0, len(cipher), 8)]
        print("\nEncrypted:", '  '.join(blocks))

        # immediate verification round‑trip
        plain = decrypt(cipher, marker)
        print("Decrypted:", plain)