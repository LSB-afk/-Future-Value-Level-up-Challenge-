const CARD_PREVIEW_COUNT = 6;

const state = {
  neighborhoods: [],
  results: [],
  selectedId: null,
  destination: "gangnam",
  budget: 70,
  persona: "single",
  apiMeta: null,
  apiOnline: false,
  isLoading: false,
  lastError: "",
  lastUpdated: null,
  refreshTimer: null,
  requestId: 0,
  map: null,
  activeSection: "recommend",
  showAllCards: false,
  evidenceRendered: false,
  weights: {
    commute: 35,
    cost: 30,
    service: 20,
    safety: 15
  }
};

const destinationLabels = {
  gangnam: "강남 업무지구",
  yeouido: "여의도",
  seoulStation: "서울역/도심",
  digital: "구로디지털단지",
  pangyo: "판교"
};

const personaLabels = {
  single: "1인 청년",
  commuter: "직장인",
  newlywed: "신혼",
  senior: "교통약자"
};

const personaBoost = {
  single: { cost: 7, service: 2 },
  commuter: { commute: 7, transit: 3 },
  newlywed: { safety: 5, service: 5 },
  senior: { safety: 7, service: 4 }
};

const scoreTips = {
  commute: "대중교통 경로 API 어댑터 기반 통근시간 점수, API 키가 없으면 검증 테이블로 폴백",
  cost: "예산 대비 월세 중앙값(2025 서울 전월세 실데이터) 기반 점수",
  service: "병원·학교·공원 좌표를 생활권 반경으로 집계한 생활 SOC 접근성 점수",
  safety: "안전·대기·녹지 환경 점수 (MVP 프록시)"
};

const nodes = {
  main: document.querySelector("main"),
  budgetInput: document.querySelector("#budgetInput"),
  budgetOutput: document.querySelector("#budgetOutput"),
  destinationInput: document.querySelector("#destinationInput"),
  commuteWeight: document.querySelector("#commuteWeight"),
  costWeight: document.querySelector("#costWeight"),
  serviceWeight: document.querySelector("#serviceWeight"),
  safetyWeight: document.querySelector("#safetyWeight"),
  commuteWeightOutput: document.querySelector("#commuteWeightOutput"),
  costWeightOutput: document.querySelector("#costWeightOutput"),
  serviceWeightOutput: document.querySelector("#serviceWeightOutput"),
  safetyWeightOutput: document.querySelector("#safetyWeightOutput"),
  resetButton: document.querySelector("#resetButton"),
  cards: document.querySelector("#cards"),
  toggleCards: document.querySelector("#toggleCards"),
  resultSummary: document.querySelector("#resultSummary"),
  mapCanvas: document.querySelector("#mapCanvas"),
  detailContent: document.querySelector("#detailContent"),
  selectedBadge: document.querySelector("#selectedBadge"),
  rankBadge: document.querySelector("#rankBadge"),
  candidateCount: document.querySelector("#candidateCount"),
  updatedAt: document.querySelector("#updatedAt"),
  apiStatusPill: document.querySelector("#apiStatusPill"),
  apiStatusLabel: document.querySelector("#apiStatusLabel"),
  evidenceTableBody: document.querySelector("#evidenceTableBody"),
  navLinks: document.querySelectorAll(".app-nav .nav-link"),
  cardTemplate: document.querySelector("#cardTemplate")
};

function clamp(value, min = 0, max = 100) {
  return Math.max(min, Math.min(max, value));
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("ko-KR");
}

function formatMoney10k(value) {
  const amount = Math.round(Number(value || 0));
  if (amount >= 10000) {
    const eok = Math.floor(amount / 10000);
    const rest = amount % 10000;
    return rest ? `${eok}억 ${formatNumber(rest)}만원` : `${eok}억원`;
  }
  return `${formatNumber(amount)}만원`;
}

function formatDistance(value) {
  const meters = Math.round(Number(value || 0));
  if (meters >= 1000) {
    return `${(meters / 1000).toFixed(1)}km`;
  }
  return `${formatNumber(meters)}m`;
}

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

