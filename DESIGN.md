# INOP — design rules and decisions

Read this before analysing, reviewing, or changing this repository.

INOP is a **thought experiment**: what a rotor cipher machine would have been
if it had been built in the 1940s with the constraints of that era honoured
rather than engineered around. It is deliberately not a modern cipher, and
most standard cryptographic advice does not apply to it.

If an analysis of this code concludes "replace this with AES", "add an HMAC",
"derive the key with Argon2", or "use libsodium", that analysis has
misunderstood the project. Those are correct recommendations for a security
product and wrong for this one. See **Non-goals** below.

---

## 1. The rule

`src/logic/inop.hpp` and `src/logic/inop.cpp` may only ever contain a rotor machine:
wired permutations, a fixed-point-free reflector, a plugboard, ring settings,
notches. **No hash functions, no block ciphers, no modern primitives.** Every
element must have a mechanical analogue that could plausibly have existed in
1940.

Everything else — padding, cover traffic, markers, the double pass, wheel
generation, randomness, the terminal interface — is *operator procedure* and
is deliberately unconstrained. It lives in `pipeline.*`, `generator.*`,
`rng.*` and `main.cpp`, where it may change freely.

This split is also the architectural rationale: the core is frozen by the rule
above, so it never needs rewriting. The prep layer is where the project
evolves.

## 2. Threat model

The adversary is a **1940s cryptanalyst**: Bletchley Park with bombes, cribs,
traffic analysis, and thousands of people, but no computers in the modern
sense and no post-war mathematics.

INOP makes **no claim** of security against a modern attacker. It has no
diffusion, its structure is well understood, and it has received no
professional cryptanalytic review. Anyone reading this should assume it
is breakable by a competent modern cryptanalyst given enough ciphertext under
one key, and should not use it for anything real.

## 3. Suites

| Suite | Alphabet | Rotors | Purpose |
|-------|----------|--------|---------|
| Legacy | 26 | 3 (fixed) | Faithful 1939 Enigma. Reference implementation and regression test. |
| INOP-38 | 38 | 5-10 | The actual machine. The operator picks the count once per session, first thing, before rings, notches or the master key are asked for — those all follow from it. |

**Legacy is locked** and must stay locked: no padding, no double pass, no
reflector motion, 5-letter output groups, and its rotor count is fixed at 3 —
it is not a suite with options. It is a museum exhibit that also serves as a
correctness check against the historic vector `BDZGOWCXLTKS` (rotors I II
III, reflector B, rings 01, key `AAA`, twelve presses of `A`). The alphabet
itself is **uppercase** — matching the convention the original wiring
tables and traffic were always published in — unlike INOP-38, whose
lowercase/numeral-suffix scheme (see the README's numeral-suffix section for
why) is a feature Legacy never touches at all. Rotor/reflector/suite names
like `I`, `B`, `26` are identifiers, not alphabet symbols, and keep whatever
case they've always had.

**Legacy's master key is 3 symbols, not 4**: one window letter per rotor, with
no orientation symbol. The historic reflector does not rotate — it is fixed
at position 0, not merely defaulted there. A 4-symbol key from an older sheet
still loads; the trailing symbol is ignored with a notice rather than
rejected outright, so old key sheets do not stop working. See
`verify_legacy_integrity()` in section 6.

Its limitations are the *point*. A Legacy machine silently drops digits from a
message, which is precisely why INOP-38's alphabet exists.

## 4. Deliberate decisions — do not "fix" these

Each of these looks like a defect and is not. They have been considered and
chosen.

**No authentication or integrity.** There is no MAC, no signature, no tamper
detection. Rotor machines had none. Out of scope.

**No key derivation function.** The master key is a rotor window setting, not
a password. Running it through PBKDF2 would be a category error.

**Ciphertext length tracks message length.** Padding scales with the message,
so length leaks for messages beyond about 30 symbols. Accepted. Padding's
purpose here is cover traffic and boundary hiding, not length hiding. (Below
~16 symbols the noise floor does bucket messages to a uniform 112.)

**Corrupting a marker destroys the message.** 32 of a typical ciphertext's
symbols are single points of failure, about 15%. Accepted; the operational
answer is retransmission under the day's backup settings, ideally reworded or
in another language.

**Legacy silently drops symbols outside its alphabet.** Historically accurate
and the motivating example for INOP-38.

