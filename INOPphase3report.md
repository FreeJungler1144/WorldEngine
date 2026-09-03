# INOP 2.0 phase 3 report

Branch `hardening/phase3`, cut from `hardening/phase1-2`. 15 commits, not
pushed, not merged. First commit 23:02 on 2026-09-02, last 00:17 on
2026-09-03, plus a README pass afterwards on request.

Every claim below is tagged. **[read]** quotes a file and line. **[arith]**
shows the calculation. **[measured]** means it was run and the numbers are
here. **[mechanism]** is an argument that has not been run, and there is
only one of those left in this document.

---

## Verification, before and after

Both taken on the same machine, same toolchain, MinGW g++ 16.1.0.

Before, on `hardening/phase1-2`:

```
ctest --test-dir build/cli
  1/1 Test #1: self_test ...   Passed    0.14 sec
  100% tests passed, 0 tests failed out of 1

inop --self-test --no-color
  ... all checks passed
```

After, on `hardening/phase3`:

```
cmake --build build/cli
  [1/1] Checking INOP source rules (core purity, RNG purity)
  -- INOP source rules: core purity and RNG purity both pass

ctest --test-dir build/cli
  100% tests passed, 0 tests failed out of 1

inop --self-test --no-color
  ... all checks passed          (22 new guard checks in section 12)

inop_benchmark --languages all
  3024 test case(s), 0 failure(s)

inop_bombe --self-check
  self-check passed

cmake --build build/cli-werror     0 warnings, 0 errors
cmake --build build/gui            clean
```

One environment note worth carrying forward: **the Bash tool on this
machine cannot capture the stdout of this program** — `inop.exe --self-test`
returns completely empty through it, exit 127 or 0 with no bytes. Through
PowerShell it works. Every run above went through PowerShell. Anyone
scripting this project from a bash-like shell here will conclude the
binaries are broken when they are not.

---

## Stage 0

**0.1 gitignore.** `setup/*.json`, `maria.txt`, `.claude/`, `DESIGN.md`
added. Commit `5f5cd84`.

Two register premises did not survive the check.

**Item 27 is half wrong. [read]** The GUI JSON config pattern was already
covered. `gui_config_store.cpp:23` is `const std::string kDir = "setup";`
and every Save Setup file is written to `kDir + "\\" + filename`, while
`.gitignore:20` has been `setup/` since before that file existed. No
`master_key` was ever exposed. The real gap is that the rule is implied by
a directory line rather than stated, so a change of `kDir` would silently
start publishing key material. `setup/*.json` now states it. Blanket
`*.json` was rejected: `CMakePresets.json` and `vcpkg.json` are tracked and
belong in the repo.

**Item 43 is half wrong. [read]** `.claude/` is ignored, but by
`C:\Users\pavol/.config/git/ignore`, a machine-local file outside the repo
that does not travel with a clone. `git check-ignore -v` names it. Now
stated in the repo too.

**0.2 the round-trip bug.** Real, reproduced first, fixed. Commit `3e83db8`.

**[measured]** Before the fix, five new checks failed and the fold
direction was correct in all five, so the defect is decode-only:

```
FAIL literal digit after diacritic round trip[svk] -> má/5
FAIL literal digit after diacritic round trip[fra] -> café/2
FAIL literal digit after diacritic round trip[pol] -> łódź/9
FAIL literal digit after diacritic round trip[yor] -> ẹ/2
FAIL literal digit after diacritic round trip[cmn] -> lǜ/4
```

After the fix all ten pass. Five languages cover the four shapes a mark can
take: one digit, the 0 slot, a doubled slot (`88`), a chained two-digit
mark (`64`).

**[read]** The cause: the separator-stripping branch required a *letter*
immediately before the `/`, and after a folded diacritic the previous input
byte is a digit. The fix tracks whether the emitted output just ended a
letter, at `languages.cpp:495`:
`if (c == '/' && prev_ends_letter && i + 1 < n &&` ... It also collapses the
old letter-slash-digit branch into the general one, so there is one rule
instead of two.