function applyDataset(dataset) {
  if (!dataset || !Array.isArray(dataset.areas)) {
    throw new Error("생활권 데이터 형식이 올바르지 않습니다.");
  }
  state.neighborhoods = dataset.areas;
  state.apiMeta = dataset.meta || null;
}

async function loadAreas() {
  try {
    const dataset = await fetchJson("/api/areas");
    applyDataset(dataset);
    state.apiOnline = true;
  } catch (apiError) {
    const dataset = await fetchJson("../data/areas.actual.json");
    applyDataset(dataset);
    state.apiOnline = false;
    state.lastError = `API 비연결: ${apiError.message}`;
  }
}

function buildRecommendationQuery() {
  return new URLSearchParams({
    budget: state.budget,
    destination: state.destination,
    persona: state.persona,
    commuteWeight: state.weights.commute,
    costWeight: state.weights.cost,
    serviceWeight: state.weights.service,
    safetyWeight: state.weights.safety,
    limit: 9
  });
}

function scoreNeighborhood(item) {
  const minutes = Number(item.commuteMinutes?.[state.destination] || 60);
  const commuteScore = clamp(105 - minutes * 1.18);
  const overBudget = Math.max(0, Number(item.rentMonthly10k) - state.budget);
  const underBudget = Math.max(0, state.budget - Number(item.rentMonthly10k));
  const costScore = clamp(82 + underBudget * 0.55 - overBudget * 1.9);
  const safetyEnvScore = Math.round(Number(item.safetyScore) * 0.58 + Number(item.carbonScore) * 0.42);
  const boost = personaBoost[state.persona] || {};

  const adjusted = {
    commute: clamp(commuteScore + (boost.commute || 0) + (boost.transit || 0)),
    cost: clamp(costScore + (boost.cost || 0)),
    service: clamp(Number(item.serviceScore) + (boost.service || 0)),
    safety: clamp(safetyEnvScore + (boost.safety || 0))
  };

  const totalWeight = Object.values(state.weights).reduce((sum, value) => sum + Number(value), 0) || 100;
  const weighted =
    adjusted.commute * state.weights.commute +
    adjusted.cost * state.weights.cost +
    adjusted.service * state.weights.service +
    adjusted.safety * state.weights.safety;

  const personaMatch = item.recommendedFor?.includes(state.persona) ? 3 : 0;
  const dataConfidence = (Number(item.dataReadiness || 80) - 80) * 0.12;
  const total = clamp(weighted / totalWeight + personaMatch + dataConfidence);

  return {
    ...item,
    total: Math.round(total),
    minutes,
    adjusted: {
      commute: Math.round(adjusted.commute),
      cost: Math.round(adjusted.cost),
      service: Math.round(adjusted.service),
      safety: Math.round(adjusted.safety)
    },
    destination: state.destination,
    destinationLabel: destinationLabels[state.destination]
  };
}

function calculateFallback() {
  return state.neighborhoods
    .map(scoreNeighborhood)
    .sort((a, b) => b.total - a.total || a.rentMonthly10k - b.rentMonthly10k || a.name.localeCompare(b.name));
}

function ensureSelection() {
  if (!state.results.length) {
    state.selectedId = null;
    return;
  }
  if (!state.selectedId || !state.results.some((item) => item.id === state.selectedId)) {
    state.selectedId = state.results[0].id;
  }
}

async function refreshRecommendations() {
  const requestId = ++state.requestId;
  state.isLoading = true;
  if (!state.results.length) {
    render();
  } else {
    renderControls();
    renderLoadingHint();
  }

  try {
    if (state.apiOnline) {
      const payload = await fetchJson(`/api/recommendations?${buildRecommendationQuery().toString()}`);
      if (requestId !== state.requestId) return;
      state.apiMeta = payload.meta || state.apiMeta;
      state.results = Array.isArray(payload.results) ? payload.results : [];
      state.lastError = "";
    } else {
      state.results = calculateFallback();
    }
  } catch (error) {
    if (requestId !== state.requestId) return;
    state.apiOnline = false;
    state.lastError = `API 응답 실패, 로컬 계산으로 전환: ${error.message}`;
    state.results = calculateFallback();
  } finally {
    if (requestId === state.requestId) {
      state.isLoading = false;
      state.lastUpdated = new Date();
      if (state.map) {
        state.map.fitted = false;
      }
      ensureSelection();
      render();
    }
  }
}

