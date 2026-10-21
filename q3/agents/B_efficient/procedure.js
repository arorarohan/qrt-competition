// Agent B "clean" procedure (validated on the grader for its first 9 calls + 1 eval: real 875.4,
// simulator 875.7). Paste bb_helpers.js first (needs TGT, batch). Then call `await step()` repeatedly
// (3 Run Code calls per step) and `await evalNow()` when you want the score of the current estimate.
// Model: P(w;t) = mean(w*mu_t) - mean(w^2)/2, hr = 20*max(0,P/target). So every unclipped (run,t)
// gives the exact linear equation  mean(w*mu_t) = P + mean(w^2)/2.

const K = 100, T = 51;
const RMS = TGT.map(g => Math.sqrt(2 * g));                 // rms(mu_t), known for free from target
const PHI = Array.from({length: K}, (_, a) => Array.from({length: K}, (_, k) =>
  a === 0 ? 1 : Math.SQRT2 * Math.cos(Math.PI * a * (k + 0.5) / K)));   // DCT-II, mean-orthonormal
const toB = w => PHI.map(p => p.reduce((s, v, k) => s + v * w[k], 0) / K);
const fromB = c => Array.from({length: K}, (_, k) => c.reduce((s, v, a) => s + v * PHI[a][k], 0));
const S = {runs: []};                                         // all (W, hr, P, mode) records
const A = 40, LT = 0.003, L0 = 1e-4;                          // modes kept, t-smoothness, ridge
const SIGNS = 3, FRAC = 0.3;                                  // interleave factor, probe size

function equations() {                                        // normalised: z = h . c_t,  c_t = coeffs/rms_t
  const M = [];
  for (const r of S.runs) for (let i = 0; i < T; i++) if (r.hr[i] > 0) {
    const w = r.W[i], q = w.reduce((s, x) => s + x * x, 0) / K;
    M.push({i, h: toB(w).slice(0, A).map(v => v / RMS[i]), z: (r.P[i] + q / 2) / RMS[i] ** 2});
  }
  return M;
}

function solve(M) {   // min sum (h.c - z)^2 + LT*sum_a ||D2_t c_a||^2 + L0*||c||^2   (conjugate gradient)
  const n = T * A, id = (i, a) => i * A + a;
  const op = x => { const o = new Float64Array(n);
    for (const m of M) { const b = m.i * A; let s = 0; for (let a = 0; a < A; a++) s += m.h[a] * x[b + a]; for (let a = 0; a < A; a++) o[b + a] += m.h[a] * s; }
    for (let a = 0; a < A; a++) { for (let i = 1; i < T - 1; i++) { const d = x[id(i - 1, a)] - 2 * x[id(i, a)] + x[id(i + 1, a)]; o[id(i - 1, a)] += LT * d; o[id(i, a)] -= 2 * LT * d; o[id(i + 1, a)] += LT * d; }
      for (let i = 0; i < T; i++) o[id(i, a)] += L0 * x[id(i, a)]; }
    return o; };
  const b = new Float64Array(n); for (const m of M) for (let a = 0; a < A; a++) b[m.i * A + a] += m.h[a] * m.z;
  const x = new Float64Array(n), r = b.slice(), p = r.slice(); let rr = r.reduce((s, v) => s + v * v, 0);
  for (let it = 0; it < 400 && rr > 1e-24; it++) { const Ap = op(p); let pAp = 0; for (let j = 0; j < n; j++) pAp += p[j] * Ap[j];
    const al = rr / pAp; for (let j = 0; j < n; j++) { x[j] += al * p[j]; r[j] -= al * Ap[j]; }
    const rn = r.reduce((s, v) => s + v * v, 0); for (let j = 0; j < n; j++) p[j] = r[j] + (rn / rr) * p[j]; rr = rn; }
  return Array.from({length: T}, (_, i) => Array.from(x.slice(i * A, (i + 1) * A)));
}

function state() {
  const C = solve(equations());
  const E = C.map(c => c.reduce((s, v) => s + v * v, 0));    // captured energy fraction ~ predicted hr/20
  const B = C.map((c, i) => fromB(c.map(v => v * RMS[i])));  // current estimate = base for probing
  const measured = Array.from({length: T}, () => new Set()), fails = Array.from({length: T}, () => ({}));
  for (const r of S.runs) if (r.mode) for (let i = 0; i < T; i++)
    if (r.hr[i] > 0) measured[i].add(r.mode[i]); else fails[i][r.mode[i]] = (fails[i][r.mode[i]] || 0) + 1;
  return {C, E, B, measured, fails};
}

async function step() {      // one batch = 3 probe runs; row i probes a not-yet-measured DCT mode around B
  const {E, B, measured, fails} = state(), n = S.runs.length, tabs = {}, modes = {};
  const done = (i, a) => measured[i].has(a) || (fails[i][a] || 0) >= 2, taken = Array.from({length: T}, () => new Set());
  for (let j = 0; j < 3; j++) {
    const pl = [];
    for (let i = 0; i < T; i++) {             // (i+j+n) % SIGNS picks one of the SIGNS lowest open modes,
      const un = [];                           // so neighbouring t rows probe different modes
      for (let a = 0; a < K && un.length <= SIGNS; a++) if (!done(i, a) && !taken[i].has(a)) un.push(a);
      const m = un[Math.min((i + j + n) % SIGNS, un.length - 1)]; pl.push(m); taken[i].add(m);
    }
    const nm = 'c' + n + '_' + j; modes[nm] = pl;
    tabs[nm] = B.map((b, i) => {             // flip sign if this mode was clipped before
      const sg = (fails[i][pl[i]] || 0) % 2 ? -1 : 1;
      const d = sg * FRAC * Math.sqrt(Math.min(1, Math.max(E[i], 0.05))) * RMS[i];
      return b.map((v, k) => +(v + d * PHI[pl[i]][k]).toFixed(5));
    });
  }
  const res = await batch(tabs, 3);
  for (const k in res) S.runs.push({name: k, W: tabs[k], hr: res[k].hr, P: res[k].P, mode: modes[k]});
  return Object.fromEntries(Object.entries(res).map(([k, v]) => [k, v.hr.reduce((a, b) => a + b, 0)]));
}

async function evalNow() {   // scores the estimate (also adds one more equation per row)
  const {B, E} = state();
  const r = await runTable(B); S.runs.push({name: 'eval', W: B, hr: r.hr, P: r.P, mode: null});
  return {real: r.hr.reduce((a, b) => a + b, 0), predicted: E.reduce((s, e) => s + 20 * Math.min(1, e), 0)};
}