**Why 3,024 benchmark cases never caught it. [read]**
`benchmark_main.cpp:435` is
`bool roundtrip = fold_diacritics(mark_literal_digits(human), lang) == back;`
— the comparison happens in the folded domain, where a stranded `/`
compares equal. The harness cannot see a decode-only defect by
construction. That is a gap in the harness, not bad luck, and it is worth
fixing separately.

---

## Stage 1 — measurement

New target `inop_langprobe` dumps the folded symbol stream through the live
path, `benchmark/diacritic_measure.py` does the statistics, five markdown
tables in `measurements/`. Nothing reimplements a fold table:
`declared_marks()` exposes the real decode tables read-only, so a change to
`languages.cpp` changes these numbers. Commits `fb9904d`, `b6a4cec`,
`50ee1e1`, `eaa71da`.

### 1.1 Digit density [measured]

Mark digits run from 26.4 percent of all transmitted symbols (Yoruba) to
zero in seven languages whose corpus carries no mark at all. Separators are
at most 0.4 percent anywhere. The classifier that splits mark digits from
literal digits agrees with an independent count of non-ASCII letters in the
raw corpus at exactly 1.000 in 38 of the 44 languages that have any, which
is what makes everything downstream trustworthy.

### 1.2 Marginal predictability — settles item 4 [measured]

**Item 4 is contradicted.** Per original character, folded text is *less*
predictable than accent-stripped text in all 48 languages, by up to +0.85
bits (Cantonese; Yoruba +0.83, Pinyin +0.64). Not one language shows
folding making text more predictable. The only negative entries are
-0.0000, in languages whose corpus carries no marks, which is the control:
with the scheme inert the two pipelines agree to four decimals.

The confound is stated in the table rather than worked around: the folded
stream is lossless and the stripped stream is not. So the table also prices
the proposed overlay directly, which is the question item 4 actually asks —
not how many bits, but where they sit. **Carrying the marks in a trailer
costs more total bits than leaving them inline in 44 of the 46 languages
that carry any mark**, by up to 1,383 bits. The two exceptions have four
marked letters each in the whole corpus.

One register estimate is **confirmed**: item 4 puts the overlay at about
1.2 symbols per accent with packing. Measured floor is 0.71 to 1.29.

### 1.3 Search-space reduction [arith over measured tables]

The fold grammar removes 0.34 to 0.39 bits per symbol, 6.5 to 7.4 percent
of the space, counted exactly with a 290-state transfer matrix. **The
ordering inverts**: a bigger mark table loses *less*, because every key is
another permitted string, and the largest loss belongs to the languages
with no table at all. Most of the constraint comes from
`mark_literal_digits()` and would survive deleting every mark in the
scheme. Ordinary language redundancy is about six times larger.

Cross-check with 1.2 passes 48 of 48: measured entropy never exceeds the
grammar capacity that bounds it.

### 1.4 Language fingerprint — settles item 3, decides item 8 [measured]

| feature set | 100 chars | 500 chars | 2000 chars |
|---|---|---|---|
| marks only | 0.4080 | 0.5398 | 0.5833 |
| (letter, mark) | 0.5164 | 0.6257 | 0.6458 |
| **letters only (control)** | **0.7799** | **0.9216** | **0.9583** |

**Item 8 is overkill.** The letters already identify the language 92
percent of the time at 500 characters, which an analyst reads off any
stripped stream with no diacritic scheme present. The mark digits manage
54 percent. A fixed-ratio trailer would be defending a channel carrying
strictly less than the plaintext beside it.

The confusions are the ones a linguist would predict: Montenegrin taken for
Bosnian 60 times in 200, Norwegian for Danish 51, Serbian for Croatian 26.