function scheduleRefresh(delay = 140) {
  window.clearTimeout(state.refreshTimer);
  state.isLoading = true;
  renderControls();
  renderLoadingHint();
  state.refreshTimer = window.setTimeout(() => {
    refreshRecommendations();
  }, delay);
}

function markerColor(score) {
  if (score >= 80) return "var(--green)";
  if (score >= 68) return "var(--gold)";
  return "var(--accent-2)";
}

function markerTone(score) {
  if (score >= 80) return "high";
  if (score >= 68) return "mid";
  return "low";
}

function initializeLeafletMap() {
  if (state.map || !window.L) return;

  nodes.mapCanvas.innerHTML = "";
  nodes.mapCanvas.classList.remove("synthetic-map");

  const instance = L.map(nodes.mapCanvas, {
    zoomControl: true,
    scrollWheelZoom: false,
    preferCanvas: true
  }).setView([37.54, 126.98], 11);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(instance);

  state.map = {
    instance,
    markerLayer: L.layerGroup().addTo(instance),
    markersById: {},
    fitted: false
  };
}

function renderLeafletMap() {
  initializeLeafletMap();
  if (!state.map) return false;

  const { instance, markerLayer } = state.map;
  markerLayer.clearLayers();
  state.map.markersById = {};

  const bounds = [];
  state.results.forEach((item, index) => {
    const selected = item.id === state.selectedId;
    const marker = L.marker([item.lat, item.lng], {
      title: `${index + 1}위 ${item.name} ${item.total}점`,
      icon: L.divIcon({
        className: "mv-map-icon-wrapper",
        html: `<span class="mv-map-icon ${markerTone(item.total)}${selected ? " is-selected" : ""}" style="--size:${18 + item.total / 5}px"><strong>${item.total}</strong></span>`,
        iconSize: [42, 42],
        iconAnchor: [21, 21],
        popupAnchor: [0, -20]
      })
    });

    marker.bindPopup(`
      <strong>${item.name}</strong> <span class="popup-rank">${index + 1}위</span><br>
      ${item.destinationLabel || destinationLabels[state.destination]} ${item.minutes}분<br>
      월세 중앙값 ${formatNumber(item.rentMonthly10k)}만원<br>
      종합점수 <strong>${item.total}점</strong>
    `);
    marker.on("click", () => selectArea(item.id, { source: "map" }));
    marker.addTo(markerLayer);
    state.map.markersById[item.id] = marker;
    bounds.push([item.lat, item.lng]);
  });

  if (bounds.length && !state.map.fitted) {
    instance.fitBounds(bounds, { padding: [26, 26], maxZoom: 12 });
    state.map.fitted = true;
  }

  window.setTimeout(() => instance.invalidateSize(), 0);
  return true;
}

function focusSelectedMarker(pan) {
  const marker = state.map?.markersById?.[state.selectedId];
  if (!marker) return;
  if (pan) {
    state.map.instance.panTo(marker.getLatLng());
  }
  marker.openPopup();
}

