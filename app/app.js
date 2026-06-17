const CARD_PREVIEW_COUNT = 5;

const state = {
  neighborhoods: [],
  results: [],
  selectedId: null,
  destination: "gangnam",
  destinationQuery: "",
  budget: 70,
  persona: "single",
  apiMeta: null,
  apiOnline: false,
  isLoading: false,
  hasMatched: false,
  lastError: "",
  lastUpdated: null,
  refreshTimer: null,
  requestId: 0,
  map: null,
  activeSection: "recommend",
  route: {
    selectedId: null,
    isLoading: false,
    result: null,
    error: "",
    focusMap: false
  },
  apartments: {
    enabled: true,
    labelMode: "sale",
    showSocRadius: true,
    isLoading: false,
    features: [],
    meta: null,
    error: "",
    lastKey: "",
    requestId: 0,
    timer: null
  },
  property: {
    selectedId: null,
    isLoading: false,
    detail: null,
    error: "",
    requestId: 0,
    comparison: [],
    agentQuestion: "이 아파트 전세 들어가도 괜찮아?",
    agentAnswer: null,
    agentLoading: false,
    agentError: ""
  },
  showAllCards: false,
  evidenceRendered: false,
  detailPanelOpen: false,
  weights: {
    commute: 25,
    cost: 25,
    service: 25,
    safety: 25
  }
};

const destinationLabels = {
  gangnam: "강남 업무지구",
  yeouido: "여의도",
  seoulStation: "서울역/도심",
  digital: "구로디지털단지",
  pangyo: "판교"
};

const destinationAddresses = {
  gangnam: "서울 강남구 역삼동",
  yeouido: "서울 영등포구 여의도동",
  seoulStation: "서울 중구 봉래동2가",
  digital: "서울 구로구 구로동",
  pangyo: "경기도 성남시 분당구 삼평동"
};

const destinationSearchOptions = [
  {
    key: "gangnam",
    label: "강남역 · 테헤란로",
    address: "서울 강남구 역삼동",
    keywords: ["강남", "역삼", "선릉", "삼성", "테헤란", "강남역"]
  },
  {
    key: "yeouido",
    label: "여의도 · 금융권",
    address: "서울 영등포구 여의도동",
    keywords: ["여의도", "국회의사당", "ifc", "더현대", "금융"]
  },
  {
    key: "seoulStation",
    label: "서울역 · 도심권",
    address: "서울 중구 봉래동2가",
    keywords: ["서울역", "중구", "시청", "광화문", "종로", "을지로", "도심"]
  },
  {
    key: "digital",
    label: "구로디지털단지",
    address: "서울 구로구 구로동",
    keywords: ["구로", "가산", "디지털", "구디", "가디"]
  },
  {
    key: "pangyo",
    label: "판교테크노밸리",
    address: "경기도 성남시 분당구 삼평동",
    keywords: ["판교", "삼평", "분당", "성남", "테크노밸리"]
  }
];

const areaAddressDefaults = {
  konkuk: "서울 광진구 화양동",
  sillim: "서울 관악구 신림동",
  cheongnyangni: "서울 동대문구 청량리동",
  wangsimni: "서울 성동구 행당동",
  guro: "서울 구로구 구로동",
  gongdeok: "서울 마포구 공덕동",
  magok: "서울 강서구 마곡동",
  sangam: "서울 마포구 상암동",
  gimpoairport: "서울 강서구 공항동"
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
  safety: "치안시설·CCTV 집계점·대기측정망·공원 접근성을 결합한 안전·환경 점수"
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
  refreshButton: document.querySelector("#refreshButton"),
  matchButton: document.querySelector("#matchButton"),
  resetButton: document.querySelector("#resetButton"),
  cards: document.querySelector("#cards"),
  toggleCards: document.querySelector("#toggleCards"),
  resultSummary: document.querySelector("#resultSummary"),
  mapCanvas: document.querySelector("#mapCanvas"),
  detailContent: document.querySelector("#detailContent"),
  routeContent: document.querySelector("#routeContent"),
  apartmentLayerToggle: document.querySelector("#apartmentLayerToggle"),
  mapLabelModeInput: document.querySelector("#mapLabelModeInput"),
  socRadiusToggle: document.querySelector("#socRadiusToggle"),
  apartmentLayerStatus: document.querySelector("#apartmentLayerStatus"),
  propertyDashboard: document.querySelector("#propertyDashboard"),
  detailSubpanel: document.querySelector("#detailSubpanel"),
  closeSubpanelButton: document.querySelector("#closeSubpanelButton"),
  subpanelCloseXButton: document.querySelector("#subpanelCloseXButton"),
  subpanelMeta: document.querySelector("#subpanelMeta"),
  selectedBadge: document.querySelector("#selectedBadge"),
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

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function formatDistance(value) {
  const meters = Math.round(Number(value || 0));
  if (meters >= 1000) {
    return `${(meters / 1000).toFixed(1)}km`;
  }
  return `${formatNumber(meters)}m`;
}

function formatFare(value) {
  const fare = Number(value || 0);
  return fare ? `${formatNumber(fare)}원` : "-";
}

function formatPercent(value, digits = 1) {
  const number = Number(value || 0);
  return `${number.toFixed(digits)}%`;
}

function riskTone(key) {
  if (key === "high") return "danger";
  if (key === "warning" || key === "unknown") return "warn";
  return "safe";
}

function labelModeName(mode = state.apartments.labelMode) {
  if (mode === "jeonse") return "전세가율";
  if (mode === "risk") return "위험도";
  if (mode === "commute") return "통근시간";
  return "매매가";
}

function propertyLabel(feature) {
  const preview = feature.pricePreview || {};
  if (state.apartments.labelMode === "jeonse") {
    return {
      primary: preview.jeonseRatio ? `전세 ${formatPercent(preview.jeonseRatio)}` : "전세율",
      secondary: preview.saleLabel ? escapeHtml(preview.saleLabel.replace(" ", "")) : "매매 추정"
    };
  }
  if (state.apartments.labelMode === "risk") {
    return {
      primary: preview.riskLevel ? escapeHtml(preview.riskLevel) : "위험도",
      secondary: preview.riskScore != null ? `${formatNumber(preview.riskScore)}점` : "점검"
    };
  }
  if (state.apartments.labelMode === "commute") {
    return {
      primary: preview.commuteLabel || "통근",
      secondary: preview.livingAreaName ? escapeHtml(preview.livingAreaName) : "생활권 기준"
    };
  }
  return {
    primary: preview.saleLabel ? escapeHtml(preview.saleLabel.replace(" ", "")) : "단지",
    secondary: preview.jeonseRatio ? `전세 ${formatPercent(preview.jeonseRatio)}` : "상세 보기"
  };
}

function clusterLabel(feature) {
  const preview = feature.pricePreview || {};
  if (state.apartments.labelMode === "jeonse") return preview.jeonseRatio ? `전세 ${formatPercent(preview.jeonseRatio)}` : `${formatNumber(feature.count)}개`;
  if (state.apartments.labelMode === "risk") return preview.riskLevelKey === "high" ? "위험 높음" : preview.riskLevelKey === "warning" ? "주의" : "위험 낮음";
  if (state.apartments.labelMode === "commute") return preview.commuteLabel || `${formatNumber(feature.count)}개`;
  return preview.sale10k ? formatMoney10k(preview.sale10k).replace(" ", "") : `${formatNumber(feature.count)}개`;
}

function updateMapScaleUI() {
}

function normalizeSearchText(value = "") {
  return String(value).replace(/\s+/g, "").toLowerCase();
}

function inferDestinationKey(value = "") {
  const normalized = normalizeSearchText(value);
  if (!normalized) return state.destination || "gangnam";

  const directMatch = destinationSearchOptions.find((option) => (
    normalizeSearchText(option.address) === normalized
    || normalizeSearchText(destinationLabels[option.key]) === normalized
    || normalizeSearchText(option.label) === normalized
  ));
  if (directMatch) return directMatch.key;

  const keywordMatch = destinationSearchOptions.find((option) => (
    option.keywords.some((keyword) => normalized.includes(normalizeSearchText(keyword)))
  ));
  return keywordMatch?.key || state.destination || "gangnam";
}

function destinationDisplayLabel() {
  const query = state.destinationQuery?.trim();
  return query || destinationLabels[state.destination] || "목적지";
}

function destinationAddressFor() {
  const query = state.destinationQuery?.trim();
  return query
    || state.apiMeta?.destinationAddresses?.[state.destination]
    || destinationAddresses[state.destination]
    || destinationLabels[state.destination]
    || "";
}

function destinationScoringLabel() {
  return destinationLabels[state.destination] || "목적지";
}

function representativeAddressFor(item) {
  return item?.representativeAddress
    || areaAddressDefaults[item?.id]
    || `${item?.district || ""} ${item?.station || item?.name || ""}`.trim();
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
    destinationLabel: destinationDisplayLabel(),
    destinationScoringLabel: destinationScoringLabel(),
    destinationAddress: destinationAddressFor(),
    representativeAddress: representativeAddressFor(item),
    reasonText: buildSpecificReason({ ...item, minutes })
  };
}

function enrichRecommendationResult(item) {
  const enriched = {
    ...item,
    destination: state.destination,
    destinationLabel: destinationDisplayLabel(),
    destinationScoringLabel: destinationScoringLabel(),
    destinationAddress: destinationAddressFor()
  };
  return {
    ...enriched,
    reasonText: buildSpecificReason(enriched)
  };
}

function calculateFallback() {
  return state.neighborhoods
    .map(scoreNeighborhood)
    .sort((a, b) => b.total - a.total || a.rentMonthly10k - b.rentMonthly10k || a.name.localeCompare(b.name));
}

async function refreshRecommendations() {
  const requestId = ++state.requestId;
  state.isLoading = true;
  state.hasMatched = true;
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
      state.results = Array.isArray(payload.results) ? payload.results.map(enrichRecommendationResult) : [];
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
      render();
    }
  }
}

