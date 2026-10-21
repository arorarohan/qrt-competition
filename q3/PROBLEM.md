# Q3 "Black-box": problem brief for agents

Self-contained description of the problem and everything established so far. Read this before you
touch the grader.

## Rules for agents

- **Never commit or push** anything to git.
- **Never click "Save & Proceed" / Submit** and never change the code in the HackerRank editor.
  Use only the Run Code API below, which doesn't submit.
- The grader is shared by everyone on the team. Keep **≤3 concurrent runs** per agent.
- Write any files only inside `q3/` (prefer `q3/agents/<your-name>/`).

## The task (as given)

HackerRank question, Python 3:
https://www.hackerrank.com/test-v2/ae20p6kc193/questions/f4nrljkoig7

> Query the black box to maximise payoff. Beware the noise.

Implement `probe(t: float) -> list[float]`. The harness reads one float `t` from stdin, calls
`probe(t)`, and writes the returned floats one per line. A custom checker scores the array.
There is no feedback inside a single execution, so any learning happens across Run Code calls, and
the final code must be a fixed function of `t`.

## Grader mechanics (confirmed)

- 51 test cases, `t = 0.00, 0.02, …, 1.00` (index `i = round(t*50)`). One Run Code evaluates all 51.
- Per case, the checker message is
  `t=…, N=<len(array)>, raw_noisy_score=…, target_score=…`
  and the case gets a HackerRank score `hr ∈ [0, 20]`. The maximum total is 51 × 20 = 1020.
- `target_score(t)` is fixed, whatever the answer (see `TGT` in `bb_helpers.js`).
- `raw_noisy_score` = payoff plus noise. The noise is proportional to the weights (all-zero
  weights → exactly 0).
- **`hr` is deterministic and noiseless**: `hr = 20 · max(0, E[payoff] / target)`, rounded to
  0.02. The same submission always gives the same hr. So `P = hr/20 · target` is the exact
  expected payoff whenever it's positive. Negative payoffs clip to 0, so you learn nothing from
  them; measure around a base portfolio that has a positive payoff.

## The hidden model (confirmed by experiment)

The box has **K = 100 internal points** `x_k = (k + 0.5)/100`. A returned array `w` of length N is
read as a step function on N equal cells of [0,1]: `w(x_k) = w[floor(x_k · N)]`. Then

    E[payoff](w; t) = mean_k [ w(x_k) · mu_k(t) ]  -  ½ · mean_k [ w(x_k)² ]

- Separable across points: no cross terms. Checked with pairs of adjacent and far cells.
- The quadratic coefficient is exactly ½ (checked at several amplitudes and t values).
- Score is linear in payoff right up to 20 (scaling the solution by c gives the predicted 2c − c²).
- Optimum: `w(x_k) = mu_k(t)`, giving `½·mean(mu²) = target_score(t)` → hr = 20.
- With N = 100, each cell holds exactly one point, so N = 100 can reach the optimum.
  N = 64 gives 1 or 2 points per cell (unequal weights), which broke an earlier estimate.

## Results so far (Run Code totals out of 1020)

| id | strategy | total |
|---|---|---|
| S0 | `[0.5]`, `[t]` etc. | ~0 |
| S1 | N=8, w = cell means from ± spikes at amplitudes 0.1/0.5 | 862.8 |
| S2 | N=32, perturb S1 one cell at a time and solve the quadratic per cell | 997.6 |
| S3 | N=64, same as S2 but assumes equal cell weights (wrong) | 979.5 |
| S4 | N=100, perturb S2 one point at a time | **1019.4** |

S4 is in `solution.py` (51×100 table `W`; `W[i]` is the estimate of mu(·, t=i/50)). It is also
the best current estimate of `mu_k(t)`. About 260 Run Code calls were used to get here.

## Tooling

`bb_helpers.js`: paste into the question page via the browser `javascript_tool`. It defines
`runExp(body)`, `runTable(table)` (51 arrays → `{hr, P, raw}`) and `batch({name: table}, conc)`.
`javascript_tool` calls time out after ~45 s, so start long batches without awaiting
(`window.job = batch(...).then(r => window.res = r)`) and poll.

Decoding a single-point perturbation (N = 100, base `b` with payoff `P0 > 0`, point `j` changed by `d`):

    ΔP = P(b + d·e_j) − P0 = (d/100)·(mu_j − b_j) − d²/200   ⇒   mu_j = b_j + 100·ΔP/d + d/2

Data: `blackbox_data.csv` holds the early experiments (raw and hr per t). `NOTES.md` has the history.

## Open questions

1. Is the final (submitted) grading the same deterministic hr, or is it based on the noisy score?
   ("Beware the noise.") If noisy, shrinking the weights may be optimal.
2. Are the hidden/final test t values the same 51 grid points? If not, `probe` must interpolate in t.
3. Is there a closed form for mu(x, t)? (It looks like a smooth field with a sign flip near
   x ≈ 0.5 for mid t.) A formula would be more robust than a lookup table.
4. How few Run Code calls are needed to reach ≥ 99%? This matters if a similar problem appears
   under time pressure.