### 1.5 Permuted-table recovery — settles a section E rejection [measured]

Split, and not along the axis the argument predicts.

| lang | recovered | mean chars |
|---|---|---|
| yor | 120/120 | 200 |
| hin | 120/120 | 718 |
| czr | 120/120 | 740 |
| yue | 0/120 | never, within 3,150 symbols |
| cmn | 0/120 | never, within 2,929 symbols |

Section E is right for languages whose marks are diverse and land on
distinct base letters — a few hundred characters, exactly as claimed. It is
not reproduced for the tone languages, where four or six digits sit on the
same five vowels at similar frequencies. Section E should say which case it
is describing.

Caveat stated in the table: the reference profile comes from the same
corpus file as the test windows, so these are upper bounds on recovery
speed, not estimates.

### What stage 1 does not do

It does not clear the diacritic overlay for work and does not condemn it.
It establishes that the **stated justification** does not hold. If the
overlay is still wanted it needs a positional argument — that a mark beside
the letter it describes helps place a crib — and that is `[mechanism]`, the
only one left in this document.

---

## Stage 2 — enforcement

Governing rule: for every "do not remove" there must be a test that fails
when it is removed. **Every guard below was verified by deleting or
inverting the thing it protects, rebuilding, and confirming the failure
names it.**

### 2.1 and 2.2 Source rules, at build time [measured]

`cmake/check_source_rules.cmake`, wired as a target every build depends on,
so not running the tests cannot skip it. Commit `a1d300c`.

| probe | result |
|---|---|
| `#include <random>` in `inop.cpp` | build refused, "DESIGN section 1: inop.hpp/inop.cpp may only ever contain a rotor machine", quoting `inop.cpp:4` |
| `std::hash` used in `inop.cpp` | build refused, "the cipher core carries a modern primitive", quoting `inop.cpp:6` |
| `#include <random>` in `pipeline.cpp` | build refused, "RNG purity: no fallback to rand() or std::random_device", quoting `pipeline.cpp:4` |

Comment lines are skipped by both scans, because `rng.cpp` and
`generator.cpp` both explain in prose why they do not use `rand()`, and a
checker that cannot tell an explanation from a call would force the
deletion of the comments that make the rule understandable.

`src/benchmark-debug` is exempt from the RNG scan and the exemption is
stated in the script rather than hidden. `benchmark_main.cpp` seeds an
`mt19937` to manufacture message *text*; every wheel, notch, ring and key
it uses comes from `random_settings()`. The exemption is by directory, so
an `mt19937` in `logic/` still fails the build.

### 2.3 to 2.5 One test per section 6 guard [measured]

Self-test section 12, 22 checks. Commit `c1c1f0d`.

| guard removed | what the suite says |
|---|---|
| entropy check dropped from generation | FAIL entropy_self_check runs before wheel generation |
| distinctness guard disabled | 5 FAILs, including both byte-identical checks |
| rotation guard disabled in generator | FAIL a batch containing a pure rotation is refused |
| validation moved after the file is opened | FAIL overwrite refusal leaves the existing file byte-identical |
| load-time validation disabled | FAIL load_wheel_file rejects a file whose rotors share a wiring, plus the rotation file |
| `random_notches` floor removed | FAIL random_notches(0) still yields one notch |
| `apply_suite_lock` stops forcing dp off | FAIL apply_suite_lock forces double pass, padding and moving reflector off, plus the section 5 Legacy lock |
| rotation ranked by ASCII not the declared alphabet | FAIL shift-by-1 wiring of ALPHA38 is caught as a rotation, plus 2 downstream |
| key-material detector fed a tracked name | FAIL KEY MATERIAL IS TRACKED BY GIT: README.md |

**2.4 needed a seam.** `gen_wheels()` inlined generation, validation and
writing, so the refusal path was reachable only by breaking the OS entropy
source. Split into `build_wheel_batch()`, `wheel_batch_problem()` and
`write_wheel_batch()` with no behaviour change. Overwrite is tested as the
worse case, since `std::ios::trunc` empties the target at open.

