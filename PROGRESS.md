# Phase 3 progress

Branch `hardening/phase3`, cut from `hardening/phase1-2`. 15 commits, not
pushed. Not committed itself, per the brief. **Run complete.**

Full write-up: `INOPphase3report.md` in this directory. Tables in
`measurements/`.

## Done

| stage | commit | what |
|---|---|---|
| 0.1 | `5f5cd84` | gitignore gaps, DESIGN.md untracked |
| 0.2 | `3e83db8` | literal-digit separator stranded after a diacritic, fixed |
| 1 | `fb9904d` | `inop_langprobe` measurement dumper |
| 1.1-1.3 | `b6a4cec` | density, predictability, search space |
| 1.4-1.5 | `50ee1e1` | fingerprint, permuted-table recovery |
| 1 | `eaa71da` | stage summary |
| 2.1-2.2 | `a1d300c` | core purity and RNG purity at build time |
| 2.3-2.5 | `c1c1f0d` | 22 guard checks, each verified by removal |
| 2.6 | `277e412` | notch rule gets one home, GUI stops truncating |
| 2.7 | `a1af1e5` | -Werror switch, sanitizer preset, vcpkg pin, CI |
| 3 | `3e340db` | `inop_bombe`, calibrated against Legacy |
| 3 | `9a79e18` | ablation, notch sweep, transposition sweep |
| 3 | `1de156c` | crash elimination |
| - | `173452e` | no apostrophes in the text this run added |
| - | `a66b5f6` | README pass: no more dangling DESIGN.md references |

## Headlines

- Item 4 contradicted, item 8 overkill, section E half right.
- Every section 6 guard now fails by name when removed.
- Daily regeneration stops the bombe dead. The double pass costs about 7x
  and does not. The notch curve is flat. Reversal and the half-swap cost
  the same.
- The Legacy control turned up the middle-rotor double-step anomaly
  unprompted, which is the best evidence the instrument is real.

## Verification

ctest green, `--self-test` green, 3,024 benchmark cases 0 failures, bombe
self-check green, `cli-werror` clean, GUI builds. Before and after both in
the report.

## Not done, deliberately

Bombe phase 2 (steckered search with a diagonal board), the diacritic
overlay redesign, the per-message indicator, README rewrite. Reasons in the
report under "What I chose not to do".

## Environment note

The Bash tool on this machine cannot capture the stdout of this program —
`inop.exe --self-test` comes back empty through it. PowerShell works. Every
run in the report went through PowerShell.
