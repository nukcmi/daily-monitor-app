// ── 웹 접근 비밀번호 게이트 ──
// 텔레그램 봇을 통해 Mini App으로 들어온 경우(initData 존재)는 통과시킨다.
// 일반 브라우저로 URL을 직접 열었을 때만 비밀번호를 요구한다.
// 주의: 이건 클라이언트 코드로 걸러지는 약한 차단이다 — 개발자도구로 소스를
// 보면 우회 가능하다. "URL을 안다고 아무나 바로 못 열게" 하는 수준의
// 최소한의 장치이며, 실제 정보보호가 필요하면 별도 인증 서버가 필요하다.
const WEB_PASSWORD = "hanwha2026";   // 필요 시 이 값만 바꾸면 된다

function initPasswordGate() {
  const insideTelegram = !!(window.Telegram?.WebApp?.initData);
  if (insideTelegram) return;
  if (sessionStorage.getItem('pw_ok') === '1') return;

  const gate = document.getElementById('pwGate');
  const input = document.getElementById('pwInput');
  const err = document.getElementById('pwError');
  gate.style.display = 'flex';

  const tryPw = () => {
    if (input.value === WEB_PASSWORD) {
      sessionStorage.setItem('pw_ok', '1');
      gate.style.display = 'none';
    } else {
      err.style.display = 'block';
      input.value = '';
      input.focus();
    }
  };
  document.getElementById('pwSubmit').onclick = tryPw;
  input.onkeydown = (e) => { if (e.key === 'Enter') tryPw(); };
  input.focus();
}
initPasswordGate();

// ── 종목 추가 요청 폼 ──
// 이 요청은 저장되지 않는다. 제출하면 담당자(지호님) 텔레그램으로 바로
// 메시지 창이 열리고, 보내는 사람이 "전송"을 눌러야 실제로 전달된다.
// 실제 config 반영은 담당자가 수동으로 처리한다 (승인 큐/DB 없음).
const ADMIN_TG_USERNAME = "nukcmi";

function initRequestForm() {
  const openBtn = document.getElementById('addReqBtn');
  const backdrop = document.getElementById('reqBackdrop');
  const closeBtn = document.getElementById('reqClose');
  const tagSelect = document.getElementById('rf_tag');
  const costFields = document.getElementById('rf_costFields');
  const form = document.getElementById('reqForm');
  if (!openBtn) return;

  const toggleCostFields = () => {
    const needsCost = ['당사 투자', '자회사'].includes(tagSelect.value);
    costFields.style.display = needsCost ? 'block' : 'none';
  };
  tagSelect.onchange = toggleCostFields;
  toggleCostFields();

  openBtn.onclick = () => backdrop.classList.add('open');
  closeBtn.onclick = () => backdrop.classList.remove('open');

  form.onsubmit = (e) => {
    e.preventDefault();
    const val = (id) => document.getElementById(id).value.trim();
    const name = val('rf_name');
    const tag = val('rf_tag');
    const requester = val('rf_requester');
    if (!name || !tag || !requester) return;

    const lines = [
      '[종목 추가 요청]',
      `회사명: ${name}`,
      val('rf_ticker') ? `티커: ${val('rf_ticker')} (${val('rf_market')})` : `거래소: ${val('rf_market')}`,
      `구분: ${tag}`,
    ];
    if (['당사 투자', '자회사'].includes(tag)) {
      if (val('rf_avgCost')) lines.push(`취득가: ${val('rf_avgCost')} ${val('rf_currency')}`);
      if (val('rf_acqLabel')) lines.push(`취득 시기: ${val('rf_acqLabel')}`);
    }
    if (val('rf_comment')) lines.push(`추가 이유: ${val('rf_comment')}`);
    lines.push(`요청자: ${requester}`);

    const text = encodeURIComponent(lines.join('\n'));
    const url = `https://t.me/${ADMIN_TG_USERNAME}?text=${text}`;
    openExternal(url);
    backdrop.classList.remove('open');
    form.reset();
    toggleCostFields();
  };
}

// ── 종목 추가 요청 폼 끝 ──

