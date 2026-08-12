// ── 폴백 샘플 데이터 ──
const FALLBACK = {
  asOf: "샘플", updated: "-", fx: "",
  attention: { company: "차AI헬스케어", text: "관계기업 투자 확대와 현금 감소가 동시에 진행." },
  companies: [
    {id:'085660',name:'차바이오텍',ticker:'085660',g:'B',event:'주요 변동 없음',tags:['+0.0%','당사 투자'],
     thesis:'CGT(세포·유전자치료제)/CDMO(위탁개발생산) 사업 진행 중',
     kpis:[['종가','-',null],['취득가','-',null],['취득가대비','-',null],['전일대비','-',null],
           ['전주대비','-',null],['거래량(20일比)','-',null],['시가총액','-',null],['52주 고점대비','-',null]],
     events:['공시·기사 기준 특이사항 없음'],watch:[],spark:[],avgCost:null,currency:'KRW',marketCloseCaption:''},
  ],
};

let payload = FALLBACK;
let chartInst = null;
const list = document.getElementById('list');

const GRADE_LABEL = { A: '높음', B: '중간', C: '낮음' };

function signClass(v) {
  if (typeof v !== 'string') return '';
  if (v.startsWith('+')) return 'val-up';
  if (v.startsWith('-')) return 'val-down';
  return '';
}

function kpiCell([label, value, sub]) {
  const cls = signClass(value);
  return `<div class="kpi"><span>${label}</span><b class="${cls}">${value}</b>${sub ? `<div class="kpi-sub">${sub}</div>` : ''}</div>`;
}

function render(f = 'ALL') {
  const arr = payload.companies.filter(x => f === 'ALL' || x.g === f);
  list.innerHTML = arr.map(x => `
    <div class="card" data-id="${x.id}">
      <div class="top">
        <div><div class="name">${x.name}</div><div class="ticker">${x.ticker}</div></div>
        <span class="badge ${x.g}">${GRADE_LABEL[x.g] || x.g}</span>
      </div>
      <div class="event">${x.event}</div>
      <div class="tags">${x.tags.map((t, i) => `<span class="tag ${i === 0 ? signClass(t) : ''}">${t}</span>`).join('')}</div>
    </div>`).join('');
  document.querySelectorAll('.card').forEach(c => c.onclick = () => detail(c.dataset.id));
}

function drawChart(spark, avgCost) {
  const canvas = document.getElementById('priceChart');
  if (!canvas || !spark || spark.length < 2) return;
  if (typeof Chart === 'undefined') {
    canvas.replaceWith(Object.assign(document.createElement('div'), {
      className: 'chart-fallback', textContent: '차트를 불러올 수 없습니다',
    }));
    return;
  }
  if (chartInst) { chartInst.destroy(); chartInst = null; }
  const up = spark[spark.length - 1] >= spark[0];
  const color = up ? '#b42318' : '#175cd3';
  const datasets = [{
    data: spark, borderColor: color, borderWidth: 1.6, pointRadius: 0, fill: true,
    backgroundColor: up ? 'rgba(180,35,24,.07)' : 'rgba(23,92,211,.07)', tension: 0.15,
  }];
  if (avgCost) {
    datasets.push({
      data: spark.map(() => avgCost), borderColor: '#98a2b3', borderWidth: 1,
      borderDash: [4, 3], pointRadius: 0, fill: false,
    });
  }
  chartInst = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: { labels: spark.map((_, i) => i), datasets },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: { x: { display: false }, y: { display: false } },
    },
  });
}

function sourceRow(s, i) {
  return `<div class="src-row" data-idx="${i}">
    <div class="src-top"><span class="src-tag">${s.source || '출처'}</span>
      ${s.date ? `<span class="src-date">${s.date}</span>` : ''}</div>
    <div class="src-title">${s.title}</div>
  </div>`;
}

