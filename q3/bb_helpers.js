// Paste into the JS console (or javascript_tool) on the Q3 question page:
// https://www.hackerrank.com/test-v2/ae20p6kc193/questions/f4nrljkoig7
// Each Run Code call evaluates all 51 test cases (t = 0.00..1.00 step 0.02) and does NOT submit.

const BASE = '/recruit/attempts/90203170/questions/f4nrljkoig7/compile_tests/';

// target_score per t index (fixed, independent of the answer)
window.TGT = [0.0287,0.0247,0.0203,0.0217,0.0216,0.0161,0.019,0.0416,0.0725,0.0968,0.1234,0.1711,0.2343,0.2871,0.3154,0.3267,0.3312,0.3316,0.3318,0.3371,0.3461,0.3525,0.3534,0.3472,0.3314,0.3085,0.2831,0.2542,0.222,0.1945,0.1738,0.1515,0.1227,0.095,0.0773,0.0686,0.0623,0.0561,0.0515,0.0479,0.0443,0.0408,0.0374,0.0335,0.0297,0.0272,0.0257,0.0241,0.0232,0.0239,0.0246];

// Run arbitrary Python for the editable part (must define probe(t)).
// Returns 51 rows [t, N, raw_noisy_score, target_score, hr_score] or an error string.
window.runExp = async function (body) {
  const code = "#\n# Complete the 'probe' function below.\n#\n\n" + body + "\n";
  const p = await fetch(BASE + '?allcases=true', {
    method: 'POST', credentials: 'include',
    headers: {'Content-Type': 'application/json', 'X-Source': 'new-candidate-site'},
    body: JSON.stringify({code, language: 'python3', head_tail_editable: false}),
  }).then(r => r.json());
  const id = (p.model || p).id;
  for (let i = 0; i < 80; i++) {
    await new Promise(r => setTimeout(r, 1500));
    const m = (await fetch(BASE + '/' + id, {credentials: 'include'}).then(r => r.json())).model;
    if (m && m.status === 1 && m.testcase_message && m.testcase_message.filter(x => x).length >= 51)
      return m.testcase_message.map((s, i) => {
        const g = s.match(/t=([\d.]+), N=(\d+), raw_noisy_score=([-\d.]+), target_score=([-\d.]+)/);
        return g ? [+g[1], +g[2], +g[3], +g[4], m.score[i]] : [s, m.stderr && m.stderr[i]];
      });
  }
  return 'timeout';
};

// Run a weight table: table[i] is the array returned for t = i/50 (51 rows).
// Returns {hr, P, raw}; P = hr/20*target = noiseless expected payoff (0 if clipped).
window.runTable = async function (table) {
  const body = 'W = ' + JSON.stringify(table.map(r => r.map(v => +(+v).toFixed(5)))) +
    '\n\ndef probe(t):\n    return W[int(round(t * 50))]';
  const res = await runExp(body);
  if (typeof res === 'string' || typeof res[0][0] !== 'number') return {err: res};
  return {hr: res.map(r => r[4]), P: res.map((r, i) => r[4] / 20 * TGT[i]), raw: res.map(r => r[2])};
};

// Run many tables with limited concurrency. tables = {name: table}. Keep conc <= 4 per agent.
window.batch = async function (tables, conc = 4) {
  const keys = Object.keys(tables), out = {}; let i = 0;
  async function worker() { while (i < keys.length) { const k = keys[i++]; out[k] = await runTable(tables[k]); } }
  await Promise.all(Array.from({length: conc}, worker));
  return out;
};

// javascript_tool calls time out after ~45s: start long jobs without awaiting, e.g.
//   window.job = batch(tabs).then(r => window.res = r); 'started'
// then poll `window.res ? 'done' : 'pending'` in later calls.