**One behaviour change, deliberate.** `build_wheel_batch()` now calls
`entropy_self_check()` itself. Previously it ran once when the maintenance
menu opened; now it also runs immediately before each batch is drawn, which
is what section 6 already claimed. `entropy_check_count()` exists so a test
can observe the call is still there.

**One harness fix fell out of the probes.** `check()` now flushes on
failure. Removing the `random_notches` floor makes a negative count index
off the front of a vector, and the buffered FAIL from the check before it
died with the process — which read as "this guard is not covered" when the
truth was the opposite. A test harness whose output vanishes when a later
test crashes is hiding evidence.

**2.5 is a ratchet, confirmed. [read]** `tracked_key_material()` reads
`.git/index` directly rather than spawning git. Two limits stated in the
comment rather than discovered later: index version 4 prefix compression
could hide a path, which fails open, and a tracked path merely containing
one of these names trips it, which fails closed. Of the two directions that
is the right one. Nothing is tracked today.

### 2.6 Single source of truth [read] [arith]

Commit `277e412`. Two constants and one predicate, nothing else in the GUI.

`registry.hpp:50` is now `constexpr int kMaxNotchesAnySuite = 5;` and
`gui_setup_panel.hpp:24` is `constexpr int kNotchBoxes = kMaxNotchesAnySuite;`.
The self-test checks that constant against the widest `max_notches` in the
suite table, so they cannot drift again. They already had: the panel
carried three boxes for a cap that had moved to five and silently truncated
generated rotors to fit.

The notch-uniqueness rule is now `duplicate_notch_symbols()` in
`registry.hpp`, beside `wiring_is_rotation()`, which is the precedent —
section 6 already records that the rotation check had to become one shared
function after the generator and the loader diverged. It returns every
clashing symbol rather than the first, which preserves the panel behaviour
exactly.

**The comment carried over from the GUI claimed that two rotors sharing a
notch measurably shrinks the keyspace. That is item 34 and it is false.**
[arith] Independent draws give C(38,3)^10, about 10^39.3; the disjoint pool
gives 38!/(3!^10 x 8!), about 10^32.3. Disjointness costs seven orders of
magnitude rather than buying any. The new comment says so and says that
whether the rule survives belongs to item 34. Moving a rule into one
place and deciding whether it is right are different jobs.

Old saved setups still load: the JSON reader fills absent boxes with empty
strings.

**Layout is [arith], not [measured].** The notch column grows from 86 to
146 pixels inside a column that is 1400 x 0.58 - 24 = 788 wide, needing
pick_w + 220 <= 420 in total. That is from the layout constants. **The
panel has not been looked at running.** It compiles; somebody should open
it.

### 2.7 Build hygiene

Commit `a1af1e5`. `INOP_WERROR` defaults OFF, ON in CI and in the new
`cli-werror` preset. Not the default deliberately: a compiler upgrade
introducing one warning should not stop the build on a machine where
somebody is trying to send a message.

**[measured]** Turning it on surfaced four warnings, all the same one, all
false: `-Wdangling-reference` on every `const Suite& su = suite("38")`.
`suite()` returns a reference into a function-local static map and keeps
nothing. `-Wno-dangling-reference` is applied only under `-Werror`, only on
GCC 13+, with the reasoning in `CMakeLists.txt`. The alternative — binding
the literal to a named local at four call sites — silences a compiler
heuristic by making the code worse. With that, the werror build is clean.

**[measured]** The sanitizer preset does not work here and the failure is
recorded rather than assumed: MinGW g++ 16.1.0 compiles with
`-fsanitize=address,undefined` and then fails to link at the CMake
compiler test, `collect2.exe: error: ld returned 1 exit status`. There is
no ASan runtime for this target. The preset is for the Linux CI job.

