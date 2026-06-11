const state = {
  neighborhoods: [],
  results: [],
  selectedId: null,
  destination: "gangnam",
  budget: 70,
  persona: "single",
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

function scoreNeighborhood(item) {
  const minutes = item.commuteMinutes[state.destination];
  const commuteScore = clamp(105 - minutes * 1.18);
  const overBudget = Math.max(0, item.rentMonthly10k - state.budget);
  const underBudget = Math.max(0, state.budget - item.rentMonthly10k);
  const costScore = clamp(82 + underBudget * 0.55 - overBudget * 1.9);
  const safetyEnvScore = Math.round(item.safetyScore * 0.58 + item.carbonScore * 0.42);
  const boost = personaBoost[state.persona] || {};

  const adjusted = {
    commute: clamp(commuteScore + (boost.commute || 0) + (boost.transit || 0)),
    cost: clamp(costScore + (boost.cost || 0)),
    service: clamp(item.serviceScore + (boost.service || 0)),
    safety: clamp(safetyEnvScore + (boost.safety || 0))
  };

  const totalWeight = Object.values(state.weights).reduce((sum, value) => sum + Number(value), 0);
  const weighted =
    adjusted.commute * state.weights.commute +
    adjusted.cost * state.weights.cost +
    adjusted.service * state.weights.service +
    adjusted.safety * state.weights.safety;

  const personaMatch = item.recommendedFor.includes(state.persona) ? 3 : 0;
  const dataConfidence = (item.dataReadiness - 80) * 0.12;
  const total = clamp(weighted / totalWeight + personaMatch + dataConfidence);

  return {
    ...item,
    total: Math.round(total),
    minutes,
    adjusted
  };
}

function calculate() {
  state.results = state.neighborhoods
    .map(scoreNeighborhood)
    .sort((a, b) => b.total - a.total || a.rentMonthly10k - b.rentMonthly10k);

  if (!state.selectedId || !state.results.some((item) => item.id === state.selectedId)) {
    state.selectedId = state.results[0]?.id;
  }
}

function markerColor(score) {
  if (score >= 80) return "var(--green)";
  if (score >= 68) return "var(--gold)";
  return "var(--accent-2)";
}

function renderMap() {
  const latValues = state.neighborhoods.map((item) => item.lat);
  const lngValues = state.neighborhoods.map((item) => item.lng);
  const minLat = Math.min(...latValues);
  const maxLat = Math.max(...latValues);
  const minLng = Math.min(...lngValues);
  const maxLng = Math.max(...lngValues);

  nodes.mapCanvas.innerHTML = "";

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

  state.results.slice(0, 8).forEach((item, index) => {
    const fragment = nodes.cardTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".result-card");
    const button = fragment.querySelector(".card-button");
    card.classList.toggle("is-selected", item.id === state.selectedId);
    fragment.querySelector(".rank").textContent = index + 1;
    fragment.querySelector(".name").textContent = `${item.name} · ${item.district}`;
    fragment.querySelector(".meta").textContent = `${destinationLabels[state.destination]} ${item.minutes}분 · 월 ${item.rentMonthly10k}만원 · ${item.station}`;
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

function renderDetail() {
  const selected = state.results.find((item) => item.id === state.selectedId);
  const rank = state.results.findIndex((item) => item.id === state.selectedId) + 1;

  if (!selected) {
    nodes.detailContent.innerHTML = "";
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
      ${metric("월 주거비", `${selected.rentMonthly10k}만원`)}
      ${metric("보증금", `${selected.deposit10k.toLocaleString()}만원`)}
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
    <div class="callout">
      <p><strong>사업 적용</strong><br>부동산 플랫폼에는 생활권 점수 API로, 지자체에는 주거-이동 부담 리포트로 제공할 수 있다.</p>
    </div>
  `;
}

function renderControls() {
  nodes.budgetOutput.textContent = `${state.budget}만원`;
  nodes.commuteWeightOutput.textContent = state.weights.commute;
  nodes.costWeightOutput.textContent = state.weights.cost;
  nodes.serviceWeightOutput.textContent = state.weights.service;
  nodes.safetyWeightOutput.textContent = state.weights.safety;
  nodes.candidateCount.textContent = state.neighborhoods.length;
  nodes.updatedAt.textContent = "샘플 데이터 기반";
}

function render() {
  calculate();
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
    render();
  });

  nodes.destinationInput.addEventListener("change", (event) => {
    state.destination = event.target.value;
    render();
  });

  document.querySelectorAll("input[name='persona']").forEach((radio) => {
    radio.addEventListener("change", (event) => {
      if (event.target.checked) {
        state.persona = event.target.value;
        render();
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
      render();
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
    render();
  });
}

async function init() {
  bindEvents();
  const response = await fetch("../data/neighborhoods.json");
  state.neighborhoods = await response.json();
  render();
}

init().catch((error) => {
  nodes.detailContent.innerHTML = `<div class="callout"><p>데이터를 불러오지 못했습니다: ${error.message}</p></div>`;
});