function scheduleRefresh(delay = 140) {
  window.clearTimeout(state.refreshTimer);
  state.requestId += 1;
  state.isLoading = false;
  state.hasMatched = false;
  state.results = [];
  state.selectedId = null;
  state.showAllCards = false;
  state.detailPanelOpen = false;
  state.evidenceRendered = false;
  state.property.selectedId = null;
  state.property.detail = null;
  state.property.error = "";
  state.property.isLoading = false;
  state.property.agentAnswer = null;
  state.property.agentError = "";
  state.property.requestId += 1;
  resetRouteState();
  if (state.map) {
    state.map.fitted = false;
  }
  render();
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

function routeModeKey(mode = "") {
  const text = String(mode).toLowerCase();
  if (text.includes("지하철") || text.includes("metro") || text.includes("subway")) return "subway";
  if (text.includes("버스") || text.includes("bus")) return "bus";
  if (text.includes("도보") || text.includes("walk")) return "walk";
  if (text.includes("철도") || text.includes("train")) return "rail";
  return "transit";
}

function subwayRouteColor(route = "") {
  const text = String(route);
  if (text.includes("1")) return "#0052A4";
  if (text.includes("2")) return "#00A84D";
  if (text.includes("3")) return "#EF7C1C";
  if (text.includes("4")) return "#00A5DE";
  if (text.includes("5")) return "#996CAC";
  if (text.includes("6")) return "#CD7C2F";
  if (text.includes("7")) return "#747F00";
  if (text.includes("8")) return "#E6186C";
  if (text.includes("9")) return "#BDB092";
  if (text.includes("분당")) return "#F5A200";
  if (text.includes("신분당")) return "#D4003B";
  if (text.includes("공항")) return "#0090D2";
  return "#00A84D";
}

function routeModeColor(step = {}) {
  const key = routeModeKey(step.mode);
  if (key === "subway") return subwayRouteColor(step.route);
  if (key === "bus") return "#386DE8";
  if (key === "walk") return "#64748B";
  if (key === "rail") return "#6D5DFC";
  return "#03C75A";
}

function routeModeIcon(mode = "") {
  const key = routeModeKey(mode);
  if (key === "subway") return "M";
  if (key === "bus") return "B";
  if (key === "walk") return "W";
  if (key === "rail") return "R";
  return "T";
}

function validRoutePoints(coordinates) {
  return (Array.isArray(coordinates) ? coordinates : [])
    .filter((point) => point?.lat != null && point?.lng != null)
    .map((point) => ({ lat: Number(point.lat), lng: Number(point.lng) }))
    .filter((point) => Number.isFinite(point.lat) && Number.isFinite(point.lng));
}

function buildSyntheticRouteAnchors(route, steps) {
  const origin = route.origin;
  const destination = route.destination;
  if (!origin?.lat || !origin?.lng || !destination?.lat || !destination?.lng) return [];

  const start = { lat: Number(origin.lat), lng: Number(origin.lng) };
  const end = { lat: Number(destination.lat), lng: Number(destination.lng) };
  const count = steps.length + 1;
  const points = [];
  for (let index = 0; index < count; index += 1) {
    const ratio = index / (count - 1);
    const bend = Math.sin(Math.PI * ratio) * 0.016;
    points.push({
      lat: start.lat + (end.lat - start.lat) * ratio + bend,
      lng: start.lng + (end.lng - start.lng) * ratio - bend * 0.55
    });
  }
  return points;
}

function bendSegment(start, end, index) {
  if (!start || !end) return [];
  const offset = 0.0045 * (index % 2 === 0 ? 1 : -1);
  const midA = {
    lat: start.lat + (end.lat - start.lat) * 0.45 + offset,
    lng: start.lng + (end.lng - start.lng) * 0.35
  };
  const midB = {
    lat: start.lat + (end.lat - start.lat) * 0.65 + offset,
    lng: start.lng + (end.lng - start.lng) * 0.72
  };
  return [start, midA, midB, end];
}

function splitGlobalCoordinatesByStep(points, steps) {
  if (points.length < 3 || !steps.length) return [];
  const segments = [];
  const usableSteps = Math.max(1, steps.length);
  for (let index = 0; index < usableSteps; index += 1) {
    const startIndex = Math.floor((index / usableSteps) * (points.length - 1));
    const endIndex = Math.max(startIndex + 1, Math.floor(((index + 1) / usableSteps) * (points.length - 1)));
    segments.push({
      step: steps[index] || { mode: "대중교통" },
      points: points.slice(startIndex, endIndex + 1),
      actual: true
    });
  }
  return segments;
}

function buildRouteSegments(route) {
  const steps = Array.isArray(route.steps) && route.steps.length ? route.steps : [{ mode: "대중교통", route: "" }];
  const explicitSegments = (Array.isArray(route.segments) ? route.segments : [])
    .map((segment, index) => ({
      step: segment.step || steps[index] || segment,
      points: validRoutePoints(segment.coordinates),
      actual: true
    }))
    .filter((segment) => segment.points.length >= 2);
  if (explicitSegments.length) return explicitSegments;

  const stepSegments = steps
    .map((step) => ({
      step,
      points: validRoutePoints(step.coordinates),
      actual: true
    }))
    .filter((segment) => segment.points.length >= 2);
  if (stepSegments.length) return stepSegments;

  const globalPoints = validRoutePoints(route.coordinates);
  const globalSegments = splitGlobalCoordinatesByStep(globalPoints, steps);
  if (globalSegments.length) return globalSegments;

  const anchors = buildSyntheticRouteAnchors(route, steps);
  return steps
    .map((step, index) => ({
      step,
      points: bendSegment(anchors[index], anchors[index + 1], index),
      actual: false
    }))
    .filter((segment) => segment.points.length >= 2);
}

function initializeLeafletMap() {
  if (state.map || !window.L) return;

  nodes.mapCanvas.innerHTML = "";
  nodes.mapCanvas.classList.remove("synthetic-map");

  const instance = L.map(nodes.mapCanvas, {
    zoomControl: true,
    scrollWheelZoom: true
  }).setView([37.54, 126.98], 11);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(instance);

  state.map = {
    instance,
    markerLayer: L.layerGroup().addTo(instance),
    apartmentLayer: L.layerGroup().addTo(instance),
    routeLayer: L.layerGroup().addTo(instance),
    socLayer: L.layerGroup().addTo(instance),
    markersById: {},
    fitted: false
  };

  instance.on("moveend zoomend", () => {
    updateMapScaleUI();
    if (state.apartments.enabled) {
      scheduleApartmentLayerLoad();
    }
  });
  updateMapScaleUI();
}

function drawRouteLine(bounds) {
  if (!state.map?.routeLayer) return;
  state.map.routeLayer.clearLayers();

  const route = state.route.result;
  if (!route || route.origin?.lat == null || route.destination?.lat == null) return;

  const segments = buildRouteSegments(route);
  const allLatLngs = segments.flatMap((segment) => (
    segment.points.map((point) => [Number(point.lat), Number(point.lng)])
  ));
  if (allLatLngs.length < 2) return;

  segments.forEach((segment, index) => {
    const step = segment.step || {};
    const latLngs = segment.points.map((point) => [Number(point.lat), Number(point.lng)]);
    const color = routeModeColor(step);
    const weight = 6;
    const dashArray = null;

    L.polyline(latLngs, {
      color: "rgba(15, 23, 42, 0.22)",
      weight: weight + 8,
      opacity: 1,
      dashArray,
      lineCap: "round",
      lineJoin: "round"
    }).addTo(state.map.routeLayer);

    L.polyline(latLngs, {
      color: "#ffffff",
      weight: weight + 4,
      opacity: 0.92,
      dashArray,
      lineCap: "round",
      lineJoin: "round"
    }).addTo(state.map.routeLayer);

    L.polyline(latLngs, {
      color,
      weight,
      opacity: segment.actual ? 0.92 : 0.78,
      dashArray,
      lineCap: "round",
      lineJoin: "round"
    }).addTo(state.map.routeLayer);

    const start = latLngs[0];
    if (index > 0 && start) {
      L.marker(start, {
        title: `${step.mode || "이동"} ${step.route || ""}`.trim(),
        icon: L.divIcon({
          className: "route-step-icon-wrapper",
          html: `<span class="route-step-node" style="--route-color:${color}">${routeModeIcon(step.mode)}</span>`,
          iconSize: [32, 32],
          iconAnchor: [16, 16]
        })
      }).addTo(state.map.routeLayer);
    }
  });

  L.circleMarker(allLatLngs[0], {
    radius: 7,
    color: "#ffffff",
    weight: 2,
    fillColor: "#03C75A",
    fillOpacity: 1
  }).bindTooltip(route.origin.label || "출발지", { direction: "top" }).addTo(state.map.routeLayer);

  L.circleMarker(allLatLngs[allLatLngs.length - 1], {
    radius: 7,
    color: "#ffffff",
    weight: 2,
    fillColor: "#EF4444",
    fillOpacity: 1
  }).bindTooltip(route.destination.label || "도착지", { direction: "top" }).addTo(state.map.routeLayer);

  allLatLngs.forEach((point) => bounds.push(point));
  if (state.route.focusMap && state.map.instance) {
    state.map.instance.flyToBounds(L.latLngBounds(allLatLngs), {
      paddingTopLeft: [72, 108],
      paddingBottomRight: [360, 190],
      maxZoom: 14,
      duration: 0.75
    });
    state.route.focusMap = false;
    state.map.fitted = true;
  }
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
        html: `<span class="mv-map-icon ${markerTone(item.total)}${selected ? " is-selected" : ""}" style="--size:${42 + item.total / 5}px"><strong>${item.total}</strong><small>${escapeHtml(item.name)}</small></span>`,
        iconSize: [70, 70],
        iconAnchor: [35, 35],
        popupAnchor: [0, -20]
      })
    });

    marker.bindPopup(`
      <strong>${item.name}</strong> <span class="popup-rank">${index + 1}위</span><br>
      ${item.destinationLabel || destinationDisplayLabel()} ${item.minutes}분<br>
      월세 중앙값 ${formatNumber(item.rentMonthly10k)}만원<br>
      종합점수 <strong>${item.total}점</strong>
    `);
    marker.on("click", () => selectArea(item.id, { source: "map" }));
    marker.addTo(markerLayer);
    state.map.markersById[item.id] = marker;
    bounds.push([item.lat, item.lng]);
  });

  drawRouteLine(bounds);

  if (bounds.length && !state.map.fitted) {
    instance.fitBounds(bounds, { padding: [26, 26], maxZoom: 12 });
    state.map.fitted = true;
  }

  if (state.apartments.enabled) {
    scheduleApartmentLayerLoad();
  } else {
    renderApartmentLayer();
  }

  window.setTimeout(() => instance.invalidateSize(), 0);
  return true;
}