`vcpkg.json` gains `builtin-baseline e026127a6f1b7442c585964d4b76a51129d1a230`,
the commit of the vcpkg checkout this machine already builds against, so
pinning changes nothing today and stops drift tomorrow.

`.github/workflows/ci.yml`: linux gcc with `-Werror`, linux with both
sanitizers, windows msvc. **None of it has ever run**, which is stated at
the top of the file. The Windows job deliberately does not set
`INOP_WERROR`: this project has never seen the MSVC warning set.

The linux job is the only thing that will ever execute the POSIX branch in `rng.cpp`
branch. Being exact about what that buys: it compiles and runs the POSIX
branch, but **nothing forks**, so the fork-safety fix is still not
exercised by any test. A test that forks and compares the draws in the
child against those in the parent would close it and is not written.

---

## Stage 3 — the bombe

New target `inop_bombe`. Offline, manufactures its own key material, never
reads or writes any, never linked into the message pipeline. Commits
`3e340db`, `9a79e18`, `1de156c`. Full tables in `measurements/3-bombe.md`.

### Calibration first [measured]

The harness carries its own copy of the double pass so it can vary the
transposition without touching `pipeline.cpp`. `--self-check` compares them
symbol for symbol with the double pass on and off, and round-trips all
three transpositions. Five checks, all pass. Without this the rest is
worthless.

### Two defects found by building it

**`Plugboard() = default` produced an unusable object. [read]** Its `map_`
was empty, so `map()` returned nullptr and `Machine::encipher()` indexed
through it — an immediate segfault with no diagnostic, found with gdb after
the harness crashed before printing anything. Nothing in the program had
ever built one, so it sat there for the first caller who tried.
`inop.hpp:157` is now `Plugboard() = delete;`. This is an edit to the
frozen core and it removes something rather than adding anything, so the
section 1 rule is intact. A plugboard with no pairs is
`Plugboard({}, alpha)`.

**The harness drew plaintext from the whole alphabet including `#`**, and
`preprocess()` prunes a literal `#`, so Pipeline returned a shorter message
than went in. The pipeline draws its own markers from the alphabet minus
SPACE_SUB for exactly this reason. Same lesson, learned twice.

### 3.1 Legacy, the control [measured]

3,690,960 setups — 7 rotors taken 3 at a time, 26^3 start positions, rings
1 1 1 — in about 2 seconds. **Recovered the setting on every run**, one
survivor from a 6-symbol crib upward, 10 to 12 survivors at 4 symbols which
is what chance predicts. The instrument works.

**It also found something nobody asked it to.** At a 24-symbol crib, about
one run in eight returns a second survivor, always of the same shape:
`(p0+1, p1+1, p2)`, the first two window positions advanced by one and the
third unchanged. Four captured instances: NQL/ORL, IJC/JKC, GZE/HAE,
JJX/KKX. That is the **middle-rotor double-step anomaly** — a machine whose
middle rotor sits on its notch steps both wheels on the first keypress and
arrives at exactly the state the partner started from. Chance agreement on
24 symbols is 26^-24, so it is not coincidence. A known property of the
historic machine, falling unprompted out of a search that had no idea it
existed, is the best evidence available that this is a bombe rather than a
program agreeing with itself.

### 3.2 The four cells [measured]

Reduced platform, every reduction named: 3 rotors (shipped 5 to 10),
catalogue of 6 (shipped: regenerated daily), rings all 1, no plugboard,
reflector orientation handed to the attacker, body 48, crib 16, padding
off. 6,584,640 setups per cell.

| configuration | survivors | truth | seconds |
|---|---|---|---|
| wirings known, double pass off | 1 | **FOUND** | 2.90 |
| wirings known, double pass on | 1 | **FOUND** | 13.54 |
| wirings unknown, double pass off | 0 | MISSED | 2.92 |
| wirings unknown, double pass on | 0 | MISSED | 13.42 |

