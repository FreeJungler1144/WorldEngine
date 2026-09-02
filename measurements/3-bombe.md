# 3 The bombe

The first numbers this project has about its central bet.

Produced by `inop_bombe`, an offline attack target built alongside `inop`
and `inop_benchmark` and never linked into anything that carries a message.
It manufactures its own settings, enciphers its own plaintext under them,
and then tries to recover what it just did.

```sh
inop_bombe --self-check
inop_bombe --legacy-phase1 --crib 24 --body 60
inop_bombe --inop-ablation --pool 6 --body 48 --crib 16
inop_bombe --notch-sweep --pool 6 --body 48 --crib 16
inop_bombe --transposition --pool 6 --body 48 --crib 16
```

## 0 Calibration, before anything else

The harness carries its own copy of the double pass, so that it can vary
the transposition without touching `pipeline.cpp`. If that copy drifts from
the shipped one, every number below is about a machine nobody ships.
`--self-check` compares them symbol for symbol:

| check | result |
|---|---|
| harness output equals `Pipeline`, double pass off | ok |
| harness output equals `Pipeline`, double pass on | ok |
| round trip under double pass off | ok |
| round trip under reversal | ok |
| round trip under half-swap | ok |

## 3.1 Legacy, phase 1, no plugboard. The control.

A negative result from an uncalibrated instrument is worthless. "The bombe
failed against INOP" and "the bombe is broken" produce identical output,
and the only thing separating them is a demonstrated break of a machine
already known to be breakable.

7 catalogue rotors taken 3 at a time, 26^3 start positions, rings 1 1 1,
reflector A: **3,690,960 setups**, crib at offset 0.

| crib length | setups | survivors | truth | seconds |
|---|---|---|---|---|
| 4 | 3,690,960 | 10 to 12 | FOUND | 0.54 |
| 6 | 3,690,960 | 1 | FOUND | 0.68 |
| 8 | 3,690,960 | 1 | FOUND | 0.78 |
| 12 | 3,690,960 | 1 | FOUND | 1.04 |
| 20 | 3,690,960 | 1 to 2 | FOUND | 1.96 |
| 24 | 3,690,960 | 1 to 2 | FOUND | 2.13 |
| 29 | 3,690,960 | 1 | FOUND | 2.40 |

**The instrument works.** Recovery was successful on every run. At a
4-symbol crib the survivor count is what chance predicts (3.69M / 26^4 is
about 8), and it collapses to one by 6 symbols.

### The second survivor, and why it is not noise

At a 24-symbol crib, roughly one run in eight returns two survivors.
Chance agreement on 24 symbols is 26^-24, so it is not that. Four captured
instances, all under the same rotor order:

| truth | partner |
|---|---|
| N Q L | O R L |
| I J C | J K C |
| G Z E | H A E |
| J J X | K K X |

Every one is `(p0+1, p1+1, p2)`: the first two window positions advanced by
one, the third unchanged, wrapping Z to A. That is the **middle-rotor
double-step anomaly**. A machine whose middle rotor sits on its notch steps
both wheels on the first keypress and arrives at exactly the state the
partner setting starts from, so the two are the same machine from character
one onward.

This is a known property of the historic Enigma, it was not looked for, and
it fell out of a search that had no idea it existed. That is the best
evidence available that this is a bombe rather than a program agreeing with
itself.

It also means the Legacy keyspace is slightly smaller than 26^3 per rotor
order. Not a defect -- Legacy is a museum exhibit and the anomaly is part
of the exhibit.

## 3.2 INOP-38 ablation

### The reduction, stated in full

Full-scale INOP-38 is not brute-forceable and no honest table can pretend
otherwise, so the platform is cut down deliberately and every cut is named:

| | shipped | measured here |
|---|---|---|
| rotors | 5 to 10 | 3 |
| wheel set | regenerated daily | catalogue of 6 |
| ring settings | random | all 1 |
| plugboard | up to 15 pairs | none |
| reflector orientation | key material | handed to the attacker |
| body | padded, 16-symbol markers | 48 symbols, padding off |

That leaves 120 rotor orders x 38^3 start positions = **6,584,640 setups**
per cell, which is the same order as the Legacy control and therefore
comparable to it.

### The four cells

| configuration | setups | survivors | truth | seconds | measures |
|---|---|---|---|---|---|
| wirings known, double pass off | 6,584,640 | 1 | **FOUND** | 2.90 | baseline. The bombe should work, and it does |
| wirings known, double pass on | 6,584,640 | 1 | **FOUND** | 13.54 | the cost of the double pass alone |
| wirings unknown, double pass off | 6,584,640 | 0 | MISSED | 2.92 | the cost of daily regeneration alone |
| wirings unknown, double pass on | 6,584,640 | 0 | MISSED | 13.42 | both. The shipped configuration |

