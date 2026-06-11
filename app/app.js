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
  route: {
    selectedId: null,
    isLoading: false,
    result: null,
    error: ""
  },
  apartments: {
    enabled: true,
    isLoading: false,
    features: [],
    meta: null,
    error: "",
    lastKey: "",
    requestId: 0,
    timer: null
  },
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

const destinationAddresses = {
  gangnam: "서울 강남구 역삼동",
  yeouido: "서울 영등포구 여의도동",
  seoulStation: "서울 중구 봉래동2가",
  digital: "서울 구로구 구로동",
  pangyo: "경기도 성남시 분당구 삼평동"
};

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
  resetButton: document.querySelector("#resetButton"),
  cards: document.querySelector("#cards"),
  toggleCards: document.querySelector("#toggleCards"),
  resultSummary: document.querySelector("#resultSummary"),
  mapCanvas: document.querySelector("#mapCanvas"),
  detailContent: document.querySelector("#detailContent"),
  routeContent: document.querySelector("#routeContent"),
  apartmentLayerToggle: document.querySelector("#apartmentLayerToggle"),
  apartmentLayerStatus: document.querySelector("#apartmentLayerStatus"),
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

function destinationAddressFor() {
  return state.apiMeta?.destinationAddresses?.[state.destination]
    || destinationAddresses[state.destination]
    || destinationLabels[state.destination]
    || "";
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
    destinationLabel: destinationLabels[state.destination],
    destinationAddress: destinationAddressFor(),
    representativeAddress: representativeAddressFor(item),
    reasonText: buildSpecificReason({ ...item, minutes })
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
    scrollWheelZoom: false
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
    markersById: {},
    fitted: false
  };

  instance.on("moveend zoomend", () => {
    if (state.apartments.enabled) {
      scheduleApartmentLayerLoad();
    }
  });
}