**Daily regeneration is the wall.** Zero survivors, truth never found,
because the answer is not in the search space at all — the wheels for that day are
fresh permutations in no catalogue. Zero rather than wrong survivors means
the attacker is not even misled.

**The double pass is a constant factor.** 4.65x, and the setting is still
recovered through it. The factor is exactly what the mechanism predicts:
with the double pass off a candidate dies as soon as the crib disagrees, so
only the 16-symbol prefix is deciphered; with it on there is no prefix to
test and the whole 48-symbol body goes through both passes. 96 against 16
is 6x in theory, 4.65x measured.

### Crash elimination — what the double pass actually removes [measured]

The four cells price the double pass against brute force, which is not the
attack it was built against. This prices it against the one that is. 200
trials per row, body 96.

| crib | crashed, dp off | crashed, half-swap | theory `1-(37/38)^m` | true placement lost, dp off | true placement lost, half-swap |
|---|---|---|---|---|---|
| 8 | 19.5% | 19.1% | 19.2% | **0 of 200** | 29 of 200 |
| 16 | 33.5% | 34.9% | 34.7% | **0 of 200** | 67 of 200 |
| 24 | 46.2% | 47.7% | 47.3% | **0 of 200** | 92 of 200 |
| 32 | 56.4% | 57.3% | 57.4% | **0 of 200** | 124 of 200 |

**The control is exact.** With the double pass off the true placement never
crashes, 0 of 200, at every crib length. That is the no-self-encipherment
property itself; one non-zero entry would have meant the harness was wrong
rather than the machine. It is the strongest validation in the run.

Crash rates match theory to within a percent everywhere. **What the double
pass changes is that the filter now eats the answer**: the true placement
crashes at the same rate as any wrong one, so an attacker applying crash
elimination discards the correct position a third of the time at a
16-symbol crib and nearly two thirds at 32. Longer cribs make it worse,
inverting the usual relationship.

So the double pass costs a classical attacker 4.65x in work per candidate
*and* forfeits a 34 percent free filter — roughly **7x combined**, with a
33.5 percent chance of discarding the answer if the filter is used anyway.
Real, first-ever measured, and still a constant factor rather than a wall.

### Notch density sweep [measured]

**The curve is flat.** 3.03, 3.02, 2.99, 3.07, 3.05 seconds for 1 through 5
notches, one survivor at every setting.

Be precise about what that refutes. It does **not** touch the rotor-motion
table, which is correct and is about a different quantity. It refutes the
step that quietly follows it: that more motion inside a message costs an
attacker more. Against exhaustive search over start positions it costs
nothing, because the search enumerates the starting state regardless of
what the machine does afterwards. **The move from 3 notches to 5 buys real
internal movement and no measured resistance to this attack.** A better
argument has to be made against an attack that exploits slow-rotor stasis,
and no such attack exists here.

### Transposition sweep [measured]

| | run 1 | run 2 | run 3 |
|---|---|---|---|
| double pass off | 2.90 | 2.91 | 2.93 |
| reversal | 13.50 | 13.51 | 13.38 |
| half-swap | 13.46 | 13.48 | 13.53 |

Identical inside a spread under one percent. An independent measurement
agreeing with the centre-seam retraction in `c68c261`: the half-swap should
be credited with removing the odd-length fixed point and with nothing else.

### Full scale, as arithmetic [arith]

Measured throughput, single-threaded: 2,270,566 setups per second with the
double pass off.

| space | size |
|---|---|
| rotor orders, 5 of 10 | 2^14.88 |
| start positions 38^5 | 2^26.24 |
| ring settings 38^4, leftmost redundant | 2^20.99 |
| reflector orientations | 2^5.25 |
| **settings, wirings known, no plugboard** | **2^67.36** |
| plugboard, 15 pairs of 38 | 2^78.0 |
| **with plugboard** | **2^145.36** |
| one rotor wiring, 38! | 2^148.55 |
| five rotor wirings | 2^742.76 |
| reflector, fixed-point-free involutions on 38 | 2^72.80 |