function detail(id) {
  const x = payload.companies.find(v => v.id === id);
  const hasSpark = x.spark && x.spark.length > 1;
  const isForeign = x.currency && x.currency !== 'KRW';
  const fxLine = isForeign
    ? `<div class="fxline">${payload.fx || ''}${x.marketCloseCaption ? ' · ' + x.marketCloseCaption : ''}</div>`
    : '';
  const hasSources = x.sources && x.sources.length > 0;
  const eventsHtml = hasSources
    ? x.sources.map(sourceRow).join('')
    : x.events.map(e => `<div class="tl">${e}</div>`).join('');
  document.getElementById('detail').innerHTML = `
    <div class="dt">${x.name}</div>
    <div class="dd">${x.thesis}</div>
    ${fxLine}
    ${hasSpark ? `<div class="sec"><h4>3개월 추세 ${x.avgCost ? '<span class="legend-dash">- - 취득가</span>' : ''}</h4>
      <div style="height:120px"><canvas id="priceChart"></canvas></div></div>` : ''}
    <div class="sec"><h4>핵심 지표</h4>
      <div class="kpis">${x.kpis.map(kpiCell).join('')}</div>
    </div>
    <div class="sec"><h4>최근 공시·기사</h4>${eventsHtml}</div>
    ${x.watch.length ? `<div class="sec"><h4>앞으로 볼 포인트</h4><ul>${x.watch.map(w => `<li>${w}</li>`).join('')}</ul></div>` : ''}`;
  document.getElementById('backdrop').classList.add('open');
  if (hasSpark) drawChart(x.spark, x.avgCost);
  if (hasSources) {
    document.querySelectorAll('.src-row').forEach(el => {
      el.onclick = () => openExternal(x.sources[+el.dataset.idx].url);
    });
  }
  if (window.Telegram?.WebApp?.HapticFeedback) Telegram.WebApp.HapticFeedback.impactOccurred('light');
}

document.getElementById('close').onclick = () => document.getElementById('backdrop').classList.remove('open');
document.querySelectorAll('.chip').forEach(b => b.onclick = () => {
  document.querySelectorAll('.chip').forEach(x => x.classList.remove('on'));
  b.classList.add('on');
  render(b.dataset.f);
});

function openExternal(url) {
  if (!url) return;
  if (window.Telegram?.WebApp?.openLink) {
    Telegram.WebApp.openLink(url);
  } else {
    window.open(url, '_blank');
  }
}

function applyPayload() {
  const sub = document.getElementById('subLine');
  if (sub) sub.textContent = `${payload.asOf} 장마감 기준 · 업데이트 ${payload.updated}`;
  document.getElementById('aCnt').textContent = payload.companies.filter(x => x.g === 'A').length;
  document.getElementById('bCnt').textContent = payload.companies.filter(x => x.g === 'B').length;
  document.getElementById('cCnt').textContent = payload.companies.filter(x => x.g === 'C').length;

  const attnBox = document.getElementById('attnBox');
  const attnCompany = document.getElementById('attnCompany');
  const attnText = document.getElementById('attnText');
  const attnLink = document.getElementById('attnLink');
  if (attnBox && attnCompany && attnText && payload.attention) {
    attnCompany.textContent = payload.attention.company;
    attnText.textContent = payload.attention.text;
    const url = payload.attention.url;
    if (url) {
      attnBox.classList.add('clickable');
      attnLink.style.display = 'block';
      attnBox.onclick = () => openExternal(url);
    } else {
      attnBox.classList.remove('clickable');
      attnLink.style.display = 'none';
      attnBox.onclick = null;
    }
  }
  render();
}

async function load() {
  try {
    const res = await fetch('./data/latest.json', { cache: 'no-store' });
    if (res.ok) payload = await res.json();
  } catch (e) {
    console.warn('데이터 로드 실패, 샘플로 표시:', e);
  }
  applyPayload();
}

if (window.Telegram?.WebApp) { Telegram.WebApp.ready(); Telegram.WebApp.expand(); }
load();
