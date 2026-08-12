// ── 폴백 샘플 데이터 ──
// data/latest.json 을 못 가져올 때만 사용된다 (배포 직후 첫 실행, 네트워크 오류 등).
const FALLBACK = {
  asOf: "샘플",
  updated: "-",
  attention: { company: "차AI헬스케어", text: "관계기업 투자 확대와 현금 감소가 동시에 진행. 카카오헬스케어 수익성 및 추가 자금조달 여부 우선 점검." },
  companies: [
    {id:'085660',name:'차바이오텍',ticker:'085660',g:'B',event:'CGT(세포·유전자치료제) 글로벌 사업 가시성 확대',tags:['Growth ↑','CGT/CDMO'],thesis:'글로벌 CGT 사업 확장성과 CDMO 수주 가시성 중심 모니터링',kpis:[['종가','-'],['취득가대비','-'],['전일대비','-'],['전주대비','-']],events:['미국 CGT 사업 관련 기사 노출'],watch:['마티카바이오 CGT CDMO 수주 계약','유상증자·CB 등 추가 자금조달','CGT 임상 파이프라인 진척'],spark:[],currency:'KRW'},
    {id:'025620',name:'차AI헬스케어',ticker:'025620',g:'A',event:'반기보고서: 투자자산 확대·본업 영업적자 지속',tags:['Profitability ↓','Liquidity ↓'],thesis:'헬스케어 플랫폼 전환은 진행 중이나 투자자산 가치와 자금조달 리스크가 핵심',kpis:[['종가','-'],['취득가대비','-'],['전일대비','-'],['전주대비','-']],events:['카카오헬스케어 150억원 추가 취득'],watch:['카카오헬스케어 영업적자 축소','추가 CB/유상증자 여부','헬스케어 자체 매출 발생'],spark:[],currency:'KRW'},
    {id:'LUMN',name:'루멘',ticker:'(미국)',g:'C',event:'주요 변동 없음',tags:['벤치마크'],thesis:'투자 검토 대상 벤치마크. 밸류에이션 매력도와 손해율 개선 추이가 핵심',kpis:[['종가','-'],['취득가대비','-'],['전일대비','-'],['전주대비','-']],events:['공시·기사 기준 특이사항 없음'],watch:['투자 검토 관점의 밸류에이션 매력도','IFP·Loss Ratio 등 핵심 지표 추이','당사 사업모델과의 시사점'],spark:[],currency:'USD'},
    {id:'LPGI',name:'Lippo General Insurance',ticker:'(인도네시아)',g:'C',event:'주요 변동 없음',tags:['관계사'],thesis:'인니 관계사. OJK 규제 변화와 자본적정성, PIKK 개정 동향이 핵심',kpis:[['종가','-'],['취득가대비','-'],['전일대비','-'],['전주대비','-']],events:['공시·기사 기준 특이사항 없음'],watch:['OJK 규제 변화','자본적정성(RBC) 동향','PIKK 개정 관련 동향'],spark:[],currency:'IDR'},
  ],
};

let payload = FALLBACK;
let chartInst = null;
const list = document.getElementById('list');

function render(f = 'ALL') {
  const arr = payload.companies.filter(x => f === 'ALL' || x.g === f);
  list.innerHTML = arr.map(x => `
    <div class="card" data-id="${x.id}">
      <div class="top">
        <div><div class="name">${x.name}</div><div class="ticker">${x.ticker}</div></div>
        <span class="badge ${x.g}">${x.g}급</span>
      </div>
      <div class="event">${x.event}</div>
      <div class="tags">${x.tags.map(t => `<span class="tag">${t}</span>`).join('')}</div>
    </div>`).join('');
  document.querySelectorAll('.card').forEach(c => c.onclick = () => detail(c.dataset.id));
}

function drawChart(spark) {
  const canvas = document.getElementById('priceChart');
  if (!canvas || !spark || spark.length < 2) return;
  if (typeof Chart === 'undefined') {
    // CDN 차단 환경(사내망 등) — 차트 없이 나머지는 정상 표시
    canvas.replaceWith(Object.assign(document.createElement('div'), {
      className: 'chart-fallback',
      textContent: '차트를 불러올 수 없습니다 (네트워크 제한)',
    }));
    return;
  }
  if (chartInst) { chartInst.destroy(); chartInst = null; }
  const up = spark[spark.length - 1] >= spark[0];
  const color = up ? '#b42318' : '#175cd3';
  chartInst = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: spark.map((_, i) => i),
      datasets: [{
        data: spark, borderColor: color, borderWidth: 1.6,
        pointRadius: 0, fill: true,
        backgroundColor: up ? 'rgba(180,35,24,.07)' : 'rgba(23,92,211,.07)',
        tension: 0.15,
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      animation: false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: { x: { display: false }, y: { display: false } },
      elements: { line: { borderJoinStyle: 'round' } },
    },
  });
}

function detail(id) {
  const x = payload.companies.find(v => v.id === id);
  const hasSpark = x.spark && x.spark.length > 1;
  document.getElementById('detail').innerHTML = `
    <div class="dt">${x.name}</div>
    <div class="dd">${x.thesis}</div>
    ${hasSpark ? `<div class="sec"><h4>3개월 추세</h4>
      <div style="height:120px"><canvas id="priceChart"></canvas></div></div>` : ''}
    <div class="sec"><h4>Key KPI</h4>
      <div class="kpis">${x.kpis.map(k => `<div class="kpi"><span>${k[0]}</span><b>${k[1]}</b></div>`).join('')}</div>
    </div>
    <div class="sec"><h4>Recent Events</h4>${x.events.map(e => `<div class="tl">${e}</div>`).join('')}</div>
    <div class="sec"><h4>Current Watch Point</h4><ul>${x.watch.map(w => `<li>${w}</li>`).join('')}</ul></div>`;
  document.getElementById('backdrop').classList.add('open');
  if (hasSpark) drawChart(x.spark);
  if (window.Telegram?.WebApp?.HapticFeedback) Telegram.WebApp.HapticFeedback.impactOccurred('light');
}

document.getElementById('close').onclick = () => document.getElementById('backdrop').classList.remove('open');
document.querySelectorAll('.chip').forEach(b => b.onclick = () => {
  document.querySelectorAll('.chip').forEach(x => x.classList.remove('on'));
  b.classList.add('on');
  render(b.dataset.f);
});

function applyPayload() {
  const sub = document.getElementById('subLine');
  if (sub) sub.textContent = `${payload.asOf} 장마감 기준 · 업데이트 ${payload.updated}`;
  document.getElementById('aCnt').textContent = payload.companies.filter(x => x.g === 'A').length;
  document.getElementById('bCnt').textContent = payload.companies.filter(x => x.g === 'B').length;
  document.getElementById('cCnt').textContent = payload.companies.filter(x => x.g === 'C').length;
  const attnCompany = document.getElementById('attnCompany');
  const attnText = document.getElementById('attnText');
  if (attnCompany && attnText && payload.attention) {
    attnCompany.textContent = payload.attention.company;
    attnText.textContent = payload.attention.text;
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