The measured platform is 2^22.65, so the gap to the shipped configuration
without a plugboard is 2^44.71 — about 2.65 million years at the measured
rate. That is the size of a space, not a security claim. Rotor machines
fall to structure, not to enumeration.

---

## Register items this run touched

| item | before | after |
|---|---|---|
| 3 | language tag rides in clear | still true, but the letters leak the language harder than the tag does. 1.4 |
| 4 | `[mechanism]`, sole justification for the overlay | **contradicted** on predictability, **confirmed** on the 1.2 symbols per accent estimate, **split** on recoverability. 1.2, 1.5 |
| 8 | fixed-ratio trailer needed | **overkill.** 1.4 |
| 27 | `*.json` uncovered | **half wrong.** Already covered by `setup/`. Now stated |
| 34 | disjointness justification false | unchanged and still open. The false claim is no longer repeated in the GUI |
| 39, 40 | section 1 and RNG rules unenforced | **closed.** Build-time checks, each verified by violation |
| 41 | section 6 guards unproven | **closed.** 22 checks, each verified by removal |
| 43 | `.claude/` neither tracked nor ignored | **half wrong.** Ignored machine-locally. Now ignored by the repo |
| 44 | nothing checks for committed key material | **closed** as a ratchet, as filed |
| 47 | no CI | **written, never run** |
| 48 | notch rule has two homes | **closed.** One home, `duplicate_notch_symbols()` |

---

## Needs owner decision

1. ~~README points at DESIGN.md about a dozen times~~ - **done after the
   run, on request**, commit `a66b5f6`. All ten references replaced: the
   reasoning is stated inline where DESIGN.md carried reasoning, and points
   at `measurements/` where it carried numbers.
2. **DESIGN.md history.** `git rm --cached` removes it going forward. Every
   past commit still contains it. Rewriting history was out of scope and
   stays out.
3. **Item 34.** The disjointness rule now has one home, which is what makes
   changing it a one-line job. Whether to change it is untouched.
4. **The GUI notch panel has not been opened.** The layout fits by
   arithmetic. Somebody should look at five boxes in a row.

## What I chose not to do, and why

- **Phase 2 of the bombe, the steckered search with a diagonal board.** The
  prompt names it as the natural stopping point. Crash elimination was
  built instead, because it measures the property the double pass actually
  removes and it fits in a morning rather than a week. What remains unknown
  is whether a 15-pair plugboard survives contact with a diagonal board.
- **The diacritic overlay redesign.** Explicitly out of scope, and stage
  1.2 removed its stated justification rather than supplying one.
- **The per-message indicator protocol (item 5).** Out of scope. Still the
  most serious item on the register and untouched by this run.
- ~~Rewriting the DESIGN.md references in the README.~~ Done afterwards on
  request, commit `a66b5f6`.
- **Fixing the benchmark harness so it can see decode-only defects.** Found
  during 0.2, named here, not fixed — it is a change to how 3,024 test
  cases are compared and deserves its own pass.
- **Item 38, parsers failing soft.** `registry.cpp:202` is still
  `if (!(is >> kind >> name >> wiring)) continue;` — a malformed line is
  silently skipped. In the register, not in this prompt.
- **A fork test for `rng.cpp`.** The CI job runs the POSIX branch but
  nothing forks. Named in the workflow file.
- **Anything that would rewrite history, unpublish more tracked files, or
  change the wire format.** None of it was needed.

## Files that are not committed, on purpose

`PROGRESS.md` and this report sit in the working tree untracked, as the
brief asked. `maria.txt`, `.claude/` and `DESIGN.md` are ignored and were
never staged. Nothing was staged that I did not change:
`git add -A`, `git add .` and `git commit -a` were never used.