function renderFallbackMap() {
  nodes.mapCanvas.innerHTML = "";
  nodes.mapCanvas.classList.add("synthetic-map");

  if (!state.neighborhoods.length) {
    nodes.mapCanvas.innerHTML = `<div class="map-empty">데이터 로딩 중</div>`;
    return;
  }

  const latValues = state.neighborhoods.map((item) => item.lat);
  const lngValues = state.neighborhoods.map((item) => item.lng);
  const minLat = Math.min(...latValues);
  const maxLat = Math.max(...latValues);
  const minLng = Math.min(...lngValues);
  const maxLng = Math.max(...lngValues);

  state.results.forEach((item) => {
    const x = 10 + ((item.lng - minLng) / (maxLng - minLng || 1)) * 80;
    const y = 84 - ((item.lat - minLat) / (maxLat - minLat || 1)) * 68;
    const marker = document.createElement("button");
    marker.type = "button";
    marker.className = `area-marker${item.id === state.selectedId ? " is-selected" : ""}`;
    marker.style.left = `${x}%`;
    marker.style.top = `${y}%`;
    marker.style.setProperty("--size", `${18 + item.total / 5}px`);
    marker.style.setProperty("--marker", markerColor(item.total));
    marker.setAttribute("aria-label", `${item.name} ${item.total}점`);
    marker.innerHTML = `<span>${item.name} ${item.total}</span>`;
    marker.addEventListener("click", () => selectArea(item.id, { source: "map" }));
    nodes.mapCanvas.append(marker);
  });
}

function renderMap() {
  if (!state.neighborhoods.length) {
    nodes.mapCanvas.innerHTML = `<div class="map-empty">데이터 로딩 중</div>`;
    return;
  }

  if (!renderLeafletMap()) {
    renderFallbackMap();
  }
}

function buildReason(item) {
  const dims = [
    ["통근", item.adjusted.commute],
    ["주거비", item.adjusted.cost],
    ["생활 SOC", item.adjusted.service],
    ["안전·환경", item.adjusted.safety]
  ].sort((a, b) => b[1] - a[1]);

  const parts = [`${dims[0][0]}·${dims[1][0]} 강점`];
  const overBudget = Math.round(Number(item.rentMonthly10k) - state.budget);
  parts.push(overBudget > 0 ? `예산 ${overBudget}만원 초과 주의` : "예산 내 후보");
  if (item.recommendedFor?.includes(state.persona)) {
    parts.push(`${personaLabels[state.persona]} 적합`);
  }
  return parts.join(" · ");
}

function renderCards() {
  nodes.cards.classList.toggle("is-loading", state.isLoading);
  nodes.cards.setAttribute("aria-busy", state.isLoading ? "true" : "false");
  nodes.cards.innerHTML = "";

  if (state.isLoading && !state.results.length) {
    nodes.cards.innerHTML = `<div class="empty-state">추천 계산 중</div>`;
    nodes.toggleCards.hidden = true;
    return;
  }

  if (!state.results.length) {
    nodes.cards.innerHTML = `<div class="empty-state">추천 결과가 없습니다.</div>`;
    nodes.toggleCards.hidden = true;
    return;
  }

  const visible = state.showAllCards ? state.results : state.results.slice(0, CARD_PREVIEW_COUNT);

  visible.forEach((item, index) => {
    const fragment = nodes.cardTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".result-card");
    const button = fragment.querySelector(".card-button");
    const destinationLabel = item.destinationLabel || destinationLabels[state.destination];
    card.classList.toggle("is-selected", item.id === state.selectedId);
    fragment.querySelector(".rank").textContent = index + 1;
    fragment.querySelector(".name").textContent = `${item.name} · ${item.district}`;
    fragment.querySelector(".meta").textContent = `${destinationLabel} ${item.minutes}분 · 월 ${item.rentMonthly10k}만원 · ${item.station}`;
    fragment.querySelector(".reason").textContent = buildReason(item);
    fragment.querySelector(".score").textContent = `${item.total}점`;
    fragment.querySelector(".bar span").style.setProperty("--bar", `${item.total}%`);
    button.addEventListener("click", () => selectArea(item.id, { source: "card" }));
    nodes.cards.append(fragment);
  });

  const total = state.results.length;
  nodes.toggleCards.hidden = total <= CARD_PREVIEW_COUNT;
  nodes.toggleCards.textContent = state.showAllCards
    ? `상위 ${CARD_PREVIEW_COUNT}개만 보기`
    : `전체 ${total}개 후보 보기`;
}

function metric(label, value) {
  return `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`;
}

