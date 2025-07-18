# INOP Cipher Machine

Welcome to **INOP** — a rotor-based encryption machine inspired by the Enigma. This project is a tribute to cryptographic history and a playground of personal design. It features three distinct modes, custom rotors, full plugboard configuration, and an extended alphabet engine capable of handling everything from short messages to 2,000+ character memory dumps.

---

## Modes

You can select between three suites, each representing a step in the machine’s evolution:

- **[1] Legacy**  
  Faithful to the **classical Enigma** structure. 3 rotors, 26-character alphabet, minimal variation. We honor the ancestors.

- **[2] INOP-38**  
  The **first official INOP version**. Based on a 38-character alphabet and 5 rotors. Offers ring settings, notches, master key seeding, randomized message markers, and full plugboard support.

- **[3] INOP-60**  
  The **newest version**. Built on a 60-character alphabet. Supports 10 rotors, large-scale plugboards (up to 25 pairs), and variable encryption depth. Designed to withstand massive input sizes without breaking stride.


## Features

###  **Extended Alphabet Support**  
  - `Legacy` uses standard A–Z.  
  - `INOP-38` adds digits, `#` and `/`.  
  - `INOP-60` includes symbols like `+-=()[]{}<>!?@&^%$£€_` on top of it.

###  **Full Rotor Stack**  
  - Custom rotor and reflector sets are supported. You can generate them yourself or use the built-in ones per suite.
  - Each rotor supports ring settings and notch configuration.
  - Rotors are selected per message (e.g. pick 5 of 10 or 10 of 20).

###  **Plugboard**  
  - Up to 25 pairwise swaps (non-overlapping).
  - Enforces rules: no self-pairing, no reused characters, strict alphabet validation.

###  **Master Key Seeding**  
  - Each suite uses a key to control rotor starting positions and reflector angle.
  - Different messages using the same settings and key will still encrypt differently (randomized marker and padding).

###  **Padding and Marker Logic**  
  - Messages are padded with randomized noise and marked with hidden boundaries.
  - You can adjust padding intensity.

###  **Encryption & Decryption**  
  - Encrypted text appears in blocks (default: 8 chars per block).
  - Message recovery is clean and faithful—even with very long, irregular, or symbol-heavy inputs.

## A Few Notes

- This machine **is not optimized** for industrial-scale throughput.
- Encryption time varies with message length and mode:
  - Small messages: near-instant.
  - Large (2,000+ characters): under a second on modern hardware.
- INOP modes encrypt differently even with the same message and config (per-message entropy).

## Example code

Select suite:
 [1] Legacy
 [2] INOP-38
 [3] INOP-60
> 1

Available Rotors: I II III IV V VI VII
Select 3 rotors in order: ii iii vi

Available Reflectors:  A, B, C
Select reflector: b

Plugboard pairs (≤10, e.g. AB CD EF):
Pairs (Enter for none):no pe lt
3 ring settings 1-26:   10 14 16
Master key (4 chars):keys

Message to encrypt (blank = quit): Test message for github gremlins.

Encrypted: PYHGLMXC  EUZZMMHI  HHLYJYSI  TTTIFQKM  HMPPCCEG  ATFNTMDP  ILKN

Decrypted: TESTMESSAGEFORGITHUBGREMLINS


Thats all from me, if you have suggestions then dont be rude. I will **not** be implementing cython. Happy encryption!