function focusSelectedMarker(options = {}) {
  const marker = state.map?.markersById?.[state.selectedId];
  if (!marker) return;
  if (options.zoom) {
    state.map.instance.flyTo(marker.getLatLng(), Math.max(state.map.instance.getZoom(), 15), {
      duration: 0.65
    });
  } else if (options.pan) {
    state.map.instance.panTo(marker.getLatLng());
  }
  marker.openPopup();
}

function focusRouteOnMap() {
  if (!state.map?.instance || !state.route.result) return;
  const latLngs = buildRouteSegments(state.route.result).flatMap((segment) => (
    segment.points.map((point) => [Number(point.lat), Number(point.lng)])
  ));
  if (latLngs.length < 2) return;
  state.map.instance.flyToBounds(L.latLngBounds(latLngs), {
    paddingTopLeft: [72, 108],
    paddingBottomRight: [360, 190],
    maxZoom: 14,
    duration: 0.75
  });
}

function apartmentLayerKey() {
  if (!state.map?.instance) return "";
  const bounds = state.map.instance.getBounds();
  const zoom = state.map.instance.getZoom();
  return [
    zoom,
    bounds.getSouth().toFixed(3),
    bounds.getWest().toFixed(3),
    bounds.getNorth().toFixed(3),
    bounds.getEast().toFixed(3),
    state.destination
  ].join(":");
}

function apartmentBoundsParam() {
  const bounds = state.map.instance.getBounds();
  return [
    bounds.getSouth().toFixed(6),
    bounds.getWest().toFixed(6),
    bounds.getNorth().toFixed(6),
    bounds.getEast().toFixed(6)
  ].join(",");
}

function renderApartmentLayerStatus() {
  if (!nodes.apartmentLayerStatus) return;
  if (!state.apartments.enabled) {
    nodes.apartmentLayerStatus.textContent = "아파트 단지 레이어 꺼짐";
    nodes.apartmentLayerStatus.className = "map-layer-status";
    return;
  }
  if (state.apartments.isLoading) {
    nodes.apartmentLayerStatus.textContent = "아파트 단지 불러오는 중";
    nodes.apartmentLayerStatus.className = "map-layer-status is-loading";
    return;
  }
  if (state.apartments.error) {
    nodes.apartmentLayerStatus.textContent = state.apartments.error;
    nodes.apartmentLayerStatus.className = "map-layer-status is-warning";
    return;
  }
  const meta = state.apartments.meta;
  if (!meta) {
    nodes.apartmentLayerStatus.textContent = "아파트 단지 데이터 준비 중";
    nodes.apartmentLayerStatus.className = "map-layer-status";
    return;
  }
  const mode = meta.complete ? "전체" : "제한 스냅샷";
  const viewCount = meta.filteredRecords || 0;
  const total = meta.totalRecords || meta.availableRecords || 0;
  nodes.apartmentLayerStatus.textContent = `${mode} ${formatNumber(total)}개 중 현재 화면 ${formatNumber(viewCount)}개`;
  nodes.apartmentLayerStatus.className = meta.complete ? "map-layer-status is-ready" : "map-layer-status is-warning";
}

function apartmentPopup(feature) {
  const approval = feature.approvalDate || (feature.approvalYear ? `${feature.approvalYear}년` : "사용승인일 없음");
  const parking = feature.parkingCount ? ` · 주차 ${formatNumber(feature.parkingCount)}대` : "";
  const preview = feature.pricePreview || {};
  const price = preview.saleLabel ? `추정 매매 ${escapeHtml(preview.saleLabel)} · 전세가율 ${formatPercent(preview.jeonseRatio)}` : "가격 미리보기 준비 중";
  return `
    <strong>${escapeHtml(feature.name)}</strong><br>
    ${escapeHtml(feature.address || `${feature.district || ""} ${feature.dong || ""}`.trim())}<br>
    ${formatNumber(feature.households)}세대 · ${formatNumber(feature.buildingCount)}개동 · ${escapeHtml(approval)}${parking}<br>
    <span class="popup-muted">${escapeHtml(feature.housingType || "공동주택")} · ${escapeHtml(feature.heating || "난방 정보 없음")}</span><br>
    <span class="popup-muted">${price}</span><br>
    <span class="popup-muted">클릭한 단지의 상세 대시보드가 아래에 열립니다.</span>
  `;
}

function clusterPopup(feature) {
  const districts = Array.isArray(feature.districts) && feature.districts.length ? feature.districts.join(", ") : "서울";
  const samples = Array.isArray(feature.sampleNames) ? feature.sampleNames.join(", ") : "";
  const preview = feature.pricePreview || {};
  const sale = preview.sale10k ? `평균 추정 매매 ${formatMoney10k(preview.sale10k)} · 전세가율 ${formatPercent(preview.jeonseRatio)}` : "";
  return `
    <strong>아파트 단지 ${formatNumber(feature.count)}개</strong><br>
    ${escapeHtml(districts)} · ${formatNumber(feature.households)}세대<br>
    ${sale ? `<span class="popup-muted">${sale}</span><br>` : ""}
    <span class="popup-muted">${escapeHtml(samples)}</span><br>
    <span class="popup-muted">확대하면 개별 단지로 표시됩니다.</span>
  `;
}

function renderApartmentLayer() {
  if (!state.map?.apartmentLayer) return;
  const layer = state.map.apartmentLayer;
  layer.clearLayers();

  if (!state.apartments.enabled) {
    renderApartmentLayerStatus();
    renderMapSidebar();
    return;
  }

  state.apartments.features.forEach((feature) => {
    if (feature.type === "cluster") {
      const priceLabel = clusterLabel(feature);
      const marker = L.marker([feature.lat, feature.lng], {
        title: `아파트 단지 ${feature.count}개`,
        icon: L.divIcon({
          className: "apt-cluster-wrapper",
          html: `<span class="apt-cluster"><strong>${formatNumber(feature.count)}</strong><small>${priceLabel}</small></span>`,
          iconSize: [74, 50],
          iconAnchor: [37, 25],
          popupAnchor: [0, -18]
        })
      });
      marker.bindPopup(clusterPopup(feature));
      marker.on("click", () => {
        const nextZoom = Math.max(state.map.instance.getZoom() + 2, 14);
        state.map.instance.setView([feature.lat, feature.lng], nextZoom);
      });
      marker.addTo(layer);
      return;
    }

    const preview = feature.pricePreview || {};
    const selected = feature.id === state.property.selectedId;
    const label = propertyLabel(feature);
    const marker = L.marker([feature.lat, feature.lng], {
      title: feature.name,
      icon: L.divIcon({
        className: "property-price-wrapper",
        html: `
          <span class="property-price-marker ${riskTone(preview.riskLevelKey)}${selected ? " is-selected" : ""}">
            <strong>${label.primary}</strong>
            <small>${label.secondary}</small>
          </span>
        `,
        iconSize: [94, 48],
        iconAnchor: [47, 24],
        popupAnchor: [0, -22]
      })
    });
    marker
      .bindPopup(apartmentPopup(feature))
      .bindTooltip(feature.name, { direction: "top", offset: [0, -4] })
      .on("click", () => selectProperty(feature.id))
      .addTo(layer);
  });
  renderApartmentLayerStatus();
  updateMapScaleUI();
  drawPropertySocRadius();
  renderMapSidebar();
}

async function loadApartmentsForMap(force = false) {
  if (!state.map?.instance || !state.apartments.enabled) return;

  const key = apartmentLayerKey();
  if (!force && key && key === state.apartments.lastKey) {
    renderApartmentLayer();
    return;
  }

  const requestId = ++state.apartments.requestId;
  state.apartments.lastKey = key;
  state.apartments.isLoading = true;
  state.apartments.error = "";
  renderApartmentLayerStatus();

  const params = new URLSearchParams({
    bounds: apartmentBoundsParam(),
    zoom: state.map.instance.getZoom(),
    destination: state.destination,
    cluster: "true",
    limit: 5000
  });

  try {
    const payload = await fetchJson(`/api/apartments?${params.toString()}`);
    if (requestId !== state.apartments.requestId) return;
    state.apartments.features = Array.isArray(payload.features) ? payload.features : [];
    state.apartments.meta = payload.meta || null;
    state.apartments.error = "";
  } catch (error) {
    if (requestId !== state.apartments.requestId) return;
    state.apartments.features = [];
    state.apartments.error = `아파트 단지 로딩 실패: ${error.message}`;
  } finally {
    if (requestId === state.apartments.requestId) {
      state.apartments.isLoading = false;
      renderApartmentLayer();
    }
  }
}

function scheduleApartmentLayerLoad(force = false) {
  window.clearTimeout(state.apartments.timer);
  state.apartments.timer = window.setTimeout(() => {
    loadApartmentsForMap(force);
  }, 160);
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

  const route = state.route.result;
  if (route?.origin && route?.destination) {
    const routeLine = document.createElement("div");
    routeLine.className = "fallback-route-line";
    routeLine.textContent = route.mode === "live_api" ? "실제 경로 계산됨" : "추정 경로";
    nodes.mapCanvas.append(routeLine);
  }
}

