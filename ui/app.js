const FALLBACK_ROWS = [
  {tokens:128,cold:40.5,wake:9.5,speedup:'4.3×'},
  {tokens:512,cold:47.6,wake:9.8,speedup:'4.9×'},
  {tokens:1024,cold:80.7,wake:10.5,speedup:'7.7×'},
  {tokens:2048,cold:146.3,wake:10.7,speedup:'13.7×'}
];

function renderChart(rows){
  const chart = document.querySelector('#chart');
  chart.innerHTML = '';
  const max = Math.max(...rows.map(r => r.cold)) * 1.05;
  rows.forEach(row => {
    const group = document.createElement('div'); group.className = 'bar-group';
    group.innerHTML = `<div class="bar cold" style="height:${row.cold/max*100}%"><span>${row.cold.toFixed(0)}ms</span></div><div class="bar wake" style="height:${row.wake/max*100}%"><span>${row.speedup}</span></div><div class="bar-label">${row.tokens.toLocaleString()}</div>`;
    chart.appendChild(group);
  });
}

function updateHeadline(rows){
  const top = rows[rows.length - 1];
  const featured = document.querySelector('.metric-card.featured strong');
  if (featured && top) featured.innerHTML = `${top.speedupValue.toFixed(1)}<span>×</span>`;
  const sub = document.querySelector('.metric-card.featured small');
  if (sub && top) sub.textContent = `At ${top.tokens.toLocaleString()} context tokens (live benchmark file)`;
}

async function loadLiveEvidence(){
  try {
    const response = await fetch('../benchmarks/results/long_context_resume.json', {cache:'no-store'});
    if (!response.ok) throw new Error(String(response.status));
    const data = await response.json();
    const rows = data.rows.map(r => ({
      tokens: r.context_tokens,
      cold: r.cold_total_seconds * 1000,
      wake: r.wake_total_seconds * 1000,
      speedup: `${r.resume_speedup.toFixed(1)}×`,
      speedupValue: r.resume_speedup,
      exact: r.fidelity_exact_tokens,
    }));
    renderChart(rows);
    updateHeadline(rows);
    const foot = document.querySelector('.chart-foot span:last-child');
    if (foot) foot.textContent = `Live from benchmarks/results/long_context_resume.json · exact match at every point: ${rows.every(r=>r.exact)}`;
  } catch (_err) {
    renderChart(FALLBACK_ROWS);
  }
}

loadLiveEvidence();

function copyClaim(){
  const claim='DecaState manages the lifecycle, persistence, branching, and portability of AI execution state.';
  navigator.clipboard?.writeText(claim);
  const toast=document.querySelector('#toast'); toast.classList.add('show'); setTimeout(()=>toast.classList.remove('show'),2200);
}