**A ciphertext carrying a symbol outside the alphabet is refused, not cleaned
up.** Plaintext going the other way is laundered through `preprocess()`, which
drops what the machine has no key for, and that is the right answer there. It is
the wrong answer for a ciphertext: ciphertext is positional, so a dropped symbol
shifts every symbol after it and the message decodes to noise with nothing to
say why. The decrypt prompt therefore names the offending character and
deciphers nothing. A hyphen picked up from a wrapped line is enough to trigger
it, and under Legacy so is any digit.

**Spaces are enciphered as `#`.** This is a usability feature, not a security
one. It is understood that the space is the most frequent symbol in English
(~17.6%) and that including it *helps* an analyst. Sentences and dates
surviving a round trip is worth more here.

**A literal `#` typed by the operator is pruned in `preprocess()`, not
enciphered.** `#` is the space substitute, and `decrypt()` unconditionally
maps every `#` back to a space — so a literal `#` and a substituted space are
the same symbol once they reach the rotors, and there is no way to recover
which one an operator meant. Carrying it through would silently turn `"A#B"`
and `"A B"` into the same round trip with no error. Dropping it is treated the
same as any other symbol the machine has no key for. Markers and padding are
unaffected: both are drawn independently by the pipeline and never pass
through `preprocess()`, so they still carry `#` freely.

**No diffusion.** Changing one plaintext symbol changes exactly one ciphertext
symbol. This is inherent to rotor machines and cannot be fixed without
abandoning the design rule. It is also why a single garbled radio symbol costs
exactly one plaintext symbol rather than a whole block — the weakness and the
virtue are the same property.

**Word boundaries survive.** Known. Treated as a convenience, never as a
defence.

**Throughput is not a goal.** The machine is fast because table-baking was
cheap, not because speed matters. At 1940s speeds the binding constraint was
an operator typing.

**Cython, and modern crypto libraries generally, will never be used.**

## 5. Decisions with non-obvious rationale

**The double pass** (encipher → swap halves → encipher from a rewound state)
is the single most important line in the pipeline. The Enigma reflector
guarantees a letter never enciphers to itself, which is what let Bletchley
crib-drag. Transposing the message between the two passes makes ciphertext
position *i* depend on plaintext position *tau(i)* instead, destroying that
guarantee while keeping the whole-message map self-inverse. Removing the
transposition turns the double pass into an identity function.

**Why the transposition is a half-swap rather than a reversal.** Whatever
transposition sits between the two passes has to be an involution, or the
whole-message map stops being self-inverse and one setup sheet no longer works
in both directions. Reversal qualifies, and was what the pipeline used. But
reversal fixes the middle index of an odd-length body, and at that index the
second pass applies the same per-position involution the first one did. The two
cancel. The ciphertext symbol there equals the plaintext symbol exactly, on
every odd-length message, at a position an analyst can compute from the length
alone — the no-self-encipherment property the double pass exists to destroy,
handed straight back at a known index.

The half-swap *tau(i) = (i + L/2) mod L* is an involution for even *L* and has
no fixed index at all, since *i + L/2 = i* has no solution. It also closes a
subtler weakness of reversal: reversal pairs a position with its mirror, so
positions near the middle of a message paired with nearly identical rotor
states, and the centre of every message was its weakest region. Under the
half-swap every pairing is exactly *L/2* apart and no position is structurally
weaker than any other.

**Odd-length bodies are rounded up to even.** The half-swap is only defined on
an even length, so `encrypt()` appends one symbol drawn from the alphabet when
the body would otherwise be odd. With padding on this never fires — `pad()`
already rounds the body out to a whole number of blocks. With padding off it
does, and since there are no markers to carve against in that mode, that symbol
surfaces on the round trip as one extra symbol at the end. That is accepted. It
is also why the filler is drawn at random instead of being a fixed sentinel,
which would be a crib sitting at a known position. In the other direction,
`decrypt()` refuses an odd-length ciphertext outright when the double pass is
on: `encrypt()` cannot produce one, so an odd length means symbols went missing
in transit, and saying so beats handing back plausible noise.

One consequence worth stating plainly: this changes the ciphertext a given
setup produces. Traffic enciphered by an earlier build will not decipher under
this one. Nothing else moved — the alphabet, the wire format, the marker scheme
and existing key sheets are all unaffected.

**Daily wheel regeneration** is the other structural defence. Bletchley never
had to solve Enigma's wiring — the Poles obtained it in 1932, and every
technique afterwards assumed it as a known constant. Regenerating wheels daily
removes that constant, which is why a bombe has nothing to grip.

