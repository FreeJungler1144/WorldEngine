# encrypt from config
import json, sys
from copy import deepcopy

from suites                  import SUITES
from rotor_and_reflector     import Rotor, Reflector
from keyboard_and_plugboard  import Keyboard, Plugboard
from inop                    import Inop
from utilities               import preprocess_message, rotor_dict, reflector_dict

def load_cfg(path="inop_config.json") -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def build_from_cfg(cfg: dict) -> Inop:
    # look up the alphabet for this suite
    alpha = next(s["alphabet"] for s in SUITES.values() if s["name"] == cfg["suite"])
    KB = Keyboard(alpha)

    # build rotors in the configured order
    rotors = [deepcopy(rotor_dict[name]) for name in cfg["rotors"]]

    # apply per-rotor notches
    for rotor_obj, name in zip(rotors, cfg.get("notch_map", {})):
        notch = cfg.get("notch_map", {}).get(name, "")
        rotor_obj.set_notches(notch)

    # build reflector
    refl = deepcopy(reflector_dict[cfg["reflector"]])

    # plugboard pairs
    plugs = cfg.get("plugs", cfg.get("plugboard", []))
    PB = Plugboard(plugs, alpha)

    # ring settings
    rings = cfg.get("ring_set", cfg.get("ring_settings", []))

    return Inop(
        KB,
        PB,
        rotors,
        refl,
        rings,
        cfg["master_key"]
    )

# ── CLI Main Loop ─────────────────────────────────────────────────
def main():
    # Load configuration
    try:
        cfg = load_cfg()
        box = build_from_cfg(cfg)
    except Exception as e:
        sys.exit(f"Failed to load configuration: {e}")

    alpha = next(s["alphabet"] for s in SUITES.values() if s["name"] == cfg["suite"])

    print("Press Enter on an empty line to quit.")
    while True:
        plaintext = input("Plaintext > ").strip()
        if not plaintext:
            break

        # Preprocess and encrypt
        clean_pt = preprocess_message(plaintext, alpha)
        box.set_key(cfg["master_key"][:-1])
        box.reflector.rotate_to_letter(cfg["master_key"][-1])
        ciphertext = "".join(box.encypher(ch) for ch in clean_pt)
        print("\nCiphertext >")

        # Automatically decrypt the same ciphertext
        box.set_key(cfg["master_key"][:-1])
        box.reflector.rotate_to_letter(cfg["master_key"][-1])
        clean_ct = preprocess_message(ciphertext, alpha)
        decrypted = "".join(box.encypher(ch) for ch in clean_ct)
        print("\nDeciphered >", decrypted.replace("#", " "))
        print()

if __name__ == "__main__":
    main()
