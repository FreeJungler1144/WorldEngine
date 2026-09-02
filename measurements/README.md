# Measurements

Numbers, not arguments. Every table here was produced by running something
against the real code and the real corpus, and every one states which
register item it settles and in which direction.

Reproduce with:

```sh
cmake --build build/cli
./build/cli/inop_langprobe --out probe_out
python benchmark/diacritic_measure.py --probe probe_out --out measurements
```

`inop_langprobe` is offline and headless, like `inop_benchmark`, and is
never linked into the live message pipeline. The probe writes the folded
symbol streams and the declared mark grammar; the script does the
statistics. Nothing in the analysis reimplements a fold table -- the
streams come out of `languages.cpp` through the probe, so a change to the
tables changes these numbers.

## What each experiment settles

| file | register item | direction |
|---|---|---|
| `1.1-digit-density.md` | none | scale-setting for the rest. Mark digits are 0 to 26 percent of transmitted symbols depending on language |
| `1.2-marginal-predictability.md` | **item 4, first half** | **contradicted.** Folded text is less predictable per original character than accent-stripped text in all 48 languages, by up to 0.85 bits. The proposed trailer also costs more total bits than inline marks in 44 of 46 marked languages |
| `1.3-search-space.md` | supports 1.2 | the fold grammar removes 0.34 to 0.39 bits per symbol, about a sixth of what ordinary language redundancy already gives away. Cross-check with 1.2 passes 48 of 48 |
| `1.4-language-fingerprint.md` | **item 3**, decides **item 8** | **item 8 is overkill.** Mark digits identify the language 54 percent of the time at 500 characters; the letters beside them already do it 92 percent of the time |
| `1.5-permuted-table-recovery.md` | **section E, keying the table** | **split.** Confirmed for Yoruba, Hindi and Czech at 200 to 740 characters. Not reproduced for Cantonese or Pinyin at any window the corpus allows |

## The one thing these numbers do not do

They do not clear the diacritic overlay redesign for work, and they do not
condemn it either. What they establish is that the **stated justification**
for it does not hold: the marks do not make text more predictable, they do
not leak the language beyond what the letters leak anyway, and moving them
into a trailer costs bits rather than saving them.

If the overlay is still wanted, it needs a different argument -- most
plausibly a positional one, that a mark sitting beside the letter it
describes helps an analyst place a crib. That claim is not measured here
and is not measurable without the bombe in stage 3.

## Methodology notes that apply to all of these

The corpora are 4,000 to 6,300 symbols per language. That is enough to
separate conditions measured on the same text with the same model, which
is what every comparison here does, and it is not enough to quote an
absolute figure as a property of a language. Where a result depends on
sample size, the table says so.

Every comparison is against the right baseline rather than against
nothing. Folded text is compared to accent-stripped text, not to uniform
random. The language classifier is compared to a letters-only control, not
to chance. This is deliberate: measuring a design against a strawman
credits the design with whatever the strawman was missing.