Read the gaps, which is the point of the table.

**The double pass is a constant factor, not a wall.** 13.54 against 2.90 is
**4.65x**, and the truth is still recovered. That factor is exactly what it
should be: with the double pass off a candidate is rejected as soon as the
crib disagrees, so only the 16-symbol prefix is deciphered; with it on,
ciphertext position i depends on plaintext position tau(i), so there is no
prefix to test and the whole 48-symbol body goes through both passes.
96 symbols of work against 16 is 6x in theory, 4.65x measured.

**This experiment cannot price what the double pass was actually built to
destroy.** Its purpose is to remove no-self-encipherment, which is what
made *crash elimination* work -- the trick the classical bombe used, discarding
crib placements where a letter would have to encipher to itself, before any
rotor is turned. This instrument never used crash elimination; it is a
brute-force crib-dragger, and it tests every placement it is given. So the
4.65x is the honest cost to a brute-force attacker and nothing more. A
bombe built the other way, on crash elimination and the diagonal board,
would lose a filter here rather than a constant factor, and that is not
measured. Stated plainly because the difference matters: **the headline
defence has been priced against an attack that does not use the property it
removes.**

**Daily regeneration is the wall.** Both unknown-wiring cells return zero
survivors and never find the truth, because the answer is not in the search
space at all: the wheels for that day are fresh permutations that appear in no
catalogue. Zero survivors rather than wrong ones means the attacker is not
even misled -- 6.58 million candidate settings produce nothing that
reproduces a 16-symbol crib.

That is a stronger statement than it looks, and also a narrower one. It
does not say the wirings cannot be recovered; it says a bombe cannot
recover them, because a bombe searches settings and this is a search over
wirings. The arithmetic for that search is below.

### Full scale, as arithmetic

Measured throughput on this machine, single-threaded: **2,270,566 setups
per second** with the double pass off, 488,475 with it on.

| space | size |
|---|---|
| rotor orders, 5 of 10 | 2^14.88 |
| start positions 38^5 | 2^26.24 |
| ring settings 38^4 (leftmost is redundant) | 2^20.99 |
| reflector orientations | 2^5.25 |
| **settings, wirings known, no plugboard** | **2^67.36** |
| plugboard, 15 pairs of 38 | 2^78.0 |
| **settings, wirings known, with plugboard** | **2^145.36** |
| one rotor wiring, 38! | 2^148.55 |
| five rotor wirings | 2^742.76 |
| one reflector, fixed-point-free involutions on 38 | 2^72.80 |

The platform measured above is 2^22.65, so the gap to the shipped
configuration without a plugboard is **2^44.71**. At the measured rate,
enumerating 2^67.36 settings takes 8.4 x 10^13 seconds, about **2.65
million years** single-threaded, before the plugboard is considered at all.
With the plugboard it is 2^145 and the number stops meaning anything.

None of that is a security claim. It is the size of a space, and rotor
machines fall to structure rather than to enumeration.

## Notch density sweep

3 rotors, wirings known, double pass off, same crib, only the notch count
varying.

| notches per rotor | setups | survivors | truth | seconds |
|---|---|---|---|---|
| 1 | 6,584,640 | 1 | FOUND | 3.03 |
| 2 | 6,584,640 | 1 | FOUND | 3.02 |
| 3 | 6,584,640 | 1 | FOUND | 2.99 |
| 4 | 6,584,640 | 1 | FOUND | 3.07 |
| 5 | 6,584,640 | 1 | FOUND | 3.05 |

**The curve is flat.** Not nearly flat: 3.03, 3.02, 2.99, 3.07, 3.05, with
one survivor at every setting. Search cost does not rise with notch count,
and the uniqueness of the solution does not improve either.

Be precise about what that refutes. It does **not** refute the measured
rotor-motion numbers, which are correct and are about a different quantity
-- how many distinct positions each wheel visits inside one message. It
refutes the step that quietly follows them: that more motion inside a
message costs an attacker more. Against exhaustive search over start
positions it costs nothing at all, because the search enumerates the
starting state regardless of how the machine moves afterwards.

The honest reading is that the move from 3 notches to 5 buys real internal
movement and **no measured resistance to this attack**. If there is a
better argument for it, it has to be made against an attack that exploits
slow-rotor stasis, and that attack is not implemented here.