function scoreRow(label, value, tip) {
  return `
    <div class="score-row" title="${tip || ""}">
      <span>${label}</span>
      <div class="mini-bar"><span style="--value:${value}%"></span></div>
      <strong>${Math.round(value)}</strong>
    </div>
  `;
}

function renderEvidence(selected) {
  if (!selected.evidence) return "";
  const evidence = selected.evidence;
  const rentDongs = Array.isArray(evidence.rentDongs) ? evidence.rentDongs.join("·") : "";
  const socCounts = evidence.socCounts || selected.socSummary?.counts || {};
  const socText = `병원 ${socCounts.hospital || 0} · 학교 ${socCounts.school || 0} · 공원 ${socCounts.park || 0}`;
  const commuteSource = evidence.commuteMode === "table_fallback"
    ? `${evidence.commuteSource} (API 키 미설정 폴백)`
    : evidence.commuteSource;
  return `
    <div class="callout">
      <p><strong>실데이터 근거</strong></p>
      <ul class="evidence-list">
        <li>출처: ${evidence.rentSource}</li>
        <li>집계 범위: ${evidence.rentDistrict || selected.district} ${rentDongs} (15~85㎡)</li>
        <li>매칭 거래: ${formatNumber(evidence.matchedRentRecords)}건 중앙값 집계</li>
        <li>좌표 검증: ${evidence.stationCoordinateSource || "서울시 역사마스터 정보"}</li>
        <li>통근 경로: ${commuteSource}</li>
        <li>생활 SOC: 반경 ${formatDistance(evidence.socRadiusMeters)} ${socText} 집계</li>
      </ul>
    </div>
  `;
}

function renderDetail() {
  const selected = state.results.find((item) => item.id === state.selectedId);
  const rank = state.results.findIndex((item) => item.id === state.selectedId) + 1;

  if (!selected) {
    nodes.selectedBadge.textContent = "선택 없음";
    nodes.rankBadge.textContent = "-";
    nodes.detailContent.innerHTML = state.isLoading ? `<div class="callout"><p>추천 결과를 계산하고 있습니다.</p></div>` : "";
    return;
  }

  nodes.selectedBadge.textContent = selected.name;
  nodes.rankBadge.textContent = `${rank}위 / ${state.results.length}개`;
  nodes.detailContent.innerHTML = `
    <div>
      <h3>${selected.name} · ${selected.district}</h3>
      <p class="muted">${selected.station} 중심 생활권, 데이터 준비도 ${selected.dataReadiness}점</p>
    </div>
    <div class="metric-grid">
      ${metric("종합점수", `${selected.total}점`)}
      ${metric("통근시간", `${selected.minutes}분`)}
      ${metric("월세 중앙값", formatMoney10k(selected.rentMonthly10k))}
      ${metric("보증금 중앙값", formatMoney10k(selected.deposit10k))}
      ${metric("전세 중앙값", formatMoney10k(selected.jeonse10k))}
      ${metric("대중교통", `${selected.transitScore}점`)}
    </div>
    <div class="score-list" aria-label="항목별 점수">
      ${scoreRow("통근", selected.adjusted.commute, scoreTips.commute)}
      ${scoreRow("주거비", selected.adjusted.cost, scoreTips.cost)}
      ${scoreRow("생활 SOC", selected.adjusted.service, scoreTips.service)}
      ${scoreRow("안전·환경", selected.adjusted.safety, scoreTips.safety)}
      <p class="score-note">주거비·생활 SOC는 실제 공공데이터 기반, 통근은 경로 API 어댑터 우선·키 없을 때 테이블 폴백, 안전·환경은 MVP 프록시 점수입니다.</p>
    </div>
    <div class="callout">
      <p><strong>추천 근거</strong><br>${selected.insight}</p>
    </div>
    ${renderEvidence(selected)}
    <div class="callout">
      <p><strong>사업 적용</strong><br>부동산 플랫폼에는 생활권 점수 API로, 지자체에는 주거-이동 부담 리포트로 제공할 수 있다.</p>
    </div>
  `;
}