**Notches are chosen for movement inside one message, not for period.** One
notch per rotor does maximise the period, and the measured numbers are correct:
on 3 rotors, 1 notch gives 54,872 (=38³, the ceiling), 2 or 3 give 13,718, 19
gives 152, and zero or "all" both collapse to 38. The general form is
*38 × (38/c)^(n−1)* for *c* notches on *n* rotors. Those numbers were being read
as the objective, and they are not it.

The period is not the scarce resource. Even 5 notches across 10 rotors leave
roughly 3×10⁹, and 3 notches leave roughly 3×10¹¹ — both are past any message that
will ever be sent by orders of magnitude, so the difference between them buys
nothing. What is scarce is how much of the machine moves *while a single message
is being sent*. Rotor *j* steps about once every *(38/c)^(j−1)* characters, so a
low notch count freezes the slow rotors solid.

Measured with `inop_benchmark --rotor-motion`: distinct positions visited over a
1,000-character message, r1 being the fast rotor, 38 positions available to
each, mean of 16 random setups.

| rotors | notches | r1 | r2 | r3 | r4 | r5 | r6-r10 |
|---|---|---|---|---|---|---|---|
| 5 | 1 | 38.0 | 27.4 | 1.6 | 1.0 | 1.0 | — |
| 5 | 3 | 38.0 | 38.0 | 7.2 | 1.4 | 1.1 | — |
| 5 | 5 | 38.0 | 38.0 | 18.2 | 3.0 | 1.1 | — |
| 7 | 3 | 38.0 | 38.0 | 7.2 | 1.6 | 1.0 | 1.0 |
| 7 | 5 | 38.0 | 38.0 | 18.1 | 3.5 | 1.4 | 1.0 |
| 10 | 3 | 38.0 | 38.0 | 7.1 | 1.2 | 1.0 | 1.0 |

The default is therefore 5 notches per rotor rather than the old 3, and
`max_notches` for INOP-38 is 5. Raising it turns rotor 3 from a wheel that sees
7 of its 38 positions into one that sees 18, and moves rotor 4 from about half a
step per message to about two. `max_notches` still works as a setting, and
`random_notches()` still enforces a floor of one — a notch-less rotor never
advances the rotor to its left, which collapses the period the same way a fixed
rotor would.

**What this does not fix, stated plainly.** Rotor 4 makes roughly two steps in a
thousand characters even at 5 notches, and rotors 5 through 10 do not move at
all. Ten rotors does not mean ten moving parts, and the phrase should not be
used as though it did. Those wheels are not dead weight: with wirings
regenerated daily they are a secret static permutation, which is real key
material against an analyst who does not know the wiring. But they contribute
statically, not dynamically, and no amount of notch tuning within the cap
changes that.

**The cap of 5 is not reachable at every rotor count.** Notch symbols are
distinct across the whole machine, not merely within one rotor, because two
rotors sharing a notch symbol measurably shrinks the keyspace. The 38-symbol
alphabet is therefore a hard ceiling on *rotor count × notches*: 5 notches each
is available up to 7 rotors, 4 up to 9, and 3 at 10. `random_settings()` clamps
to what the alphabet can supply rather than refusing to generate, and the key
sheet generator says so before it writes.

If the cap of 5 is ever revisited, the precedent for many notches is Enigma
itself — the Abwehr Enigma G used wheels with 11, 15 and 17 notches, so a higher
cap would not be un-Enigma.

**The leftmost rotor ring setting is redundant.** Nothing sits to the left of it
to receive a carry, so changing its ring is equivalent to changing its starting
position and adds no key beyond it. This is the classic Enigma result and it
holds here for the same reason. No keyspace figure in this repository currently
claims otherwise — the only combinatorial figure quoted anywhere is the
plugboard one below, which is unaffected — but any future one has to divide by
38 to account for it.

**15 plugboard pairs is both the maximum and the optimum** for a 38-symbol
alphabet (2⁷⁸·⁰). Beyond the peak the count falls, mirroring the historical
result where 11 plugs beat 13 on the 26-letter Enigma.

**Baked offset tables** in `Rotor` are a pure performance choice with no
behavioural effect. Output is identical to the original Python implementation
symbol for symbol.

## 6. Guards — do not remove

These exist because a silently broken generator is the worst failure this
program can have: it does not crash, and its output looks plausible. This has
already happened once, producing 100 rotors that were all the same shift
cipher.