## Transposition sweep

Same crib, same wheels, same key. Three runs each, to separate the two
transpositions from timing noise.

| transposition | run 1 | run 2 | run 3 | survivors | truth |
|---|---|---|---|---|---|
| double pass off | 2.90 | 2.91 | 2.93 | 1 | FOUND |
| reversal | 13.50 | 13.51 | 13.38 | 1 | FOUND |
| half-swap | 13.46 | 13.48 | 13.53 | 1 | FOUND |

**Reversal and the half-swap cost exactly the same**, well inside a spread
that is itself under one percent. DESIGN section 5 already says the
half-swap buys only the removal of the odd-length fixed point, after the
centre-seam argument was retracted. This is an independent measurement
agreeing with that retraction: to an attacker, the two transpositions are
interchangeable, and the half-swap should continue to be credited with the
fixed point and nothing else.

## Crash elimination: the number the ablation was missing

The four-cell table prices the double pass against brute force, which is
not the attack it was built against. This prices it against the one that
is.

Before a bombe turns a rotor it slides the crib along the ciphertext and
throws out every placement where a symbol would have to encipher to itself.
A reflector without fixed points makes that impossible, so a crash proves
the placement wrong. The filter is free, and it is the thing the double
pass destroys.

200 trials per row, body 96, `--crash-elimination`.

| crib | placements | crashed, dp off | crashed, half-swap | theory `1-(37/38)^m` | true placement discarded, dp off | true placement discarded, half-swap |
|---|---|---|---|---|---|---|
| 8 | 17,800 | 19.5% | 19.1% | 19.2% | **0 of 200** | 29 of 200 (14.5%) |
| 16 | 16,200 | 33.5% | 34.9% | 34.7% | **0 of 200** | 67 of 200 (33.5%) |
| 24 | 14,600 | 46.2% | 47.7% | 47.3% | **0 of 200** | 92 of 200 (46.0%) |
| 32 | 13,000 | 56.4% | 57.3% | 57.4% | **0 of 200** | 124 of 200 (62.0%) |

Three things, in order of importance.

**The control is exact.** With the double pass off, the true placement
never crashes -- 0 of 200, at every crib length. That is not luck, it is
the no-self-encipherment property, and a single non-zero entry in that
column would have meant the harness was wrong rather than the machine. It
is the strongest validation in this document.

**The measured crash rate matches theory to within a percent** at all four
crib lengths, in both configurations. The filter itself is unaffected by
the double pass: it still removes the same third of placements, because
ciphertext still looks random against a crib.

**What the double pass changes is that the filter now eats the answer.**
With the half-swap on, the true placement crashes at the same rate as any
wrong one -- 14.5%, 33.5%, 46.0%, 62.0%, rising with crib length exactly as
a random placement would. An attacker who applies crash elimination to
INOP-38 discards the correct crib position a third of the time at a
16-symbol crib, and two thirds of the time at 32. The longer the crib, the
worse it gets, which inverts the usual relationship: against Enigma a
longer crib is a better crib.

So the double pass costs a classical attacker two separate things:

| | measured |
|---|---|
| work per candidate setting | 4.65x more |
| free placement filter | 34% saving at a 16-symbol crib, forfeited |
| penalty for using it anyway | the right answer discarded 33.5% of the time |

Multiplying the first two gives roughly **7x** against this class of
attack. That is the honest headline. It is a real cost, it is the first
number the project has for it, and it is a constant factor rather than a
wall. Daily regeneration remains the only measured defence that stops the
attack outright rather than taxing it.

## What was not built

**Phase 2, the steckered bombe.** Assume a plugboard pair, propagate the
implications of the crib through the wiring, reject on contradiction. That is
the actual idea behind the bombe, and the diagonal board is what makes it work. Not
implemented. The consequence is stated above: the double pass has been
priced against brute force, and brute force is not the attack the double
pass was designed against.

Crash elimination was in this list until it was measured, and moving it out
changed the conclusion: the double pass costs about 7x against a classical
attacker rather than the 4.65x the four-cell table alone suggested. The
remaining gap is the steckered search, and it is the piece that would say
whether a plugboard of 15 pairs survives contact with a diagonal board.

One more thing this instrument cannot see. It searches settings under a
known machine. Nothing here attacks the wirings themselves -- the
statistical route of recovering a rotor from a large body of traffic under
one key, which is what the depth problem in register item 5 actually feeds.
Daily regeneration answers a bombe. Whether it answers that is a separate
question and it is not measured anywhere in this repository.