function renderMap() {
  renderApartmentLayerStatus();
  updateMapScaleUI();
  if (!state.neighborhoods.length) {
    nodes.mapCanvas.innerHTML = `<div class="map-empty">데이터 로딩 중</div>`;
    return;
  }

  if (!renderLeafletMap()) {
    renderFallbackMap();
  }
}

function drawPropertySocRadius() {
  if (!state.map?.socLayer) return;
  state.map.socLayer.clearLayers();
  const detail = state.property.detail;
  if (!state.apartments.showSocRadius || !detail?.lat || !detail?.lng) return;
  const radiusMeters = Number(detail.socRadius?.meters || 1600);
  L.circle([Number(detail.lat), Number(detail.lng)], {
    radius: radiusMeters,
    color: "#23665a",
    weight: 2,
    opacity: 0.8,
    fillColor: "#2f8f58",
    fillOpacity: 0.08,
    dashArray: "8 8"
  })
    .bindTooltip(`생활 SOC 반경 ${formatDistance(radiusMeters)}`, { direction: "top" })
    .addTo(state.map.socLayer);
}

function renderMapSidebar() {
  // Map-side list panels were removed; sidebar cards are the single ranking surface.
}

function renderMapRouteChip() {
  // Route details stay in the subpanel; the map keeps only the route geometry.
}

function renderDetailSubpanelState() {
  const selected = state.results.find((item) => item.id === state.selectedId);
  const open = Boolean(state.detailPanelOpen && selected);
  document.querySelector(".workspace")?.classList.toggle("has-subpanel", open);

  if (!nodes.detailSubpanel) return;
  nodes.detailSubpanel.hidden = !open;
  nodes.detailSubpanel.setAttribute("aria-hidden", open ? "false" : "true");

  if (nodes.subpanelMeta) {
    nodes.subpanelMeta.textContent = selected ? "" : "매칭 결과를 선택하세요";
  }
}

function propertyMetric(label, value, note = "") {
  return `
    <div class="property-metric">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      ${note ? `<small>${escapeHtml(note)}</small>` : ""}
    </div>
  `;
}

function statusText(status) {
  if (status === "high") return "집중 확인";
  if (status === "warning") return "주의";
  if (status === "unknown") return "미확인";
  return "양호";
}

function renderTrendChart(rows) {
  if (!Array.isArray(rows) || rows.length < 2) {
    return `<div class="chart-empty">거래 추이 데이터 준비 중</div>`;
  }
  const values = rows.flatMap((row) => [Number(row.sale10k || 0), Number(row.jeonse10k || 0)]).filter(Boolean);
  const min = Math.min(...values) * 0.96;
  const max = Math.max(...values) * 1.04;
  const width = 420;
  const height = 170;
  const left = 34;
  const right = 14;
  const top = 18;
  const bottom = 32;
  const usableWidth = width - left - right;
  const usableHeight = height - top - bottom;
  const y = (value) => top + usableHeight - ((Number(value) - min) / (max - min || 1)) * usableHeight;
  const x = (index) => left + (index / (rows.length - 1)) * usableWidth;
  const salePoints = rows.map((row, index) => `${x(index).toFixed(1)},${y(row.sale10k).toFixed(1)}`).join(" ");
  const jeonsePoints = rows.map((row, index) => `${x(index).toFixed(1)},${y(row.jeonse10k).toFixed(1)}`).join(" ");
  const first = rows[0]?.month || "";
  const last = rows[rows.length - 1]?.month || "";
  return `
    <svg class="property-trend-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="최근 거래 추이 그래프">
      <line x1="${left}" y1="${top}" x2="${left}" y2="${height - bottom}" />
      <line x1="${left}" y1="${height - bottom}" x2="${width - right}" y2="${height - bottom}" />
      <polyline class="sale-line" points="${salePoints}" />
      <polyline class="jeonse-line" points="${jeonsePoints}" />
      <text x="${left}" y="${height - 10}">${escapeHtml(first)}</text>
      <text x="${width - right}" y="${height - 10}" text-anchor="end">${escapeHtml(last)}</text>
      <text x="${left}" y="12">${escapeHtml(formatMoney10k(max))}</text>
      <text x="${width - right}" y="12" text-anchor="end">매매 / 전세</text>
    </svg>
    <div class="chart-legend">
      <span><i class="chart-dot sale"></i>매매 추정</span>
      <span><i class="chart-dot jeonse"></i>전세 추정</span>
    </div>
  `;
}

function renderRiskSignals(risk) {
  const signals = Array.isArray(risk?.signals) ? risk.signals : [];
  return signals.map((item) => `
    <li class="risk-signal ${riskTone(item.status)}">
      <div>
        <strong>${escapeHtml(item.label)}</strong>
        <span>${escapeHtml(item.evidence)}</span>
      </div>
      <em>${escapeHtml(item.value)} · ${statusText(item.status)}</em>
    </li>
  `).join("");
}

function renderPriceLiveStatus(price) {
  const liveStatus = price?.liveStatus || {};
  const labels = {
    molitTrade: "매매 실거래",
    molitRent: "전월세 실거래",
    publicPrice: "공시가격"
  };
  const entries = Object.entries(labels).map(([key, label]) => ({ key, label, status: liveStatus[key] || {} }));
  if (!entries.some((entry) => Object.keys(entry.status).length)) return "";
  return `
    <div class="price-live-status" aria-label="가격 API 연계 상태">
      ${entries.map(({ key, label, status }) => `
        <div class="price-live-status-item ${status.mode === "live_api" ? "is-live" : ""}" data-price-status="${escapeHtml(key)}">
          <strong>${escapeHtml(label)}</strong>
          <span>${escapeHtml(status.mode || "not_configured")} · ${formatNumber(status.recordCount || 0)}건</span>
          <small>${escapeHtml(status.note || "")}</small>
        </div>
      `).join("")}
    </div>
  `;
}

function renderContractChecklist(risk) {
  const items = Array.isArray(risk?.contractChecklist) ? risk.contractChecklist : [];
  if (!items.length) return `<div class="compare-empty">계약 전 확인 체크리스트 준비 중</div>`;
  return `
    <ul class="checklist-list">
      ${items.map((item) => `
        <li class="checklist-item priority-${escapeHtml(item.priority || "medium")}">
          <div>
            <strong>${escapeHtml(item.label)}</strong>
            <span>${escapeHtml(item.reason)}</span>
          </div>
          <em>${escapeHtml(item.status)}</em>
        </li>
      `).join("")}
    </ul>
  `;
}