- `entropy_self_check()` — runs at startup, before generation, and in the
  self-test. 4096 raw bytes must cover at least 250 of the 256 byte values,
  score under 500 on a chi-square over those values (255 degrees of freedom,
  mean 255), and land within 600 set bits of the expected 16,384 on a monobit
  count. 512 draws of `secure_below(38)` must cover at least 36 of the 38
  values and score under 120 on their own chi-square (37 degrees of freedom).
  Every one of those limits has a false-alarm probability below one in a
  billion on a healthy source. The earlier limits — 64 distinct bytes of 4096,
  15 distinct draws of 512 — only caught total failure: a generator restricted
  to 20 symbols passed both of them, which is exactly the kind of quiet
  breakage this guard exists for. The rejection bounds in `secure_below()` and
  `secure_string()` are separately correct and unbiased, and are not part of
  what was tightened.
- Rotor wirings that are a pure rotation of the alphabet are rejected. That is
  a Caesar rotor, and five in series still compose to one.
- The rotation check ranks symbols by their position in the **declared**
  alphabet, never by `std::sort` of the wiring — ALPHA26 happens to already
  be in ASCII order, which is exactly what let that distinction go unnoticed
  once. It lives in a single shared function so the generator and the loader
  can never diverge on it again.
- A batch whose wirings are not all distinct is discarded, not written.
- `inop_wheels.txt` is validated on **load**, not only on generation, so a bad
  file left on disk cannot poison later sessions.
- `random_notches()` clamps to a minimum of one.
- `apply_suite_lock()` enforces the Legacy restrictions and is covered by the
  self-test.
- `verify_legacy_integrity()` — runs at startup, before the main menu, and
  again whenever Legacy is actually selected (interactively or via a loaded
  settings file). Checks the historic Enigma vector (rotors I II III,
  reflector B, rings 1 1 1, key `AAA`, twelve `A`s → `BDZGOWCXLTKS`), the
  Legacy suite descriptor itself (26 symbols / 3 rotors / block 5 /
  `historic_lock` / `notches_are_fixed`), and that `apply_suite_lock()`
  actually forces double pass, padding and moving reflector off. Any failure
  names the check and exits non-zero — Legacy silently drifting from the
  machine it claims to be would be a correctness failure, not a style issue.

**Key material is never committed.** `inop_wheels.txt`, `inop_keysheet.txt`
and `*.settings` are in `.gitignore`.

## 7. Known open items

Genuine, unresolved, and welcome:

1. **The master key is reused for a whole session.** Every message sent under
   one key is in depth with every other. A per-message indicator protocol is
   the right fix. This is the owner's decision and is deliberately unassigned.

Resolved since the last pass, kept here for history:

- ~~Reflector motion adds no period~~ — fixed. The reflector used to advance
  one position per character, which is exactly what the fast rotor does, so its
  position was a relabelling of the fast rotor position and contributed no state
  at all. It now runs on its own counter one tooth short of the alphabet: 37 of
  its 38 orientations, so the reflector and the fast rotor repeat together on
  lcm(37, 38) = 1406 rather than 38, multiplying the machine period by 37.
  Changing the step *size* would not have helped — any motion driven by the same
  per-character count is a function of *k mod 38*, so the modulus is the thing
  that had to change. Mechanically it is still a gear turning once per keypress,
  just one with fewer teeth than the wheels beside it, which keeps it inside the
  rule in section 1. Implemented as 36 plain steps followed by a jump back to
  the keyed orientation, so the hot path costs the same single increment it
  always did. The starting orientation is still real key material and still
  comes from the last symbol of the master key. Confirmed by
  `inop_benchmark --rotor-motion`, which reports the reflector visiting 37.0
  distinct positions over a 1,000-character message. The alternative in the
  original note — nesting the reflector at the end of the odometer — was not
  taken: it buys period without buying any movement inside a message, which is
  the resource section 5 establishes is actually scarce.

