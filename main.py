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
import random

debug = Debug()
debug.toggle_global(False)

# ── 0. pick suite & alphabet ─────────────────────────────────────
SUITE = CURRENT['name']        # "Legacy", "INOP-38" or "INOP-60"
ALPHA = CURRENT['alphabet']    # your string of 26/38/60 chars

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
def build_machine(alpha, rotor_pool, rotor_names, reflector_choice, rings, notches, plugs, master_key):
    # apply any per-run notch overrides
    for name, notch_chars in notches.items():
        rotor_pool[name].set_notches(notch_chars)

    # now instantiate the rotors in user-picked order
    rotor_objs = [rotor_pool[name] for name in rotor_names]

    # reflector_choice might already be an object or a name
    if isinstance(reflector_choice, Reflector):
        refl_obj = reflector_choice
    else:
        refl_obj = deepcopy(reflector_dict[reflector_choice])

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
def pad_message(msg: str, alpha: str, base_noise=6, block=8, target_residue=1):
    scaled_noise = max(base_noise, int(len(msg) * 0.25))
    residue = (len(msg) + scaled_noise) % block
    extra = (target_residue - residue) % block
    n = int(scaled_noise + extra)

    front_len = random.randint(0, n)
    suffix_len = n - front_len

    prefix = "".join(random.choice(alpha) for _ in range(front_len))
    suffix = "".join(random.choice(alpha) for _ in range(suffix_len))
    return prefix + msg + suffix

def make_marker(alpha: str, length: int = 4) -> str:
    return ''.join(random.choice(alpha) for _ in range(length))

def extract_message(full: str, marker: str) -> str:
    i = full.find(marker)
    j = full.rfind(marker)
    if i == -1 or j == -1 or j == i:
        raise ValueError("Markers not found - decryption or padding went wrong")
    return full[i + len(marker) : j]

DO_MIRROR = True
DO_PADDING = False

def rewind():
    machine.set_key(master_key[:-1])
    machine.reflector.rotate_to_letter(master_key[-1])

def enc_dec(msg: str):
    # ── 0) optional padding + marker wrap ─────────────────────────
    if DO_PADDING:
        # pick a hidden marker and wrap the message
        marker = make_marker(ALPHA, 4)
        wrapped_msg = marker + msg + marker
        padded_msg = pad_message(wrapped_msg, ALPHA)
    else:
        # no marker or padding
        marker = None
        padded_msg = msg

    # ── 1) normalize into your alphabet ────────────────────────────
    clean = preprocess_message(padded_msg, ALPHA)

    # ── 2) encrypt ─────────────────────────────────────────────────
    rewind()
    cipher = "".join(machine.encypher(ch) for ch in clean)
    blocks = [cipher[i:i+8] for i in range(0, len(cipher), 8)]
    print("\nEncrypted:", '  '.join(blocks))

    # ── 3) optional inversion ──────────────────────────────────────
    if DO_MIRROR:
        cipher_to_decrypt = cipher[::-1]
        inv_blocks = [cipher_to_decrypt[i:i+8] for i in range(0, len(cipher_to_decrypt), 8)]
        print("Inverted:", '  '.join(inv_blocks))
    else:
        cipher_to_decrypt = cipher

    # ── 4) decrypt ─────────────────────────────────────────────────
    rewind()
    full_plain = "".join(machine.encypher(ch) for ch in cipher_to_decrypt)

    # ── 5) output ──────────────────────────────────────────────────
    if DO_PADDING:
        # extract between the two markers
        try:
            real = extract_message(full_plain, marker)
        except ValueError:
            real = "<ERROR: marker not found>"
        print("\nDecrypted:", real.replace("#", " "))
    else:
        # no markers to strip—just show the direct plaintext
        print("\nDecrypted:", full_plain.replace("#", " "))

# ── run loop ─────────────────────────────────────────────────────
while True:
    txt = input("\nMessage to encrypt (blank = quit): ")
    if not txt.strip():
        break
    enc_dec(txt)