function renderEvidenceTable() {
  if (!nodes.evidenceTableBody || state.evidenceRendered || !state.neighborhoods.length) return;

  const rows = [...state.neighborhoods]
    .sort((a, b) => (b.evidence?.matchedRentRecords || 0) - (a.evidence?.matchedRentRecords || 0))
    .map((item) => {
      const evidence = item.evidence || {};
      const dongs = Array.isArray(evidence.rentDongs) ? evidence.rentDongs.join(", ") : "-";
      const socCounts = evidence.socCounts || item.socSummary?.counts || {};
      const socSummary = `병원 ${socCounts.hospital || 0} · 학교 ${socCounts.school || 0} · 공원 ${socCounts.park || 0}`;
      return `
        <tr>
          <th scope="row">${item.name}<span class="cell-sub">${item.district}</span></th>
          <td>${dongs}</td>
          <td class="num">${formatNumber(evidence.matchedRentRecords)}건</td>
          <td class="num">${formatNumber(item.rentMonthly10k)}만원</td>
          <td class="num">${formatMoney10k(item.deposit10k)}</td>
          <td class="num">${formatMoney10k(item.jeonse10k)}</td>
          <td>${socSummary}<span class="cell-sub">반경 ${formatDistance(evidence.socRadiusMeters)}</span></td>
        </tr>
      `;
    });

  const totalRecords = state.neighborhoods.reduce(
    (sum, item) => sum + Number(item.evidence?.matchedRentRecords || 0),
    0
  );
  rows.push(`
    <tr class="total-row">
      <th scope="row">합계</th>
      <td>생활권 ${state.neighborhoods.length}개</td>
      <td class="num">${formatNumber(totalRecords)}건</td>
      <td colspan="4" class="muted">15~85㎡ 거래 중앙값 · 생활 SOC 반경 집계 기준</td>
    </tr>
  `);

  nodes.evidenceTableBody.innerHTML = rows.join("");
  state.evidenceRendered = true;
}

function renderApiStatus() {
  if (!nodes.apiStatusPill) return;
  if (state.apiOnline) {
    nodes.apiStatusPill.textContent = "API 연결됨";
    nodes.apiStatusPill.className = "nav-status is-online";
    nodes.apiStatusPill.title = "추천이 서버 API에서 계산됩니다.";
  } else {
    nodes.apiStatusPill.textContent = "로컬 계산";
    nodes.apiStatusPill.className = "nav-status is-offline";
    nodes.apiStatusPill.title = state.lastError || "API 미연결 시 브라우저에서 동일 로직으로 계산합니다.";
  }
  if (nodes.apiStatusLabel) {
    nodes.apiStatusLabel.textContent = state.apiOnline ? "API" : "로컬";
  }
}

function renderLoadingHint() {
  nodes.cards.classList.toggle("is-loading", state.isLoading);
  nodes.cards.setAttribute("aria-busy", state.isLoading ? "true" : "false");
}

function renderControls() {
  const sourceYear = state.apiMeta?.housingSource?.year;
  const modeLabel = state.apiOnline ? "API" : "로컬";
  nodes.budgetOutput.textContent = `${state.budget}만원`;
  nodes.commuteWeightOutput.textContent = state.weights.commute;
  nodes.costWeightOutput.textContent = state.weights.cost;
  nodes.serviceWeightOutput.textContent = state.weights.service;
  nodes.safetyWeightOutput.textContent = state.weights.safety;
  nodes.candidateCount.textContent = state.apiMeta?.totalCandidates || state.neighborhoods.length;

  const total = state.results.length || state.neighborhoods.length;
  const shown = state.results.length
    ? (state.showAllCards ? state.results.length : Math.min(CARD_PREVIEW_COUNT, state.results.length))
    : 0;
  nodes.resultSummary.textContent = total ? `전체 후보 ${total}개 중 상위 ${shown}개` : "";

  const stamp = state.lastUpdated
    ? state.lastUpdated.toLocaleTimeString("ko-KR", { hour12: false })
    : "";
  nodes.updatedAt.textContent = state.isLoading
    ? "조건 반영 중…"
    : sourceYear
      ? `${modeLabel} 계산 · ${sourceYear} 서울 전월세 실데이터${stamp ? ` · ${stamp} 기준` : ""}`
      : "데이터 준비 중";
}