- ~~Interactive notch entry accepted a blank~~ — fixed, and tightened
  further: the hand-entry prompt now requires at least one notch symbol,
  full stop. Neither a blank answer nor `-` is accepted. This matches the
  floor `random_notches()` already enforced on the generator side (`if
  (count < 1) count = 1`) — a notch-less rotor never lands on a notch, so it
  never advances the rotor to its left, which collapses the whole machine's
  period the same way a fixed rotor would. `-` still means "none" when
  *displayed* (`save_settings`, the settings display) for suites whose
  wheels carry no notches at all (Legacy's historic wheels), and a
  zero-notch rotor loaded from a hand-edited settings file or key sheet
  still builds — this fix is specifically about the interactive prompt not
  being able to produce one by accident.
- ~~Digits in Legacy~~ — the per-language lookup table now exists
  (`src/logic/languages.cpp`), exactly as anticipated: it's prep-layer only,
  gated to INOP-38, and never touches Legacy. Legacy keeps the historical
  convention (`NULL EINS ZWEI …`, or simply dropping digits) as its only
  option, unchanged.

## 8. Known code-level issues

Accepted or open, but already identified — no need to report these again:

- `Machine::encipher` is `const` while mutating `mutable` rotor state, and now
  the reflector counter as well.
- `rng.cpp`'s POSIX branch holds a static `FILE*` that is never closed and is
  not thread-safe. Single-threaded program. The separate fork-safety problem in
  the same file is fixed: the buffered entropy pool used to survive a `fork()`
  intact, so parent and child drew identical bytes and therefore identical
  wheels and key sheets, with nothing to notice it. The pool is now discarded
  whenever the pid changes. That branch does not compile or run on the
  development machine, which is Windows, so it is reviewed but not exercised.
- The optional GUI still shows three notch boxes per rotor (`kNotchBoxes` in
  `gui_setup_panel.hpp`), which was written to match the INOP-38 `max_notches`
  value back when that was 3. Now that the cap is 5, the Generate Setup button
  draws up to 5 notches per rotor and then copies only the first 3 into the
  editable boxes. The resulting setup is valid and round-trips; it simply
  carries fewer notches than were drawn. Fixing it is the one-line change
  `kNotchBoxes = 5` plus whatever the panel layout needs to fit two more boxes,
  and it was left alone here only because this pass was scoped to exclude the
  GUI.
- `std::exit()` inside `ask()` bypasses destructors.
- `main.cpp` is long and could be split.
- `carve()` (pipeline.cpp) uses `find`/`rfind`; a marker sequence occurring by
  chance in the padding would break extraction. Probability is negligible at
  16 symbols from 38, but the case is unguarded.

## 9. The numeral-suffix diacritic scheme

INOP-38s alphabet is `a-z0-9#/`, with no accented letters. Dropping
diacritics on the floor loses real information — *é* and *e* stop being
distinguishable, and Pinyins four tones on *ā/á/ǎ/à* collapse to one letter.
Since INOP-38 already carries digits, the fix reuses them: an accented
letter folds to its base letter followed by a digit naming which mark it
carried.

| Digit | Diacritic | Examples |
|---|---|---|
| 1 | macron | ā → a1 |
| 2 | acute | á → a2, ć → c2, ĺ → l2 |
| 3 | caron (also reused for breve) | ǎ → a3, ň → n3, ğ → g3, ă → a3 |
| 4 | grave | à → a4 |
| 5 | circumflex | â → a5, ê → e5, ô → o5, ŵ → w5, ŷ → y5 |
| 6 | umlaut / diaeresis | ü → u6, ö → o6, ä → a6 |
| 7 | tilde | ñ → n7, ã → a7, õ → o7 |
| 8 | cedilla (consonants) / ogonek (vowels) | ç → c8, ş → s8, ą → a8, ę → e8 |
| 9 | ring-above | å → a9, ů → u9 |
| 0 | one genuinely distinct (non-diacritic) letter, at most one per language | German ß → s0, Turkish dotless ı → i0, Croatian đ → d0, Polish ł → l0, Danish ø → o0, Maltese ħ → h0 |
| 88 | dot-below, its own doubled slot | Yoruba ẹ → e88, Hindi ṭ → t88, Hindi ḥ → h88 |

Cedilla and ogonek never land on the same base letter, so sharing digit 8
between them is unambiguous. A repeated digit chains a second mark on top
of the first — Pinyins ü-with-tone stacks a tone digit after the umlaut
(*ǖ/ǘ/ǚ/ǜ → u61/u62/u63/u64*); Hungarians double-acute (*ő/ű*) and the
dot-above mark (Lithuanian *ė*, Polish/Maltese *ż*, Maltese *ċ/ġ*) each get
their own doubled slot (`22`, `33`) rather than a fresh single digit.

Ligatures (French *œ/æ*, Danish/Norwegian *æ*) decompose to their two plain
base letters in sequence (*œ → oe*, *æ → ae*) instead of using the
special-letter scheme. This is a one-way simplification — nothing decodes
an *oe* back into *œ*. Romanians comma-below (*ș/ț*) is the one mark still
dropped with no encoding at all, an accepted loss.

Turkish gets case-aware folding: plain lowercasing would turn a
word-initial capital *I* into dotted *i*, which is wrong. In Turkish, *I*
lowercases to dotless *ı*, and *İ* lowercases to dotted *i* — both letters
in "Işık" get marked `i0`, correctly.

A second pass fixes digit collision: a literal digit right after a letter
in the raw input is genuinely ambiguous with the diacritic marker (`a2`
could mean *á, folded* or *the letters a and 2*). Whenever a literal digit
directly follows a letter with no separator, a `/` gets force-inserted
between them — "Room A2" becomes "room a/2". `mark_literal_digits()` looks
past punctuation that `fold_diacritics()` will later strip, not just the
literal previous byte — "text(2024)" also gets marked ("text/(2024)"),
because the `(` disappears during folding and the digit would otherwise
land unmarked right against the letter (found via real Wikipedia-sourced
benchmark corpus text, which naturally has this pattern; synthetic test
strings never did). A diacritic-fold pair never gets a separator; a forced
literal digit always does. On decrypt, that `/` tells `resubstitute()` to
strip it and hand back a plain number instead of attempting a lookup. A
`/` is not inserted before a bare number with no preceding letter, so
"1964" stays "1964".

Encoding is lossless in a way plain accent-stripping is not: `e2` can only
have come from *é*, never from *e*, so decryption restores the accent
exactly. `fold_diacritics()` and `resubstitute()` live in
`src/logic/languages.cpp`; encoding is the same for every language via one
shared global table, so decoding must be too: `resubstitute()` tries the
active language's own table first, and falls back to a global table
(merged from every language's own table) for a mark that's legitimate in
some *other* supported language but not this one — a foreign proper noun,
a loanword, a gloss. The one real ambiguity in the merged table — digit 3
alone covers both Pinyin's caron and Romanian's breve, and the two
languages disagree on what it means — is excluded from the fallback
automatically rather than guessed at, so a Pinyin name inside a Romanian
message stays a visibly stranded digit instead of silently decoding to
the wrong character. That exclusion is computed at startup from whichever
languages' tables actually collide, not hand-maintained, so it stays
correct if a future language introduces a new collision.

Officially supported, 48 languages, alphabetical by name: Albanian,
Basque, Bosnian, Cantonese, Catalan, Creole, Croatian, Czech, Danish,
Dutch, English, Estonian, Finnish, French, German, Hindi
(Latin), Hungarian, Igbo, Indonesian, Irish, Italian, Korean (Latin),
Kurdish (Kurmanji), Latin, Lithuanian, Luxembourgish, Malay, Maltese,
Mandarin (via Pinyin), Maori, Montenegrin, Norwegian, Polish, Portuguese,
Romanian, Scottish Gaelic, Serbian (Latin), Slovak, Slovenian, Somali,
Spanish, Swahili, Swedish, Tagalog, Turkish, Welsh, Yoruba, Zulu/Xhosa.
Cantonese is a diacritic tone scheme devised for this project specifically
(not a claim to match Yale or Jyutping, which are both tone-number
systems) — six tones over the five plain vowels, reusing the same
mark-shape digits Mandarin already uses for its own four tones. Hebrew is
not currently supported — real-world Hebrew text has no niqqud (vowel
points), which an academic transliteration scheme needs to be meaningful,
and shin/sin (š/ś) can't even be disambiguated without it; revisit once
there's a real plan for non-Latin-native scripts.

## 10. Non-goals

INOP will never:

- become a block cipher, or use hash functions in the cipher core
- add authenticated encryption, KDFs, or modern primitives
- depend on a cryptographic library
- claim security against a modern adversary
- optimise for throughput as an end in itself

**The graphical interface is a deliberate, bounded exception, not a
reversal of this section.** The terminal remains the primary, complete
interface — it has zero dependencies beyond a compiler and works exactly
as it always has. The optional `INOP_WITH_GUI` build adds a single
settings-panel window (GLFW + raw OpenGL + stb_truetype, opt-in via a
terminal menu option) once GLFW became reliably buildable on the
operator's machine. It does not touch the cipher core, does not change
what a CLI-only build depends on, and does not open the door to a general
GUI framework — see `src/interface/gui.hpp`'s header comment and the
GUI-specific files under `src/interface/gui_*` for the boundary.

The category is the achievement. A better rotor machine, not a modern one.
