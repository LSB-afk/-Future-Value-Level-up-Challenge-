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
  refreshTimer: null,
  requestId: 0,
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

const personaBoost = {
  single: { cost: 7, service: 2 },
  commuter: { commute: 7, transit: 3 },
  newlywed: { safety: 5, service: 5 },
  senior: { safety: 7, service: 4 }
};

const nodes = {
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
  mapCanvas: document.querySelector("#mapCanvas"),
  detailContent: document.querySelector("#detailContent"),
  selectedBadge: document.querySelector("#selectedBadge"),
  rankBadge: document.querySelector("#rankBadge"),
  candidateCount: document.querySelector("#candidateCount"),
  updatedAt: document.querySelector("#updatedAt"),
  cardTemplate: document.querySelector("#cardTemplate")
};

function clamp(value, min = 0, max = 100) {
  return Math.max(min, Math.min(max, value));
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString("ko-KR");
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
      ensureSelection();
      render();
    }
  }
}

function scheduleRefresh(delay = 140) {
  window.clearTimeout(state.refreshTimer);
  state.isLoading = true;
  renderControls();
  state.refreshTimer = window.setTimeout(() => {
    refreshRecommendations();
  }, delay);
}

function markerColor(score) {
  if (score >= 80) return "var(--green)";
  if (score >= 68) return "var(--gold)";
  return "var(--accent-2)";
}

function renderMap() {
  nodes.mapCanvas.innerHTML = "";

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
    marker.addEventListener("click", () => selectArea(item.id));
    nodes.mapCanvas.append(marker);
  });
}

function renderCards() {
  nodes.cards.innerHTML = "";

  if (state.isLoading && !state.results.length) {
    nodes.cards.innerHTML = `<div class="empty-state">추천 계산 중</div>`;
    return;
  }

  if (!state.results.length) {
    nodes.cards.innerHTML = `<div class="empty-state">추천 결과가 없습니다.</div>`;
    return;
  }

  state.results.slice(0, 8).forEach((item, index) => {
    const fragment = nodes.cardTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".result-card");
    const button = fragment.querySelector(".card-button");
    const destinationLabel = item.destinationLabel || destinationLabels[state.destination];
    card.classList.toggle("is-selected", item.id === state.selectedId);
    fragment.querySelector(".rank").textContent = index + 1;
    fragment.querySelector(".name").textContent = `${item.name} · ${item.district}`;
    fragment.querySelector(".meta").textContent = `${destinationLabel} ${item.minutes}분 · 월 ${item.rentMonthly10k}만원 · ${item.station}`;
    fragment.querySelector(".score").textContent = `${item.total}점`;
    fragment.querySelector(".bar span").style.setProperty("--bar", `${item.total}%`);
    button.addEventListener("click", () => selectArea(item.id));
    nodes.cards.append(fragment);
  });
}

function metric(label, value) {
  return `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`;
}

function scoreRow(label, value) {
  return `
    <div class="score-row">
      <span>${label}</span>
      <div class="mini-bar"><span style="--value:${value}%"></span></div>
      <strong>${Math.round(value)}</strong>
    </div>
  `;
}

function renderEvidence(selected) {
  if (!selected.evidence) return "";
  const rentDongs = Array.isArray(selected.evidence.rentDongs) ? selected.evidence.rentDongs.join(", ") : "";
  return `
    <div class="callout">
      <p><strong>실데이터 근거</strong><br>${selected.evidence.rentSource} · ${rentDongs} · ${formatNumber(selected.evidence.matchedRentRecords)}건 집계</p>
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
  nodes.rankBadge.textContent = `${rank}위`;
  nodes.detailContent.innerHTML = `
    <div>
      <h3>${selected.name} · ${selected.district}</h3>
      <p class="muted">${selected.station} 중심 생활권, 데이터 준비도 ${selected.dataReadiness}점</p>
    </div>
    <div class="metric-grid">
      ${metric("종합점수", `${selected.total}점`)}
      ${metric("통근시간", `${selected.minutes}분`)}
      ${metric("월세 중앙값", `${formatNumber(selected.rentMonthly10k)}만원`)}
      ${metric("보증금 중앙값", `${formatNumber(selected.deposit10k)}만원`)}
      ${metric("전세 중앙값", `${formatNumber(selected.jeonse10k)}만원`)}
      ${metric("대중교통", `${selected.transitScore}점`)}
    </div>
    <div class="score-list" aria-label="항목별 점수">
      ${scoreRow("통근", selected.adjusted.commute)}
      ${scoreRow("주거비", selected.adjusted.cost)}
      ${scoreRow("생활 SOC", selected.adjusted.service)}
      ${scoreRow("안전·환경", selected.adjusted.safety)}
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

function renderControls() {
  const sourceYear = state.apiMeta?.housingSource?.year;
  const modeLabel = state.apiOnline ? "API" : "로컬";
  nodes.budgetOutput.textContent = `${state.budget}만원`;
  nodes.commuteWeightOutput.textContent = state.weights.commute;
  nodes.costWeightOutput.textContent = state.weights.cost;
  nodes.serviceWeightOutput.textContent = state.weights.service;
  nodes.safetyWeightOutput.textContent = state.weights.safety;
  nodes.candidateCount.textContent = state.apiMeta?.totalCandidates || state.neighborhoods.length;
  nodes.updatedAt.textContent = state.isLoading
    ? "추천 계산 중"
    : sourceYear
      ? `${modeLabel} · ${sourceYear} 서울 전월세`
      : "데이터 준비 중";
}

function render() {
  renderControls();
  renderMap();
  renderCards();
  renderDetail();
}

function selectArea(id) {
  state.selectedId = id;
  render();
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
    scheduleRefresh(0);
  });
}

async function init() {
  bindEvents();
  render();
  await loadAreas();
  await refreshRecommendations();
}

init().catch((error) => {
  nodes.cards.innerHTML = `<div class="empty-state">데이터를 불러오지 못했습니다.</div>`;
  nodes.detailContent.innerHTML = `<div class="callout"><p>데이터를 불러오지 못했습니다: ${error.message}</p></div>`;
});
