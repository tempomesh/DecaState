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

// ---- API Gateway audit panel: live gateway first, real snapshot fallback ----
function tok(n){ return (n==null)?'—':Number(n).toLocaleString(); }
function gwCard(r){
  const u = r.usage||{};
  const hit = r.provider_cache_hit;
  const real = r.mode!=='selftest';
  const save = r.saving||{};
  const model = r.model||'—';
  const status = r.status;
  const saveLine = (save.net_input_saving_usd!=null)
    ? `$${save.net_input_saving_usd} <span class="gw-hash">illustration</span>` : '—';
  return `<div class="gw-card">
    <div class="gw-top"><strong>${model}</strong>
      <span class="gw-mode ${real?'real':'selftest'}">${real?'REAL FORWARD · '+status:'SELF-TEST · echo'}</span></div>
    <div class="gw-rows">
      <div class="gw-row">Prompt integrity <b class="${r.prompt_integrity==='unchanged'?'ok':'miss'}">${r.prompt_integrity||'—'}</b></div>
      <div class="gw-row">Byte-identical forward <b class="${r.byte_identical_forward?'ok':'miss'}">${r.byte_identical_forward?'✓ verified':'✗'}</b></div>
      <div class="gw-row">Provider cache <b class="${hit?'hit':'miss'}">${hit?'HIT':'miss'}</b></div>
      <div class="gw-row">cache read / creation <b>${tok(u.cache_read_input_tokens)} / ${tok(u.cache_creation_input_tokens)}</b></div>
      <div class="gw-row">input / output <b>${tok(u.input_tokens)} / ${tok(u.output_tokens)}</b></div>
      <div class="gw-row">est. input saving <b>${saveLine}</b></div>
      <div class="gw-row">body sha256 <b class="gw-hash">${(r.request_body_sha256||'').slice(0,16)}…</b></div>
    </div></div>`;
}
const GW_PRICING = {'claude-opus-5':5,'claude-opus-4-8':5,'claude-sonnet-5':2,'claude-sonnet-4-6':3,'claude-haiku-4-5':1,'claude-fable-5':10};
async function renderGatewayTotals(records, live){
  const el = document.querySelector('#gw-totals');
  if (!el) return;
  let t = null;
  if (live) {
    for (const port of [8799, 8787]) {
      try { const r = await fetch(`http://127.0.0.1:${port}/savings`,{cache:'no-store'});
        if (r.ok){ t = await r.json(); break; } } catch(_e){}
    }
  }
  if (!t) { // compute from records client-side (same math, same honesty)
    t = {requests:0, cache_read_tokens:0, est_net_saving_usd:0};
    for (const r of records){
      if (r.mode==='selftest' || r.status!==200) continue;
      const u=r.usage||{}; const rate=GW_PRICING[r.model];
      const read=u.cache_read_input_tokens||0, write=u.cache_creation_input_tokens||0;
      t.requests++; t.cache_read_tokens+=read;
      if (rate!=null) t.est_net_saving_usd += (read*(rate-rate*0.1) - write*(rate*0.25))/1e6;
    }
    t.est_net_saving_usd = Math.round(t.est_net_saving_usd*1e6)/1e6;
  }
  if (!t.requests){ el.innerHTML=''; return; }
  el.innerHTML = `
    <div class="gw-total"><b>${t.requests}</b><span>real requests measured</span></div>
    <div class="gw-total"><b>${Number(t.cache_read_tokens).toLocaleString()}</b><span>cached tokens reused (provider-reported)</span></div>
    <div class="gw-total accent"><b>$${t.est_net_saving_usd}</b><span>est. net input saving · provider price delta</span></div>
    <div class="gw-total"><span class="gw-hash">read ~0.1× · write ~1.25× · published pricing · not a bill</span></div>`;
}
async function loadGatewayAudit(){
  const grid = document.querySelector('#gw-grid');
  const status = document.querySelector('#gw-status');
  const source = document.querySelector('#gw-source');
  let records=null, live=false;
  for (const port of [8799, 8787]) {
    try {
      const res = await fetch(`http://127.0.0.1:${port}/audit`, {cache:'no-store'});
      if (res.ok){ records=(await res.json()).records; live=true; break; }
    } catch(_e){}
  }
  if (!records) {
    try { const res = await fetch('./gateway_audit.json',{cache:'no-store'});
      if (res.ok) records=(await res.json()).records; } catch(_e){}
  }
  if (!records || !records.length){
    status.textContent='OFFLINE'; grid.innerHTML='<div class="gw-card"><div class="gw-rows"><div class="gw-row">Start it with <b class="gw-hash">decastate gateway</b></div></div></div>';
    source.textContent='audit source: none'; return;
  }
  status.textContent = live?'● LIVE':'SNAPSHOT';
  status.className = live?'live':'snap';
  source.textContent = live?'audit source: live gateway /audit':'audit source: recorded gateway_audit.json';
  grid.innerHTML = records.slice(-4).reverse().map(gwCard).join('');
  renderGatewayTotals(records, live);
}
loadGatewayAudit();

// ---- API added-savings card (top metrics): from the measured 3-leg experiment ----
async function loadApiSavingCard(){
  const pct=document.querySelector('#api-saving-pct'), sub=document.querySelector('#api-saving-sub'),
        bar=document.querySelector('#api-saving-bar');
  if(!pct) return;
  try{
    const res=await fetch('../benchmarks/results/api_added_savings.json',{cache:'no-store'});
    if(!res.ok) throw new Error(res.status);
    const d=await res.json(); const a=d.anthropic||{}; const o=d.openai||{};
    if(a.added_saving_pct!=null){
      pct.innerHTML=`+${a.added_saving_pct}<span>%</span>`;
      bar.style.width=Math.min(100,a.added_saving_pct)+'%';
      const oc=o.rows?` · OpenAI: ${Number(o.rows[1].cached).toLocaleString()} tok auto-cached (measured)`:'';
      sub.textContent=`Added for NON-caching Anthropic clients (2-req pair, provider-billed)${oc}`;
    } else { pct.textContent='n/a'; sub.textContent='run scripts/api_added_savings_proof.py'; }
  }catch(_e){ pct.textContent='n/a'; sub.textContent='experiment results not found'; }
}
loadApiSavingCard();

function copyClaim(){
  const claim='DecaState manages the lifecycle, persistence, branching, and portability of AI execution state.';
  navigator.clipboard?.writeText(claim);
  const toast=document.querySelector('#toast'); toast.classList.add('show'); setTimeout(()=>toast.classList.remove('show'),2200);
}
