# Agent B: query-efficient black-box estimation

Goal: reach at least 99% of 1020 with as few Run Code calls as possible, without using the S4 mu table.
Total grader calls used by this agent: **59 of 60**.

## Key facts used
- One run gives one scalar per t. If hr > 0, then `mean(w·mu_t) = P + mean(w²)/2` is an **exact linear
  equation** in mu_t. The only source of noise is hr rounding (0.02), which is negligible.
- `P > 0` iff `rms(w − mu) < rms(mu)`. So probes must stay close to a running estimate. Probes from
  0 (or from a poor base) clip and are lost. `rms(mu_t) = sqrt(2·target_t)` is known for free.
- With a 100-dim unknown per t and one equation per run, the score after R runs is set by how much
  of mu_t's energy lies in the subspace probed so far. Hadamard/sign mixing of cells adds nothing:
  it is still one equation per t. The gains come from choosing a good basis (DCT in x) and from
  sharing information across neighbouring t.

## Procedure (procedure.js, "clean" version)
1. Represent mu_t in the DCT-II basis (mean-orthonormal), with coefficients normalised by rms_t.
2. Each batch of 3 calls: build the estimate by regularised least squares over all equations so far
   (40 modes, second-difference smoothness in t with λ=0.003, ridge 1e-4, solved by CG). Use that
   estimate B as the base. Row t probes `B_t + d·φ_a`, where a is one of the 3 lowest DCT modes not
   yet measured at that row. The choice is offset by t, so neighbouring rows probe different modes
   (the t-smoothness term fills the gaps). `d = 0.3·sqrt(captured energy)·rms_t`. If a probe
   clipped, retry the mode with the opposite sign. Skip a mode after two clips.
3. The captured energy `Σ ĉ²` per row predicts the eval score almost exactly (checked on 3 evals,
   errors of 0.1 to 0.3 points). Real eval runs are only needed as spot checks.

## Score vs Run Code calls
Calls = the number of runs whose data the estimate uses (eval runs are extra).

| calls | exploratory run (actual eval) | clean procedure |
|---:|---:|---:|
| 9  | –                        | **875.4 real** (sim 875.7) |
| 15 | 888.5 (older estimator)  | ~994 (sim) |
| 18 | 905.3                    | ~999 (sim) |
| 21 | 928 (replay)             | **≥1010 = 99% (sim)** |
| 24 | 956 (replay)             | ~1015.6 (sim) |
| 27 | 974.8                    | – |
| 30 | 994 (replay)             | ~1018 (sim) |
| 36 | 1005.5 (replay)          | – |
| 39 | 1017.9 (replay)          | ~1018.2 (sim) |
| 42 | 1019.1                   | – |
| 48 | **1019.8** (best, saved) | – |

- "replay" = the exact model applied to the first n runs of real data. It matched every real eval
  made with the same estimator to within 0.3 points.
- "sim" = the procedure run against a stand-in for the field built from all real data. The first 10
  calls of the clean procedure were run for real on the grader: across all 51 rows of all 10 runs,
  real and simulated hr differed by at most 0.08. The stand-in has no energy above about mode 40 at
  the rough small-t rows, so the late part of the simulated curve is slightly optimistic.
- The exploratory run crossed 99% at about 37 calls. It wasted about 10 calls on a probe amplitude
  that was too large (all clipped), on random-vector probes (about 1% energy each and confused the
  estimator), and on a sign-flip bug (one mode at t=0.08 clipped 6 times).

## What mattered
1. **Probing around the running estimate.** This keeps every equation unclipped and lets the probe
   size grow as the estimate improves.
2. **The DCT basis in x.** At mid and large t, mu is smooth with a sharp feature near x≈0.5. About
   15–20 modes give over 99.5%. Low DCT modes carry most of the energy, for example `−φ1`
   (60% correlation) and `φ3`.
3. **Sharing across t.** Neighbouring rows probe different modes and a smoothness penalty
   interpolates between them. This gave about 3× more modes per run at mid t, which reached 19.98/20
   by about 27 calls. The bottleneck is t ≤ 0.08 (rows 0–5, tiny target), where mu is rough and
   needs about 20–30 modes measured one per run. That sets the floor of about 21 calls.
4. Simulated variants gave no gain from interleave factor 2 or 4, or from rows-0–7-independent vs
   all-shared. Probe size 0.3–0.5·sqrt(E) works best (0.7 or more hurts; 0.2 stalls on skipped modes).

## Files
- `solution.py`: best table (Run Code 1019.84 / 1020, from 48 calls), same format as q3/solution.py.
- `coeffs.json` + `build_solution.py`: 51×40 DCT coefficients and the expander. Checksums match
  the evaluated table.
- `procedure.js`: the clean procedure (paste after bb_helpers.js; `await step()` / `await evalNow()`).
