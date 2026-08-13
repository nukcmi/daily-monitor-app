// ── 폴백 샘플 데이터 (data/latest.json fetch 실패 시에만 사용) ──
const FALLBACK = {
  updated: "-", fx: "",
  attention: { company: "-", text: "데이터를 불러오는 중입니다.", url: null },
  companies: [],
};

let payload = FALLBACK;
let chartInst = null;
const list = document.getElementById('list');

const GRADE_LABEL = { A: '높음', B: '중간', C: '낮음' };
const GRADE_CLASS = { A: 'high', B: 'mid', C: 'low' };

function signClass(v) {
  if (typeof v !== 'string' || v === '-') return '';
  if (v.startsWith('+')) return 'val-up';
  if (v.startsWith('-') && v.length > 1 && /\d/.test(v[1])) return 'val-down';
  return '';
}

function impactBadge(g) {
  const cls = GRADE_CLASS[g] || 'low';
  return `<span class="impact-badge impact-${cls}"><span class="impact-dot"></span>${GRADE_LABEL[g] || g}</span>`;
}

function kpiCell([label, value, sub]) {
  const cls = signClass(value);
  return `<div class="kpi"><span>${label}</span><b class="${cls}">${value}</b>${sub ? `<div class="kpi-sub">${sub}</div>` : ''}</div>`;
}

// 종목 카드 하단 2개 핵심 지표 (config cardKpis 기반, 회사마다 다름)
function cardKpiRow(x) {
  if (!x.cardKpis || x.cardKpis.length < 2) return '';
  const [a, b] = x.cardKpis;
  return `<div class="card-kpis">
    <div class="card-kpi"><b>${a.value}</b><span>${a.label}</span></div>
    <div class="card-kpi"><b>${b.value}</b><span>${b.label}</span></div>
  </div>`;
}

function render(f = 'ALL') {
  const arr = payload.companies.filter(x => f === 'ALL' || x.g === f);
  list.innerHTML = arr.map(x => {
    const priceCls = signClass(x.tags && x.tags[0]);
    return `
    <div class="card" data-id="${x.id}">
      <div class="top">
        <div class="name-block"><div class="name">${x.name}</div>
          <div class="ticker">${x.ticker}</div>
          ${x.exchangeLine ? `<div class="exline">${x.exchangeLine}</div>` : ''}
        </div>
        ${impactBadge(x.g)}
      </div>
      <div class="event">${x.event}</div>
      <div class="price-row">
        <div class="price-col"><span class="price-label">현재가</span><b>${x.priceText || '-'}</b></div>
        <div class="price-col right"><span class="price-label">일간 등락률</span><b class="${priceCls}">${(x.tags && x.tags[0]) || '-'}</b></div>
      </div>
    </div>`;
  }).join('');
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
  const closes = spark.map(p => p.close);
  const labels = spark.map(p => p.date);
  const up = closes[closes.length - 1] >= closes[0];
  const color = up ? '#D92D20' : '#175CD3';
  const datasets = [{
    data: closes, borderColor: color, borderWidth: 1.6, pointRadius: 0, fill: true,
    backgroundColor: up ? 'rgba(217,45,32,.07)' : 'rgba(23,92,211,.07)', tension: 0.15,
  }];
  if (avgCost) {
    datasets.push({
      data: closes.map(() => avgCost), borderColor: '#98A2B3', borderWidth: 1,
      borderDash: [4, 3], pointRadius: 0, fill: false,
    });
  }
  // X축: 약 5개 눈금만 골라 표시 (매일 찍으면 겹쳐서 안 보임)
  const tickStep = Math.max(1, Math.round(labels.length / 5));
  chartInst = new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: { labels, datasets },
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      plugins: { legend: { display: false }, tooltip: { enabled: false } },
      scales: {
        x: {
          display: true, grid: { display: false },
          ticks: {
            color: '#98A2B3', font: { size: 9 }, maxRotation: 0,
            callback: (val, i) => (i % tickStep === 0 ? labels[i] : ''),
          },
        },
        y: {
          display: true, position: 'right',
          grid: { color: '#EEF1F4' },
          ticks: { color: '#98A2B3', font: { size: 9 }, maxTicksLimit: 4 },
        },
      },
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

function openExternal(url) {
  if (!url) return;
  if (window.Telegram?.WebApp?.openLink) {
    Telegram.WebApp.openLink(url);
  } else {
    window.open(url, '_blank');
  }
}

function detail(id) {
  const x = payload.companies.find(v => v.id === id);
  const hasSpark = x.spark && x.spark.length > 1;
  const hasSources = x.sources && x.sources.length > 0;
  const eventsHtml = hasSources
    ? x.sources.map(sourceRow).join('')
    : x.events.map(e => `<div class="tl">${e}</div>`).join('');
  document.getElementById('detail').innerHTML = `
    <div class="dt">${x.name} ${impactBadge(x.g)}</div>
    <div class="dsub">${x.ticker}${x.exchangeLine ? ' · ' + x.exchangeLine : ''}</div>
    <div class="dd">${x.thesis}</div>
    ${hasSpark ? `<div class="sec"><h4>3개월 추세 ${x.avgCost ? '<span class="legend-dash">- - 취득가</span>' : ''}</h4>
      <div style="height:120px"><canvas id="priceChart"></canvas></div></div>` : ''}
    <div class="sec"><h4>핵심 지표</h4>
      <div class="kpis">${x.kpis.map(kpiCell).join('')}</div>
    </div>
    <div class="sec"><h4>최근 공시·기사</h4>${eventsHtml}</div>
    ${x.watch.length ? `<div class="sec"><h4>주요 확인사항</h4><ul>${x.watch.map(w => `<li>${w}</li>`).join('')}</ul></div>` : ''}`;
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

function applyPayload() {
  const upd = document.getElementById('updatedLine');
  if (upd) upd.textContent = `Updated · ${payload.updated} KST`;

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
