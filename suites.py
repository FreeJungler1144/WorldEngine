from typing import Dict

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