function drawRouteLine(bounds) {
  if (!state.map?.routeLayer) return;
  state.map.routeLayer.clearLayers();

  const route = state.route.result;
  if (!route || route.origin?.lat == null || route.destination?.lat == null) return;

  const coordinates = Array.isArray(route.coordinates) && route.coordinates.length >= 2
    ? route.coordinates
    : [route.origin, route.destination];
  const latLngs = coordinates
    .filter((point) => point?.lat != null && point?.lng != null)
    .map((point) => [Number(point.lat), Number(point.lng)]);
  if (latLngs.length < 2) return;

  const isFallback = route.mode !== "live_api";
  L.polyline(latLngs, {
    color: isFallback ? "#b4872a" : "#356c9c",
    weight: 5,
    opacity: 0.78,
    dashArray: isFallback ? "8 8" : null
  }).addTo(state.map.routeLayer);

  L.circleMarker(latLngs[0], {
    radius: 7,
    color: "#ffffff",
    weight: 2,
    fillColor: "#356c9c",
    fillOpacity: 1
  }).bindTooltip(route.origin.label || "출발지").addTo(state.map.routeLayer);

  L.circleMarker(latLngs[latLngs.length - 1], {
    radius: 7,
    color: "#ffffff",
    weight: 2,
    fillColor: "#c94d2f",
    fillOpacity: 1
  }).bindTooltip(route.destination.label || "도착지").addTo(state.map.routeLayer);

  latLngs.forEach((point) => bounds.push(point));
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

function focusSelectedMarker(pan) {
  const marker = state.map?.markersById?.[state.selectedId];
  if (!marker) return;
  if (pan) {
    state.map.instance.panTo(marker.getLatLng());
  }
  marker.openPopup();
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
    bounds.getEast().toFixed(3)
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
  return `
    <strong>${escapeHtml(feature.name)}</strong><br>
    ${escapeHtml(feature.address || `${feature.district || ""} ${feature.dong || ""}`.trim())}<br>
    ${formatNumber(feature.households)}세대 · ${formatNumber(feature.buildingCount)}개동 · ${escapeHtml(approval)}${parking}<br>
    <span class="popup-muted">${escapeHtml(feature.housingType || "공동주택")} · ${escapeHtml(feature.heating || "난방 정보 없음")}</span>
  `;
}

function clusterPopup(feature) {
  const districts = Array.isArray(feature.districts) && feature.districts.length ? feature.districts.join(", ") : "서울";
  const samples = Array.isArray(feature.sampleNames) ? feature.sampleNames.join(", ") : "";
  return `
    <strong>아파트 단지 ${formatNumber(feature.count)}개</strong><br>
    ${escapeHtml(districts)} · ${formatNumber(feature.households)}세대<br>
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
    return;
  }

  state.apartments.features.forEach((feature) => {
    if (feature.type === "cluster") {
      const marker = L.marker([feature.lat, feature.lng], {
        title: `아파트 단지 ${feature.count}개`,
        icon: L.divIcon({
          className: "apt-cluster-wrapper",
          html: `<span class="apt-cluster"><strong>${formatNumber(feature.count)}</strong></span>`,
          iconSize: [44, 44],
          iconAnchor: [22, 22],
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

    L.circleMarker([feature.lat, feature.lng], {
      radius: 4,
      color: "#ffffff",
      weight: 1.5,
      fillColor: "#6f4aa8",
      fillOpacity: 0.82
    })
      .bindPopup(apartmentPopup(feature))
      .bindTooltip(feature.name, { direction: "top", offset: [0, -4] })
      .addTo(layer);
  });
  renderApartmentLayerStatus();
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
  if (!state.neighborhoods.length) {
    nodes.mapCanvas.innerHTML = `<div class="map-empty">데이터 로딩 중</div>`;
    return;
  }

  if (!renderLeafletMap()) {
    renderFallbackMap();
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
        return `
          <li>
            <span class="route-mode">${escapeHtml(mode)}</span>
            <strong>${escapeHtml(title)}</strong>
            <span>${escapeHtml(step.startName || "출발")} → ${escapeHtml(step.endName || "도착")}</span>
            <em>${formatNumber(step.minutes || 0)}분 · ${formatDistance(step.distanceMeters || 0)}</em>
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
        <button class="text-button" type="button" data-route-map>지도에서 보기</button>
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
      <p class="score-note">주거비·생활 SOC·안전환경은 공공데이터 스냅샷 기반, 통근은 경로 API 어댑터 우선·키 없을 때 테이블 폴백입니다.</p>
    </div>
    <div class="callout">
      <p><strong>추천 근거</strong><br>${buildReason(selected)} ${selected.insight}</p>
    </div>
    ${renderRentExamples(selected)}
    ${renderSafetyEnvSummary(selected)}
    ${renderEvidence(selected)}
    <div class="callout">
      <p><strong>사업 적용</strong><br>부동산 플랫폼에는 생활권 점수 API로, 지자체에는 주거-이동 부담 리포트로 제공할 수 있다.</p>
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
    error: ""
  };
  if (state.map?.routeLayer) {
    state.map.routeLayer.clearLayers();
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
    state.route = { selectedId: selected.id, isLoading: false, result: null, error: "집 위치를 입력하세요." };
    renderRoutePanel();
    return;
  }
  if (destinationText) {
    params.set("destinationQuery", destinationText);
  } else {
    params.set("destination", state.destination);
  }

  state.route = { selectedId: selected.id, isLoading: true, result: null, error: "" };
  renderRoutePanel();

  try {
    const payload = await fetchJson(`/api/commute-route?${params.toString()}`);
    state.route = { selectedId: selected.id, isLoading: false, result: payload, error: "" };
    if (state.map) {
      state.map.fitted = false;
    }
    render();
  } catch (error) {
    state.route = {
      selectedId: selected.id,
      isLoading: false,
      result: null,
      error: `경로 계산 실패: ${error.message}`
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
    activateSection("map", { updateHash: true });
    if (state.map) {
      state.map.fitted = false;
      renderMap();
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
  renderRoutePanel();
  renderEvidenceTable();
}

function selectArea(id, options = {}) {
  if (state.selectedId !== id) {
    resetRouteState();
  }
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
      if (state.apartments.enabled) {
        scheduleApartmentLayerLoad();
      }
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
    resetRouteState();
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
    resetRouteState();
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
