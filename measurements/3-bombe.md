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
made *crash elimination* work -- the classical bombe's trick of discarding
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
space at all: the day's wheels are fresh permutations that appear in no
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

## What was not built

**Phase 2, the steckered bombe.** Assume a plugboard pair, propagate the
crib's implications through the wiring, reject on contradiction. That is
the bombe's actual idea and the diagonal board is what makes it work. Not
implemented. The consequence is stated above: the double pass has been
priced against brute force, and brute force is not the attack the double
pass was designed against.

**Crash elimination.** The filter that discards a crib placement when a
symbol would have to encipher to itself. It is the cheap half of the
classical method and the half the double pass removes.

Both belong to the same piece of work, and it is the piece that would turn
the 4.65x above into a number about the defence rather than a number about
message length.