function render() {
  renderControls();
  renderApiStatus();
  renderMap();
  renderCards();
  renderDetail();
  renderEvidenceTable();
}

function selectArea(id, options = {}) {
  state.selectedId = id;

  const rank = state.results.findIndex((item) => item.id === id);
  if (rank >= CARD_PREVIEW_COUNT && !state.showAllCards) {
    state.showAllCards = true;
  }

  render();
  focusSelectedMarker(options.source === "card");
}

function setActiveNav(sectionId) {
  nodes.navLinks.forEach((link) => {
    link.classList.toggle("is-active", link.dataset.section === sectionId);
  });
}

function activateSection(sectionId, options = {}) {
  const target = document.getElementById(sectionId) ? sectionId : "recommend";
  state.activeSection = target;
  document.querySelectorAll("main > .anchor-target").forEach((section) => {
    section.classList.toggle("is-active-view", section.id === target);
  });
  setActiveNav(target);

  if (options.updateHash && window.location.hash !== `#${target}`) {
    window.history.pushState(null, "", `#${target}`);
  }

  if (target === "map" && state.map?.instance) {
    window.setTimeout(() => {
      state.map.instance.invalidateSize();
      focusSelectedMarker(false);
    }, 80);
  }
}

function initNavigation() {
  nodes.navLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      activateSection(link.dataset.section, { updateHash: true });
    });
  });

  window.addEventListener("hashchange", () => {
    activateSection(window.location.hash.replace("#", "") || "recommend");
  });
  activateSection(window.location.hash.replace("#", "") || "recommend");
}

function bindEvents() {
  nodes.budgetInput.addEventListener("input", (event) => {
    state.budget = Number(event.target.value);
    scheduleRefresh();
  });

  nodes.destinationInput.addEventListener("change", (event) => {
    state.destination = event.target.value;
    scheduleRefresh(0);
  });

  document.querySelectorAll("input[name='persona']").forEach((radio) => {
    radio.addEventListener("change", (event) => {
      if (event.target.checked) {
        state.persona = event.target.value;
        scheduleRefresh(0);
      }
    });
  });

  [
    ["commuteWeight", "commute"],
    ["costWeight", "cost"],
    ["serviceWeight", "service"],
    ["safetyWeight", "safety"]
  ].forEach(([inputId, key]) => {
    nodes[inputId].addEventListener("input", (event) => {
      state.weights[key] = Number(event.target.value);
      scheduleRefresh();
    });
  });

  nodes.toggleCards.addEventListener("click", () => {
    state.showAllCards = !state.showAllCards;
    renderControls();
    renderCards();
  });

  nodes.resetButton.addEventListener("click", () => {
    state.budget = 70;
    state.destination = "gangnam";
    state.persona = "single";
    state.weights = { commute: 35, cost: 30, service: 20, safety: 15 };
    nodes.budgetInput.value = state.budget;
    nodes.destinationInput.value = state.destination;
    document.querySelector("input[name='persona'][value='single']").checked = true;
    nodes.commuteWeight.value = state.weights.commute;
    nodes.costWeight.value = state.weights.cost;
    nodes.serviceWeight.value = state.weights.service;
    nodes.safetyWeight.value = state.weights.safety;
    state.selectedId = null;
    state.showAllCards = false;
    scheduleRefresh(0);
  });
}

async function init() {
  bindEvents();
  initNavigation();
  render();
  await loadAreas();
  await refreshRecommendations();
}

init().catch((error) => {
  nodes.cards.innerHTML = `<div class="empty-state">데이터를 불러오지 못했습니다.</div>`;
  nodes.detailContent.innerHTML = `<div class="callout"><p>데이터를 불러오지 못했습니다: ${error.message}</p></div>`;
});