function renderCompareTable() {
  const rows = state.property.comparison;
  if (!rows.length) {
    return `<div class="compare-empty">비교에 추가한 단지가 없습니다. 상세 패널에서 최대 3개까지 추가할 수 있습니다.</div>`;
  }
  return `
    <div class="property-compare-table">
      <table>
        <thead>
          <tr>
            <th scope="col">단지</th>
            <th scope="col">매매</th>
            <th scope="col">전세가율</th>
            <th scope="col">위험 신호</th>
            <th scope="col">생활권</th>
            <th scope="col"></th>
          </tr>
        </thead>
        <tbody>
          ${rows.map((item) => `
            <tr>
              <th scope="row">${escapeHtml(item.name)}</th>
              <td>${formatMoney10k(item.price.recentSale10k)}</td>
              <td>${formatPercent(item.price.jeonseRatio)}</td>
              <td><span class="risk-pill ${riskTone(item.risk.levelKey)}">${escapeHtml(item.risk.level)}</span></td>
              <td>${escapeHtml(item.lifestyle.livingAreaName)} · SOC ${formatNumber(item.lifestyle.serviceScore)}</td>
              <td><button class="text-button" type="button" data-compare-remove="${escapeHtml(item.id)}">제거</button></td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderAgentAnswer() {
  const answer = state.property.agentAnswer;
  if (state.property.agentLoading) {
    return `<div class="agent-answer is-loading">데이터 근거를 정리하는 중입니다.</div>`;
  }
  if (state.property.agentError) {
    return `<div class="agent-answer is-error">${escapeHtml(state.property.agentError)}</div>`;
  }
  if (!answer) {
    return `<div class="agent-answer">질문을 입력하면 가격·생활권·전세 위험 신호 근거를 함께 답변합니다.</div>`;
  }
  return `
    <div class="agent-answer">
      <p>${escapeHtml(answer.answer)}</p>
      ${renderAgentBasisGroups(answer)}
      ${(answer.suggestedComparisons || []).length ? `
        <div class="agent-suggestions">
          ${(answer.suggestedComparisons || []).map((item) => `
            <button type="button" class="chip-button" data-agent-property-id="${escapeHtml(item.id)}">
              ${escapeHtml(item.name)} · ${escapeHtml(item.saleLabel)} · ${escapeHtml(item.riskLevel)}
            </button>
          `).join("")}
        </div>
      ` : ""}
      <small>${escapeHtml(answer.disclaimer || "")}</small>
    </div>
  `;
}

function renderAgentBasisGroups(answer) {
  const groups = answer?.basisGroups || null;
  if (!groups) {
    return `<ul>${(answer?.basis || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
  }
  return `
    <div class="agent-basis-grid">
      ${Object.entries(groups).map(([title, items]) => `
        <section>
          <strong>${escapeHtml(title)}</strong>
          <ul>${(items || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        </section>
      `).join("")}
    </div>
  `;
}

function addPropertyToCompare(detail) {
  if (!detail) return;
  const existing = state.property.comparison.find((item) => item.id === detail.id);
  if (existing) return;
  state.property.comparison = [...state.property.comparison, detail].slice(-3);
  renderPropertyDashboard();
}

function removePropertyFromCompare(id) {
  state.property.comparison = state.property.comparison.filter((item) => item.id !== id);
  renderPropertyDashboard();
}

function closePropertyDashboard() {
  state.property.selectedId = null;
  state.property.detail = null;
  state.property.error = "";
  state.property.isLoading = false;
  state.property.agentAnswer = null;
  state.property.agentError = "";
  state.property.requestId += 1;
  renderApartmentLayer();
  renderPropertyDashboard();
  drawPropertySocRadius();
}

async function askPropertyAgent(event) {
  event?.preventDefault();
  const detail = state.property.detail;
  if (!detail) return;
  const input = document.querySelector("#propertyAgentQuestion");
  const question = input?.value?.trim() || state.property.agentQuestion;
  state.property.agentQuestion = question;
  state.property.agentLoading = true;
  state.property.agentError = "";
  renderPropertyDashboard();
  try {
    const params = new URLSearchParams({ id: detail.id, question });
    const payload = await fetchJson(`/api/property-agent?${params.toString()}`);
    state.property.agentAnswer = payload.agent || null;
  } catch (error) {
    state.property.agentError = `AI Agent 응답 실패: ${error.message}`;
  } finally {
    state.property.agentLoading = false;
    renderPropertyDashboard();
  }
}

function bindPropertyDashboardEvents() {
  document.querySelector("#propertyCloseButton")?.addEventListener("click", closePropertyDashboard);
  document.querySelector("#addCompareButton")?.addEventListener("click", () => {
    addPropertyToCompare(state.property.detail);
  });
  document.querySelectorAll("[data-compare-remove]").forEach((button) => {
    button.addEventListener("click", () => removePropertyFromCompare(button.dataset.compareRemove));
  });
  document.querySelector("#propertyAgentForm")?.addEventListener("submit", askPropertyAgent);
  document.querySelectorAll("[data-agent-property-id]").forEach((button) => {
    button.addEventListener("click", () => selectProperty(button.dataset.agentPropertyId));
  });
}

function renderPropertyDashboard() {
  if (!nodes.propertyDashboard) return;

  if (state.property.isLoading) {
    nodes.propertyDashboard.classList.add("has-property-detail");
    nodes.propertyDashboard.innerHTML = `
      <div class="property-empty">
        <strong>단지 상세 정보를 불러오는 중입니다.</strong>
        <span>실거래·공시가격 연계 구조와 전세 위험 신호를 계산합니다.</span>
      </div>
    `;
    return;
  }

  if (state.property.error) {
    nodes.propertyDashboard.classList.add("has-property-detail");
    nodes.propertyDashboard.innerHTML = `<div class="property-empty is-error">${escapeHtml(state.property.error)}</div>`;
    drawPropertySocRadius();
    return;
  }

  const detail = state.property.detail;
  if (!detail) {
    nodes.propertyDashboard.classList.remove("has-property-detail");
    nodes.propertyDashboard.innerHTML = `
      <div class="property-empty">
        <strong>지도에서 아파트 단지를 선택하세요.</strong>
        <span>단지 가격, 전세 위험 신호, 생활권 정보, AI 요약을 한 화면에서 확인할 수 있습니다.</span>
      </div>
    `;
    drawPropertySocRadius();
    return;
  }

  nodes.propertyDashboard.classList.add("has-property-detail");
  const price = detail.price || {};
  const risk = detail.risk || {};
  const lifestyle = detail.lifestyle || {};
  const ai = detail.aiSummary || {};
  const areaText = (detail.areaOptions || []).map((item) => `${item.exclusiveM2}㎡`).join(" / ");
  const compareExists = state.property.comparison.some((item) => item.id === detail.id);
  nodes.propertyDashboard.innerHTML = `
    <div class="property-head">
      <div>
        <p class="eyebrow">부동산 상세 대시보드</p>
        <h3>${escapeHtml(detail.name)}</h3>
        <p>${escapeHtml(detail.address || "")}</p>
      </div>
      <div class="property-actions">
        <button id="propertyCloseButton" class="property-close-button" type="button" aria-label="부동산 상세 대시보드 닫기">×</button>
        <span class="risk-pill ${riskTone(risk.levelKey)}">${escapeHtml(risk.level || "점검 필요")} · ${formatNumber(risk.score)}점</span>
        <button id="addCompareButton" class="ghost-button" type="button" ${compareExists ? "disabled" : ""}>
          ${compareExists ? "비교 추가됨" : "비교에 추가"}
        </button>
      </div>
    </div>

    <div class="property-grid">
      <section class="property-card">
        <div class="property-card-title">
          <h4>기본 정보</h4>
          <span>OpenAptInfo</span>
        </div>
        <div class="property-metrics two">
          ${propertyMetric("건물 유형", detail.buildingType || "공동주택")}
          ${propertyMetric("주택 유형", detail.housingType || "확인 필요")}
          ${propertyMetric("준공/사용승인", detail.approvalYear ? `${detail.approvalYear}년` : "확인 필요", `${formatNumber(detail.buildingAge)}년 경과`)}
          ${propertyMetric("세대/동수", `${formatNumber(detail.households)}세대`, `${formatNumber(detail.buildingCount)}개동`)}
          ${propertyMetric("면적 옵션", areaText || "확인 필요")}
          ${propertyMetric("용도지역", detail.landUse || "연계 예정")}
        </div>
      </section>

      <section class="property-card">
        <div class="property-card-title">
          <h4>가격 정보</h4>
          <span>${escapeHtml(price.sourceLabel || "공공 데이터 기반")}</span>
        </div>
        <div class="property-metrics two">
          ${propertyMetric("최근 매매가", formatMoney10k(price.recentSale10k), "실거래 API 연계 전 추정")}
          ${propertyMetric("최근 전세가", formatMoney10k(price.recentJeonse10k), `전세가율 ${formatPercent(price.jeonseRatio)}`)}
          ${propertyMetric("월세", `${formatMoney10k(price.monthlyDeposit10k)} / 월 ${formatMoney10k(price.monthlyRent10k)}`, "생활권 월세 중앙값 기반")}
          ${propertyMetric("공시가격", formatMoney10k(price.officialPrice10k), "공시가격 API 연계 전 추정")}
          ${propertyMetric("주변 평균 매매", formatMoney10k(price.surroundingAverageSale10k), `${price.saleGapPercent > 0 ? "+" : ""}${formatPercent(price.saleGapPercent)} 차이`)}
          ${propertyMetric("최근 변동률", `${price.priceChangeRate > 0 ? "+" : ""}${formatPercent(price.priceChangeRate)}`, "최근 1년 추정")}
        </div>
        ${renderPriceLiveStatus(price)}
      </section>

      <section class="property-card wide">
        <div class="property-card-title">
          <h4>거래 추이</h4>
          <span>최근 12개월</span>
        </div>
        ${renderTrendChart(detail.transactions)}
      </section>

      <section class="property-card">
        <div class="property-card-title">
          <h4>전세 위험 신호 점검</h4>
          <span>법적 판정 아님</span>
        </div>
        <p class="risk-summary">${escapeHtml(risk.summary || "")}</p>
        <ul class="risk-list">${renderRiskSignals(risk)}</ul>
        <p class="property-note">${escapeHtml(risk.disclaimer || "")}</p>
      </section>

      <section class="property-card">
        <div class="property-card-title">
          <h4>계약 전 확인 체크리스트</h4>
          <span>전세 위험 보완</span>
        </div>
        ${renderContractChecklist(risk)}
      </section>

      <section class="property-card">
        <div class="property-card-title">
          <h4>생활권 정보</h4>
          <span>${escapeHtml(lifestyle.livingAreaName || "")}</span>
        </div>
        <div class="property-metrics two">
          ${propertyMetric("대중교통", `${formatNumber(lifestyle.transitScore)}점`, lifestyle.station || "")}
          ${propertyMetric("생활 SOC", `${formatNumber(lifestyle.serviceScore)}점`, `병원 ${formatNumber(lifestyle.counts?.hospital)} · 학교 ${formatNumber(lifestyle.counts?.school)} · 공원 ${formatNumber(lifestyle.counts?.park)}`)}
          ${propertyMetric("안전", `${formatNumber(lifestyle.safetyScore)}점`, `치안시설 ${formatNumber(lifestyle.counts?.police)} · CCTV ${formatNumber(lifestyle.counts?.cctv)}`)}
          ${propertyMetric("환경", `${formatNumber(lifestyle.carbonScore)}점`, "대기질·녹지 접근성")}
          ${propertyMetric("SOC 반경", formatDistance(detail.socRadius?.meters || 1600), "지도 원으로 표시")}
        </div>
      </section>

      <section class="property-card wide">
        <div class="property-card-title">
          <h4>AI 요약</h4>
          <span>데이터 근거 기반</span>
        </div>
        <p class="ai-headline">${escapeHtml(ai.headline || "")}</p>
        <div class="ai-summary-grid">
          <div><strong>장점</strong><ul>${(ai.strengths || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div>
          <div><strong>단점</strong><ul>${(ai.weaknesses || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div>
          <div><strong>주의사항</strong><ul>${(ai.cautions || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul></div>
        </div>
        <p class="recommendation-text">${escapeHtml(ai.recommendation || "")}</p>
      </section>

      <section class="property-card wide">
        <div class="property-card-title">
          <h4>단지 비교</h4>
          <span>최대 3개</span>
        </div>
        ${renderCompareTable()}
      </section>

      <section class="property-card wide">
        <div class="property-card-title">
          <h4>AI Agent 질의응답</h4>
          <span>가격·이동·위험 신호 통합</span>
        </div>
        <form id="propertyAgentForm" class="agent-form">
          <input id="propertyAgentQuestion" type="text" value="${escapeHtml(state.property.agentQuestion)}" aria-label="AI Agent 질문">
          <button class="primary-button" type="submit">질문</button>
        </form>
        ${renderAgentAnswer()}
      </section>

      <section class="property-card wide data-status">
        <div class="property-card-title">
          <h4>데이터 연계 상태</h4>
          <span>실데이터와 추정 구분</span>
        </div>
        <dl>
          ${Object.entries(detail.dataStatus || {}).map(([key, value]) => `<div><dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd></div>`).join("")}
        </dl>
      </section>
    </div>
  `;
  bindPropertyDashboardEvents();
  drawPropertySocRadius();
}

async function selectProperty(id) {
  if (!id) return;
  state.property.selectedId = id;
  state.property.isLoading = true;
  state.property.error = "";
  state.property.agentAnswer = null;
  state.property.agentError = "";
  state.property.requestId += 1;
  const requestId = state.property.requestId;
  renderApartmentLayer();
  renderPropertyDashboard();

  try {
    const payload = await fetchJson(`/api/property-detail?id=${encodeURIComponent(id)}`);
    if (requestId !== state.property.requestId) return;
    state.property.detail = payload.detail || null;
    if (state.property.detail) {
      state.property.agentQuestion = `${state.property.detail.name} 전세 들어가도 괜찮아?`;
      addPropertyToCompare(state.property.detail);
      drawPropertySocRadius();
    }
  } catch (error) {
    if (requestId !== state.property.requestId) return;
    state.property.detail = null;
    state.property.error = `단지 상세 정보를 불러오지 못했습니다: ${error.message}`;
  } finally {
    if (requestId === state.property.requestId) {
      state.property.isLoading = false;
      renderApartmentLayer();
      renderPropertyDashboard();
    }
  }
}

function buildReason(item) {
  return item.reasonText || buildSpecificReason(item);
}

function buildSpecificReason(item) {
  const socCounts = item.evidence?.socCounts || item.socSummary?.counts || {};
  const safetyCounts = item.evidence?.safetyEnvCounts || item.safetyEnvSummary?.counts || {};
  const destinationLabel = item.destinationLabel || destinationLabels[state.destination] || "목적지";
  const monthlyRent = Math.round(Number(item.rentMonthly10k || 0));
  const budgetDelta = Math.round(state.budget - monthlyRent);
  const budgetText = budgetDelta >= 0 ? "예산 내" : `예산 ${Math.abs(budgetDelta)}만원 초과`;
  return `${destinationLabel} ${formatNumber(item.minutes)}분 · 월세 중앙값 ${formatNumber(monthlyRent)}만원 · 병원 ${socCounts.hospital || 0}개·학교 ${socCounts.school || 0}개·공원 ${socCounts.park || 0}개 · 치안시설 ${safetyCounts.police || 0}개·CCTV ${formatNumber(safetyCounts.cctv || 0)}대 · ${personaLabels[state.persona]} ${budgetText}`;
}

function formatRentExample(example) {
  const rentType = example.rentType || "거래";
  const monthly = Number(example.monthlyRent10k || 0);
  const price = rentType === "월세"
    ? `보증금 ${formatMoney10k(example.deposit10k)} / 월 ${formatMoney10k(monthly)}`
    : `전세 ${formatMoney10k(example.deposit10k)}`;
  const floor = example.floor ? `${escapeHtml(example.floor)}층` : "층 정보 없음";
  return `${escapeHtml(example.dong)} · ${escapeHtml(example.contractMonth)} · ${escapeHtml(example.buildingUse || rentType)} · ${formatNumber(example.areaM2)}㎡ · ${floor} · ${price}`;
}

function renderRentExamples(selected) {
  const examples = Array.isArray(selected.rentExamples) ? selected.rentExamples : [];
  if (!examples.length) return "";
  return `
    <div class="callout">
      <p><strong>실거래 예시</strong></p>
      <ul class="evidence-list rent-example-list">
        ${examples.map((example) => `<li>${formatRentExample(example)}</li>`).join("")}
      </ul>
      <p class="score-note">전월세 공개파일에서 상세 지번·건물명은 제외하고 후보 매물 판단에 필요한 금액·면적·용도만 표시합니다.</p>
    </div>
  `;
}

function renderSafetyEnvSummary(selected) {
  const summary = selected.safetyEnvSummary || {};
  const counts = summary.counts || selected.evidence?.safetyEnvCounts || {};
  const nearest = summary.nearestFacilities || {};
  const police = nearest.police?.name ? `${nearest.police.name} ${formatDistance(nearest.police.distanceMeters)}` : "근접 치안시설 없음";
  const park = nearest.park?.name ? `${nearest.park.name} ${formatDistance(nearest.park.distanceMeters)}` : "근접 공원 없음";
  return `
    <div class="callout">
      <p><strong>안전·환경 근거</strong><br>
        반경 ${formatDistance(summary.radiusMeters || selected.evidence?.safetyEnvRadiusMeters || 0)} 내
        치안시설 ${counts.police || 0}개, CCTV ${formatNumber(counts.cctv || 0)}대, 공원 ${counts.park || 0}개를 반영했습니다.
        가장 가까운 치안시설은 ${escapeHtml(police)}, 환경 접근성 기준 공원은 ${escapeHtml(park)}입니다.
        대기 기준은 ${escapeHtml(summary.airStation || selected.evidence?.airStation || "서울시 도시대기 측정망")}을 사용합니다.</p>
    </div>
  `;
}

function renderRouteCredentialHint() {
  const integrations = state.apiMeta?.integrations || {};
  const ready = [];
  if (integrations.odsay) ready.push("ODsay");
  if (integrations.tmap) ready.push("TMAP");
  if (ready.length) {
    return `<p class="field-hint route-live-ready">${ready.join("·")} 키 감지됨. 경로 계산 시 live API를 우선 호출합니다.</p>`;
  }
  return `<p class="field-hint">ODsay/TMAP 키가 없으면 거리 기반 폴백을 표시합니다. 키는 환경변수로만 주입하고 코드에는 저장하지 않습니다.</p>`;
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
    nodes.cards.innerHTML = `<div class="empty-state">${state.hasMatched ? "조건에 맞는 매칭 결과가 없습니다." : "조건을 설정하고 매칭하기 버튼을 눌러주세요"}</div>`;
    nodes.toggleCards.hidden = true;
    return;
  }

  const visible = state.showAllCards ? state.results : state.results.slice(0, CARD_PREVIEW_COUNT);

  visible.forEach((item, index) => {
    const fragment = nodes.cardTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".result-card");
    const button = fragment.querySelector(".card-button");
    card.classList.toggle("is-selected", item.id === state.selectedId);
    fragment.querySelector(".rank").textContent = index + 1;
    fragment.querySelector(".name").textContent = `${item.name} · ${item.district}`;
    button.addEventListener("click", () => selectArea(item.id, { source: "card", openDetailPanel: true }));
    nodes.cards.append(fragment);
  });

  const total = state.results.length;
  nodes.toggleCards.hidden = total <= CARD_PREVIEW_COUNT;
  nodes.toggleCards.textContent = state.showAllCards
    ? `상위 ${CARD_PREVIEW_COUNT}개만 보기`
    : "더보기";
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

function routeProviderLabel(provider) {
  if (provider === "odsay") return "ODsay";
  if (provider === "tmap") return "TMAP";
  return "폴백";
}

function routeModeLabel(mode) {
  return mode === "live_api" ? "실제 경로 API" : "거리 기반 추정";
}

function renderRouteSteps(route) {
  const steps = Array.isArray(route.steps) ? route.steps : [];
  if (!steps.length) {
    return `<p class="muted route-empty">표시할 세부 단계가 없습니다.</p>`;
  }
  return `
    <ol class="route-steps">
      ${steps.map((step) => {
        const mode = step.mode || "이동";
        const title = step.route || (mode === "도보" ? "도보 이동" : "구간 이동");
        const color = routeModeColor(step);
        return `
          <li style="--route-color:${color}">
            <span class="route-mode">${routeModeIcon(mode)}</span>
            <strong>${escapeHtml(title)}</strong>
            <span>${escapeHtml(step.startName || "출발")} → ${escapeHtml(step.endName || "도착")}</span>
            <em>${escapeHtml(mode)} · ${formatNumber(step.minutes || 0)}분 · ${formatDistance(step.distanceMeters || 0)}</em>
          </li>
        `;
      }).join("")}
    </ol>
  `;
}

function renderRouteResult(selected) {
  if (state.route.selectedId !== selected.id) return "";
  if (state.route.isLoading) {
    return `<div class="route-result is-loading">실제 통근 경로를 계산하고 있습니다.</div>`;
  }
  if (state.route.error) {
    return `<div class="route-result is-error">${escapeHtml(state.route.error)}</div>`;
  }
  const route = state.route.result;
  if (!route) return "";
  const summary = route.summary || {};
  return `
    <div class="route-result">
      <div class="route-result-head">
        <strong>${routeProviderLabel(route.provider)} · ${routeModeLabel(route.mode)}</strong>
        <button class="text-button" type="button" data-route-map>지도 중심 이동</button>
      </div>
      <div class="route-summary-grid">
        ${metric("총 소요", `${formatNumber(summary.totalMinutes)}분`)}
        ${metric("환승", `${formatNumber(summary.transferCount)}회`)}
        ${metric("도보", formatDistance(summary.totalWalkMeters))}
        ${metric("요금", formatFare(summary.fare))}
      </div>
      <p class="route-label">${escapeHtml(route.origin?.label)} → ${escapeHtml(route.destination?.label)}</p>
      ${renderRouteSteps(route)}
      ${route.notice ? `<p class="score-note">${escapeHtml(route.notice)}</p>` : ""}
    </div>
  `;
}

function renderRouteAreaOptions(selected) {
  const areas = state.results.length ? state.results : state.neighborhoods;
  return areas.map((item, index) => {
    const selectedAttr = item.id === selected.id ? " selected" : "";
    return `<option value="${escapeHtml(item.id)}"${selectedAttr}>${index + 1}위 ${escapeHtml(item.name)} · ${escapeHtml(item.district)}</option>`;
  }).join("");
}

function renderRoutePlanner(selected) {
  const originValue = representativeAddressFor(selected);
  const destinationValue = selected.destinationAddress || destinationAddressFor();
  return `
    <div class="route-planner">
      <div class="route-form">
        <label class="field compact route-area-field">
          <span>검증 생활권</span>
          <select id="routeAreaInput">
            ${renderRouteAreaOptions(selected)}
          </select>
        </label>
        <label class="field compact route-origin-field">
          <span>집 주소</span>
          <input id="routeOriginInput" type="text" value="${escapeHtml(originValue)}" placeholder="예: 서울 광진구 화양동">
        </label>
        <label class="field compact route-destination-field">
          <span>회사 주소</span>
          <input id="routeDestinationInput" type="text" value="${escapeHtml(destinationValue)}" placeholder="예: 서울 강남구 역삼동">
        </label>
        <label class="field compact">
          <span>경로 API</span>
          <select id="routeProviderInput">
            <option value="auto">자동 선택</option>
            <option value="odsay">ODsay</option>
            <option value="tmap">TMAP</option>
          </select>
        </label>
        <button id="routeUseSelectedButton" class="ghost-button route-action" type="button">추천 생활권 주소 사용</button>
        <button id="routeCalculateButton" class="ghost-button route-action primary" type="button">통근 루트 계산</button>
      </div>
      <p class="field-hint">기본 대표 주소는 로컬 좌표로 바로 변환됩니다. 직접 입력한 상세 주소 검색은 Kakao REST 키가 있을 때 동작합니다.</p>
      ${renderRouteCredentialHint()}
      ${renderRouteResult(selected)}
    </div>
  `;
}

function renderEvidence(selected) {
  if (!selected.evidence) return "";
  const evidence = selected.evidence;
  const rentDongs = Array.isArray(evidence.rentDongs) ? evidence.rentDongs.join("·") : "";
  const socCounts = evidence.socCounts || selected.socSummary?.counts || {};
  const safetyCounts = evidence.safetyEnvCounts || selected.safetyEnvSummary?.counts || {};
  const socText = `병원 ${socCounts.hospital || 0} · 학교 ${socCounts.school || 0} · 공원 ${socCounts.park || 0}`;
  const safetyText = `치안시설 ${safetyCounts.police || 0} · CCTV ${formatNumber(safetyCounts.cctv || 0)}대 · 대기측정 ${evidence.airStation || selected.safetyEnvSummary?.airStation || "서울시 도시대기 측정망"}`;
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
        <li>안전·환경: 반경 ${formatDistance(evidence.safetyEnvRadiusMeters)} ${safetyText}</li>
        <li>실거래 예시: ${formatNumber(evidence.rentExampleCount || selected.rentExamples?.length || 0)}건 표시용 발췌</li>
      </ul>
    </div>
  `;
}

function renderDetail() {
  const selected = state.results.find((item) => item.id === state.selectedId);

  if (!selected) {
    nodes.selectedBadge.textContent = "선택 없음";
    nodes.detailContent.innerHTML = state.isLoading ? `<div class="callout"><p>추천 결과를 계산하고 있습니다.</p></div>` : "";
    return;
  }

  nodes.selectedBadge.textContent = selected.name;
  nodes.detailContent.innerHTML = `
    <div>
      <h3>${selected.name} · ${selected.district}</h3>
    </div>
    <div class="score-list" aria-label="항목별 점수">
      ${scoreRow("통근", selected.adjusted.commute, scoreTips.commute)}
      ${scoreRow("주거비", selected.adjusted.cost, scoreTips.cost)}
      ${scoreRow("생활 SOC", selected.adjusted.service, scoreTips.service)}
      ${scoreRow("안전·환경", selected.adjusted.safety, scoreTips.safety)}
    </div>
    <div class="metric-grid">
      ${metric("종합점수", `${selected.total}점`)}
      ${metric("통근시간", `${selected.minutes}분`)}
      ${metric("월세 중앙값", formatMoney10k(selected.rentMonthly10k))}
      ${metric("보증금 중앙값", formatMoney10k(selected.deposit10k))}
      ${metric("전세 중앙값", formatMoney10k(selected.jeonse10k))}
      ${metric("대중교통", `${selected.transitScore}점`)}
    </div>
  `;
}

function renderRoutePanel() {
  const selected = state.results.find((item) => item.id === state.selectedId);

  if (!nodes.routeContent) return;
  if (!selected) {
    nodes.routeContent.innerHTML = state.isLoading
      ? `<div class="callout"><p>추천 후보를 불러온 뒤 통근 루트를 계산할 수 있습니다.</p></div>`
      : `<div class="callout"><p>추천 생활권을 선택하거나 추천 조건을 계산하면 집 주소와 회사 주소 기준 통근 루트를 검증할 수 있습니다.</p></div>`;
    return;
  }

  nodes.routeContent.innerHTML = renderRoutePlanner(selected);
  bindRoutePlanner(selected);
}

function resetRouteState() {
  state.route = {
    selectedId: null,
    isLoading: false,
    result: null,
    error: "",
    focusMap: false
  };
  if (state.map?.routeLayer) {
    state.map.routeLayer.clearLayers();
  }
}

async function calculateRouteForSelected(selected, provider = "auto") {
  if (!selected) return;
  const origin = representativeAddressFor(selected);
  const destinationText = selected.destinationAddress || destinationAddressFor();
  const params = new URLSearchParams({
    origin,
    provider,
    destinationQuery: destinationText
  });

  state.route = { selectedId: selected.id, isLoading: true, result: null, error: "", focusMap: false };
  renderRoutePanel();

  try {
    const payload = await fetchJson(`/api/commute-route?${params.toString()}`);
    if (state.selectedId !== selected.id) return;
    state.route = { selectedId: selected.id, isLoading: false, result: payload, error: "", focusMap: true };
    if (state.map) {
      state.map.fitted = false;
    }
    render();
  } catch (error) {
    if (state.selectedId !== selected.id) return;
    state.route = {
      selectedId: selected.id,
      isLoading: false,
      result: null,
      error: `경로 계산 실패: ${error.message}`,
      focusMap: false
    };
    renderRoutePanel();
  }
}

async function calculateCommuteRoute(selected) {
  const originInput = document.querySelector("#routeOriginInput");
  const destinationInput = document.querySelector("#routeDestinationInput");
  const providerInput = document.querySelector("#routeProviderInput");
  if (!originInput || !destinationInput || !providerInput) return;

  const origin = originInput.value.trim();
  const destinationText = destinationInput.value.trim();
  const params = new URLSearchParams({
    origin,
    provider: providerInput.value || "auto"
  });

  if (!origin) {
    state.route = { selectedId: selected.id, isLoading: false, result: null, error: "집 위치를 입력하세요.", focusMap: false };
    renderRoutePanel();
    return;
  }
  if (destinationText) {
    params.set("destinationQuery", destinationText);
  } else {
    params.set("destination", state.destination);
  }

  state.route = { selectedId: selected.id, isLoading: true, result: null, error: "", focusMap: false };
  renderRoutePanel();

  try {
    const payload = await fetchJson(`/api/commute-route?${params.toString()}`);
    state.route = { selectedId: selected.id, isLoading: false, result: payload, error: "", focusMap: true };
    if (state.map) {
      state.map.fitted = false;
    }
    render();
  } catch (error) {
    state.route = {
      selectedId: selected.id,
      isLoading: false,
      result: null,
      error: `경로 계산 실패: ${error.message}`,
      focusMap: false
    };
    renderRoutePanel();
  }
}

function bindRoutePlanner(selected) {
  const routeAreaInput = document.querySelector("#routeAreaInput");
  const originInput = document.querySelector("#routeOriginInput");
  const providerInput = document.querySelector("#routeProviderInput");
  const useSelectedButton = document.querySelector("#routeUseSelectedButton");
  const calculateButton = document.querySelector("#routeCalculateButton");
  const mapButton = document.querySelector("[data-route-map]");

  if (providerInput && state.route.selectedId === selected.id && state.route.result?.provider) {
    providerInput.value = state.route.result.provider === "fallback" ? "auto" : state.route.result.provider;
  }

  routeAreaInput?.addEventListener("change", (event) => {
    selectArea(event.target.value, { source: "route" });
  });

  useSelectedButton?.addEventListener("click", () => {
    if (originInput) {
      originInput.value = representativeAddressFor(selected);
    }
  });

  calculateButton?.addEventListener("click", () => calculateCommuteRoute(selected));

  mapButton?.addEventListener("click", () => {
    if (state.map) {
      focusRouteOnMap();
    }
  });
}

function renderEvidenceTable() {
  if (!nodes.evidenceTableBody || state.evidenceRendered || !state.neighborhoods.length) return;

  const rows = [...state.neighborhoods]
    .sort((a, b) => (b.evidence?.matchedRentRecords || 0) - (a.evidence?.matchedRentRecords || 0))
    .map((item) => {
      const evidence = item.evidence || {};
      const dongs = Array.isArray(evidence.rentDongs) ? evidence.rentDongs.join(", ") : "-";
      const socCounts = evidence.socCounts || item.socSummary?.counts || {};
      const safetyCounts = evidence.safetyEnvCounts || item.safetyEnvSummary?.counts || {};
      const socSummary = `병원 ${socCounts.hospital || 0} · 학교 ${socCounts.school || 0} · 공원 ${socCounts.park || 0}`;
      const safetySummary = `치안 ${safetyCounts.police || 0} · CCTV ${formatNumber(safetyCounts.cctv || 0)}대`;
      return `
        <tr>
          <th scope="row">${item.name}<span class="cell-sub">${item.district}</span></th>
          <td>${dongs}</td>
          <td class="num">${formatNumber(evidence.matchedRentRecords)}건</td>
          <td class="num">${formatNumber(item.rentMonthly10k)}만원</td>
          <td class="num">${formatMoney10k(item.deposit10k)}</td>
          <td class="num">${formatMoney10k(item.jeonse10k)}</td>
          <td>${socSummary}<span class="cell-sub">반경 ${formatDistance(evidence.socRadiusMeters)}</span></td>
          <td>${safetySummary}<span class="cell-sub">${item.safetyEnvSummary?.airStation || evidence.airStation || "도시대기 측정망"}</span></td>
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
      <td colspan="5" class="muted">15~85㎡ 거래 중앙값 · 생활 SOC/안전환경 반경 집계 기준</td>
    </tr>
  `);

  nodes.evidenceTableBody.innerHTML = rows.join("");
  state.evidenceRendered = true;
}

function renderApiStatus() {
  if (nodes.apiStatusPill) {
    if (state.apiOnline) {
      nodes.apiStatusPill.textContent = "API 연결됨";
      nodes.apiStatusPill.className = "nav-status is-online";
      nodes.apiStatusPill.title = "추천이 서버 API에서 계산됩니다.";
    } else {
      nodes.apiStatusPill.textContent = "로컬 계산";
      nodes.apiStatusPill.className = "nav-status is-offline";
      nodes.apiStatusPill.title = state.lastError || "API 미연결 시 브라우저에서 동일 로직으로 계산합니다.";
    }
  }
  if (nodes.apiStatusLabel) {
    nodes.apiStatusLabel.textContent = state.apiOnline ? "API" : "로컬";
  }
  if (nodes.refreshButton) {
    nodes.refreshButton.title = state.apiOnline
      ? "API 데이터로 추천 새로고침"
      : "로컬 데이터로 추천 새로고침";
  }
}

function renderLoadingHint() {
  nodes.cards.classList.toggle("is-loading", state.isLoading);
  nodes.cards.setAttribute("aria-busy", state.isLoading ? "true" : "false");
}

function syncRangeProgress(input) {
  if (!input) return;
  const min = Number(input.min || 0);
  const max = Number(input.max || 100);
  const value = Number(input.value || 0);
  const progress = max === min ? 0 : ((value - min) / (max - min)) * 100;
  input.style.setProperty("--range-progress", `${clamp(progress)}%`);
}

function syncAllRangeProgress() {
  [
    nodes.budgetInput,
    nodes.commuteWeight,
    nodes.costWeight,
    nodes.serviceWeight,
    nodes.safetyWeight
  ].forEach(syncRangeProgress);
}

function renderControls() {
  const sourceYear = state.apiMeta?.housingSource?.year;
  const modeLabel = state.apiOnline ? "API" : "로컬";
  nodes.budgetOutput.textContent = `${state.budget}만원`;
  nodes.commuteWeightOutput.textContent = `${state.weights.commute}%`;
  nodes.costWeightOutput.textContent = `${state.weights.cost}%`;
  nodes.serviceWeightOutput.textContent = `${state.weights.service}%`;
  nodes.safetyWeightOutput.textContent = `${state.weights.safety}%`;
  if (nodes.candidateCount) {
    nodes.candidateCount.textContent = state.apiMeta?.totalCandidates || state.neighborhoods.length;
  }
  if (nodes.destinationInput && nodes.destinationInput.value !== state.destinationQuery) {
    nodes.destinationInput.value = state.destinationQuery;
  }
  if (nodes.matchButton) {
    nodes.matchButton.disabled = state.isLoading || !state.neighborhoods.length;
    nodes.matchButton.textContent = state.isLoading ? "매칭 중" : "매칭하기";
  }
  syncAllRangeProgress();

  nodes.resultSummary.textContent = "";

  const stamp = state.lastUpdated
    ? state.lastUpdated.toLocaleTimeString("ko-KR", { hour12: false })
    : "";
  nodes.updatedAt.textContent = state.isLoading
    ? "매칭 계산 중…"
    : !state.hasMatched
      ? ""
      : sourceYear
        ? `${modeLabel} 계산 · ${sourceYear} 서울 전월세 실데이터${stamp ? ` · ${stamp} 기준` : ""}`
        : "데이터 준비 중";
}

function render() {
  renderControls();
  renderApiStatus();
  renderMap();
  renderMapSidebar();
  renderMapRouteChip();
  renderPropertyDashboard();
  renderCards();
  renderDetail();
  renderRoutePanel();
  renderDetailSubpanelState();
  renderEvidenceTable();
}

function selectArea(id, options = {}) {
  const shouldResetRoute = options.resetRoute ?? ["card", "map", "route"].includes(options.source);
  if (state.selectedId !== id || shouldResetRoute) {
    resetRouteState();
  }
  state.selectedId = id;

  const rank = state.results.findIndex((item) => item.id === id);
  if (rank >= CARD_PREVIEW_COUNT && !state.showAllCards) {
    state.showAllCards = true;
  }

  if (options.openDetailPanel) {
    state.detailPanelOpen = true;
  }

  render();
  focusSelectedMarker({ zoom: ["card", "map"].includes(options.source) });
}

function setActiveNav(sectionId) {
  nodes.navLinks.forEach((link) => {
    link.classList.toggle("is-active", link.dataset.section === sectionId);
  });
}

function activateSection(sectionId, options = {}) {
  const target = document.getElementById(sectionId) ? sectionId : "recommend";
  state.activeSection = target;
  document.body.classList.toggle("is-map-view", target === "map");
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
      if (state.apartments.enabled) {
        scheduleApartmentLayerLoad();
      }
      focusSelectedMarker();
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

function resetUserSettings() {
  state.budget = 70;
  state.destination = "gangnam";
  state.destinationQuery = "";
  state.persona = "single";
  state.weights = { commute: 25, cost: 25, service: 25, safety: 25 };
  state.results = [];
  state.selectedId = null;
  state.showAllCards = false;
  state.detailPanelOpen = false;
  state.hasMatched = false;
  state.isLoading = false;
  state.apartments.enabled = true;
  state.apartments.labelMode = "sale";
  state.apartments.showSocRadius = true;
  state.apartments.lastKey = "";
  state.property.selectedId = null;
  state.property.detail = null;
  state.property.error = "";
  state.evidenceRendered = false;

  nodes.budgetInput.value = state.budget;
  nodes.destinationInput.value = state.destinationQuery;
  document.querySelector("input[name='persona'][value='single']").checked = true;
  nodes.commuteWeight.value = state.weights.commute;
  nodes.costWeight.value = state.weights.cost;
  nodes.serviceWeight.value = state.weights.service;
  nodes.safetyWeight.value = state.weights.safety;
  if (nodes.apartmentLayerToggle) nodes.apartmentLayerToggle.checked = true;
  if (nodes.mapLabelModeInput) nodes.mapLabelModeInput.value = "sale";
  if (nodes.socRadiusToggle) nodes.socRadiusToggle.checked = true;
  resetRouteState();
  if (state.map) {
    state.map.fitted = false;
  }
}

async function refreshAllData() {
  if (nodes.refreshButton) {
    nodes.refreshButton.disabled = true;
    nodes.refreshButton.classList.add("is-loading");
  }

  window.clearTimeout(state.refreshTimer);
  resetUserSettings();
  render();

  try {
    await loadAreas();
    render();
    if (state.apartments.enabled) {
      scheduleApartmentLayerLoad(true);
    }
  } finally {
    if (nodes.refreshButton) {
      nodes.refreshButton.disabled = false;
      nodes.refreshButton.classList.remove("is-loading");
    }
    renderApiStatus();
  }
}

function bindEvents() {
  nodes.budgetInput.addEventListener("input", (event) => {
    state.budget = Number(event.target.value);
    scheduleRefresh();
  });

  const updateDestinationFromInput = (value, delay = 180) => {
    const query = String(value || "");
    const normalizedQuery = query.trim();
    state.destinationQuery = query;
    if (normalizedQuery) {
      state.destination = inferDestinationKey(normalizedQuery);
    }
    state.apartments.lastKey = "";
    resetRouteState();
    scheduleRefresh(delay);
    if (state.apartments.enabled) {
      scheduleApartmentLayerLoad(true);
    }
  };

  nodes.destinationInput.addEventListener("input", (event) => {
    updateDestinationFromInput(event.target.value, 220);
  });

  nodes.destinationInput.addEventListener("change", (event) => {
    updateDestinationFromInput(event.target.value, 0);
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

  nodes.matchButton?.addEventListener("click", () => {
    window.clearTimeout(state.refreshTimer);
    state.showAllCards = false;
    state.detailPanelOpen = false;
    state.property.selectedId = null;
    state.property.detail = null;
    state.property.error = "";
    state.property.isLoading = false;
    state.property.agentAnswer = null;
    state.property.agentError = "";
    state.property.requestId += 1;
    resetRouteState();
    refreshRecommendations();
  });

  [nodes.closeSubpanelButton, nodes.subpanelCloseXButton].forEach((button) => {
    button?.addEventListener("click", () => {
      state.detailPanelOpen = false;
      renderDetailSubpanelState();
    });
  });

  nodes.refreshButton?.addEventListener("click", () => {
    refreshAllData();
  });

  nodes.resetButton?.addEventListener("click", () => {
    resetUserSettings();
    scheduleRefresh(0);
  });

  nodes.apartmentLayerToggle?.addEventListener("change", (event) => {
    state.apartments.enabled = event.target.checked;
    state.apartments.lastKey = "";

    if (!state.apartments.enabled) {
      state.apartments.features = [];
      state.apartments.error = "";
      state.map?.apartmentLayer?.clearLayers();
      renderApartmentLayerStatus();
      return;
    }

    scheduleApartmentLayerLoad(true);
    renderApartmentLayerStatus();
  });

  nodes.mapLabelModeInput?.addEventListener("change", (event) => {
    state.apartments.labelMode = event.target.value;
    renderApartmentLayer();
    renderMapSidebar();
    updateMapScaleUI();
  });

  nodes.socRadiusToggle?.addEventListener("change", (event) => {
    state.apartments.showSocRadius = event.target.checked;
    drawPropertySocRadius();
  });
}

async function init() {
  bindEvents();
  initNavigation();
  render();
  await loadAreas();
  render();
}

init().catch((error) => {
  nodes.cards.innerHTML = `<div class="empty-state">데이터를 불러오지 못했습니다.</div>`;
  nodes.detailContent.innerHTML = `<div class="callout"><p>데이터를 불러오지 못했습니다: ${error.message}</p></div>`;
});