// ── 폴백 샘플 데이터 (data/latest.json fetch 실패 시에만 사용) ──
const FALLBACK = {
  updated: "-", fx: "",
  attentionItems: [{ company: "-", text: "데이터를 불러오는 중입니다.", impact: "", level: "low", url: null }],
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

function miniSpark(spark, up, avgCost, w = 100, h = 36) {
  if (!spark || spark.length < 2) return '';
  const closes = spark.map(p => p.close);
  let min = Math.min(...closes), max = Math.max(...closes);
  if (avgCost) { min = Math.min(min, avgCost); max = Math.max(max, avgCost); }
  const range = (max - min) || 1;
  const yOf = (v) => h - ((v - min) / range) * h;
  const pts = closes.map((v, i) => `${((i / (closes.length - 1)) * w).toFixed(1)},${yOf(v).toFixed(1)}`);
  const color = up ? '#F0616D' : '#6FA8F5';
  const fillId = `sf${Math.random().toString(36).slice(2, 8)}`;
  const areaPath = `M${pts[0]} L${pts.join(' L')} L${w},${h} L0,${h} Z`;
  const costLine = avgCost
    ? `<line x1="0" y1="${yOf(avgCost).toFixed(1)}" x2="${w}" y2="${yOf(avgCost).toFixed(1)}"
        stroke="#7B8494" stroke-width="1" stroke-dasharray="3,2"/>` : '';
  return `<svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" class="mini-spark">
    <defs><linearGradient id="${fillId}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="${color}" stop-opacity=".28"/>
      <stop offset="100%" stop-color="${color}" stop-opacity="0"/>
    </linearGradient></defs>
    <path d="${areaPath}" fill="url(#${fillId})" stroke="none"/>
    ${costLine}
    <polyline points="${pts.join(' ')}" fill="none" stroke="${color}" stroke-width="1.8"
      stroke-linejoin="round" stroke-linecap="round"/>
  </svg>`;
}

function render(f = 'ALL') {
  const arr = payload.companies.filter(x => x.g === f || f === 'ALL');
  const rows = arr.map(x => {
    const priceCls = signClass(x.tags && x.tags[0]);
    const up = priceCls !== 'val-down';
    // kpis: [종가,취득가,취득가대비,전일대비,전주대비,거래량,시가총액,52주고점대비]
    const kpiMap = {};
    (x.kpis || []).forEach(([label, value]) => { kpiMap[label] = value; });

    return `
    <tr class="wl-row" data-id="${x.id}">
      <td class="wl-code">
        <div class="wl-code-top">${x.id}${impactBadge(x.g)}</div>
        <div class="wl-name">${x.name}${x.ticker && x.ticker !== x.id ? ` <span class="wl-sub">${x.ticker}</span>` : ''}</div>
      </td>
      <td class="wl-spark">${miniSpark(x.spark, up, x.avgCost)}</td>
      <td class="wl-num wl-price">${x.priceText || '-'}</td>
      <td class="wl-num ${priceCls}">${x.changeText || '-'}</td>
      <td class="wl-num ${priceCls}">${(x.tags && x.tags[0]) || '-'}</td>
      <td class="wl-num wl-mut">${x.prevCloseText || '-'}</td>
      <td class="wl-num wl-mut">${x.openText || '-'}</td>
      <td class="wl-num wl-mut">${x.highText || '-'}</td>
      <td class="wl-num wl-mut">${x.lowText || '-'}</td>
    </tr>
    <tr class="wl-sub-row" data-id="${x.id}">
      <td colspan="9" class="wl-info">
        ${x.event} &nbsp;·&nbsp;
        취득가대비 <b class="${signClass(kpiMap['취득가대비'])}">${kpiMap['취득가대비'] || '-'}</b> &nbsp;·&nbsp;
        시가총액 <b>${kpiMap['시가총액'] || '-'}</b> &nbsp;·&nbsp;
        52주 고점대비 <b class="${signClass(kpiMap['52주 고점대비'])}">${kpiMap['52주 고점대비'] || '-'}</b>
      </td>
    </tr>`;
  }).join('');

  list.innerHTML = `
  <div class="wl-wrap">
    <table class="wl-table">
      <thead><tr>
        <th class="wl-code">종목</th>
        <th class="wl-spark">추세</th>
        <th class="wl-num">현재가</th>
        <th class="wl-num">변동</th>
        <th class="wl-num">변동률</th>
        <th class="wl-num">전일종가</th>
        <th class="wl-num">시가</th>
        <th class="wl-num">고가</th>
        <th class="wl-num">저가</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>
  </div>`;
  document.querySelectorAll('.wl-row, .wl-sub-row').forEach(c => c.onclick = () => detail(c.dataset.id));
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
  const color = up ? '#F0616D' : '#6FA8F5';
  const datasets = [{
    data: closes, borderColor: color, borderWidth: 1.8, pointRadius: 0, fill: true,
    backgroundColor: up ? 'rgba(240,97,109,.12)' : 'rgba(111,168,245,.12)', tension: 0.15,
  }];
  if (avgCost) {
    datasets.push({
      data: closes.map(() => avgCost), borderColor: '#7B8494', borderWidth: 1,
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
            color: '#7B8494', font: { size: 9 }, maxRotation: 0,
            callback: (val, i) => (i % tickStep === 0 ? labels[i] : ''),
          },
        },
        y: {
          display: true, position: 'right',
          grid: { color: 'rgba(255,255,255,.06)' },
          ticks: { color: '#7B8494', font: { size: 9 }, maxTicksLimit: 4 },
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

  const attnList = document.getElementById('attnList');
  if (attnList && payload.attentionItems) {
    attnList.innerHTML = payload.attentionItems.map((a, i) => {
      const cls = GRADE_CLASS[{ high: 'A', mid: 'B', low: 'C' }[a.level]] || 'low';
      const clickable = a.url ? ' clickable' : '';
      return `<section class="attention${clickable}" data-idx="${i}">
        <small>${i === 0 ? '금일 핵심' : '함께 볼 이슈'} · <span class="impact-badge impact-${cls}"><span class="impact-dot"></span>${GRADE_LABEL[{ high: 'A', mid: 'B', low: 'C' }[a.level]] || ''}</span></small>
        <h3>${a.company}</h3>
        <p>${a.text}</p>
        ${a.impact ? `<div class="attn-impact">당사 영향 · ${a.impact}</div>` : ''}
        ${a.url ? '<div class="attn-link">원문 보기 →</div>' : ''}
      </section>`;
    }).join('');
    attnList.querySelectorAll('.attention.clickable').forEach(el => {
      const item = payload.attentionItems[+el.dataset.idx];
      el.onclick = () => openExternal(item.url);
    });
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
initRequestForm();
load();
