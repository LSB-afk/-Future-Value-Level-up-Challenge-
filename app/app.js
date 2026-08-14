const CARD_PREVIEW_COUNT = 5;
const MATCH_RESULT_LIMIT = 10;
const SEOUL_CENTER = [37.5665, 126.9780];
const SEOUL_OVERVIEW_ZOOM = 12;
const DISTRICT_CLUSTER_MAX_ZOOM = 13;
const BOOKMARK_STORAGE_KEY = "movevalue-apartment-bookmarks";
const SIDEBAR_WIDTH_STORAGE_KEY = "movevalue-sidebar-width-v3";
const SIDEBAR_MIN_WIDTH = 360;
const SIDEBAR_MAX_WIDTH = 620;
const DEFAULT_ROUTE_TRANSPORT_MODE = "car";
const KAKAO_SOC_RADIUS_METERS = 1000;
const KAKAO_SAFETY_RADIUS_METERS = 1000;
const ROUTE_TRANSPORT_MODES = [
  { key: "car", label: "자동차", icon: "car-front" },
  { key: "transit", label: "대중교통", icon: "bus-front" },
  { key: "bicycle", label: "자전거", icon: "bike" },
  { key: "walk", label: "도보", icon: "person-standing" }
];
const SOC_CATEGORY_DEFINITIONS = {
  medical: {
    label: "의료",
    aliases: ["medical", "hospital", "clinic", "pharmacy", "emergency"],
    targetCount: 3
  },
  transport: {
    label: "교통",
    aliases: ["transport", "subway", "station", "busStop", "bus_stop", "transferCenter", "transfer_center"],
    targetCount: 4
  },
  convenience: {
    label: "생활편의",
    aliases: ["convenience", "convenienceStore", "convenience_store", "mart", "bank", "laundry"],
    targetCount: 6
  },
  education: {
    label: "교육",
    aliases: ["education", "school", "daycare", "kindergarten", "elementarySchool", "elementary_school", "academy"],
    targetCount: 4
  },
  leisure: {
    label: "문화·체육",
    aliases: ["leisure", "library", "culture", "sports", "gym"],
    targetCount: 3
  },
  welfare: {
    label: "복지시설",
    aliases: ["welfare", "communityCenter", "community_center", "welfareCenter", "welfare_center", "seniorWelfare", "senior_welfare"],
    targetCount: 3
  }
};
const SOC_PERSONA_WEIGHTS = {
  single: { medical: 15, transport: 30, convenience: 35, education: 5, leisure: 10, welfare: 5 },
  family: { medical: 15, transport: 15, convenience: 20, education: 35, leisure: 10, welfare: 5 },
  newlywed: { medical: 15, transport: 20, convenience: 20, education: 25, leisure: 15, welfare: 5 },
  senior: { medical: 35, transport: 10, convenience: 10, education: 0, leisure: 15, welfare: 30 }
};
const PERSONA_LABELS = {
  single: "1인 가구",
  family: "자녀 가구",
  newlywed: "신혼",
  senior: "노인"
};
const PERSONA_DEFAULT_WEIGHTS = {
  single: { commute: 30, cost: 35, service: 15, safety: 20 },
  newlywed: { commute: 25, cost: 30, service: 25, safety: 20 },
  family: { commute: 15, cost: 20, service: 35, safety: 30 },
  senior: { commute: 10, cost: 20, service: 35, safety: 35 }
};
const BUDGET_MODE_CONFIG = {
  monthly: { label: "월 주거 예산", shortLabel: "월세", min: 0, max: 150, step: 1, defaultValue: 0, unit: "만원", displayScale: 1, displayStep: 1 },
  jeonse: { label: "전세 예산", shortLabel: "전세", min: 0, max: 200000, step: 1000, defaultValue: 0, unit: "억", displayScale: 10000, displayStep: 0.1 },
  sale: { label: "매매 예산", shortLabel: "매매", min: 0, max: 400000, step: 1000, defaultValue: 0, unit: "억", displayScale: 10000, displayStep: 0.1 }
};

const state = {
  neighborhoods: [],
  apartmentCandidates: [],
  results: [],
  selectedId: null,
  destination: "gangnam",
  destinationQuery: "",
  destinationLocation: null,
  budget: 0,
  budgetMode: "monthly",
  persona: "single",
  apiMeta: null,
  apiOnline: false,
  isLoading: false,
  hasMatched: false,
  matchValidationMessage: "",
  lastError: "",
  lastUpdated: null,
  refreshTimer: null,
  requestId: 0,
  routeRequestId: 0,
  map: null,
  locationSearch: {
    target: "main",
    requestId: 0,
    timer: null,
    isLoading: false,
    open: false,
    items: [],
    error: ""
  },
  activeSection: "recommend",
  route: {
    selectedId: null,
    isLoading: false,
    result: null,
    error: "",
    focusMap: false,
    transportMode: DEFAULT_ROUTE_TRANSPORT_MODE
  },
  aiCommute: {
    selectedId: null,
    requestId: 0,
    isLoading: false,
    result: null,
    error: ""
  },
  apartments: {
    enabled: true,
    labelMode: "sale",
    isLoading: false,
    features: [],
    meta: null,
    error: "",
    lastKey: "",
    requestId: 0,
    timer: null
  },
  infrastructureFocus: {
    category: "",
    label: ""
  },
  liveInfrastructure: {
    selectedId: null,
    requestId: 0,
    isLoading: false,
    data: null,
    error: ""
  },
  liveSafety: {
    selectedId: null,
    requestId: 0,
    isLoading: false,
    data: null,
    error: ""
  },
  liveAir: {
    selectedId: null,
    requestId: 0,
    isLoading: false,
    data: null,
    error: ""
  },
  liveCctv: {
    selectedId: null,
    requestId: 0,
    isLoading: false,
    data: null,
    error: ""
  },
  property: {
    selectedId: null,
    isLoading: false,
    detail: null,
    error: "",
    requestId: 0,
    agentQuestion: "이 아파트 전세 들어가도 괜찮아?",
    agentAnswer: null,
    agentLoading: false,
    agentError: "",
    trendMode: ""
  },
  agent: {
    open: false,
    messages: [],
    followUps: [],
    targetId: null,
    targetName: "",
    isLoading: false,
    error: ""
  },
  bookmarks: {
    ids: [],
    details: {},
    panelOpen: false,
    isLoading: false,
    error: ""
  },
  showAllCards: false,
  evidenceRendered: false,
  detailPanelOpen: false,
  detailSubpanelTab: "matching",
  weights: {
    ...PERSONA_DEFAULT_WEIGHTS.single
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

const destinationCoordinates = {
  gangnam: { lat: 37.4979, lng: 127.0276 },
  yeouido: { lat: 37.5219, lng: 126.9245 },
  seoulStation: { lat: 37.5563, lng: 126.9723 },
  digital: { lat: 37.4853, lng: 126.9015 },
  pangyo: { lat: 37.3947, lng: 127.1112 }
};

const seoulDistrictCoordinates = {
  강남구: { lat: 37.5172, lng: 127.0473 },
  강동구: { lat: 37.5301, lng: 127.1238 },
  강북구: { lat: 37.6396, lng: 127.0257 },
  강서구: { lat: 37.5509, lng: 126.8495 },
  관악구: { lat: 37.4784, lng: 126.9516 },
  광진구: { lat: 37.5385, lng: 127.0824 },
  구로구: { lat: 37.4955, lng: 126.8874 },
  금천구: { lat: 37.4569, lng: 126.8955 },
  노원구: { lat: 37.6542, lng: 127.0568 },
  도봉구: { lat: 37.6688, lng: 127.0471 },
  동대문구: { lat: 37.5744, lng: 127.0396 },
  동작구: { lat: 37.5124, lng: 126.9393 },
  마포구: { lat: 37.5663, lng: 126.9019 },
  서대문구: { lat: 37.5791, lng: 126.9368 },
  서초구: { lat: 37.4837, lng: 127.0324 },
  성동구: { lat: 37.5633, lng: 127.0371 },
  성북구: { lat: 37.5894, lng: 127.0167 },
  송파구: { lat: 37.5145, lng: 127.1059 },
  양천구: { lat: 37.5170, lng: 126.8666 },
  영등포구: { lat: 37.5264, lng: 126.8963 },
  용산구: { lat: 37.5326, lng: 126.9905 },
  은평구: { lat: 37.6027, lng: 126.9291 },
  종로구: { lat: 37.5735, lng: 126.9790 },
  중구: { lat: 37.5641, lng: 126.9979 },
  중랑구: { lat: 37.6063, lng: 127.0927 }
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

const scoreTips = {
  commute: "목적지까지의 대중교통 통근시간을 반영한 점수",
  cost: "선택한 예산 기준 대비 단지 가격을 반영한 주거비 점수",
  service: "의료·교통·생활편의·교육·문화·체육·복지시설을 가구 유형별 비중으로 합산한 생활 SOC 점수",
  safety: "치안·환경 접근성과 단지 전세 위험 신호를 결합한 안전 점수"
};

const nodes = {
  main: document.querySelector("main"),
  budgetInput: document.querySelector("#budgetInput"),
  budgetOutput: document.querySelector("#budgetOutput"),
  budgetLabel: document.querySelector("#budgetLabel"),
  budgetUnit: document.querySelector("#budgetUnit"),
  destinationInput: document.querySelector("#destinationInput"),
  destinationClearButton: document.querySelector("#destinationClearButton"),
  destinationSuggestions: document.querySelector("#destinationSuggestions"),
  destinationValidation: document.querySelector("#destinationValidation"),
  commuteWeight: document.querySelector("#commuteWeight"),
  costWeight: document.querySelector("#costWeight"),
  serviceWeight: document.querySelector("#serviceWeight"),
  safetyWeight: document.querySelector("#safetyWeight"),
  commuteWeightOutput: document.querySelector("#commuteWeightOutput"),
  costWeightOutput: document.querySelector("#costWeightOutput"),
  serviceWeightOutput: document.querySelector("#serviceWeightOutput"),
  safetyWeightOutput: document.querySelector("#safetyWeightOutput"),
  refreshButton: document.querySelector("#refreshButton"),
  bookmarkPanelButton: document.querySelector("#bookmarkPanelButton"),
  bookmarkCount: document.querySelector("#bookmarkCount"),
  matchButton: document.querySelector("#matchButton"),
  resetButton: document.querySelector("#resetButton"),
  cards: document.querySelector("#cards"),
  toggleCards: document.querySelector("#toggleCards"),
  resultSummary: document.querySelector("#resultSummary"),
  sidebarResizeHandle: document.querySelector("#sidebarResizeHandle"),
  mapCanvas: document.querySelector("#mapCanvas"),
  detailContent: document.querySelector("#detailContent"),
  routeContent: document.querySelector("#routeContent"),
  infrastructureContent: document.querySelector("#infrastructureContent"),
  apartmentLayerToggle: document.querySelector("#apartmentLayerToggle"),
  mapLabelModeInput: document.querySelector("#mapLabelModeInput"),
  apartmentLayerStatus: document.querySelector("#apartmentLayerStatus"),
  propertyDashboard: document.querySelector("#propertyDashboard"),
  jeonseRiskContent: document.querySelector("#jeonseRiskContent"),
  bookmarkPanel: document.querySelector("#bookmarkPanel"),
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

function sidebarWidthBounds() {
  if (window.innerWidth <= 860) {
    return { min: SIDEBAR_MIN_WIDTH, max: SIDEBAR_MAX_WIDTH };
  }
  const reservedMapWidth = state.detailPanelOpen ? 420 : 560;
  const reservedSubpanelWidth = state.detailPanelOpen ? 568 : 0;
  const maxByViewport = Math.max(SIDEBAR_MIN_WIDTH, window.innerWidth - reservedMapWidth - reservedSubpanelWidth);
  return {
    min: Math.min(SIDEBAR_MIN_WIDTH, maxByViewport),
    max: Math.max(SIDEBAR_MIN_WIDTH, Math.min(SIDEBAR_MAX_WIDTH, maxByViewport))
  };
}

function setSidebarWidth(width, { persist = false } = {}) {
  const { min, max } = sidebarWidthBounds();
  const nextWidth = Math.round(clamp(Number(width) || SIDEBAR_MIN_WIDTH, min, max));
  document.documentElement.style.setProperty("--sidebar-width", `${nextWidth}px`);
  if (persist) {
    try {
      window.localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, String(nextWidth));
    } catch {
      // Resizing should still work even when localStorage is unavailable.
    }
  }
  window.requestAnimationFrame(() => {
    state.map?.instance?.invalidateSize({ pan: false });
  });
}

function invalidateMapLayout() {
  const map = state.map?.instance;
  if (!map) return;
  window.requestAnimationFrame(() => {
    map.invalidateSize({ pan: false });
    window.requestAnimationFrame(() => {
      map.invalidateSize({ pan: false });
    });
  });
}

function restoreSidebarWidth() {
  try {
    const savedWidth = Number(window.localStorage.getItem(SIDEBAR_WIDTH_STORAGE_KEY) || 0);
    if (savedWidth) setSidebarWidth(savedWidth);
  } catch {
    // Ignore storage failures.
  }
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

function budgetConfig(mode = state.budgetMode) {
  return BUDGET_MODE_CONFIG[mode] || BUDGET_MODE_CONFIG.monthly;
}

function displayBudgetValue(value = state.budget, mode = state.budgetMode) {
  const config = budgetConfig(mode);
  const displayValue = Number(value || 0) / Number(config.displayScale || 1);
  return Number.isInteger(displayValue) ? String(displayValue) : displayValue.toFixed(1);
}

function parseBudgetDisplayValue(value, mode = state.budgetMode) {
  const config = budgetConfig(mode);
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return state.budget;
  return numeric * Number(config.displayScale || 1);
}

function budgetTargetValue(item, mode = state.budgetMode) {
  if (mode === "sale") return Math.round(Number(item.sale10k || item.pricePreview?.sale10k || 0));
  if (mode === "jeonse") return Math.round(Number(item.jeonse10k || item.pricePreview?.jeonse10k || 0));
  return Math.round(Number(item.rentMonthly10k || item.monthlyRent10k || item.pricePreview?.monthlyRent10k || 0));
}

function formatBudgetValue(value, mode = state.budgetMode) {
  return mode === "monthly" ? `${formatNumber(value)}만원` : formatMoney10k(value);
}

function costScoreForBudget(targetValue, budgetValue, mode = state.budgetMode) {
  const target = Number(targetValue || 0);
  const budget = Number(budgetValue || 0);
  if (!target) return 50;
  if (!budget) return 0;
  const usageRatio = target / budget;
  if (usageRatio <= 1) {
    return clamp(100 - Math.abs(1 - usageRatio) * 72);
  }
  return clamp(100 - (usageRatio - 1) * 600);
}

function greenAccessScoreFromDistance(distanceMeters) {
  const distance = Number(distanceMeters);
  if (!Number.isFinite(distance)) return 0;
  return Math.round(clamp(100 - (distance / KAKAO_SAFETY_RADIUS_METERS) * 60, 40, 100));
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

function formatAverageSpeed(summary = {}) {
  const distanceKm = Number(summary.distanceMeters || 0) / 1000;
  const totalMinutes = Number(summary.totalMinutes || 0);
  if (!distanceKm || !totalMinutes) {
    return "정보 없음";
  }

  const averageKph = distanceKm / (totalMinutes / 60);
  return `${averageKph.toFixed(1)}km/h`;
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

function loadBookmarksFromStorage() {
  try {
    const saved = JSON.parse(window.localStorage.getItem(BOOKMARK_STORAGE_KEY) || "[]");
    state.bookmarks.ids = Array.isArray(saved)
      ? [...new Set(saved.filter((id) => typeof id === "string" && id))]
      : [];
  } catch {
    state.bookmarks.ids = [];
  }
}

function persistBookmarks() {
  try {
    window.localStorage.setItem(BOOKMARK_STORAGE_KEY, JSON.stringify(state.bookmarks.ids));
  } catch {
    // Local storage may be unavailable in privacy-restricted browser contexts.
  }
}

function isBookmarked(id) {
  return state.bookmarks.ids.includes(id);
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
      secondary: preview.livingAreaName ? escapeHtml(preview.livingAreaName) : "입지 기준"
    };
  }
  return {
    primary: preview.saleLabel ? escapeHtml(preview.saleLabel.replace(" ", "")) : "단지",
    secondary: preview.jeonseRatio ? `전세 ${formatPercent(preview.jeonseRatio)}` : "상세 보기"
  };
}

function updateMapScaleUI() {
}

function normalizeSearchText(value = "") {
  return String(value).replace(/\s+/g, "").toLowerCase();
}

function seoulDongPartsFromText(...values) {
  const compact = normalizeSearchText(values.filter(Boolean).join(" "));
  const districtMatch = compact.match(/서울(?:특별시)?([가-힣]+구)/);
  const tail = districtMatch ? compact.slice(districtMatch.index + districtMatch[0].length) : "";
  const dongMatch = districtMatch ? tail.match(/([가-힣]+동(?:\d가)?)/) : null;
  const roadMatch = districtMatch ? tail.match(/([가-힣0-9]+(?:대로|로|길)(?:\d+길)?)/) : null;
  return {
    ok: Boolean(compact.includes("서울") && districtMatch && (dongMatch || roadMatch)),
    district: districtMatch?.[1] || "",
    dong: dongMatch?.[1] || "",
    road: roadMatch?.[1] || ""
  };
}

function validateDestinationInput(value = state.destinationQuery, location = state.destinationLocation) {
  const text = String(value || "").trim();
  if (!text) {
    return { ok: false, message: "목적지를 입력해주세요." };
  }
  const parts = seoulDongPartsFromText(text, location?.address, location?.roadAddress, location?.label);
  if (!parts.ok) {
    return { ok: false, message: "서울특별시 + 구 + 동 또는 도로명까지 입력하거나 목록에서 선택해주세요." };
  }
  if (location && location.selectable === false) {
    return { ok: false, message: "구 단위가 아니라 동까지 선택해야 이동할 수 있습니다." };
  }
  return { ok: true, ...parts, message: "" };
}

function localDestinationLocationFor(value = state.destinationQuery) {
  const parts = seoulDongPartsFromText(value);
  if (!parts.ok) return null;
  const matches = state.apartmentCandidates.filter((item) => (
    normalizeSearchText(item.district) === normalizeSearchText(parts.district)
    && normalizeSearchText(item.dong) === normalizeSearchText(parts.dong)
    && item.lat != null
    && item.lng != null
  ));
  if (!matches.length) return null;
  const lat = matches.reduce((sum, item) => sum + Number(item.lat), 0) / matches.length;
  const lng = matches.reduce((sum, item) => sum + Number(item.lng), 0) / matches.length;
  const address = `서울특별시 ${parts.district} ${parts.dong}`;
  return {
    label: address,
    address,
    lat,
    lng,
    source: "local_apartment_dong",
    selectable: true
  };
}

function selectedDestinationLocation() {
  const validation = validateDestinationInput();
  if (!validation.ok) return null;
  if (state.destinationLocation?.lat != null && state.destinationLocation?.lng != null) {
    return state.destinationLocation;
  }
  return localDestinationLocationFor();
}

function destinationCoordinatesForRequest() {
  const selectedLocation = selectedDestinationLocation();
  if (selectedLocation?.lat != null && selectedLocation?.lng != null) {
    return { lat: Number(selectedLocation.lat), lng: Number(selectedLocation.lng) };
  }
  return null;
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

function currentDestinationCoordinates() {
  const selectedLocation = selectedDestinationLocation();
  if (selectedLocation?.lat != null && selectedLocation?.lng != null) {
    return { lat: Number(selectedLocation.lat), lng: Number(selectedLocation.lng) };
  }

  const query = state.destinationQuery?.trim();
  if (!query) return destinationCoordinates[state.destination] || destinationCoordinates.gangnam;

  const normalized = normalizeSearchText(query);
  const preset = destinationSearchOptions.find((option) => (
    normalizeSearchText(option.address) === normalized
    || normalizeSearchText(option.label) === normalized
    || option.keywords.some((keyword) => normalized === normalizeSearchText(keyword))
  ));
  if (preset) return destinationCoordinates[preset.key];

  const district = Object.keys(seoulDistrictCoordinates).find((name) => normalized.includes(normalizeSearchText(name)));
  return district ? seoulDistrictCoordinates[district] : destinationCoordinates[state.destination] || destinationCoordinates.gangnam;
}

function destinationDisplayLabel() {
  const query = state.destinationQuery?.trim();
  return state.destinationLocation?.label || query || destinationLabels[state.destination] || "목적지";
}

function destinationAddressFor() {
  const query = state.destinationQuery?.trim();
  return state.destinationLocation?.address
    || query
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
    || item?.address
    || areaAddressDefaults[item?.id]
    || `${item?.district || ""} ${item?.station || item?.name || ""}`.trim();
}

function selectedMatchResult() {
  return state.results.find((item) => item.id === state.selectedId) || null;
}

function selectedDetailItem() {
  const result = selectedMatchResult();
  if (result) return result;
  if (state.property.detail?.id === state.selectedId) return state.property.detail;
  return state.apartmentCandidates.find((item) => item.id === state.selectedId)
    || state.apartments.features.find((item) => item.id === state.selectedId)
    || null;
}

function selectedInfrastructureItem() {
  const selected = selectedDetailItem();
  if (!selected) return null;
  if (selected.socSummary || selected.safetyEnvSummary) return selected;
  if (selected.lat != null && selected.lng != null && state.neighborhoods.length) {
    return scoreApartmentCandidate(selected);
  }
  return selected;
}

async function fetchJson(path) {
  const response = await fetch(path, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return response.json();
}

function locationSearchNodes(target = "main") {
  if (target === "route") {
    return {
      input: document.querySelector("#routeDestinationInput"),
      list: document.querySelector("#routeDestinationSuggestions"),
      validation: document.querySelector("#routeDestinationValidation")
    };
  }
  return {
    input: nodes.destinationInput,
    list: nodes.destinationSuggestions,
    validation: nodes.destinationValidation
  };
}

function locationSuggestionInputValue(item = {}) {
  return item.address || item.label || "";
}

function isLocalScopeSuggestion(item = {}) {
  return ["city", "district", "dong", "apartment"].includes(item.type);
}

function locationSuggestionLabelHtml(item = {}) {
  const label = item.label || item.address || "위치";
  if (item.type === "city") {
    return `<span class="location-suggestion-accent">${escapeHtml(label)}</span>`;
  }
  if (item.type === "district") {
    const district = item.district || label.replace(/^서울(?:특별시|시)?\s*/, "");
    return `<span class="location-suggestion-accent">서울시</span> ${escapeHtml(district)}`;
  }
  if (item.type === "dong") {
    return `<span class="location-suggestion-accent">${escapeHtml(item.district || "")}</span> ${escapeHtml(item.dong || label)}`.trim();
  }
  if (item.type === "apartment") {
    const prefix = item.dong ? `${item.dong} ` : "";
    const name = item.apartmentName || (prefix && label.startsWith(prefix) ? label.slice(prefix.length) : label);
    return `<span class="location-suggestion-accent">${escapeHtml(item.dong || "")}</span> ${escapeHtml(name)}`.trim();
  }
  return escapeHtml(label);
}

function locationSuggestionSubtitle(item = {}) {
  if (isLocalScopeSuggestion(item)) return "";
  if (item.type === "dong") return "";
  if (item.type === "district") return item.hint || "동까지 선택 필요";
  if (item.label && item.address && item.label !== item.address) return item.address;
  return item.roadAddress || item.hint || "";
}

function isResidentialDestinationSuggestion(item = {}) {
  if (item.type === "apartment") return true;
  const text = normalizeSearchText([
    item.label,
    item.address,
    item.roadAddress,
    item.category,
    item.apartmentName
  ].filter(Boolean).join(" "));
  const residentialTokens = ["아파트", "주거시설", "공동주택", "연립", "다세대", "빌라"];
  return residentialTokens.some((token) => text.includes(normalizeSearchText(token)));
}

function renderDestinationValidation(target = "main") {
  const { validation } = locationSearchNodes(target);
  if (!validation) return;
  const result = validateDestinationInput();
  validation.textContent = state.destinationQuery.trim() ? result.message : "";
  validation.classList.toggle("is-error", Boolean(state.destinationQuery.trim() && !result.ok));
}

function renderLocationSuggestions(target = state.locationSearch.target) {
  const { list, input } = locationSearchNodes(target);
  if (!list || !input) return;
  const isActiveTarget = state.locationSearch.target === target;
  const shouldShow = isActiveTarget
    && state.locationSearch.open
    && Boolean(input.value.trim())
    && (state.locationSearch.isLoading || state.locationSearch.items.length || state.locationSearch.error);

  list.hidden = !shouldShow;
  if (!shouldShow) {
    input.setAttribute("aria-expanded", "false");
    renderDestinationValidation(target);
    return;
  }

  input.setAttribute("aria-expanded", "true");
  if (state.locationSearch.isLoading) {
    list.innerHTML = `<div class="location-suggestion-status">검색 중</div>`;
    renderDestinationValidation(target);
    return;
  }
  if (state.locationSearch.error) {
    list.innerHTML = `<div class="location-suggestion-status is-error">${escapeHtml(state.locationSearch.error)}</div>`;
    renderDestinationValidation(target);
    return;
  }

  list.innerHTML = state.locationSearch.items.map((item, index) => {
    const subtitle = locationSuggestionSubtitle(item);
    const selectable = item.selectable !== false;
    const hasPin = !isLocalScopeSuggestion(item);
    const classes = [
      "location-suggestion",
      selectable ? "" : "is-incomplete",
      hasPin ? "has-pin" : "is-text-only",
      isLocalScopeSuggestion(item) ? "is-scope" : ""
    ].filter(Boolean).join(" ");
    return `
      <button
        class="${classes}"
        type="button"
        role="option"
        data-location-index="${index}"
        aria-disabled="${selectable ? "false" : "true"}"
      >
        ${hasPin ? `<span class="location-suggestion-pin" aria-hidden="true"></span>` : ""}
        <span>
          <strong>${locationSuggestionLabelHtml(item)}</strong>
          ${subtitle ? `<small>${escapeHtml(subtitle)}</small>` : ""}
        </span>
      </button>
    `;
  }).join("");
  renderDestinationValidation(target);
}

function hideLocationSuggestions() {
  state.locationSearch.open = false;
  renderLocationSuggestions("main");
  renderLocationSuggestions("route");
}

function setDestinationFromSuggestion(item = {}, target = "main") {
  const value = locationSuggestionInputValue(item);
  state.destinationQuery = value;
  state.destinationLocation = {
    label: item.label || value,
    address: item.address || value,
    roadAddress: item.roadAddress || "",
    lat: item.lat,
    lng: item.lng,
    source: item.source || "location_suggestion",
    selectable: item.selectable !== false
  };
  if (value.trim()) {
    state.destination = inferDestinationKey(value);
  }
  state.apartments.lastKey = "";
  state.locationSearch.open = false;
  state.locationSearch.items = [];
  resetRouteState();

  const { input } = locationSearchNodes(target);
  if (input) input.value = value;
  if (nodes.destinationInput) nodes.destinationInput.value = value;

  if (target === "route") {
    renderControls();
    renderRoutePanel();
  } else {
    scheduleRefresh(0);
  }
}

function drillDownLocationSuggestion(item = {}, target = "main") {
  const value = locationSuggestionInputValue(item);
  state.destinationQuery = value;
  state.destinationLocation = null;
  state.matchValidationMessage = "";
  state.locationSearch.open = Boolean(value.trim());
  state.locationSearch.items = [];
  resetRouteState();

  const { input } = locationSearchNodes(target);
  if (input) input.value = value;
  if (nodes.destinationInput) nodes.destinationInput.value = value;

  requestLocationSuggestions(value, target);
  if (target === "route") {
    renderControls();
    renderRoutePanel();
  } else {
    renderControls();
  }
}

function clearDestinationInput() {
  window.clearTimeout(state.locationSearch.timer);
  state.destinationQuery = "";
  state.destinationLocation = null;
  state.locationSearch.open = false;
  state.locationSearch.isLoading = false;
  state.locationSearch.items = [];
  state.locationSearch.error = "";
  state.matchValidationMessage = "";
  if (nodes.destinationInput) nodes.destinationInput.value = "";
  if (nodes.destinationClearButton) nodes.destinationClearButton.hidden = true;
  resetRouteState();
  scheduleRefresh(0);
  window.setTimeout(() => nodes.destinationInput?.focus(), 0);
}

function fallbackLocationSuggestions(query = "", limit = 8) {
  const compactQuery = normalizeSearchText(query).replace("서울특별시", "서울");
  if (!compactQuery) return [];

  const groups = new Map();
  state.apartmentCandidates.forEach((item) => {
    if (!item.district || !item.dong || item.lat == null || item.lng == null) return;
    const key = `${item.district}|${item.dong}`;
    const group = groups.get(key) || { district: item.district, dong: item.dong, lat: 0, lng: 0, count: 0 };
    group.lat += Number(item.lat);
    group.lng += Number(item.lng);
    group.count += 1;
    groups.set(key, group);
  });

  return [...groups.values()]
    .map((group) => {
      const label = `서울특별시 ${group.district} ${group.dong}`;
      return {
        type: "dong",
        label,
        address: label,
        lat: group.lat / group.count,
        lng: group.lng / group.count,
        district: group.district,
        dong: group.dong,
        source: "local_apartment_dong",
        selectable: true,
        hint: "서울 구·동 기준 위치"
      };
    })
    .filter((item) => {
      const blob = `${item.label} ${item.label.replace("서울특별시", "서울")}`;
      return normalizeSearchText(blob).includes(compactQuery);
    })
    .slice(0, limit);
}

function requestLocationSuggestions(query, target = "main") {
  window.clearTimeout(state.locationSearch.timer);
  const value = String(query || "").trim();
  state.locationSearch.target = target;
  state.locationSearch.open = Boolean(value);
  state.locationSearch.error = "";
  state.locationSearch.items = value ? state.locationSearch.items : [];
  if (!value) {
    state.locationSearch.isLoading = false;
    state.locationSearch.items = [];
    renderLocationSuggestions(target);
    return;
  }

  const requestId = ++state.locationSearch.requestId;
  state.locationSearch.isLoading = true;
  renderLocationSuggestions(target);
  state.locationSearch.timer = window.setTimeout(async () => {
    try {
      const payload = await fetchJson(`/api/location-suggestions?query=${encodeURIComponent(value)}&limit=30`);
      if (requestId !== state.locationSearch.requestId) return;
      state.locationSearch.items = Array.isArray(payload.suggestions)
        ? payload.suggestions.filter((item) => !isResidentialDestinationSuggestion(item))
        : [];
      state.locationSearch.error = "";
    } catch (error) {
      if (requestId !== state.locationSearch.requestId) return;
      state.locationSearch.items = fallbackLocationSuggestions(value);
      state.locationSearch.error = state.locationSearch.items.length ? "" : `위치 검색 실패: ${error.message}`;
    } finally {
      if (requestId === state.locationSearch.requestId) {
        state.locationSearch.isLoading = false;
        renderLocationSuggestions(target);
      }
    }
  }, 180);
}

function bindLocationSuggestionList(target = "main") {
  const { list } = locationSearchNodes(target);
  if (!list) return;
  list.addEventListener("mousedown", (event) => {
    event.preventDefault();
  });
  list.addEventListener("click", (event) => {
    const button = event.target.closest("[data-location-index]");
    if (!button) return;
    const item = state.locationSearch.items[Number(button.dataset.locationIndex)];
    if (!item) return;
    if (item.drilldown) {
      drillDownLocationSuggestion(item, target);
      return;
    }
    setDestinationFromSuggestion(item, target);
  });
}

function applyDataset(dataset) {
  if (!dataset || !Array.isArray(dataset.areas)) {
    throw new Error("생활권 데이터 형식이 올바르지 않습니다.");
  }
  state.neighborhoods = dataset.areas;
  state.apiMeta = dataset.meta || null;
}

function applyApartmentDataset(dataset) {
  const candidates = Array.isArray(dataset?.apartments)
    ? dataset.apartments
    : Array.isArray(dataset?.features)
      ? dataset.features.filter((item) => item.type !== "cluster")
      : [];
  if (!candidates.length) {
    throw new Error("아파트 후보 데이터 형식이 올바르지 않습니다.");
  }
  state.apartmentCandidates = candidates;
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

async function loadApartmentCandidates() {
  try {
    const dataset = state.apiOnline
      ? await fetchJson("/api/apartments?cluster=false&limit=10000")
      : await fetchJson("../data/apartments.seoul.snapshot.json");
    applyApartmentDataset(dataset);
  } catch (apiError) {
    const dataset = await fetchJson("../data/apartments.seoul.snapshot.json");
    applyApartmentDataset(dataset);
    state.lastError = `아파트 API 비연결: ${apiError.message}`;
  }
}

function buildRecommendationQuery() {
  const destinationLocation = selectedDestinationLocation();
  const params = new URLSearchParams({
    budget: state.budget,
    budgetMode: state.budgetMode,
    destination: state.destination,
    destinationQuery: state.destinationQuery.trim(),
    destinationAddress: destinationLocation?.address || state.destinationQuery.trim(),
    persona: state.persona,
    commuteWeight: state.weights.commute,
    costWeight: state.weights.cost,
    serviceWeight: state.weights.service,
    safetyWeight: state.weights.safety,
    limit: MATCH_RESULT_LIMIT
  });
  const destination = destinationCoordinatesForRequest();
  if (destination) {
    params.set("destinationLat", destination.lat);
    params.set("destinationLng", destination.lng);
  }
  return params;
}

function haversineKm(aLat, aLng, bLat, bLng) {
  const radius = 6371.0088;
  const toRadians = (value) => Number(value) * Math.PI / 180;
  const phi1 = toRadians(aLat);
  const phi2 = toRadians(bLat);
  const deltaPhi = toRadians(Number(bLat) - Number(aLat));
  const deltaLambda = toRadians(Number(bLng) - Number(aLng));
  const h = Math.sin(deltaPhi / 2) ** 2
    + Math.cos(phi1) * Math.cos(phi2) * Math.sin(deltaLambda / 2) ** 2;
  return radius * 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
}

function stableFactor(seed, minimum, maximum) {
  let hash = 2166136261;
  for (const character of String(seed || "apartment")) {
    hash ^= character.charCodeAt(0);
    hash = Math.imul(hash, 16777619);
  }
  const ratio = (hash >>> 0) / 4294967295;
  return minimum + (maximum - minimum) * ratio;
}

function nearestNeighborhoodForApartment(apartment) {
  const district = String(apartment.district || "").replace(/^서울(?:특별시)?\s*/, "");
  const sameDistrict = state.neighborhoods.filter((item) => (
    district && String(item.district || "").includes(district)
  ));
  const candidates = sameDistrict.length ? sameDistrict : state.neighborhoods;
  return candidates.reduce((nearest, item) => {
    const distance = haversineKm(apartment.lat, apartment.lng, item.lat, item.lng);
    return !nearest || distance < nearest.distance ? { item, distance } : nearest;
  }, null)?.item || {};
}

function numericFrom(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function socCountFromAliases(sources, aliases) {
  for (const source of sources) {
    if (!source || typeof source !== "object") continue;
    let count = 0;
    let hasValue = false;
    aliases.forEach((alias) => {
      if (Object.prototype.hasOwnProperty.call(source, alias)) {
        count += numericFrom(source[alias]);
        hasValue = true;
      }
    });
    if (hasValue) return { count, hasValue };
  }
  return { count: 0, hasValue: false };
}

function scoreFromFacilityCount(count, targetCount) {
  return clamp(45 + Math.min(Math.max(count, 0) / Math.max(targetCount, 1), 1) * 55);
}

function socCategoryScoresFor(area) {
  const baseScore = clamp(numericFrom(area.serviceScore ?? area.socScore, 70));
  const soc = area.socSummary || {};
  const evidence = area.evidence || {};
  const counts = soc.counts || {};
  const categoryCounts = soc.categoryCounts || soc.countsByCategory || evidence.socCategoryCounts || {};
  const categoryScores = soc.categoryScores || area.socCategoryScores || evidence.socCategoryScores || {};

  return Object.fromEntries(Object.entries(SOC_CATEGORY_DEFINITIONS).map(([key, definition]) => {
    const explicitScore = categoryScores[key];
    if (explicitScore != null && explicitScore !== "") {
      return [key, Math.round(clamp(numericFrom(explicitScore, baseScore)))];
    }
    if (key === "transport") {
      return [key, Math.round(clamp(numericFrom(area.transitScore, baseScore)))];
    }
    const { count, hasValue } = socCountFromAliases([categoryCounts, counts, evidence.socCounts], definition.aliases);
    return [
      key,
      Math.round(hasValue ? scoreFromFacilityCount(count, definition.targetCount) : baseScore)
    ];
  }));
}

function personaSocWeights(persona = state.persona) {
  return SOC_PERSONA_WEIGHTS[persona] || SOC_PERSONA_WEIGHTS.single;
}

function computePersonaSocScore(area, persona = state.persona) {
  const categoryScores = socCategoryScoresFor(area);
  const weights = personaSocWeights(persona);
  const totalWeight = Object.values(weights).reduce((sum, value) => sum + Number(value), 0) || 100;
  const weighted = Object.entries(weights).reduce((sum, [key, weight]) => {
    return sum + numericFrom(categoryScores[key], 70) * Number(weight);
  }, 0);
  return {
    score: Math.round(clamp(weighted / totalWeight)),
    categoryScores,
    weights
  };
}

function socSummaryTextFor(area, persona = state.persona, limit = 3) {
  const scoring = {
    categoryScores: area.socCategoryScores || computePersonaSocScore(area, persona).categoryScores,
    weights: area.socPersonaWeights || personaSocWeights(persona)
  };
  return Object.keys(SOC_CATEGORY_DEFINITIONS)
    .filter((key) => Number(scoring.weights[key]) > 0)
    .sort((a, b) => Number(scoring.weights[b]) - Number(scoring.weights[a]))
    .slice(0, limit)
    .map((key) => `${SOC_CATEGORY_DEFINITIONS[key].label} ${formatNumber(scoring.categoryScores[key])}점`)
    .join(" · ");
}

function scoreApartmentCandidate(apartment) {
  const area = nearestNeighborhoodForApartment(apartment);
  const pricePreview = apartment.pricePreview || {};
  const marketFactor = stableFactor(`${apartment.id}:market`, 0.92, 1.16);
  const monthlyRent = Math.round(Number(area.rentMonthly10k || 65) * marketFactor);
  const deposit = Math.round(Number(area.deposit10k || 1000) * stableFactor(`${apartment.id}:deposit`, 0.85, 1.3));
  const jeonse = Number(pricePreview.jeonse10k) || Math.round(Number(area.jeonse10k || 26000) * marketFactor);
  const sale = Number(pricePreview.sale10k) || Math.round(jeonse / stableFactor(`${apartment.id}:ratio`, 0.55, 0.72));
  const budgetTarget = budgetTargetValue({ rentMonthly10k: monthlyRent, jeonse10k: jeonse, sale10k: sale }, state.budgetMode);
  const destination = currentDestinationCoordinates();
  const areaMinutes = Number(area.commuteMinutes?.[state.destination] || 60);
  const apartmentDistance = haversineKm(apartment.lat, apartment.lng, destination.lat, destination.lng);
  const areaDistance = haversineKm(area.lat, area.lng, destination.lat, destination.lng);
  const minutes = Math.round(clamp(areaMinutes + (apartmentDistance - areaDistance) * 2.2, 10, 120));
  const commuteScore = clamp(105 - minutes * 1.18);
  const costScore = costScoreForBudget(budgetTarget, state.budget, state.budgetMode);
  const neighborhoodSafety = Number(area.safetyScore || 70) * 0.58 + Number(area.carbonScore || 70) * 0.42;
  const propertySafety = 100 - Number(pricePreview.riskScore || 0);
  const socScoring = computePersonaSocScore(area, state.persona);
  const adjusted = {
    commute: clamp(commuteScore),
    cost: clamp(costScore),
    service: socScoring.score,
    safety: clamp(neighborhoodSafety * 0.85 + propertySafety * 0.15)
  };
  const totalWeight = Object.values(state.weights).reduce((sum, value) => sum + Number(value), 0) || 100;
  const weighted = Object.keys(state.weights).reduce((sum, key) => sum + adjusted[key] * state.weights[key], 0);
  const dataConfidence = (Number(area.dataReadiness || 80) - 80) * 0.12;
  const result = {
    ...apartment,
    propertyType: "apartment",
    total: Math.round(clamp(weighted / totalWeight + dataConfidence)),
    minutes,
    adjusted: Object.fromEntries(Object.entries(adjusted).map(([key, value]) => [key, Math.round(value)])),
    destination: state.destination,
    destinationLabel: destinationDisplayLabel(),
    destinationAddress: destinationAddressFor(),
    representativeAddress: apartment.address,
    rentMonthly10k: monthlyRent,
    deposit10k: deposit,
    jeonse10k: Math.round(jeonse),
    sale10k: Math.round(sale),
    pricePreview,
    transitScore: area.transitScore,
    serviceScore: socScoring.score,
    baseServiceScore: area.serviceScore,
    socCategoryScores: socScoring.categoryScores,
    socPersonaWeights: socScoring.weights,
    safetyScore: area.safetyScore,
    carbonScore: area.carbonScore,
    dataReadiness: area.dataReadiness,
    socSummary: area.socSummary,
    safetyEnvSummary: area.safetyEnvSummary,
    evidence: area.evidence,
    livingArea: { id: area.id, name: area.name, station: area.station, district: area.district }
  };
  return { ...result, reasonText: buildSpecificReason(result) };
}

function scoreNeighborhood(item) {
  const minutes = Number(item.commuteMinutes?.[state.destination] || 60);
  const commuteScore = clamp(105 - minutes * 1.18);
  const costScore = costScoreForBudget(budgetTargetValue(item, state.budgetMode), state.budget, state.budgetMode);
  const safetyEnvScore = Math.round(Number(item.safetyScore) * 0.58 + Number(item.carbonScore) * 0.42);
  const socScoring = computePersonaSocScore(item, state.persona);
  const adjusted = {
    commute: clamp(commuteScore),
    cost: clamp(costScore),
    service: socScoring.score,
    safety: clamp(safetyEnvScore)
  };

  const totalWeight = Object.values(state.weights).reduce((sum, value) => sum + Number(value), 0) || 100;
  const weighted =
    adjusted.commute * state.weights.commute +
    adjusted.cost * state.weights.cost +
    adjusted.service * state.weights.service +
    adjusted.safety * state.weights.safety;

  const dataConfidence = (Number(item.dataReadiness || 80) - 80) * 0.12;
  const total = clamp(weighted / totalWeight + dataConfidence);

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
    serviceScore: socScoring.score,
    baseServiceScore: item.serviceScore,
    socCategoryScores: socScoring.categoryScores,
    socPersonaWeights: socScoring.weights,
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
  return state.apartmentCandidates
    .map(scoreApartmentCandidate)
    .sort((a, b) => b.total - a.total || budgetTargetValue(a) - budgetTargetValue(b) || a.name.localeCompare(b.name))
    .slice(0, MATCH_RESULT_LIMIT);
}

async function refreshRecommendations() {
  const requestId = ++state.requestId;
  cancelApartmentLayerWork();
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
      const payload = await fetchJson(`/api/apartment-recommendations?${buildRecommendationQuery().toString()}`);
      if (requestId !== state.requestId) return;
      state.apiMeta = payload.meta || state.apiMeta;
      if (payload.meta?.destinationLocation?.lat != null && payload.meta?.destinationLocation?.lng != null) {
        state.destinationLocation = {
          label: payload.meta.destinationLabel || state.destinationQuery.trim() || payload.meta.destinationLocation.label || "목적지",
          address: payload.meta.destinationAddress || payload.meta.destinationLocation.address || state.destinationQuery.trim(),
          roadAddress: payload.meta.destinationLocation.roadAddress || "",
          lat: payload.meta.destinationLocation.lat,
          lng: payload.meta.destinationLocation.lng,
          source: payload.meta.destinationLocation.source || "recommendation_destination",
          selectable: true
        };
      }
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
  state.matchValidationMessage = "";
  state.results = [];
  state.selectedId = null;
  state.showAllCards = false;
  state.detailPanelOpen = false;
  state.detailSubpanelTab = "matching";
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
  if (text.includes("자동차") || text.includes("car") || text.includes("drive")) return "car";
  if (text.includes("자전거") || text.includes("bicycle") || text.includes("bike") || text.includes("cycle")) return "bicycle";
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
  if (key === "car") return "#2563EB";
  if (key === "bicycle") return "#F59E0B";
  if (key === "subway") return subwayRouteColor(step.route);
  if (key === "bus") return "#386DE8";
  if (key === "walk") return "#64748B";
  if (key === "rail") return "#6D5DFC";
  return "#03C75A";
}

function routeModeIcon(mode = "") {
  const key = routeModeKey(mode);
  if (key === "car") return "C";
  if (key === "bicycle") return "BI";
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

function shouldRenderRouteStepMarkers(route = {}) {
  return (route.transportMode || DEFAULT_ROUTE_TRANSPORT_MODE) === "transit";
}

function shouldMergeRouteSegments(route = {}) {
  return ["car", "bicycle", "walk"].includes(route.transportMode || "");
}

function isSameRoutePoint(a, b) {
  return Boolean(a && b && Math.abs(a.lat - b.lat) < 0.000001 && Math.abs(a.lng - b.lng) < 0.000001);
}

function appendRoutePoint(points, point) {
  if (!point || isSameRoutePoint(points.at(-1), point)) return;
  points.push(point);
}

function mergeRouteSegments(route, segments) {
  const mergedPoints = [];
  const globalPoints = validRoutePoints(route.coordinates);
  const sourcePoints = globalPoints.length >= 2
    ? globalPoints
    : segments.flatMap((segment) => segment.points || []);

  sourcePoints.forEach((point) => appendRoutePoint(mergedPoints, point));
  if (mergedPoints.length < 2) return segments;

  return [{
    step: {
      mode: route.transportMode || "route",
      route: routeModeLabel(route)
    },
    points: mergedPoints,
    actual: segments.some((segment) => segment.actual)
  }];
}

function clusterMarkerSize(count, { min = 36, max = 96 } = {}) {
  const numericCount = Math.max(1, Number(count) || 1);
  const ratio = Math.log10(numericCount) / Math.log10(160);
  return Math.round(clamp(min + ratio * (max - min), min, max));
}

function initializeLeafletMap() {
  if (state.map || !window.L) return;

  nodes.mapCanvas.innerHTML = "";
  nodes.mapCanvas.classList.remove("synthetic-map");

  const instance = L.map(nodes.mapCanvas, {
    zoomControl: true,
    scrollWheelZoom: true
  }).setView(SEOUL_CENTER, SEOUL_OVERVIEW_ZOOM);

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
  }).addTo(instance);

  const markerLayer = typeof L.markerClusterGroup === "function"
    ? L.markerClusterGroup({
        maxClusterRadius: (zoom) => (zoom >= 16 ? 34 : 52),
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        spiderfyOnMaxZoom: true,
        spiderfyDistanceMultiplier: 1.25,
        iconCreateFunction(cluster) {
          const count = cluster.getChildCount();
          const size = clusterMarkerSize(count, { min: 36, max: 88 });
          return L.divIcon({
            className: "mv-cluster-icon-wrapper",
            html: `<span class="mv-cluster-icon" style="--cluster-size:${size}px"><strong>${formatNumber(count)}</strong></span>`,
            iconSize: [size, size],
            iconAnchor: [size / 2, size / 2]
          });
        }
      })
    : L.layerGroup();
  markerLayer.addTo(instance);

  const apartmentLayer = typeof L.markerClusterGroup === "function"
    ? L.markerClusterGroup({
        maxClusterRadius: (zoom) => (zoom >= 16 ? 48 : zoom >= 14 ? 66 : 82),
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        spiderfyOnMaxZoom: true,
        spiderfyDistanceMultiplier: 1.3,
        iconCreateFunction(cluster) {
          const count = cluster.getChildCount();
          const size = clusterMarkerSize(count, { min: 36, max: 96 });
          return L.divIcon({
            className: "apt-cluster-wrapper",
            html: `<span class="apt-cluster" style="--cluster-size:${size}px"><strong>${formatNumber(count)}</strong></span>`,
            iconSize: [size, size],
            iconAnchor: [size / 2, size / 2]
          });
        }
      })
    : L.layerGroup();
  apartmentLayer.addTo(instance);

  state.map = {
    instance,
    markerLayer,
    apartmentLayer,
    districtLayer: L.layerGroup().addTo(instance),
    routeLayer: L.layerGroup().addTo(instance),
    destinationLayer: L.layerGroup().addTo(instance),
    infrastructureLayer: L.layerGroup().addTo(instance),
    markersById: {},
    propertyMarkersById: {},
    fitted: false,
    cameraRequestId: 0
  };

  instance.on("moveend zoomend", () => {
    updateMapScaleUI();
    if (state.apartments.enabled && !state.hasMatched) {
      scheduleApartmentLayerLoad();
    }
  });
  updateMapScaleUI();
}

function drawRouteLine(bounds) {
  if (!state.map?.routeLayer) return;
  state.map.routeLayer.clearLayers();

  if (!state.detailPanelOpen || state.detailSubpanelTab !== "route") return;

  const route = state.route.result;
  if (!route || route.origin?.lat == null || route.destination?.lat == null) return;

  let segments = buildRouteSegments(route);
  if (shouldMergeRouteSegments(route)) {
    segments = mergeRouteSegments(route, segments);
  }
  const showStepMarkers = shouldRenderRouteStepMarkers(route);
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
    if (showStepMarkers && index > 0 && start) {
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

  L.marker(allLatLngs[allLatLngs.length - 1], {
    title: route.destination.label || "도착지",
    icon: L.divIcon({
      className: "route-destination-pin-wrapper",
      html: `
        <span class="route-destination-pin" aria-hidden="true">
          <svg viewBox="0 0 24 30" role="img" focusable="false">
            <path d="M12 29C12 29 22 18.8 22 10.8C22 4.8 17.5 1 12 1C6.5 1 2 4.8 2 10.8C2 18.8 12 29 12 29Z" fill="#2563EB" stroke="#ffffff" stroke-width="2"/>
            <circle cx="12" cy="10.8" r="3.4" fill="#ffffff"/>
          </svg>
        </span>
      `,
      iconSize: [32, 40],
      iconAnchor: [16, 38],
      popupAnchor: [0, -34]
    })
  }).bindTooltip(route.destination.label || "도착지", { direction: "top" }).addTo(state.map.routeLayer);

  allLatLngs.forEach((point) => bounds.push(point));
  if (state.route.focusMap && state.map.instance) {
    state.route.focusMap = false;
    state.map.fitted = true;
    focusRouteOnMap();
  }
}

function destinationPinIcon() {
  return L.divIcon({
    className: "route-destination-pin-wrapper",
    html: `
      <span class="route-destination-pin" aria-hidden="true">
        <svg viewBox="0 0 24 30" role="img" focusable="false">
          <path d="M12 29C12 29 22 18.8 22 10.8C22 4.8 17.5 1 12 1C6.5 1 2 4.8 2 10.8C2 18.8 12 29 12 29Z" fill="#2563EB" stroke="#ffffff" stroke-width="2"/>
          <circle cx="12" cy="10.8" r="3.4" fill="#ffffff"/>
        </svg>
      </span>
    `,
    iconSize: [32, 40],
    iconAnchor: [16, 38],
    popupAnchor: [0, -34]
  });
}

const INFRASTRUCTURE_CATEGORY_META = {
  medical: { label: "의료", className: "medical", source: "soc" },
  transport: { label: "교통", className: "transport", source: "soc" },
  convenience: { label: "생활편의", className: "convenience", source: "soc" },
  education: { label: "교육", className: "school", source: "soc" },
  leisure: { label: "문화·체육", className: "leisure", source: "soc" },
  welfare: { label: "복지시설", className: "welfare", source: "soc" },
  hospital: { label: "병원", className: "medical", source: "soc" },
  school: { label: "학교", className: "school", source: "soc" },
  park: { label: "공원", className: "park", source: "soc" },
  police: { label: "치안시설", className: "police", source: "safety" },
  cctv: { label: "CCTV", className: "cctv", source: "safety" },
  air: { label: "대기환경", className: "air", source: "safety" },
  green: { label: "녹지 접근", className: "park", source: "safety" }
};

function offsetLatLng(lat, lng, distanceMeters = 400, bearingDeg = 0) {
  const radius = 6371008.8;
  const angularDistance = Number(distanceMeters || 0) / radius;
  const bearing = bearingDeg * Math.PI / 180;
  const lat1 = Number(lat) * Math.PI / 180;
  const lng1 = Number(lng) * Math.PI / 180;
  const lat2 = Math.asin(
    Math.sin(lat1) * Math.cos(angularDistance)
    + Math.cos(lat1) * Math.sin(angularDistance) * Math.cos(bearing)
  );
  const lng2 = lng1 + Math.atan2(
    Math.sin(bearing) * Math.sin(angularDistance) * Math.cos(lat1),
    Math.cos(angularDistance) - Math.sin(lat1) * Math.sin(lat2)
  );
  return [lat2 * 180 / Math.PI, lng2 * 180 / Math.PI];
}

function liveInfrastructureStateFor(selected) {
  if (!selected?.id || state.liveInfrastructure.selectedId !== selected.id) return null;
  return state.liveInfrastructure;
}

function liveInfrastructureDataFor(selected) {
  const liveState = liveInfrastructureStateFor(selected);
  const data = liveState?.data;
  if (!data || !["live_api", "partial_error"].includes(data.mode)) return null;
  return data;
}

function liveSocCategoryDisplayData(selected, category) {
  const live = liveInfrastructureDataFor(selected);
  const data = live?.categories?.[category];
  if (!data) return null;
  return {
    count: Number(data.count || 0),
    hasValue: true,
    nearest: data.nearest || null,
    samples: Array.isArray(data.samples) ? data.samples : []
  };
}

function ensureLiveInfrastructure(selected) {
  if (!selected?.id) return;
  const lat = Number(selected.lat);
  const lng = Number(selected.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;

  const liveState = liveInfrastructureStateFor(selected);
  if (liveState?.isLoading || liveState?.data || liveState?.error) return;

  const requestId = state.liveInfrastructure.requestId + 1;
  state.liveInfrastructure = {
    selectedId: selected.id,
    requestId,
    isLoading: true,
    data: null,
    error: ""
  };

  const params = new URLSearchParams({
    id: selected.id,
    lat: String(lat),
    lng: String(lng),
    radius: String(KAKAO_SOC_RADIUS_METERS)
  });

  fetchJson(`/api/kakao-soc?${params.toString()}`)
    .then((payload) => {
      if (state.liveInfrastructure.requestId !== requestId) return;
      state.liveInfrastructure = {
        selectedId: selected.id,
        requestId,
        isLoading: false,
        data: payload,
        error: payload?.ok ? "" : (payload?.error || "생활 SOC 정보를 불러오지 못했습니다.")
      };
      renderInfrastructurePanel();
      renderMap();
    })
    .catch((error) => {
      if (state.liveInfrastructure.requestId !== requestId) return;
      state.liveInfrastructure = {
        selectedId: selected.id,
        requestId,
        isLoading: false,
        data: null,
        error: error.message || "생활 SOC 정보를 불러오지 못했습니다."
      };
      renderInfrastructurePanel();
    });
}

function liveSafetyStateFor(selected) {
  if (!selected?.id || state.liveSafety.selectedId !== selected.id) return null;
  return state.liveSafety;
}

function liveSafetyDataFor(selected) {
  const liveState = liveSafetyStateFor(selected);
  const data = liveState?.data;
  if (!data || !["live_api", "partial_error"].includes(data.mode)) return null;
  return data;
}

function liveSafetyCategoryDisplayData(selected, category) {
  const live = liveSafetyDataFor(selected);
  const data = live?.categories?.[category];
  if (!data) return null;
  return {
    count: Number(data.count || 0),
    hasValue: true,
    nearest: data.nearest || null,
    samples: Array.isArray(data.samples) ? data.samples : []
  };
}

function ensureLiveSafety(selected) {
  if (!selected?.id) return;
  const lat = Number(selected.lat);
  const lng = Number(selected.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;

  const liveState = liveSafetyStateFor(selected);
  if (liveState?.isLoading || liveState?.data || liveState?.error) return;

  const requestId = state.liveSafety.requestId + 1;
  state.liveSafety = {
    selectedId: selected.id,
    requestId,
    isLoading: true,
    data: null,
    error: ""
  };

  const params = new URLSearchParams({
    id: selected.id,
    lat: String(lat),
    lng: String(lng),
    radius: String(KAKAO_SAFETY_RADIUS_METERS)
  });

  fetchJson(`/api/kakao-safety?${params.toString()}`)
    .then((payload) => {
      if (state.liveSafety.requestId !== requestId) return;
      state.liveSafety = {
        selectedId: selected.id,
        requestId,
        isLoading: false,
        data: payload,
        error: payload?.ok ? "" : (payload?.error || "안전 시설 정보를 불러오지 못했습니다.")
      };
      renderInfrastructurePanel();
      renderMap();
    })
    .catch((error) => {
      if (state.liveSafety.requestId !== requestId) return;
      state.liveSafety = {
        selectedId: selected.id,
        requestId,
        isLoading: false,
        data: null,
        error: error.message || "안전 시설 정보를 불러오지 못했습니다."
      };
      renderInfrastructurePanel();
    });
}

function districtNameForAir(selected) {
  const district = cleanDistrictName(selected?.district || "");
  if (district) return district;
  const address = String(selected?.address || "");
  const match = address.match(/서울(?:특별시|시)?\s*([가-힣]+구)/);
  return match?.[1] || "";
}

function liveAirStateFor(selected) {
  if (!selected?.id || state.liveAir.selectedId !== selected.id) return null;
  return state.liveAir;
}

function liveAirDataFor(selected) {
  const liveState = liveAirStateFor(selected);
  const data = liveState?.data;
  if (!data || data.mode !== "live_api" || !data.air) return null;
  return data.air;
}

function airDescription(air) {
  if (!air) return "정보 없음";
  const parts = [];
  if (air.station) parts.push(`${air.station} 측정소`);
  if (air.grade) parts.push(air.grade);
  if (air.pm25 != null) parts.push(`PM2.5 ${formatNumber(air.pm25)}㎍/㎥`);
  if (air.pm10 != null) parts.push(`PM10 ${formatNumber(air.pm10)}㎍/㎥`);
  return parts.join(" · ") || "서울시 대기환경 API";
}

function ensureLiveAir(selected) {
  if (!selected?.id) return;
  const district = districtNameForAir(selected);
  if (!district) return;

  const liveState = liveAirStateFor(selected);
  if (liveState?.isLoading || liveState?.data || liveState?.error) return;

  const requestId = state.liveAir.requestId + 1;
  state.liveAir = {
    selectedId: selected.id,
    requestId,
    isLoading: true,
    data: null,
    error: ""
  };

  const params = new URLSearchParams({ district });
  fetchJson(`/api/seoul-air?${params.toString()}`)
    .then((payload) => {
      if (state.liveAir.requestId !== requestId) return;
      state.liveAir = {
        selectedId: selected.id,
        requestId,
        isLoading: false,
        data: payload,
        error: payload?.ok ? "" : (payload?.error || "대기환경 정보를 불러오지 못했습니다.")
      };
      renderInfrastructurePanel();
      renderMap();
    })
    .catch((error) => {
      if (state.liveAir.requestId !== requestId) return;
      state.liveAir = {
        selectedId: selected.id,
        requestId,
        isLoading: false,
        data: null,
        error: error.message || "대기환경 정보를 불러오지 못했습니다."
      };
      renderInfrastructurePanel();
    });
}

function liveCctvStateFor(selected) {
  if (!selected?.id || state.liveCctv.selectedId !== selected.id) return null;
  return state.liveCctv;
}

function liveCctvDataFor(selected) {
  const liveState = liveCctvStateFor(selected);
  const data = liveState?.data;
  if (!data || data.mode !== "live_api" || !data.category) return null;
  return data.category;
}

function cctvDescription(category) {
  if (!category) return "정보 없음";
  const nearest = category.nearest;
  const parts = [];
  if (nearest?.name) parts.push(nearest.name);
  if (nearest?.distanceMeters != null) parts.push(formatDistance(nearest.distanceMeters));
  if (category.count != null) parts.push(`CCTV ${formatNumber(category.count)}대`);
  return parts.join(" · ") || "공공데이터포털 CCTV API";
}

function ensureLiveCctv(selected) {
  if (!selected?.id) return;
  const lat = Number(selected.lat);
  const lng = Number(selected.lng);
  const district = districtNameForAir(selected);
  if (!Number.isFinite(lat) || !Number.isFinite(lng) || !district) return;

  const liveState = liveCctvStateFor(selected);
  if (liveState?.isLoading || liveState?.data || liveState?.error) return;

  const requestId = state.liveCctv.requestId + 1;
  state.liveCctv = {
    selectedId: selected.id,
    requestId,
    isLoading: true,
    data: null,
    error: ""
  };

  const params = new URLSearchParams({
    district,
    lat: String(lat),
    lng: String(lng),
    radius: String(KAKAO_SAFETY_RADIUS_METERS)
  });
  fetchJson(`/api/public-cctv?${params.toString()}`)
    .then((payload) => {
      if (state.liveCctv.requestId !== requestId) return;
      state.liveCctv = {
        selectedId: selected.id,
        requestId,
        isLoading: false,
        data: payload,
        error: payload?.ok ? "" : (payload?.error || "CCTV 정보를 불러오지 못했습니다.")
      };
      renderInfrastructurePanel();
      renderMap();
    })
    .catch((error) => {
      if (state.liveCctv.requestId !== requestId) return;
      state.liveCctv = {
        selectedId: selected.id,
        requestId,
        isLoading: false,
        data: null,
        error: error.message || "CCTV 정보를 불러오지 못했습니다."
      };
      renderInfrastructurePanel();
    });
}

function infrastructureSamplesFor(selected, category) {
  const meta = INFRASTRUCTURE_CATEGORY_META[category] || {};
  if (meta.source === "soc") {
    const liveSamples = liveInfrastructureDataFor(selected)?.categories?.[category]?.samples;
    if (Array.isArray(liveSamples) && liveSamples.length) return liveSamples;
  }
  if (category === "cctv") {
    const liveSamples = liveCctvDataFor(selected)?.samples;
    if (Array.isArray(liveSamples) && liveSamples.length) return liveSamples;
  }
  if (meta.source === "safety" && ["police", "green"].includes(category)) {
    const liveSamples = liveSafetyDataFor(selected)?.categories?.[category]?.samples;
    if (Array.isArray(liveSamples) && liveSamples.length) return liveSamples;
  }
  const soc = selected.socSummary || {};
  const safety = selected.safetyEnvSummary || {};
  if (category === "green") {
    return [safety.nearestFacilities?.park, ...(safety.sampleFacilities || []).filter((item) => item.category === "park")]
      .filter(Boolean);
  }
  if (category === "air") {
    const liveAir = liveAirDataFor(selected);
    if (liveAir) {
      return [{
        category: "air",
        name: liveAir.nearest?.name || `${liveAir.station || "서울시"} 대기측정소`,
        description: airDescription(liveAir),
        distanceMeters: 900
      }];
    }
    return [{
      category: "air",
      name: safety.airStation || "대기측정소",
      distanceMeters: 900
    }];
  }
  const summary = meta.source === "safety" ? safety : soc;
  const categoryKeys = SOC_CATEGORY_DEFINITIONS[category]?.aliases || [category];
  return (summary.sampleFacilities || [])
    .filter((item) => categoryKeys.includes(item.category))
    .slice(0, 8);
}

function facilityLatLng(selected, facility, category, index) {
  if (Number.isFinite(Number(facility?.lat)) && Number.isFinite(Number(facility?.lng))) {
    return [Number(facility.lat), Number(facility.lng)];
  }
  const distance = Number(facility?.distanceMeters || 450);
  const categoryOrder = Object.keys(INFRASTRUCTURE_CATEGORY_META).indexOf(category);
  const bearing = ((categoryOrder + 1) * 47 + index * 31) % 360;
  return offsetLatLng(Number(selected.lat), Number(selected.lng), distance, bearing);
}

function infrastructureIcon(category) {
  const meta = INFRASTRUCTURE_CATEGORY_META[category] || INFRASTRUCTURE_CATEGORY_META.park;
  return L.divIcon({
    className: "infrastructure-map-marker-wrapper",
    html: `<span class="infrastructure-map-marker type-${escapeHtml(meta.className)}">${infrastructureIconSvg(category)}</span>`,
    iconSize: [34, 34],
    iconAnchor: [17, 32],
    popupAnchor: [0, -30]
  });
}

function infrastructureIconSvg(category) {
  const icons = {
    hospital: `<svg class="hospital-cross-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14"/><path d="M5 12h14"/></svg>`,
    medical: `<svg class="hospital-cross-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14"/><path d="M5 12h14"/></svg>`,
    school: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 10.5 12 5l9 5.5-9 5.5-9-5.5Z"/><path d="M6.5 12.8v4.4c1.7 1.2 3.5 1.8 5.5 1.8s3.8-.6 5.5-1.8v-4.4"/><path d="M20 11v5"/></svg>`,
    education: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 10.5 12 5l9 5.5-9 5.5-9-5.5Z"/><path d="M6.5 12.8v4.4c1.7 1.2 3.5 1.8 5.5 1.8s3.8-.6 5.5-1.8v-4.4"/><path d="M20 11v5"/></svg>`,
    transport: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 4h12a2 2 0 0 1 2 2v9.5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2Z"/><path d="M7 8h10"/><path d="M8 17.5 6.5 20"/><path d="M16 17.5 17.5 20"/><circle cx="8" cy="14" r="1"/><circle cx="16" cy="14" r="1"/></svg>`,
    convenience: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 9h14l-1 11H6L5 9Z"/><path d="M8 9a4 4 0 0 1 8 0"/><path d="M9 13h6"/></svg>`,
    park: `<svg class="park-tree-icon" viewBox="0 0 24 24" aria-hidden="true"><path class="tree-trunk" d="M10 15h4v5a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1v-5Z"/><path class="tree-leaf" d="M12 3 5.8 9.2a1 1 0 0 0 .7 1.8H8l-3.2 3.2a1 1 0 0 0 .7 1.8h13a1 1 0 0 0 .7-1.8L16 11h1.5a1 1 0 0 0 .7-1.8L12 3Z"/></svg>`,
    leisure: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20h16"/><path d="M6 20V9l6-4 6 4v11"/><path d="M9 20v-5h6v5"/><path d="M9 11h1"/><path d="M14 11h1"/></svg>`,
    welfare: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10Z"/><path d="M9 11h6"/></svg>`,
    police: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3 5.5 5.5v5.2c0 4.1 2.6 7.8 6.5 10.3 3.9-2.5 6.5-6.2 6.5-10.3V5.5L12 3Z"/><path d="M9 11.2h6"/><path d="M12 8.2v6"/></svg>`,
    cctv: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m4 9 10.5-3 1.5 5.2-10.5 3L4 9Z"/><path d="m14.8 8.5 4.2-1.2 1 3.5-4.2 1.2"/><path d="M9.5 14.5 8 20"/><path d="M6 20h6"/></svg>`,
    air: `<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8h9.5a2.5 2.5 0 1 0-2.1-3.9"/><path d="M3.5 13h15a2.5 2.5 0 1 1-2.1 3.9"/><path d="M5 18h6"/></svg>`,
    green: `<svg class="park-tree-icon" viewBox="0 0 24 24" aria-hidden="true"><path class="tree-trunk" d="M10 15h4v5a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1v-5Z"/><path class="tree-leaf" d="M12 3 5.8 9.2a1 1 0 0 0 .7 1.8H8l-3.2 3.2a1 1 0 0 0 .7 1.8h13a1 1 0 0 0 .7-1.8L16 11h1.5a1 1 0 0 0 .7-1.8L12 3Z"/></svg>`
  };
  return icons[category] || icons.park;
}

function renderInfrastructureMarkers(bounds = []) {
  if (!state.map?.infrastructureLayer) return;
  state.map.infrastructureLayer.clearLayers();

  const selected = selectedInfrastructureItem();
  const category = state.infrastructureFocus.category;
  if (state.detailSubpanelTab !== "infrastructure" || !selected || !category || !INFRASTRUCTURE_CATEGORY_META[category]) return;

  const samples = infrastructureSamplesFor(selected, category);
  if (!samples.length) return;

  const markerBounds = [];
  samples.forEach((facility, index) => {
    const latLng = facilityLatLng(selected, facility, category, index);
    markerBounds.push(latLng);
    bounds.push(latLng);
    const distance = facility.distanceMeters != null ? formatDistance(facility.distanceMeters) : "거리 정보 없음";
    L.marker(latLng, {
      title: facility.name || INFRASTRUCTURE_CATEGORY_META[category].label,
      icon: infrastructureIcon(category),
      zIndexOffset: 720
    }).bindPopup(`
      <div class="infra-popup">
        <strong>${escapeHtml(facility.name || INFRASTRUCTURE_CATEGORY_META[category].label)}</strong>
        <span>${escapeHtml(INFRASTRUCTURE_CATEGORY_META[category].label)} · ${escapeHtml(distance)}</span>
        ${facility.count ? `<small>CCTV ${formatNumber(facility.count)}대 집계점</small>` : ""}
        ${facility.lat && facility.lng ? "" : "<small>거리 기반 추정 위치</small>"}
      </div>
    `, { className: "match-price-popup" }).addTo(state.map.infrastructureLayer);
  });

  if (markerBounds.length && state.detailSubpanelTab === "infrastructure") {
    state.map.instance.fitBounds([[selected.lat, selected.lng], ...markerBounds], {
      padding: [58, 58],
      maxZoom: 16,
      animate: true
    });
    state.map.fitted = true;
  }
}

function renderDestinationMarker(bounds) {
  if (!state.map?.destinationLayer) return;
  state.map.destinationLayer.clearLayers();
  if (!state.hasMatched || isRouteSubpanelActive()) return;

  const destinationLocation = selectedDestinationLocation();
  if (!destinationLocation?.lat || !destinationLocation?.lng) return;

  const latLng = [Number(destinationLocation.lat), Number(destinationLocation.lng)];
  L.marker(latLng, {
    icon: destinationPinIcon(),
    zIndexOffset: 900
  }).addTo(state.map.destinationLayer);

  bounds.push(latLng);
}

function renderLeafletMap() {
  initializeLeafletMap();
  if (!state.map) return false;

  const { instance, markerLayer } = state.map;
  markerLayer.clearLayers();
  state.map.markersById = {};

  const bounds = [];
  const visibleResults = mapResultsForCurrentView();
  visibleResults.forEach((item, index) => {
    const selected = item.id === state.selectedId;
    const marker = L.marker([item.lat, item.lng], {
      icon: L.divIcon({
        className: "mv-map-icon-wrapper",
        html: `
          <span class="property-price-marker${selected ? " is-selected" : ""}">
            <span class="property-home-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" focusable="false">
                <path d="M4 11.2 12 4l8 7.2v8.1a.7.7 0 0 1-.7.7h-4.6v-5.4H9.3V20H4.7a.7.7 0 0 1-.7-.7v-8.1Z" fill="currentColor"/>
              </svg>
            </span>
          </span>
        `,
        iconSize: [38, 44],
        iconAnchor: [19, 41],
        popupAnchor: [0, -38]
      })
    });

    marker.on("click", () => selectApartmentMatch(item.id, { source: "map", openDetailPanel: true }));
    marker.addTo(markerLayer);
    state.map.markersById[item.id] = marker;
    bounds.push([item.lat, item.lng]);
  });

  renderDestinationMarker(bounds);
  renderInfrastructureMarkers(bounds);
  drawRouteLine(bounds);
  if (bounds.length && !state.map.fitted) {
    const destinationLocation = selectedDestinationLocation();
    const routePanelFocused = isRouteSubpanelActive() && state.route.result;
    const matchFocusBounds = state.hasMatched && destinationLocation && !routePanelFocused
      ? [
          [destinationLocation.lat, destinationLocation.lng],
          ...visibleResults.slice(0, 5).map((item) => [item.lat, item.lng])
        ]
      : bounds;
    const maxZoom = routePanelFocused
      ? routeFocusMaxZoom(state.route.result)
      : state.hasMatched
        ? 15
        : 12;
    instance.fitBounds(matchFocusBounds, { padding: [44, 44], maxZoom, animate: false });
    state.map.fitted = true;
  }

  if (state.hasMatched) {
    renderApartmentLayer();
  } else if (state.apartments.enabled) {
    scheduleApartmentLayerLoad();
  } else {
    renderApartmentLayer();
  }

  window.setTimeout(() => instance.invalidateSize(), 0);
  return true;
}

function beginMapCameraTransition() {
  if (!state.map?.instance) return 0;
  state.map.cameraRequestId = Number(state.map.cameraRequestId || 0) + 1;
  state.map.instance.stop();
  return state.map.cameraRequestId;
}

function isCurrentMapCameraTransition(requestId) {
  return Boolean(state.map && state.map.cameraRequestId === requestId);
}

function routeFocusMaxZoom(route = {}) {
  const meters = Number(route.summary?.distanceMeters || 0);
  if (!Number.isFinite(meters) || meters <= 0) return 16;
  if (meters <= 900) return 18;
  if (meters <= 1800) return 17;
  if (meters <= 3500) return 16;
  if (meters <= 8000) return 15;
  return 14;
}

function focusSelectedMarker(options = {}) {
  const marker = state.map?.markersById?.[state.selectedId];
  if (!marker) return;
  const requestId = beginMapCameraTransition();
  const markerLayer = state.map.markerLayer;
  const openMarker = () => {
    if (!isCurrentMapCameraTransition(requestId) || state.detailSubpanelTab === "route") return;
  };

  if (options.zoom) {
    state.map.instance.closePopup();
    state.map.instance.flyTo(marker.getLatLng(), Math.max(state.map.instance.getZoom(), 15), {
      duration: 0.65
    });
    state.map.instance.once("moveend", openMarker);
    return;
  } else if (options.pan) {
    state.map.instance.panTo(marker.getLatLng());
  }

  if (typeof markerLayer?.zoomToShowLayer === "function") {
    markerLayer.zoomToShowLayer(marker, openMarker);
  } else {
    openMarker();
  }
}

function focusRouteOnMap() {
  if (!state.map?.instance || !state.route.result) return;
  const requestId = beginMapCameraTransition();
  const latLngs = buildRouteSegments(state.route.result).flatMap((segment) => (
    segment.points.map((point) => [Number(point.lat), Number(point.lng)])
  ));
  if (latLngs.length < 2) return;
  state.map.instance.closePopup();
  window.requestAnimationFrame(() => {
    if (!isCurrentMapCameraTransition(requestId) || state.detailSubpanelTab !== "route") return;
    state.map.instance.invalidateSize({ pan: false });
    state.map.instance.flyToBounds(L.latLngBounds(latLngs), {
      paddingTopLeft: [72, 108],
      paddingBottomRight: [360, 190],
      maxZoom: routeFocusMaxZoom(state.route.result),
      duration: 0.75
    });
  });
}

function isRouteSubpanelActive() {
  return Boolean(state.detailPanelOpen && state.detailSubpanelTab === "route");
}

function mapResultsForCurrentView() {
  if (!isRouteSubpanelActive()) return state.results;
  const selected = selectedMatchResult();
  return selected ? [selected] : [];
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
  if (isRouteSubpanelActive()) {
    nodes.apartmentLayerStatus.textContent = "선택 아파트만 표시";
    nodes.apartmentLayerStatus.className = "map-layer-status is-ready";
    return;
  }
  if (state.hasMatched && state.results.length) {
    nodes.apartmentLayerStatus.textContent = `추천 상위 ${formatNumber(state.results.length)}개 표시`;
    nodes.apartmentLayerStatus.className = "map-layer-status is-ready";
    return;
  }
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
  const mode = meta.complete ? "전체" : meta.prototypeExpanded ? "프로토타입" : "제한 스냅샷";
  const viewCount = meta.filteredRecords || 0;
  const total = meta.prototypeExpanded
    ? meta.availableRecords || viewCount
    : meta.totalRecords || meta.availableRecords || 0;
  nodes.apartmentLayerStatus.textContent = `${mode} ${formatNumber(total)}개 중 현재 화면 ${formatNumber(viewCount)}개`;
  nodes.apartmentLayerStatus.className = meta.complete ? "map-layer-status is-ready" : "map-layer-status is-warning";
}

function apartmentPopup(feature) {
  return `
    <div class="match-popup">
      <strong class="match-popup-name">${escapeHtml(feature.name || "아파트")}</strong>
    </div>
  `;
}

function openApartmentFeatureDetail(feature) {
  if (!feature?.id) return;
  resetRouteState();
  state.selectedId = feature.id;
  state.detailPanelOpen = true;
  state.detailSubpanelTab = "matching";
  state.showAllCards = false;
  render();
  selectProperty(feature.id);
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

function cleanDistrictName(value) {
  return String(value || "")
    .replace(/^서울(?:특별시|시)?\s*/, "")
    .trim();
}

function shouldRenderDistrictApartmentClusters() {
  return Boolean(
    state.map?.instance
    && !state.hasMatched
    && state.apartments.enabled
    && state.apartmentCandidates.length
    && state.map.instance.getZoom() <= DISTRICT_CLUSTER_MAX_ZOOM
  );
}

function districtApartmentGroups() {
  const groups = new Map();
  state.apartmentCandidates.forEach((item) => {
    const district = cleanDistrictName(item.district);
    const lat = Number(item.lat);
    const lng = Number(item.lng);
    if (!district || !Number.isFinite(lat) || !Number.isFinite(lng)) return;

    const group = groups.get(district) || {
      district,
      lat: 0,
      lng: 0,
      count: 0
    };
    group.lat += lat;
    group.lng += lng;
    group.count += 1;
    groups.set(district, group);
  });

  return [...groups.values()]
    .map((group) => ({
      ...group,
      lat: group.lat / group.count,
      lng: group.lng / group.count
    }))
    .sort((left, right) => right.count - left.count);
}

function renderDistrictApartmentClusters() {
  const layer = state.map?.districtLayer;
  if (!layer) return false;
  layer.clearLayers();
  state.map.apartmentLayer?.clearLayers();
  state.map.propertyMarkersById = {};

  if (!shouldRenderDistrictApartmentClusters()) return false;

  districtApartmentGroups().forEach((group) => {
    const marker = L.marker([group.lat, group.lng], {
      icon: L.divIcon({
        className: "district-cluster-wrapper",
        html: `
          <span class="district-cluster">
            <strong>${formatNumber(group.count)}</strong>
            <span>${escapeHtml(group.district)}</span>
          </span>
        `,
        iconSize: [148, 44],
        iconAnchor: [74, 22],
        popupAnchor: [0, -22]
      })
    });
    marker.on("click", () => {
      state.map.instance.setView([group.lat, group.lng], DISTRICT_CLUSTER_MAX_ZOOM + 1);
    });
    marker.addTo(layer);
  });

  return true;
}

function renderApartmentLayer() {
  if (!state.map?.apartmentLayer) return;
  const layer = state.map.apartmentLayer;
  layer.clearLayers();
  state.map.districtLayer?.clearLayers();
  state.map.propertyMarkersById = {};

  if (state.hasMatched) {
    renderApartmentLayerStatus();
    return;
  }

  if (!state.apartments.enabled) {
    renderApartmentLayerStatus();
    renderMapSidebar();
    return;
  }

  if (renderDistrictApartmentClusters()) {
    renderApartmentLayerStatus();
    updateMapScaleUI();
    renderMapSidebar();
    return;
  }

  const recommendationIds = new Set(state.results.map((item) => item.id));
  state.apartments.features.forEach((feature) => {
    if (feature.type !== "cluster" && recommendationIds.has(feature.id)) return;
    if (feature.type === "cluster") {
      const size = clusterMarkerSize(feature.count, { min: 36, max: 96 });
      const marker = L.marker([feature.lat, feature.lng], {
        title: `아파트 단지 ${feature.count}개`,
        icon: L.divIcon({
          className: "apt-cluster-wrapper",
          html: `<span class="apt-cluster" style="--cluster-size:${size}px"><strong>${formatNumber(feature.count)}</strong></span>`,
          iconSize: [size, size],
          iconAnchor: [size / 2, size / 2],
          popupAnchor: [0, -22]
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

    const selected = feature.id === state.property.selectedId;
    const marker = L.marker([feature.lat, feature.lng], {
      icon: L.divIcon({
        className: "property-price-wrapper",
        html: `
          <span class="property-price-marker${selected ? " is-selected" : ""}">
            <span class="property-home-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" focusable="false">
                <path d="M4 11.2 12 4l8 7.2v8.1a.7.7 0 0 1-.7.7h-4.6v-5.4H9.3V20H4.7a.7.7 0 0 1-.7-.7v-8.1Z" fill="currentColor"/>
              </svg>
            </span>
          </span>
        `,
        iconSize: [38, 44],
        iconAnchor: [19, 41],
        popupAnchor: [0, -38]
      })
    });
    marker
      .on("click", () => openApartmentFeatureDetail(feature))
      .addTo(layer);
    state.map.propertyMarkersById[feature.id] = marker;
  });
  renderApartmentLayerStatus();
  updateMapScaleUI();
  renderMapSidebar();
}

function openSelectedPropertyPopup() {
  const marker = state.map?.propertyMarkersById?.[state.property.selectedId];
  if (!marker) return;
  window.requestAnimationFrame(() => {
    state.map?.instance?.closePopup();
  });
}

async function loadApartmentsForMap(force = false) {
  if (!state.map?.instance || !state.apartments.enabled) return;

  if (shouldRenderDistrictApartmentClusters()) {
    state.apartments.isLoading = false;
    state.apartments.error = "";
    renderApartmentLayer();
    return;
  }

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
    cluster: typeof L.markerClusterGroup === "function" ? "false" : "true",
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

  const visibleResults = mapResultsForCurrentView();
  const mapCandidates = state.results.length ? state.results : state.apartmentCandidates;
  if (!mapCandidates.length) {
    nodes.mapCanvas.innerHTML = `<div class="map-empty">데이터 로딩 중</div>`;
    return;
  }

  const latValues = mapCandidates.map((item) => item.lat);
  const lngValues = mapCandidates.map((item) => item.lng);
  const minLat = Math.min(...latValues);
  const maxLat = Math.max(...latValues);
  const minLng = Math.min(...lngValues);
  const maxLng = Math.max(...lngValues);

  visibleResults.forEach((item) => {
    const x = 10 + ((item.lng - minLng) / (maxLng - minLng || 1)) * 80;
    const y = 84 - ((item.lat - minLat) / (maxLat - minLat || 1)) * 68;
    const marker = document.createElement("button");
    marker.type = "button";
    marker.className = `area-marker${item.id === state.selectedId ? " is-selected" : ""}`;
    marker.style.left = `${x}%`;
    marker.style.top = `${y}%`;
    marker.style.setProperty("--size", `${18 + item.total / 5}px`);
    marker.style.setProperty("--marker", markerColor(item.total));
    marker.setAttribute("aria-label", item.name);
    marker.innerHTML = `<span>${item.name}</span>`;
    marker.addEventListener("click", () => selectApartmentMatch(item.id, { source: "map", openDetailPanel: true }));
    nodes.mapCanvas.append(marker);
  });

  const route = state.route.result;
  if (state.detailPanelOpen && state.detailSubpanelTab === "route" && route?.origin && route?.destination) {
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

function renderMapSidebar() {
  // Map-side list panels were removed; sidebar cards are the single ranking surface.
}

function renderMapRouteChip() {
  // Route details stay in the subpanel; the map keeps only the route geometry.
}

function renderDetailSubpanelState() {
  const selected = selectedDetailItem();
  const open = Boolean(state.detailPanelOpen && selected);
  document.querySelector(".workspace")?.classList.toggle("has-subpanel", open);

  if (!nodes.detailSubpanel) return;
  nodes.detailSubpanel.hidden = !open;
  nodes.detailSubpanel.setAttribute("aria-hidden", open ? "false" : "true");

  const activeTab = ["matching", "apartment", "route", "infrastructure", "jeonseRisk"].includes(state.detailSubpanelTab)
    ? state.detailSubpanelTab
    : "matching";
  nodes.detailSubpanel.querySelectorAll("[data-subpanel-tab]").forEach((button) => {
    const active = button.dataset.subpanelTab === activeTab;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-selected", active ? "true" : "false");
    button.tabIndex = active ? 0 : -1;
  });
  nodes.detailSubpanel.querySelectorAll("[data-subpanel-panel]").forEach((panel) => {
    panel.hidden = panel.dataset.subpanelPanel !== activeTab;
  });

  if (!open || activeTab !== "route") {
    state.map?.routeLayer?.clearLayers();
  } else if (state.route.result && state.map?.routeLayer?.getLayers().length === 0) {
    drawRouteLine([]);
  }

  const apartmentPanel = nodes.detailSubpanel.querySelector('[data-subpanel-panel="apartment"]');
  const showingPropertyDashboard = Boolean(state.property.selectedId);
  apartmentPanel?.classList.toggle("has-property-dashboard", showingPropertyDashboard);

  if (nodes.subpanelMeta) {
    nodes.subpanelMeta.textContent = selected ? "" : "매칭 결과를 선택하세요";
  }
}

function activateDetailSubpanelTab(tab) {
  state.detailSubpanelTab = tab;
  renderDetailSubpanelState();
  if (tab === "infrastructure") {
    renderInfrastructurePanel();
  }
  renderMap();
  if (tab !== "route") {
    focusSelectedMarker({ zoom: true });
    return;
  }

  const selected = selectedDetailItem();
  const routeReady = state.route.selectedId === selected?.id
    && (state.route.isLoading || state.route.result);
  if (selected && selectedMatchResult() && !routeReady) {
    calculateCommuteRoute(selected);
  } else if (state.route.result) {
    focusRouteOnMap();
  }
}

function resetMapToSeoul() {
  if (!state.map?.instance) return;
  state.map.instance.flyTo(SEOUL_CENTER, SEOUL_OVERVIEW_ZOOM, {
    duration: 0.65
  });
  state.map.fitted = true;
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

function isLiveStatus(status) {
  return status?.mode === "live_api" && Number(status?.recordCount || 0) > 0;
}

function propertyDataNote(isLive, liveLabel, emptyLabel = "매칭된 실거래 정보 없음") {
  return isLive ? liveLabel : emptyLabel;
}

function formatAreaM2(value) {
  const area = Number(value);
  if (!Number.isFinite(area) || area <= 0) return "";
  return `${area.toLocaleString("ko-KR", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2
  })}㎡`;
}

function liveAreaOptionsText(detail) {
  const liveAreas = (detail.areaOptions || [])
    .filter((item) => item.sourceMode === "molit_live" && Number(item.exclusiveM2) > 0)
    .map((item) => formatAreaM2(item.exclusiveM2))
    .filter(Boolean);
  return liveAreas.length ? liveAreas.join(" / ") : "정보 없음";
}

function liveTransactionRecords(price, predicate) {
  return (price.molitRentRecords || []).filter((item) => predicate(item));
}

function latestTradeRecord(price) {
  const records = Array.isArray(price.molitTradeRecords) ? price.molitTradeRecords : [];
  return records
    .filter((item) => Number(item.amount10k || 0) > 0 && Number(item.exclusiveM2 || 0) > 0)
    .sort((a, b) => {
      const left = `${a.dealYear || ""}${String(a.dealMonth || "").padStart(2, "0")}${String(a.dealDay || "").padStart(2, "0")}`;
      const right = `${b.dealYear || ""}${String(b.dealMonth || "").padStart(2, "0")}${String(b.dealDay || "").padStart(2, "0")}`;
      return right.localeCompare(left);
    })[0] || null;
}

function pricePerPyeongText(record) {
  const amount10k = Number(record?.amount10k || 0);
  const exclusiveM2 = Number(record?.exclusiveM2 || 0);
  const pyeong = exclusiveM2 / 3.3058;
  if (!amount10k || !Number.isFinite(pyeong) || pyeong <= 0) return "정보 없음";
  return `평당 ${formatMoney10k(amount10k / pyeong)}`;
}

function formatChartMoney10k(value) {
  const amount = Number(value || 0);
  if (!amount) return "0";
  if (amount >= 10000) {
    const eok = amount / 10000;
    return `${Number.isInteger(eok) ? eok.toFixed(0) : eok.toFixed(1)}억`;
  }
  return `${formatNumber(Math.round(amount))}만`;
}

function statusText(status) {
  if (status === "high") return "집중 확인";
  if (status === "warning") return "주의";
  if (status === "unknown") return "미확인";
  return "양호";
}

function activeTrendMode() {
  return state.property.trendMode || (state.budgetMode === "sale" ? "sale" : "rent");
}

function renderTrendChart(rows, detail = null) {
  const liveRows = Array.isArray(rows) ? rows.filter((row) => row.sourceMode !== "trend_estimate") : [];
  const indexedRows = liveRows.map((row, index) => ({ ...row, index }));
  const saleData = indexedRows
    .map((row) => ({ month: row.month || "", value: Number(row.sale10k || 0), volume: Number(row.saleVolume || 0), index: row.index }))
    .filter((row) => row.month && row.value > 0);
  const jeonseData = indexedRows
    .map((row) => ({ month: row.month || "", value: Number(row.jeonse10k || 0), volume: Number(row.jeonseVolume || 0), index: row.index }))
    .filter((row) => row.month && row.value > 0);
  const monthlyData = indexedRows
    .map((row) => ({ month: row.month || "", value: Number(row.monthlyRent10k || 0), volume: Number(row.monthlyRentVolume || 0), index: row.index }))
    .filter((row) => row.month && row.value > 0);
  const trendMode = activeTrendMode();
  const rentTrendKind = jeonseData.length >= 2 ? "jeonse" : "monthly";
  const primaryData = trendMode === "sale" ? saleData : (rentTrendKind === "jeonse" ? jeonseData : monthlyData);
  const pointCount = primaryData.length;
  if (liveRows.length < 2 || pointCount < 2) {
    return `<div class="chart-empty">실거래 기반 월별 추이 정보 없음</div>`;
  }
  const values = primaryData.map((row) => row.value);
  const min = Math.max(0, Math.min(...values) * 0.72);
  const max = Math.max(...values) * 1.12;
  const width = 440;
  const height = 255;
  const left = 46;
  const right = 18;
  const top = 18;
  const bottom = 70;
  const volumeTop = height - 44;
  const volumeBottom = height - 18;
  const usableWidth = width - left - right;
  const usableHeight = height - top - bottom;
  const y = (value) => top + usableHeight - ((Number(value) - min) / (max - min || 1)) * usableHeight;
  const x = (index) => left + (index / (liveRows.length - 1)) * usableWidth;
  const recentAverage = primaryData.length ? primaryData[primaryData.length - 1].value : 0;
  const summaryLabel = trendMode === "sale"
    ? "최근 매매 월별 평균"
    : rentTrendKind === "jeonse"
      ? "최근 전세 월별 평균"
      : "최근 월세 월별 평균";
  const averageLine = primaryData.length ? primaryData.reduce((sum, row) => sum + row.value, 0) / primaryData.length : 0;
  const highestPoint = primaryData.length ? primaryData.reduce((best, row) => (row.value > best.value ? row : best), primaryData[0]) : null;
  const lowestPoint = primaryData.length ? primaryData.reduce((best, row) => (row.value < best.value ? row : best), primaryData[0]) : null;
  const maxVolume = Math.max(...indexedRows.map((row) => Number(row.volume || 0)), 1);
  const ticks = Array.from({ length: 5 }, (_, index) => min + ((max - min) / 4) * index).reverse();
  const monthLabel = (month) => {
    const value = String(month || "");
    if (!value.includes(".")) return value;
    const [year, monthPart] = value.split(".");
    return `'${year.slice(-2)}.${monthPart}`;
  };
  const linePoints = primaryData.map((row) => `${x(row.index).toFixed(1)},${y(row.value).toFixed(1)}`).join(" ");
  const primaryDots = primaryData.map((row) => `
    <circle class="trend-primary-point" cx="${x(row.index).toFixed(1)}" cy="${y(row.value).toFixed(1)}" r="3.8">
      <title>${escapeHtml(`${row.month} ${trendMode === "sale" ? "매매" : "전월세"} ${formatMoney10k(row.value)}${row.volume ? ` · ${row.volume}건` : ""}`)}</title>
    </circle>
  `).join("");
  const volumeBars = indexedRows.map((row) => {
    const volume = Number(row.volume || 0);
    const barHeight = Math.max(2, (volume / maxVolume) * (volumeBottom - volumeTop));
    const barWidth = Math.max(3, Math.min(8, usableWidth / Math.max(18, liveRows.length * 2)));
    return `
      <rect class="volume-bar" x="${(x(row.index) - barWidth / 2).toFixed(1)}" y="${(volumeBottom - barHeight).toFixed(1)}" width="${barWidth.toFixed(1)}" height="${barHeight.toFixed(1)}" rx="1.5">
        <title>${escapeHtml(`${row.month} 거래량 ${formatNumber(volume)}건`)}</title>
      </rect>
    `;
  }).join("");
  const latestX = primaryData.length ? x(primaryData[primaryData.length - 1].index) : 0;
  const latestGuide = primaryData.length ? `
    <rect class="trend-latest-zone" x="${latestX.toFixed(1)}" y="${top}" width="${Math.max(0, width - right - latestX).toFixed(1)}" height="${(volumeTop - top).toFixed(1)}" />
    <line class="trend-latest-line" x1="${latestX.toFixed(1)}" y1="${top}" x2="${latestX.toFixed(1)}" y2="${volumeBottom}" />
  ` : "";
  const gridLines = ticks.map((tick) => `
    <g>
      <line class="trend-grid-line" x1="${left}" y1="${y(tick).toFixed(1)}" x2="${width - right}" y2="${y(tick).toFixed(1)}" />
      <text class="trend-axis-label" x="${left - 8}" y="${(y(tick) + 4).toFixed(1)}" text-anchor="end">${escapeHtml(formatChartMoney10k(tick))}</text>
    </g>
  `).join("");
  const first = liveRows[0]?.month || "";
  const middle = liveRows[Math.floor((liveRows.length - 1) / 2)]?.month || "";
  const last = liveRows[liveRows.length - 1]?.month || "";
  const trendLabel = trendMode === "sale" ? "매매" : "전월세";
  return `
    <div class="trend-panel">
      <div class="trend-toolbar">
        <div class="trend-market-tabs" aria-label="거래 유형">
          <button class="${trendMode === "sale" ? "active" : ""}" type="button" data-trend-market="sale">매매</button>
          <button class="${trendMode !== "sale" ? "active" : ""}" type="button" data-trend-market="rent">전월세</button>
        </div>
      </div>
      <p class="trend-summary-label">${escapeHtml(summaryLabel)}</p>
      <strong class="trend-summary-value">${escapeHtml(formatMoney10k(recentAverage))}</strong>
      <svg class="property-trend-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="최근 거래 추이 그래프">
        ${latestGuide}
        ${gridLines}
        ${averageLine ? `<line class="trend-average-line" x1="${left}" y1="${y(averageLine).toFixed(1)}" x2="${width - right}" y2="${y(averageLine).toFixed(1)}" />` : ""}
        <polyline class="trend-primary-line" points="${linePoints}" />
        ${primaryDots}
        ${highestPoint ? `
          <circle class="highest-sale-point" cx="${x(highestPoint.index).toFixed(1)}" cy="${y(highestPoint.value).toFixed(1)}" r="5" />
          <text class="highest-sale-label" x="${x(highestPoint.index).toFixed(1)}" y="${(y(highestPoint.value) - 16).toFixed(1)}" text-anchor="middle">${escapeHtml(formatChartMoney10k(highestPoint.value))}</text>
          <text class="highest-sale-label sub" x="${x(highestPoint.index).toFixed(1)}" y="${(y(highestPoint.value) - 4).toFixed(1)}" text-anchor="middle">최고</text>
        ` : ""}
        ${lowestPoint && highestPoint && lowestPoint !== highestPoint ? `
          <circle class="lowest-jeonse-point" cx="${x(lowestPoint.index).toFixed(1)}" cy="${y(lowestPoint.value).toFixed(1)}" r="5" />
          <text class="lowest-jeonse-label" x="${x(lowestPoint.index).toFixed(1)}" y="${(y(lowestPoint.value) + 16).toFixed(1)}" text-anchor="middle">${escapeHtml(formatChartMoney10k(lowestPoint.value))}</text>
          <text class="lowest-jeonse-label sub" x="${x(lowestPoint.index).toFixed(1)}" y="${(y(lowestPoint.value) + 28).toFixed(1)}" text-anchor="middle">최저</text>
        ` : ""}
        <text class="volume-title" x="${left - 2}" y="${volumeTop - 7}" text-anchor="end">거래량</text>
        ${volumeBars}
        <text class="trend-axis-label" x="${left}" y="${height - 2}">${escapeHtml(monthLabel(first))}</text>
        ${middle && middle !== first && middle !== last ? `<text class="trend-axis-label" x="${x(Math.floor((liveRows.length - 1) / 2)).toFixed(1)}" y="${height - 2}" text-anchor="middle">${escapeHtml(monthLabel(middle))}</text>` : ""}
        <text class="trend-axis-label" x="${width - right}" y="${height - 2}" text-anchor="end">${escapeHtml(monthLabel(last))}</text>
      </svg>
      <div class="chart-legend">
        <span><i class="chart-dot sale"></i>${escapeHtml(trendLabel)} 실거래</span>
        <span><i class="chart-dot average"></i>평균선</span>
        <span><i class="chart-dot jeonse"></i>최저가</span>
      </div>
    </div>
  `;
}

function aiSummaryPriceComparison(detail = null) {
  const price = detail?.price || {};
  const mode = state.budgetMode;
  const modeLabel = budgetConfig(mode).shortLabel;
  const liveStatus = price.liveStatus || {};
  let actualValue = 0;
  let hasPrice = false;

  if (mode === "monthly") {
    hasPrice = liveTransactionRecords(price, (item) => Number(item.monthlyRent10k || 0) > 0).length > 0;
    actualValue = Number(price.monthlyRent10k || 0);
  } else if (mode === "jeonse") {
    hasPrice = liveTransactionRecords(price, (item) => !Number(item.monthlyRent10k || 0)).length > 0;
    actualValue = Number(price.recentJeonse10k || 0);
  } else if (mode === "sale") {
    const latestTrade = latestTradeRecord(price);
    hasPrice = isLiveStatus(liveStatus.molitTrade) || Boolean(latestTrade);
    actualValue = Number(price.recentSale10k || latestTrade?.amount10k || 0);
  }

  return {
    mode,
    modeLabel,
    hasPrice: Boolean(hasPrice && actualValue),
    actualValue,
    budgetValue: Number(state.budget || 0)
  };
}

function aiSummaryPriceStrength(detail = null) {
  const comparison = aiSummaryPriceComparison(detail);
  const { mode, modeLabel, hasPrice, actualValue, budgetValue } = comparison;

  if (!hasPrice) return `최신 아파트 ${modeLabel} 가격 정보를 불러오지 못하였습니다.`;
  if (!budgetValue) return `최신 아파트 ${modeLabel} 가격 정보를 확인했습니다.`;

  const diff = Math.abs(Math.round(actualValue - budgetValue));
  const subject = `${modeLabel} 가격`;
  const diffText = formatBudgetValue(diff, mode);
  if (diff === 0) return `${subject}은 설정한 금액과 동일합니다.`;
  if (actualValue < budgetValue) return `${subject}은 설정한 금액보다 약 ${diffText} 적습니다.`;
  return "";
}

function aiSummaryLiveCarRoute(selected = null) {
  const route = state.aiCommute.result || state.route.result;
  const routeSelectedId = state.aiCommute.result ? state.aiCommute.selectedId : state.route.selectedId;
  const isSelectedRoute = selected?.id && routeSelectedId === selected.id;
  const isLiveCarRoute = isSelectedRoute
    && route?.transportMode === "car"
    && route?.provider === "tmap"
    && route?.mode === "live_api"
    && Number(route?.summary?.totalMinutes || 0) > 0;
  return isLiveCarRoute ? route : null;
}

function aiSummaryCommuteStrength(selected = null) {
  const route = aiSummaryLiveCarRoute(selected);
  if (!route) return "최신 통근 정보를 불러오지 못하였습니다.";

  const minutes = Number(route.summary.totalMinutes || 0);
  if (minutes <= 20) return `자동차로 약 ${formatNumber(minutes)}분 소요되어 통근이 편리합니다.`;
  if (minutes <= 60) return `자동차로 약 ${formatNumber(minutes)}분 소요됩니다.`;
  return "최신 통근 정보를 확인했습니다.";
}

function aiSummaryStrengths(summary = {}, context = {}) {
  const existing = (summary.strengths || [])
    .filter((item) => !String(item).includes("지하철 접근성"))
    .filter((item) => !String(item).includes("월세 기준은"))
    .filter((item) => !String(item).includes("월세 실거래 기준은"));
  return [
    aiSummaryPriceStrength(context.detail),
    aiSummaryCommuteStrength(context.selected),
    ...existing
  ].filter(Boolean).slice(0, 3);
}

function aiSummaryCautions(summary = {}, context = {}) {
  const cautions = [];
  const price = aiSummaryPriceComparison(context.detail);
  if (price.hasPrice && price.budgetValue > 0 && price.actualValue > price.budgetValue) {
    const diffText = formatBudgetValue(Math.round(price.actualValue - price.budgetValue), price.mode);
    cautions.push(`${price.modeLabel} 가격은 설정한 금액보다 약 ${diffText} 많아 예산 초과입니다.`);
  }

  const route = aiSummaryLiveCarRoute(context.selected);
  const commuteMinutes = Number(route?.summary?.totalMinutes || 0);
  if (commuteMinutes > 60) {
    cautions.push(`자동차로 약 ${formatNumber(commuteMinutes)}분 소요되어 통근시간이 긴 편입니다.`);
  }

  const gaptong = context.detail?.safeguard?.gaptong || {};
  if (["danger", "warning"].includes(gaptong.verdictKey)) {
    const label = gaptong.verdictLabel || "깡통주택 위험 신호";
    cautions.push(`전세 위험 신호 점검에서 ${label}으로 확인되어 계약 전 추가 확인이 필요합니다.`);
  }

  if (cautions.length) return cautions.slice(0, 3);
  return ["현재 확인된 주요 주의사항은 없습니다."];
}

function aiSummaryHeadline(context = {}) {
  const selected = context.selected || {};
  const name = selected.name || "선택한 아파트";
  const scores = selected.adjusted || {};
  if (!scores.cost && !scores.commute && !scores.service) {
    return `${name}은 공개 데이터 기준으로 가격·통근·생활 편의성을 종합적으로 검토할 수 있는 후보입니다.`;
  }
  const criteria = [
    { key: "cost", label: "가격", value: Number(scores.cost || 0) },
    { key: "commute", label: "통근", value: Number(scores.commute || 0) },
    { key: "service", label: "생활 편의성", value: Number(scores.service || 0) }
  ];
  const weak = criteria.filter((item) => item.value && item.value < 70);
  const good = criteria.filter((item) => item.value >= 75);

  if (good.length === criteria.length) {
    return `${name}은 공개 데이터 기준으로 가격·통근·생활 편의성의 균형이 좋은 후보입니다.`;
  }
  if (weak.length >= 2) {
    return `${name}은 공개 데이터 기준으로 가격·통근·생활 편의성 중 일부 조건이 다소 아쉬운 후보입니다.`;
  }
  if (weak.length === 1) {
    return `${name}은 ${weak[0].label}에서 아쉬움이 있으나, 가격·통근·생활 편의성을 종합적으로 검토할 수 있는 후보입니다.`;
  }
  return `${name}은 공개 데이터 기준으로 가격·통근·생활 편의성을 종합적으로 검토할 수 있는 후보입니다.`;
}

function renderAiSummaryCard(summary = {}, context = {}) {
  const headline = aiSummaryHeadline(context);
  const strengths = aiSummaryStrengths(summary, context);
  const cautions = aiSummaryCautions(summary, context);
  return `
    <section class="property-card ai-summary-card">
      <div class="property-card-title">
        <h4>AI 요약</h4>
      </div>
      <p class="ai-headline">${escapeHtml(headline)}</p>
      <div class="ai-summary-grid">
        <div>
          <strong>장점</strong>
          <ul>${strengths.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        </div>
        <div>
          <strong>주의</strong>
          <ul>${cautions.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
        </div>
      </div>
    </section>
  `;
}

function renderAiSummaryPendingCard() {
  return `
    <section class="property-card ai-summary-card ai-summary-card-pending">
      <div class="property-card-title">
        <h4>AI 요약</h4>
        <span>AI 분석중</span>
      </div>
      <p class="ai-headline">선택한 아파트의 주거 조건을 종합적으로 분석하고 있습니다.</p>
    </section>
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

function renderGaptongVerdict(safeguard) {
  const verdict = safeguard?.gaptong;
  if (!verdict) return "";
  return `
    <div class="gaptong-verdict tone-${escapeHtml(verdict.verdictKey || "unknown")}">
      <div class="gaptong-head">
        <strong>깡통주택 자동 판정 · ${escapeHtml(verdict.verdictLabel || "")}</strong>
        <em>전세가율 ${formatPercent(verdict.ratioPct)} / 기준 ${formatPercent(verdict.thresholdPct)}</em>
      </div>
      <div class="gaptong-bar" role="img" aria-label="전세가율 ${formatPercent(verdict.ratioPct)}, 깡통주택 기준 ${formatPercent(verdict.thresholdPct)}">
        <span class="gaptong-fill" style="width:${Math.min(100, Number(verdict.ratioPct) || 0)}%"></span>
        <span class="gaptong-threshold" style="left:${Number(verdict.thresholdPct) || 80}%"></span>
      </div>
      <p class="gaptong-detail">${escapeHtml(verdict.detail || "")}</p>
      <small class="property-note">${escapeHtml(verdict.basis || "")}</small>
    </div>
  `;
}

function renderBlindSpots(safeguard) {
  const rows = Array.isArray(safeguard?.blindSpots) ? safeguard.blindSpots : [];
  if (!rows.length) return "";
  return `
    <ul class="blindspot-list">
      ${rows.map((row) => `
        <li class="blindspot-item level-${escapeHtml(row.level || "info")}">
          <strong>${escapeHtml(row.label)}</strong>
          <span>${escapeHtml(row.detail)}</span>
        </li>
      `).join("")}
    </ul>
  `;
}

function renderSelfServeChecks(safeguard) {
  const rows = Array.isArray(safeguard?.selfServeChecks) ? safeguard.selfServeChecks : [];
  if (!rows.length) return "";
  return `
    <ul class="selfserve-list">
      ${rows.map((row) => `
        <li class="selfserve-item">
          <div>
            <strong>${escapeHtml(row.label)}</strong>
            <span>${escapeHtml(row.target)}</span>
            <small>${escapeHtml(row.how)}</small>
          </div>
          <a href="${escapeHtml(row.url)}" target="_blank" rel="noopener noreferrer">바로가기</a>
        </li>
      `).join("")}
    </ul>
  `;
}

function renderConsentChecks(safeguard) {
  const rows = Array.isArray(safeguard?.consentChecks) ? safeguard.consentChecks : [];
  if (!rows.length) return "";
  return `
    <ul class="consent-list">
      ${rows.map((row) => `
        <li class="consent-item">
          <strong>${escapeHtml(row.label)}</strong>
          <span>${escapeHtml(row.why)}</span>
          <p class="consent-refused"><em>거부당하면</em> ${escapeHtml(row.ifRefused)}</p>
        </li>
      `).join("")}
    </ul>
  `;
}

function renderTenancyTimeline(safeguard) {
  const timeline = safeguard?.timeline;
  const steps = Array.isArray(timeline?.steps) ? timeline.steps : [];
  if (!steps.length) return "";
  return `
    <p class="timeline-summary">${escapeHtml(timeline.gapSummary || "")}</p>
    <ol class="tenancy-timeline">
      ${steps.map((step) => `
        <li class="tenancy-step risk-${escapeHtml(step.risk || "safe")}">
          <span class="tenancy-day">${escapeHtml(step.day)}</span>
          <div>
            <strong>${escapeHtml(step.action)}</strong>
            <span>${escapeHtml(step.detail)}</span>
          </div>
        </li>
      `).join("")}
    </ol>
  `;
}

function renderSpecialClauses(safeguard) {
  const clauses = Array.isArray(safeguard?.timeline?.clauses) ? safeguard.timeline.clauses : [];
  if (!clauses.length) return "";
  return `
    <div class="clause-list">
      ${clauses.map((clause, index) => `
        <article class="clause-card">
          <div class="clause-head">
            <strong>${escapeHtml(clause.title)}</strong>
            <button type="button" class="clause-copy" data-clause-index="${index}">복사</button>
          </div>
          <p>${escapeHtml(clause.text)}</p>
        </article>
      `).join("")}
    </div>
  `;
}

function renderSupportCenter(safeguard) {
  const center = safeguard?.center;
  if (!center) return "";
  return `
    <div class="support-center">
      <div class="support-center-head">
        <strong>${escapeHtml(center.name)}</strong>
        <em>약 ${escapeHtml(String(center.distanceKm))}km</em>
      </div>
      <p>${escapeHtml(center.service)}</p>
      <div class="support-center-meta">
        ${propertyMetric("운영 요일", center.days)}
        ${propertyMetric("운영 시간", center.hours)}
        ${propertyMetric("전화", center.phone)}
        ${propertyMetric("주소", center.address)}
      </div>
      <a class="support-center-link" href="${escapeHtml(center.reserveUrl)}" target="_blank" rel="noopener noreferrer">안전계약 컨설팅 예약</a>
      <small class="property-note">${escapeHtml(center.note)}</small>
    </div>
  `;
}

async function copyTextToClipboard(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const area = document.createElement("textarea");
    area.value = text;
    area.setAttribute("readonly", "");
    area.style.cssText = "position:fixed;top:0;left:0;opacity:0;";
    document.body.appendChild(area);
    area.select();
    let copied = false;
    try {
      copied = document.execCommand("copy");
    } catch {
      copied = false;
    }
    area.remove();
    return copied;
  }
}

async function handleClauseCopy(button) {
  const clauses = state.property.detail?.safeguard?.timeline?.clauses || [];
  const clause = clauses[Number(button.dataset.clauseIndex)];
  if (!clause) return;
  const copied = await copyTextToClipboard(clause.text);
  button.textContent = copied ? "복사됨" : "복사 실패";
  window.setTimeout(() => {
    button.textContent = "복사";
  }, 1600);
}

const AGENT_DEFAULT_FOLLOW_UPS = [
  "전세 들어가도 괜찮아?",
  "깡통주택이야?",
  "계약 전에 뭘 확인해야 해?",
  "왜 추천한 거야?",
  "비슷한 가격대에 더 안전한 곳 있어?"
];

function agentTarget() {
  const detail = state.property.detail;
  if (detail?.id) return { id: detail.id, name: detail.name };
  const selected = selectedDetailItem();
  if (selected?.id) return { id: selected.id, name: selected.name };
  const top = state.results[0] || state.apartmentCandidates[0] || null;
  return top?.id ? { id: top.id, name: top.name } : null;
}

function renderAgentBasisGroups(answer) {
  const groups = answer?.basisGroups || null;
  if (!groups) {
    return `<ul>${(answer?.basis || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
  }
  const filled = Object.entries(groups).filter(([, items]) => (items || []).length);
  if (!filled.length) return "";
  return `
    <details class="agent-basis">
      <summary>근거 ${filled.length}종 보기</summary>
      <div class="agent-basis-grid">
        ${filled.map(([title, items]) => `
          <section>
            <strong>${escapeHtml(title)}</strong>
            <ul>${(items || []).map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
          </section>
        `).join("")}
      </div>
    </details>
  `;
}

function renderAgentMessage(message) {
  if (message.role === "user") {
    return `<div class="agent-msg is-user"><p>${escapeHtml(message.text)}</p></div>`;
  }
  const answer = message.answer || {};
  const comparisons = answer.suggestedComparisons || [];
  return `
    <div class="agent-msg is-agent">
      ${message.target ? `<span class="agent-msg-target">${escapeHtml(message.target)}</span>` : ""}
      <p>${escapeHtml(answer.answer || message.text || "")}</p>
      ${renderAgentBasisGroups(answer)}
      ${comparisons.length ? `
        <div class="agent-suggestions">
          ${comparisons.map((item) => `
            <button type="button" class="chip-button" data-agent-property-id="${escapeHtml(item.id)}">
              ${escapeHtml(item.name)} · ${escapeHtml(item.saleLabel)} · ${escapeHtml(item.riskLevel)}
            </button>
          `).join("")}
        </div>
      ` : ""}
      ${answer.disclaimer ? `<small>${escapeHtml(answer.disclaimer)}</small>` : ""}
    </div>
  `;
}

function renderAgentPanel() {
  const panel = document.querySelector("#agentPanel");
  const launcher = document.querySelector("#agentLauncher");
  if (!panel || !launcher) return;

  if (state.bookmarks.panelOpen) {
    panel.hidden = true;
    launcher.hidden = true;
    launcher.setAttribute("aria-expanded", "false");
    launcher.classList.remove("is-active");
    return;
  }

  launcher.hidden = false;
  panel.hidden = !state.agent.open;
  launcher.setAttribute("aria-expanded", String(state.agent.open));
  launcher.classList.toggle("is-active", state.agent.open);
  if (!state.agent.open) return;

  const target = agentTarget();
  const context = document.querySelector("#agentContextLabel");
  if (context) {
    context.textContent = target
      ? `${target.name} 기준으로 답변합니다`
      : "매칭을 실행하거나 단지를 선택하면 그 단지 기준으로 답변합니다";
  }

  const thread = document.querySelector("#agentThread");
  if (thread) {
    const intro = state.agent.messages.length
      ? ""
      : `<div class="agent-msg is-agent is-intro">
           <p>가격·통근·전세 위험 신호 데이터를 근거로 답변합니다. 아래 질문을 눌러 시작해 보세요.</p>
         </div>`;
    thread.innerHTML = intro
      + state.agent.messages.map(renderAgentMessage).join("")
      + (state.agent.isLoading ? `<div class="agent-msg is-agent is-loading">근거를 정리하는 중입니다.</div>` : "")
      + (state.agent.error ? `<div class="agent-msg is-agent is-error">${escapeHtml(state.agent.error)}</div>` : "");
    thread.scrollTop = thread.scrollHeight;
  }

  const followUps = document.querySelector("#agentFollowUps");
  if (followUps) {
    const items = state.agent.followUps.length ? state.agent.followUps : AGENT_DEFAULT_FOLLOW_UPS;
    followUps.innerHTML = items
      .map((item) => `<button type="button" class="agent-followup" data-agent-followup="${escapeHtml(item)}">${escapeHtml(item)}</button>`)
      .join("");
  }

  bindAgentThreadEvents();
}

function openAgentPanel() {
  state.agent.open = true;
  renderAgentPanel();
  document.querySelector("#agentInput")?.focus();
}

function closeAgentPanel() {
  state.agent.open = false;
  renderAgentPanel();
  document.querySelector("#agentLauncher")?.focus();
}

function resetAgentConversation() {
  state.agent.messages = [];
  state.agent.followUps = [];
  state.agent.error = "";
  renderAgentPanel();
}

async function sendAgentMessage(question) {
  const text = String(question || "").trim();
  if (!text || state.agent.isLoading) return;

  const target = agentTarget();
  if (!target) {
    state.agent.error = "먼저 목적지를 입력해 매칭을 실행하거나 지도에서 단지를 선택하세요.";
    renderAgentPanel();
    return;
  }

  state.agent.messages.push({ role: "user", text });
  state.agent.isLoading = true;
  state.agent.error = "";
  renderAgentPanel();

  try {
    const params = new URLSearchParams({ id: target.id, question: text });
    const payload = await fetchJson(`/api/property-agent?${params.toString()}`);
    const answer = payload.agent || null;
    state.agent.messages.push({ role: "agent", answer, target: target.name });
    state.agent.followUps = answer?.followUps || [];
  } catch (error) {
    state.agent.error = `AI Agent 응답 실패: ${error.message}`;
  } finally {
    state.agent.isLoading = false;
    renderAgentPanel();
  }
}

function bindAgentThreadEvents() {
  document.querySelectorAll("#agentThread [data-agent-property-id]").forEach((button) => {
    button.addEventListener("click", () => {
      selectProperty(button.dataset.agentPropertyId);
    });
  });
  document.querySelectorAll("#agentFollowUps [data-agent-followup]").forEach((button) => {
    button.addEventListener("click", () => sendAgentMessage(button.dataset.agentFollowup));
  });
}

function bindAgentPanelEvents() {
  document.querySelector("#agentLauncher")?.addEventListener("click", () => {
    if (state.agent.open) closeAgentPanel();
    else openAgentPanel();
  });
  document.querySelector("#agentCloseButton")?.addEventListener("click", closeAgentPanel);
  document.querySelector("#agentResetButton")?.addEventListener("click", resetAgentConversation);
  const submitAgentInput = () => {
    const input = document.querySelector("#agentInput");
    const value = input?.value || "";
    if (input) input.value = "";
    sendAgentMessage(value);
  };
  document.querySelector("#agentForm")?.addEventListener("submit", (event) => {
    event.preventDefault();
    submitAgentInput();
  });
  document.querySelector("#agentInput")?.addEventListener("keydown", (event) => {
    if (event.key !== "Enter" || event.isComposing || event.keyCode === 229) return;
    event.preventDefault();
    submitAgentInput();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && state.agent.open) closeAgentPanel();
  });
}

function bookmarkSummary(id) {
  const detail = state.bookmarks.details[id] || null;
  const result = state.results.find((item) => item.id === id) || null;
  const candidate = state.apartmentCandidates.find((item) => item.id === id) || null;
  const price = detail?.price || {};
  const lifestyle = detail?.lifestyle || {};
  const risk = detail?.risk || {};
  return {
    id,
    name: detail?.name || result?.name || candidate?.name || "아파트",
    address: detail?.address || result?.address || candidate?.address || "",
    district: detail?.district || result?.district || candidate?.district || "",
    score: result?.total,
    commuteMinutes: result?.minutes ?? candidate?.pricePreview?.commuteMinutes,
    sale10k: price.recentSale10k ?? result?.sale10k ?? candidate?.pricePreview?.sale10k,
    jeonse10k: price.recentJeonse10k ?? result?.jeonse10k ?? candidate?.pricePreview?.jeonse10k,
    monthlyRent10k: price.monthlyRent10k ?? result?.rentMonthly10k,
    monthlyDeposit10k: price.monthlyDeposit10k ?? result?.deposit10k,
    jeonseRatio: price.jeonseRatio ?? candidate?.pricePreview?.jeonseRatio,
    riskLevel: risk.level || candidate?.pricePreview?.riskLevel || "",
    riskLevelKey: risk.levelKey || candidate?.pricePreview?.riskLevelKey || "unknown",
    households: detail?.households ?? result?.households ?? candidate?.households,
    approvalYear: detail?.approvalYear ?? result?.approvalYear ?? candidate?.approvalYear,
    serviceScore: lifestyle.serviceScore ?? result?.serviceScore,
    safetyScore: lifestyle.safetyScore ?? result?.safetyScore
  };
}

function bookmarkValue(value, formatter = (item) => item) {
  return value === undefined || value === null || value === "" ? "-" : formatter(value);
}

function renderBookmarkCompareTable() {
  const items = state.bookmarks.ids.map(bookmarkSummary);
  if (!items.length) {
    return `
      <div class="bookmark-empty">
        <strong>즐겨찾기한 아파트가 없습니다.</strong>
        <span>매칭 결과나 아파트 상세 정보에서 별표를 선택하세요.</span>
      </div>
    `;
  }

  const rows = [
    { label: "매칭 점수", value: (item) => bookmarkValue(item.score, (value) => `${formatNumber(value)}점`) },
    { label: "통근시간", value: (item) => bookmarkValue(item.commuteMinutes, (value) => `${formatNumber(value)}분`) },
    { label: "추정 매매가", value: (item) => bookmarkValue(item.sale10k, formatMoney10k) },
    { label: "추정 전세가", value: (item) => bookmarkValue(item.jeonse10k, formatMoney10k) },
    { label: "월세", value: (item) => bookmarkValue(item.monthlyRent10k, (value) => `${formatMoney10k(item.monthlyDeposit10k)} / 월 ${formatMoney10k(value)}`) },
    { label: "전세가율", value: (item) => bookmarkValue(item.jeonseRatio, formatPercent) },
    { label: "위험도", value: (item) => item.riskLevel ? `<span class="risk-pill ${riskTone(item.riskLevelKey)}">${escapeHtml(item.riskLevel)}</span>` : "-" },
    { label: "세대수·준공", value: (item) => `${bookmarkValue(item.households, (value) => `${formatNumber(value)}세대`)} · ${bookmarkValue(item.approvalYear, (value) => `${value}년`)}` },
    { label: "생활 SOC", value: (item) => bookmarkValue(item.serviceScore, (value) => `${formatNumber(value)}점`) },
    { label: "안전", value: (item) => bookmarkValue(item.safetyScore, (value) => `${formatNumber(value)}점`) }
  ];

  return `
    <div class="bookmark-compare-scroll">
      <table class="bookmark-compare-table">
        <thead>
          <tr>
            <th scope="col">비교 항목</th>
            ${items.map((item) => `
              <th scope="col">
                <button class="bookmark-property-link" type="button" data-bookmark-open="${escapeHtml(item.id)}">${escapeHtml(item.name)}</button>
                <small>${escapeHtml(item.district)}</small>
                <button class="bookmark-remove-button" type="button" data-bookmark-remove="${escapeHtml(item.id)}" aria-label="${escapeHtml(item.name)} 즐겨찾기 해제" title="즐겨찾기 해제">★</button>
              </th>
            `).join("")}
          </tr>
        </thead>
        <tbody>
          <tr class="bookmark-address-row">
            <th scope="row">주소</th>
            ${items.map((item) => `<td>${escapeHtml(item.address || "-")}</td>`).join("")}
          </tr>
          ${rows.map((row) => `
            <tr>
              <th scope="row">${row.label}</th>
              ${items.map((item) => `<td>${row.value(item)}</td>`).join("")}
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

function renderBookmarkHeader() {
  if (!nodes.bookmarkPanelButton || !nodes.bookmarkCount) return;
  const count = state.bookmarks.ids.length;
  nodes.bookmarkCount.textContent = formatNumber(count);
  nodes.bookmarkPanelButton.classList.toggle("has-bookmarks", count > 0);
  nodes.bookmarkPanelButton.classList.toggle("is-open", state.bookmarks.panelOpen);
  const icon = nodes.bookmarkPanelButton.querySelector("span");
  if (icon) icon.textContent = count ? "★" : "☆";
}

function bindBookmarkPanelEvents() {
  document.querySelector("#closeBookmarkPanelButton")?.addEventListener("click", closeBookmarkPanel);
  document.querySelectorAll("[data-bookmark-remove]").forEach((button) => {
    button.addEventListener("click", () => toggleBookmark(button.dataset.bookmarkRemove));
  });
  document.querySelectorAll("[data-bookmark-open]").forEach((button) => {
    button.addEventListener("click", () => {
      closeBookmarkPanel();
      selectProperty(button.dataset.bookmarkOpen);
    });
  });
}

function renderBookmarkPanel() {
  if (!nodes.bookmarkPanel) return;
  renderBookmarkHeader();
  nodes.bookmarkPanel.hidden = !state.bookmarks.panelOpen;
  if (!state.bookmarks.panelOpen) {
    nodes.bookmarkPanel.innerHTML = "";
    return;
  }
  nodes.bookmarkPanel.innerHTML = `
    <header class="bookmark-panel-header">
      <div>
        <p class="eyebrow">저장한 아파트</p>
        <h2>즐겨찾기 비교 <span>${formatNumber(state.bookmarks.ids.length)}</span></h2>
      </div>
      <button id="closeBookmarkPanelButton" class="property-close-button" type="button" aria-label="즐겨찾기 비교 닫기">×</button>
    </header>
    <div class="bookmark-panel-body">
      ${state.bookmarks.isLoading ? `<div class="bookmark-loading">아파트 상세 정보를 불러오는 중입니다.</div>` : ""}
      ${state.bookmarks.error ? `<div class="bookmark-error">${escapeHtml(state.bookmarks.error)}</div>` : ""}
      ${renderBookmarkCompareTable()}
    </div>
  `;
  bindBookmarkPanelEvents();
}

async function loadBookmarkDetails() {
  const missing = state.bookmarks.ids.filter((id) => !state.bookmarks.details[id]);
  if (!missing.length) return;
  state.bookmarks.isLoading = true;
  state.bookmarks.error = "";
  renderBookmarkPanel();
  const failures = [];
  await Promise.all(missing.map(async (id) => {
    try {
      const payload = await fetchJson(`/api/property-detail?id=${encodeURIComponent(id)}`);
      if (payload.detail) state.bookmarks.details[id] = payload.detail;
    } catch {
      failures.push(id);
    }
  }));
  state.bookmarks.isLoading = false;
  state.bookmarks.error = failures.length ? "일부 아파트 상세 정보를 불러오지 못했습니다." : "";
  renderBookmarkPanel();
}

function refreshBookmarkViews() {
  renderBookmarkHeader();
  renderCards();
  renderDetail();
  renderPropertyDashboard();
  renderJeonseRiskPanel();
  renderBookmarkPanel();
}

async function toggleBookmark(id, detail = null) {
  if (!id) return;
  if (isBookmarked(id)) {
    state.bookmarks.ids = state.bookmarks.ids.filter((item) => item !== id);
    delete state.bookmarks.details[id];
  } else {
    state.bookmarks.ids = [...state.bookmarks.ids, id];
    if (detail) state.bookmarks.details[id] = detail;
  }
  persistBookmarks();
  refreshBookmarkViews();
  if (isBookmarked(id) && !state.bookmarks.details[id]) {
    await loadBookmarkDetails();
  }
}

function openBookmarkPanel() {
  state.bookmarks.panelOpen = true;
  state.agent.open = false;
  state.detailPanelOpen = false;
  closePropertyDashboard();
  renderDetailSubpanelState();
  renderBookmarkPanel();
  renderAgentPanel();
  invalidateMapLayout();
  loadBookmarkDetails();
}

function closeBookmarkPanel() {
  state.bookmarks.panelOpen = false;
  renderBookmarkPanel();
  renderAgentPanel();
  invalidateMapLayout();
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
  renderJeonseRiskPanel();
  renderDetailSubpanelState();
  renderAgentPanel();
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
  document.querySelectorAll("[data-trend-market]").forEach((button) => {
    button.addEventListener("click", () => {
      state.property.trendMode = button.dataset.trendMarket === "sale" ? "sale" : "rent";
      renderPropertyDashboard();
    });
  });
  document.querySelectorAll(".clause-copy").forEach((button) => {
    button.addEventListener("click", () => handleClauseCopy(button));
  });
  bindAgentCtaEvents();
}

function bindPropertyAgentEvents() {
  document.querySelector("#propertyAgentForm")?.addEventListener("submit", askPropertyAgent);
  document.querySelectorAll("[data-agent-property-id]").forEach((button) => {
    button.addEventListener("click", () => selectProperty(button.dataset.agentPropertyId));
  });
}

function bindAgentCtaEvents() {
  document.querySelector("#openAgentFromDashboard")?.addEventListener("click", openAgentPanel);
}

function renderAgentCtaCard() {
  return `
    <section class="property-card wide agent-cta">
      <div class="property-card-title">
        <h4>AI Agent 질의응답</h4>
        <span>근거 기반 설명</span>
      </div>
      <p class="property-note">전세 안전성, 깡통 여부, 확인 서류 등을 대화로 물어볼 수 있습니다.</p>
      <button id="openAgentFromDashboard" class="primary-button compact-button" type="button">AI Agent에게 물어보기</button>
    </section>
  `;
}

function renderPropertyDashboard() {
  if (!nodes.propertyDashboard) return;

  if (state.property.isLoading) {
    nodes.propertyDashboard.classList.add("has-property-detail");
    nodes.propertyDashboard.innerHTML = `
      <div class="property-empty">
        <strong>단지 상세 정보를 불러오는 중입니다.</strong>
        <span>실거래·전용면적 연계 구조와 전세 위험 신호를 계산합니다.</span>
      </div>
    `;
    return;
  }

  if (state.property.error) {
    nodes.propertyDashboard.classList.add("has-property-detail");
    nodes.propertyDashboard.innerHTML = `<div class="property-empty is-error">${escapeHtml(state.property.error)}</div>`;
    return;
  }

  const detail = state.property.detail;
  if (!detail) {
    nodes.propertyDashboard.classList.remove("has-property-detail");
    nodes.propertyDashboard.innerHTML = `
      <div class="property-empty">
        <strong>지도에서 아파트 단지를 선택하세요.</strong>
        <span>단지 가격과 전세 위험 신호를 확인할 수 있습니다.</span>
      </div>
    `;
    return;
  }

  nodes.propertyDashboard.classList.add("has-property-detail");
  const price = detail.price || {};
  const liveStatus = price.liveStatus || {};
  const tradeLive = isLiveStatus(liveStatus.molitTrade);
  const jeonseLive = liveTransactionRecords(price, (item) => !Number(item.monthlyRent10k || 0)).length > 0;
  const monthlyLive = liveTransactionRecords(price, (item) => Number(item.monthlyRent10k || 0) > 0).length > 0;
  const latestTrade = latestTradeRecord(price);
  const areaText = liveAreaOptionsText(detail);
  const parkingCount = Number(detail.parkingCount || 0);
  const households = Number(detail.households || 0);
  const parkingPerHousehold = parkingCount && households ? `세대당 ${(parkingCount / households).toFixed(2)}대` : "세대당 정보 없음";
  nodes.propertyDashboard.innerHTML = `
    <div class="property-grid">
      <section class="property-card">
        <div class="property-card-title">
          <h4>기본 정보</h4>
        </div>
        <div class="property-metrics two">
          ${propertyMetric("건물 유형", detail.buildingType || "공동주택")}
          ${propertyMetric("주택 유형", detail.housingType || "확인 필요")}
          ${propertyMetric("준공/사용승인", detail.approvalYear ? `${detail.approvalYear}년` : "확인 필요", `${formatNumber(detail.buildingAge)}년 경과`)}
          ${propertyMetric("세대/동수", `${formatNumber(detail.households)}세대`, `${formatNumber(detail.buildingCount)}개동`)}
          ${propertyMetric("전용면적", areaText, propertyDataNote(areaText !== "정보 없음", "국토부 매매·전월세 실거래가 API"))}
          ${propertyMetric("주차대수", parkingCount ? `${formatNumber(parkingCount)}대` : "정보 없음", parkingCount ? parkingPerHousehold : "OpenAptInfo 제공 정보 없음")}
        </div>
      </section>

      <section class="property-card">
        <div class="property-card-title">
          <h4>가격 정보</h4>
        </div>
        <div class="property-metrics two">
          ${propertyMetric("최근 매매가", tradeLive ? formatMoney10k(price.recentSale10k) : "정보 없음", propertyDataNote(tradeLive, "국토부 매매 실거래가 API"))}
          ${propertyMetric("최근 전세가", jeonseLive ? formatMoney10k(price.recentJeonse10k) : "정보 없음", propertyDataNote(jeonseLive, "국토부 전월세 실거래가 API"))}
          ${propertyMetric("월세", monthlyLive ? `${formatMoney10k(price.monthlyDeposit10k)} / 월 ${formatMoney10k(price.monthlyRent10k)}` : "정보 없음", propertyDataNote(monthlyLive, "국토부 전월세 실거래가 API"))}
          ${propertyMetric("평당 가격", latestTrade ? pricePerPyeongText(latestTrade) : "정보 없음", propertyDataNote(Boolean(latestTrade), "국토부 매매 실거래가·전용면적 기준"))}
        </div>
      </section>

      <section class="property-card wide">
        <div class="property-card-title">
          <h4>거래 추이</h4>
        </div>
        ${renderTrendChart(detail.transactions, detail)}
      </section>

    </div>
  `;
  bindPropertyDashboardEvents();
}

function renderJeonseRiskPanel() {
  if (!nodes.jeonseRiskContent) return;

  if (state.property.isLoading) {
    nodes.jeonseRiskContent.classList.add("has-property-detail");
    nodes.jeonseRiskContent.innerHTML = `
      <div class="property-empty">
        <strong>전세 위험 정보를 불러오는 중입니다.</strong>
        <span>전세가율, 보증금 비율, 계약 전 확인 항목을 계산합니다.</span>
      </div>
    `;
    return;
  }

  if (state.property.error) {
    nodes.jeonseRiskContent.classList.add("has-property-detail");
    nodes.jeonseRiskContent.innerHTML = `<div class="property-empty is-error">${escapeHtml(state.property.error)}</div>`;
    return;
  }

  const detail = state.property.detail;
  if (!detail) {
    nodes.jeonseRiskContent.classList.remove("has-property-detail");
    nodes.jeonseRiskContent.innerHTML = `
      <div class="property-empty">
        <strong>추천 아파트를 선택하세요.</strong>
        <span>선택한 단지의 전세 위험 신호와 계약 전 확인 항목을 볼 수 있습니다.</span>
      </div>
    `;
    return;
  }

  nodes.jeonseRiskContent.classList.add("has-property-detail");
  const risk = detail.risk || {};
  const safeguard = detail.safeguard || {};
  nodes.jeonseRiskContent.innerHTML = `
    <div class="property-grid">
      <section class="property-card wide">
        <div class="property-card-title">
          <h4>전세 위험 신호 점검</h4>
          <span>법적 판정 아님</span>
        </div>
        ${renderGaptongVerdict(safeguard)}
        <p class="risk-summary">${escapeHtml(risk.summary || "")}</p>
        <ul class="risk-list">${renderRiskSignals(risk)}</ul>
        <p class="property-note">${escapeHtml(risk.disclaimer || "")}</p>
      </section>

      <section class="property-card wide">
        <div class="property-card-title">
          <h4>계약 전 확인 체크리스트</h4>
          <span>주의 요소 안내</span>
        </div>
        ${renderContractChecklist(risk)}
      </section>

      <section class="property-card wide">
        <div class="property-card-title">
          <h4>정보 사각지대</h4>
          <span>가격 데이터에 없는 항목</span>
        </div>
        ${renderBlindSpots(safeguard)}
        <h5 class="safeguard-subtitle">임대인 동의 없이 지금 확인할 수 있는 것</h5>
        ${renderSelfServeChecks(safeguard)}
        <h5 class="safeguard-subtitle">임대인 동의가 필요한 것 · 거부당했을 때</h5>
        ${renderConsentChecks(safeguard)}
      </section>

      <section class="property-card wide">
        <div class="property-card-title">
          <h4>대항력 확보 타임라인</h4>
          <span>전입신고 익일 0시 공백</span>
        </div>
        ${renderTenancyTimeline(safeguard)}
        <h5 class="safeguard-subtitle">공백을 막는 특약 문구</h5>
        ${renderSpecialClauses(safeguard)}
      </section>

      <section class="property-card wide">
        <div class="property-card-title">
          <h4>가까운 안전계약 컨설팅</h4>
          <span>계약 전 전문가 검토</span>
        </div>
        ${renderSupportCenter(safeguard)}
      </section>
    </div>
  `;
  bindPropertyDashboardEvents();
}

async function selectProperty(id) {
  if (!id) return;
  state.bookmarks.panelOpen = false;
  renderBookmarkPanel();
  state.property.selectedId = id;
  state.property.detail = null;
  state.property.isLoading = true;
  state.property.error = "";
  state.property.agentAnswer = null;
  state.property.agentError = "";
  state.property.trendMode = "";
  state.property.requestId += 1;
  const requestId = state.property.requestId;
  renderApartmentLayer();
  openSelectedPropertyPopup();
  renderPropertyDashboard();
  renderJeonseRiskPanel();
  renderDetailSubpanelState();
  try {
    const payload = await fetchJson(`/api/property-detail?id=${encodeURIComponent(id)}`);
    if (requestId !== state.property.requestId) return;
    state.property.detail = payload.detail || null;
    if (state.property.detail) {
      state.property.agentQuestion = `${state.property.detail.name} 전세 들어가도 괜찮아?`;
    }
  } catch (error) {
    if (requestId !== state.property.requestId) return;
    state.property.detail = null;
    state.property.error = `단지 상세 정보를 불러오지 못했습니다: ${error.message}`;
  } finally {
    if (requestId === state.property.requestId) {
      state.property.isLoading = false;
      renderApartmentLayer();
      openSelectedPropertyPopup();
      renderDetail();
      renderPropertyDashboard();
      renderJeonseRiskPanel();
      renderDetailSubpanelState();
      renderAgentPanel();
    }
  }
}

function buildReason(item) {
  return item.reasonText || buildSpecificReason(item);
}

function buildSpecificReason(item) {
  const destinationLabel = item.destinationLabel || destinationLabels[state.destination] || "목적지";
  const targetValue = budgetTargetValue(item, state.budgetMode);
  const budgetDelta = Math.round(state.budget - targetValue);
  const budgetText = budgetDelta >= 0 ? "예산 내" : `예산 ${formatBudgetValue(Math.abs(budgetDelta), state.budgetMode)} 초과`;
  const socText = socSummaryTextFor(item, state.persona, 3);
  return `${destinationLabel} ${formatNumber(item.minutes)}분 · ${budgetConfig().shortLabel} ${formatBudgetValue(targetValue)} · ${socText} · ${budgetText}`;
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
    if (state.matchValidationMessage) {
      nodes.cards.innerHTML = `<div class="empty-state is-error">${escapeHtml(state.matchValidationMessage)}</div>`;
    } else {
      nodes.cards.innerHTML = `<div class="empty-state">${state.hasMatched ? "조건에 맞는 매칭 결과가 없습니다." : "조건을 설정하고 매칭하기 버튼을 눌러주세요"}</div>`;
    }
    nodes.toggleCards.hidden = true;
    return;
  }

  const visible = state.showAllCards ? state.results : state.results.slice(0, CARD_PREVIEW_COUNT);

  visible.forEach((item, index) => {
    const fragment = nodes.cardTemplate.content.cloneNode(true);
    const card = fragment.querySelector(".result-card");
    const button = fragment.querySelector(".card-button");
    const bookmarkButton = fragment.querySelector(".card-bookmark-button");
    card.classList.toggle("is-selected", item.id === state.selectedId);
    fragment.querySelector(".rank").textContent = index + 1;
    fragment.querySelector(".name").textContent = item.name;
    fragment.querySelector(".card-meta").textContent = representativeAddressFor(item);
    button.addEventListener("click", () => selectApartmentMatch(item.id, { source: "card", openDetailPanel: true }));
    const bookmarked = isBookmarked(item.id);
    bookmarkButton.textContent = bookmarked ? "★" : "☆";
    bookmarkButton.classList.toggle("is-bookmarked", bookmarked);
    bookmarkButton.setAttribute("aria-label", `${item.name} ${bookmarked ? "즐겨찾기 해제" : "즐겨찾기 추가"}`);
    bookmarkButton.addEventListener("click", () => toggleBookmark(item.id));
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

function adjustedScoresForDetail(selected = {}, detail = null) {
  const adjusted = { ...(selected.adjusted || {}) };
  const price = aiSummaryPriceComparison(detail);
  if (price.hasPrice) {
    adjusted.cost = Math.round(costScoreForBudget(price.actualValue, price.budgetValue, price.mode));
  }

  const route = aiSummaryLiveCarRoute(selected);
  const routeMinutes = Number(route?.summary?.totalMinutes || 0);
  if (routeMinutes > 0) {
    adjusted.commute = Math.round(clamp(105 - routeMinutes * 1.18));
  }

  const lifestyle = detail?.lifestyle || {};
  const serviceScore = Number(lifestyle.serviceScore || 0);
  if (serviceScore > 0) {
    adjusted.service = Math.round(clamp(serviceScore));
  }

  const safetyScore = Number(lifestyle.safetyScore || 0);
  const carbonScore = Number(lifestyle.carbonScore || 0);
  const riskScore = Number(detail?.risk?.score ?? detail?.price?.riskScore ?? selected.pricePreview?.riskScore ?? 0);
  if (safetyScore > 0 || carbonScore > 0 || riskScore > 0) {
    const environmentScore = safetyScore && carbonScore
      ? safetyScore * 0.58 + carbonScore * 0.42
      : safetyScore || carbonScore || Number(selected.safetyScore || 70);
    const propertySafety = 100 - riskScore;
    adjusted.safety = Math.round(clamp(environmentScore * 0.85 + propertySafety * 0.15));
  }

  return adjusted;
}

function transportModeLabel(mode = DEFAULT_ROUTE_TRANSPORT_MODE) {
  return ROUTE_TRANSPORT_MODES.find((item) => item.key === mode)?.label || "자동차";
}

function routeModeLabel(route = {}) {
  return `${transportModeLabel(route.transportMode)} 최적 경로`;
}

function renderRouteModeSelector() {
  const activeMode = state.route.transportMode || DEFAULT_ROUTE_TRANSPORT_MODE;
  return `
    <div class="route-mode-selector" role="group" aria-label="이동수단 선택">
      ${ROUTE_TRANSPORT_MODES.map((mode) => `
        <button
          class="route-mode-option${mode.key === activeMode ? " is-active" : ""}"
          type="button"
          data-route-transport="${mode.key}"
          aria-pressed="${mode.key === activeMode ? "true" : "false"}"
        >
          <span>${mode.label}</span>
          <i data-lucide="${mode.icon}" aria-hidden="true"></i>
        </button>
      `).join("")}
    </div>
  `;
}

function renderRouteSummary(route) {
  const summary = route.summary || {};
  const transportMode = route.transportMode || DEFAULT_ROUTE_TRANSPORT_MODE;
  if (transportMode === "car") {
    return `
      ${metric("총 소요", `${formatNumber(summary.totalMinutes)}분`)}
      ${metric("이동 거리", formatDistance(summary.distanceMeters))}
      ${metric("택시 요금", formatFare(summary.taxiFare))}
      ${metric("평균 속도", formatAverageSpeed(summary))}
    `;
  }
  if (transportMode === "bicycle") {
    return `
      ${metric("총 소요", `${formatNumber(summary.totalMinutes)}분`)}
      ${metric("이동 거리", formatDistance(summary.distanceMeters))}
      ${metric("예상 소모", `${formatNumber(summary.estimatedCalories)}kcal`)}
      ${metric("이용 요금", summary.fare ? formatFare(summary.fare) : "무료")}
    `;
  }
  if (transportMode === "walk") {
    return `
      ${metric("총 소요", `${formatNumber(summary.totalMinutes)}분`)}
      ${metric("이동 거리", formatDistance(summary.distanceMeters))}
      ${metric("예상 걸음", `${formatNumber(summary.stepCount)}보`)}
      ${metric("이용 요금", summary.fare ? formatFare(summary.fare) : "무료")}
    `;
  }
  return `
    ${metric("총 소요", `${formatNumber(summary.totalMinutes)}분`)}
    ${metric("환승", `${formatNumber(summary.transferCount)}회`)}
    ${metric("도보", formatDistance(summary.totalWalkMeters))}
    ${metric("요금", formatFare(summary.fare))}
  `;
}

function shouldCondenseRouteSteps(route = {}) {
  return ["car", "bicycle", "walk"].includes(route.transportMode || "");
}

function renderRouteEndpointSteps(route) {
  return `
    <ol class="route-steps">
      <li style="--route-color:#03C75A">
        <span class="route-mode">S</span>
        <strong>출발지</strong>
        <span>${escapeHtml(route.origin?.label || "출발지")}</span>
      </li>
      <li style="--route-color:#EF4444">
        <span class="route-mode">E</span>
        <strong>도착지</strong>
        <span>${escapeHtml(route.destination?.label || "도착지")}</span>
      </li>
    </ol>
  `;
}

function renderRouteSteps(route) {
  if (shouldCondenseRouteSteps(route)) {
    return renderRouteEndpointSteps(route);
  }

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
  return `
    <div class="route-result">
      <div class="route-result-head">
        <strong>${routeModeLabel(route)}</strong>
        <button class="text-button" type="button" data-route-map>지도 중심 이동</button>
      </div>
      <div class="route-summary-grid">
        ${renderRouteSummary(route)}
      </div>
      ${renderRouteSteps(route)}
    </div>
  `;
}

function renderRoutePlanner(selected) {
  const originValue = representativeAddressFor(selected);
  const destinationValue = selectedMatchResult() ? (selected.destinationAddress || destinationAddressFor()) : "";
  return `
    <div class="route-planner">
      <div class="route-origin-summary">
        <span>출발 아파트</span>
        <strong>${escapeHtml(selected.name)}</strong>
        <small>${escapeHtml(originValue)}</small>
      </div>
      <div class="route-form">
        <label class="field compact route-destination-field">
          <span>목적지</span>
          <span class="search-input-wrap">
            <input
              id="routeDestinationInput"
              type="text"
              value="${escapeHtml(destinationValue)}"
              autocomplete="off"
              aria-autocomplete="list"
              aria-controls="routeDestinationSuggestions"
              placeholder="주소를 입력하세요.">
            <div id="routeDestinationSuggestions" class="location-suggestions" role="listbox" hidden></div>
          </span>
          <small id="routeDestinationValidation" class="field-hint destination-validation" aria-live="polite"></small>
        </label>
      </div>
      ${renderRouteModeSelector()}
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
  const selected = selectedDetailItem();
  const matched = selectedMatchResult();

  if (!selected) {
    nodes.selectedBadge.textContent = "선택 없음";
    nodes.detailContent.innerHTML = state.isLoading ? `<div class="callout"><p>추천 결과를 계산하고 있습니다.</p></div>` : "";
    return;
  }

  const selectedDetail = state.property.selectedId === selected.id ? state.property.detail : null;
  const aiSummary = selectedDetail?.aiSummary || null;
  const adjustedScores = { ...(selected.adjusted || {}) };
  const selectedForSummary = { ...selected, adjusted: adjustedScores };
  nodes.selectedBadge.textContent = selected.name;
  if (!matched) {
    nodes.detailContent.innerHTML = `
      <section class="property-card match-result-card">
        <div>
          <h3>${escapeHtml(selected.name || "아파트")}</h3>
          <p class="detail-address">${escapeHtml(representativeAddressFor(selected))}</p>
        </div>
        <div class="callout">
          <p>조건을 입력하고 매칭하기를 누르면 통근, 주거비, 생활 SOC, 안전 점수가 표시됩니다.</p>
        </div>
      </section>
      ${selectedDetail?.aiSummary ? renderAiSummaryCard(selectedDetail.aiSummary, { selected: selectedForSummary, detail: selectedDetail }) : renderAiSummaryPendingCard()}
      ${renderAgentCtaCard()}
    `;
    bindAgentCtaEvents();
    return;
  }
  nodes.detailContent.innerHTML = `
    <section class="property-card match-result-card">
      <div>
        <h3>${escapeHtml(selected.name)}</h3>
        <p class="detail-address">${escapeHtml(selected.address || `${selected.district || ""} ${selected.dong || ""}`.trim())}</p>
      </div>
      <div class="score-list" aria-label="항목별 점수">
        ${scoreRow("통근", adjustedScores.commute, scoreTips.commute)}
        ${scoreRow("주거비", adjustedScores.cost, scoreTips.cost)}
        ${scoreRow("생활 SOC", adjustedScores.service, scoreTips.service)}
        ${scoreRow("안전", adjustedScores.safety, scoreTips.safety)}
      </div>
    </section>
    ${aiSummary ? renderAiSummaryCard(aiSummary, { selected: selectedForSummary, detail: selectedDetail }) : renderAiSummaryPendingCard()}
    ${renderAgentCtaCard()}
  `;
  ensureAiSummaryCommuteRoute(selected);
  bindAgentCtaEvents();
}

function renderRoutePanel() {
  const selected = selectedDetailItem();

  if (!nodes.routeContent) return;
  if (!selected) {
    nodes.routeContent.innerHTML = state.isLoading
      ? `<div class="callout"><p>추천 후보를 불러온 뒤 통근 루트를 계산할 수 있습니다.</p></div>`
      : `<div class="callout"><p>추천 아파트를 선택하면 단지에서 목적지까지의 통근 루트를 계산할 수 있습니다.</p></div>`;
    return;
  }

  nodes.routeContent.innerHTML = renderRoutePlanner(selected);
  bindRoutePlanner(selected);
  window.lucide?.createIcons();
}

function infrastructureItem(label, value, nearest = null, category = "") {
  const name = nearest?.name || "정보 없음";
  const distance = nearest?.distanceMeters != null ? formatDistance(nearest.distanceMeters) : "";
  const description = nearest?.description || `${name}${distance ? ` · ${distance}` : ""}`;
  return `
    <button class="infrastructure-item${state.infrastructureFocus.category === category ? " is-active" : ""}" type="button" data-infrastructure-category="${escapeHtml(category)}">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      <small>${escapeHtml(description)}</small>
    </button>
  `;
}

function bindInfrastructurePanelEvents() {
  document.querySelectorAll("[data-infrastructure-category]").forEach((button) => {
    button.addEventListener("click", () => {
      const category = button.dataset.infrastructureCategory || "";
      state.infrastructureFocus.category = state.infrastructureFocus.category === category ? "" : category;
      state.infrastructureFocus.label = INFRASTRUCTURE_CATEGORY_META[category]?.label || "";
      renderInfrastructurePanel();
      renderMap();
    });
  });
}

function socCategoryDisplayData(selected, category) {
  const soc = selected.socSummary || {};
  const evidence = selected.evidence || {};
  const counts = soc.counts || {};
  const categoryCounts = soc.categoryCounts || soc.countsByCategory || evidence.socCategoryCounts || {};
  const definition = SOC_CATEGORY_DEFINITIONS[category] || {};
  const aliases = definition.aliases || [category];
  const { count, hasValue } = socCountFromAliases([categoryCounts, counts, evidence.socCounts], aliases);
  const nearest = aliases
    .map((key) => soc.nearestFacilities?.[key])
    .find(Boolean) || null;
  return { count, hasValue, nearest };
}

function renderInfrastructurePanel() {
  if (!nodes.infrastructureContent) return;
  const selected = selectedInfrastructureItem();
  if (!selected) {
    nodes.infrastructureContent.innerHTML = `<div class="callout"><p>아파트를 선택하면 주변 인프라를 확인할 수 있습니다.</p></div>`;
    return;
  }

  if (state.detailPanelOpen && state.detailSubpanelTab === "infrastructure") {
    ensureLiveInfrastructure(selected);
    ensureLiveSafety(selected);
    ensureLiveAir(selected);
    ensureLiveCctv(selected);
  }
  const liveState = liveInfrastructureStateFor(selected);
  const liveData = liveInfrastructureDataFor(selected);
  const liveSafetyState = liveSafetyStateFor(selected);
  const liveSafetyData = liveSafetyDataFor(selected);
  const liveAirState = liveAirStateFor(selected);
  const liveAir = liveAirDataFor(selected);
  const liveCctvState = liveCctvStateFor(selected);
  const liveCctv = liveCctvDataFor(selected);
  const soc = selected.socSummary || {};
  const safety = selected.safetyEnvSummary || {};
  const safetyCounts = safety.counts || {};
  const safetyNearest = safety.nearestFacilities || {};
  const isSocLoading = Boolean(liveState?.isLoading && !liveData);
  const isSafetyLoading = Boolean(liveSafetyState?.isLoading && !liveSafetyData);
  const isAirLoading = Boolean(liveAirState?.isLoading && !liveAir);
  const isCctvLoading = Boolean(liveCctvState?.isLoading && !liveCctv);
  const socDisplay = (category) => {
    const label = SOC_CATEGORY_DEFINITIONS[category]?.label || category;
    if (isSocLoading) {
      return infrastructureItem(label, "불러오는 중", { name: "카카오 API 조회 중" }, category);
    }
    const data = liveSocCategoryDisplayData(selected, category) || socCategoryDisplayData(selected, category);
    return infrastructureItem(
      label,
      data.hasValue ? `${formatNumber(data.count)}개` : "정보 없음",
      data.nearest,
      category
    );
  };
  const socNote = liveData
    ? "아파트 기준 반경 1km에 존재하는 생활 SOC 입니다."
    : liveState?.isLoading
      ? `카카오 장소 검색으로 반경 ${formatDistance(KAKAO_SOC_RADIUS_METERS)} 공공성 높은 생활 SOC를 불러오는 중입니다.`
      : liveState?.data?.mode === "missing_key"
        ? "카카오 API 키가 없어 기존 공공 기준 인프라를 표시합니다."
        : liveState?.error
          ? "카카오 장소 검색에 실패해 기존 공공 기준 인프라를 표시합니다."
          : `${selected.livingArea?.name || "인근 생활권"} 기준 인프라입니다.`;
  const livePolice = liveSafetyCategoryDisplayData(selected, "police");
  const liveGreen = liveSafetyCategoryDisplayData(selected, "green");
  const policeItem = isSafetyLoading
    ? infrastructureItem("치안시설", "불러오는 중", { name: "카카오 API 조회 중" }, "police")
    : infrastructureItem(
      "치안시설",
      livePolice ? `${formatNumber(livePolice.count)}개` : `${formatNumber(safetyCounts.police)}개`,
      livePolice?.nearest || safetyNearest.police,
      "police"
    );
  const greenItem = isSafetyLoading
    ? infrastructureItem("녹지 접근", "불러오는 중", { name: "카카오 API 조회 중" }, "green")
    : infrastructureItem(
      "녹지 접근",
      liveGreen?.nearest ? `${formatNumber(greenAccessScoreFromDistance(liveGreen.nearest.distanceMeters))}점` : `${formatNumber(safety.greenScore)}점`,
      liveGreen?.nearest || safetyNearest.park,
      "green"
    );
  const airItem = isAirLoading
    ? infrastructureItem("대기환경", "불러오는 중", { name: "서울시 API 조회 중" }, "air")
    : liveAir
      ? infrastructureItem(
        "대기환경",
        `${formatNumber(liveAir.score)}점`,
        {
          name: liveAir.nearest?.name || `${liveAir.station || districtNameForAir(selected)} 대기측정소`,
          description: airDescription(liveAir)
        },
        "air"
      )
      : infrastructureItem(
        "대기환경",
        `${formatNumber(safety.airQualityScore)}점`,
        safety.airStation ? { name: safety.airStation } : null,
        "air"
      );
  const cctvItem = isCctvLoading
    ? infrastructureItem("CCTV", "불러오는 중", { name: "공공데이터포털 조회 중" }, "cctv")
    : liveCctv
      ? infrastructureItem(
        "CCTV",
        `${formatNumber(liveCctv.siteCount)}개 지점`,
        {
          ...(liveCctv.nearest || {}),
          description: cctvDescription(liveCctv)
        },
        "cctv"
      )
      : infrastructureItem("CCTV", `${formatNumber(safetyCounts.cctv)}대`, safetyNearest.cctv, "cctv");

  nodes.infrastructureContent.innerHTML = `
    <section class="infrastructure-category">
      <div class="infrastructure-category-title">생활 SOC</div>
      <p class="infrastructure-note">${escapeHtml(socNote)}</p>
      <div class="infrastructure-list">
        ${socDisplay("medical")}
        ${socDisplay("transport")}
        ${socDisplay("convenience")}
        ${socDisplay("education")}
        ${socDisplay("leisure")}
        ${socDisplay("welfare")}
      </div>
    </section>

    <section class="infrastructure-category">
      <div class="infrastructure-category-title">안전</div>
      <div class="infrastructure-list">
        ${policeItem}
        ${cctvItem}
        ${airItem}
        ${greenItem}
      </div>
    </section>
  `;
  bindInfrastructurePanelEvents();
}

function resetRouteState() {
  const transportMode = state.route.transportMode || DEFAULT_ROUTE_TRANSPORT_MODE;
  state.routeRequestId += 1;
  state.aiCommute.requestId += 1;
  state.aiCommute = {
    selectedId: null,
    requestId: state.aiCommute.requestId,
    isLoading: false,
    result: null,
    error: ""
  };
  state.route = {
    selectedId: null,
    isLoading: false,
    result: null,
    error: "",
    focusMap: false,
    transportMode
  };
  if (state.map?.routeLayer) {
    state.map.routeLayer.clearLayers();
  }
}

async function ensureAiSummaryCommuteRoute(selected) {
  if (!selected?.id || state.aiCommute.selectedId === selected.id || state.aiCommute.isLoading) return;

  const origin = representativeAddressFor(selected);
  const destinationLocation = selectedDestinationLocation();
  const destinationAddress = destinationLocation?.address || state.destinationQuery.trim() || destinationAddressFor();
  const destination = destinationCoordinatesForRequest();
  if (!origin || !destinationAddress || !destination) {
    state.aiCommute = { selectedId: selected.id, requestId: state.aiCommute.requestId + 1, isLoading: false, result: null, error: "통근 좌표 없음" };
    return;
  }

  const requestId = state.aiCommute.requestId + 1;
  state.aiCommute = { selectedId: selected.id, requestId, isLoading: true, result: null, error: "" };
  const params = new URLSearchParams({
    origin,
    provider: "tmap",
    transportMode: "car",
    destinationAddress,
    destinationLat: destination.lat,
    destinationLng: destination.lng
  });
  if (state.destinationQuery.trim()) {
    params.set("destinationQuery", state.destinationQuery.trim());
  }

  try {
    const payload = await fetchJson(`/api/commute-route?${params.toString()}`);
    if (requestId !== state.aiCommute.requestId) return;
    state.aiCommute = { selectedId: selected.id, requestId, isLoading: false, result: payload, error: "" };
  } catch (error) {
    if (requestId !== state.aiCommute.requestId) return;
    state.aiCommute = { selectedId: selected.id, requestId, isLoading: false, result: null, error: error.message };
  }
  renderDetail();
}

async function calculateCommuteRoute(selected, options = {}) {
  const destinationInput = document.querySelector("#routeDestinationInput");
  if (!destinationInput) return;

  const transportMode = options.transportMode || state.route.transportMode || DEFAULT_ROUTE_TRANSPORT_MODE;
  const requestId = state.routeRequestId + 1;
  state.routeRequestId = requestId;
  const origin = representativeAddressFor(selected);
  const destinationText = destinationInput.value.trim();
  const destinationValidation = validateDestinationInput(destinationText, state.destinationLocation);
  if (!destinationValidation.ok) {
    state.route = { selectedId: selected.id, isLoading: false, result: null, error: destinationValidation.message, focusMap: false, transportMode };
    state.locationSearch.open = true;
    state.locationSearch.target = "route";
    requestLocationSuggestions(destinationText, "route");
    renderRoutePanel();
    return;
  }
  const destinationLocation = selectedDestinationLocation();
  const params = new URLSearchParams({
    origin,
    provider: "tmap",
    transportMode,
    destinationAddress: destinationLocation?.address || destinationText
  });
  const destination = destinationCoordinatesForRequest();
  if (destination) {
    params.set("destinationLat", destination.lat);
    params.set("destinationLng", destination.lng);
  }

  if (!origin) {
    state.route = { selectedId: selected.id, isLoading: false, result: null, error: "아파트 주소를 확인할 수 없습니다.", focusMap: false, transportMode };
    renderRoutePanel();
    return;
  }
  if (destinationText) {
    params.set("destinationQuery", destinationText);
  } else {
    params.set("destination", state.destination);
  }

  state.route = { selectedId: selected.id, isLoading: true, result: null, error: "", focusMap: false, transportMode };
  state.map?.routeLayer?.clearLayers();
  renderRoutePanel();

  try {
    const payload = await fetchJson(`/api/commute-route?${params.toString()}`);
    if (requestId !== state.routeRequestId) return;
    state.route = { selectedId: selected.id, isLoading: false, result: payload, error: "", focusMap: true, transportMode };
    if (state.map) {
      state.map.fitted = false;
    }
    render();
  } catch (error) {
    if (requestId !== state.routeRequestId) return;
    state.route = {
      selectedId: selected.id,
      isLoading: false,
      result: null,
      error: `경로 계산 실패: ${error.message}`,
      focusMap: false,
      transportMode
    };
    renderRoutePanel();
  }
}

function bindRoutePlanner(selected) {
  const destinationInput = document.querySelector("#routeDestinationInput");
  const mapButton = document.querySelector("[data-route-map]");
  const transportButtons = document.querySelectorAll("[data-route-transport]");

  destinationInput?.addEventListener("input", (event) => {
    state.destinationQuery = event.target.value;
    state.destinationLocation = null;
    if (state.destinationQuery.trim()) {
      state.destination = inferDestinationKey(state.destinationQuery);
    }
    if (nodes.destinationInput) {
      nodes.destinationInput.value = state.destinationQuery;
    }
    requestLocationSuggestions(state.destinationQuery, "route");
  });

  destinationInput?.addEventListener("focus", () => {
    if (destinationInput.value.trim()) {
      state.locationSearch.open = true;
      state.locationSearch.target = "route";
      requestLocationSuggestions(destinationInput.value, "route");
    }
  });

  destinationInput?.addEventListener("blur", () => {
    window.setTimeout(hideLocationSuggestions, 120);
  });

  destinationInput?.addEventListener("change", () => calculateCommuteRoute(selected));
  destinationInput?.addEventListener("keydown", (event) => {
    if (event.key !== "Enter") return;
    event.preventDefault();
    calculateCommuteRoute(selected);
  });

  transportButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const transportMode = button.dataset.routeTransport;
      const sameRoute = state.route.selectedId === selected.id
        && state.route.transportMode === transportMode
        && state.route.result;
      if (sameRoute) {
        focusRouteOnMap();
        return;
      }
      calculateCommuteRoute(selected, { transportMode });
    });
  });

  mapButton?.addEventListener("click", () => {
    if (state.map) {
      focusRouteOnMap();
    }
  });

  bindLocationSuggestionList("route");
  renderLocationSuggestions("route");
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
      <td>아파트 후보 ${state.apartmentCandidates.length}개</td>
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

function cancelApartmentLayerWork() {
  window.clearTimeout(state.apartments.timer);
  state.apartments.requestId += 1;
  state.apartments.isLoading = false;
  state.map?.apartmentLayer?.clearLayers();
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

function normalizeBudgetValue(value) {
  const config = budgetConfig();
  const min = Number(nodes.budgetInput?.min || config.min);
  const max = Number(nodes.budgetInput?.max || config.max);
  const step = Number(nodes.budgetInput?.step || config.step);
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return state.budget;
  return clamp(Math.round(numeric / step) * step, min, max);
}

function syncBudgetModeControls() {
  const config = budgetConfig();
  if (nodes.budgetLabel) nodes.budgetLabel.textContent = config.label;
  if (nodes.budgetUnit) nodes.budgetUnit.textContent = config.unit;
  if (nodes.budgetInput) {
    nodes.budgetInput.min = config.min;
    nodes.budgetInput.max = config.max;
    nodes.budgetInput.step = config.step;
  }
  if (nodes.budgetOutput) {
    nodes.budgetOutput.min = config.min / Number(config.displayScale || 1);
    nodes.budgetOutput.max = config.max / Number(config.displayScale || 1);
    nodes.budgetOutput.step = config.displayStep || config.step;
    nodes.budgetOutput.setAttribute("aria-label", config.label);
  }
  document.querySelectorAll('input[name="budgetMode"]').forEach((input) => {
    input.checked = input.value === state.budgetMode;
  });
}

function setBudgetMode(mode, { refresh = true } = {}) {
  if (!BUDGET_MODE_CONFIG[mode]) return;
  state.budgetMode = mode;
  state.budget = budgetConfig(mode).defaultValue;
  syncBudgetModeControls();
  setBudget(state.budget, { refresh });
}

function setBudget(value, { syncTextInput = true, refresh = true } = {}) {
  state.budget = normalizeBudgetValue(value);
  if (nodes.budgetInput) nodes.budgetInput.value = state.budget;
  if (syncTextInput && nodes.budgetOutput) nodes.budgetOutput.value = displayBudgetValue(state.budget);
  syncRangeProgress(nodes.budgetInput);
  if (refresh) scheduleRefresh();
}

function syncWeightInputs() {
  if (nodes.commuteWeight) nodes.commuteWeight.value = state.weights.commute;
  if (nodes.costWeight) nodes.costWeight.value = state.weights.cost;
  if (nodes.serviceWeight) nodes.serviceWeight.value = state.weights.service;
  if (nodes.safetyWeight) nodes.safetyWeight.value = state.weights.safety;
  syncAllRangeProgress();
}

function applyPersonaDefaultWeights(persona) {
  state.weights = {
    ...(PERSONA_DEFAULT_WEIGHTS[persona] || PERSONA_DEFAULT_WEIGHTS.single)
  };
  syncWeightInputs();
}

function renderControls() {
  syncBudgetModeControls();
  if (nodes.budgetOutput && document.activeElement !== nodes.budgetOutput) {
    nodes.budgetOutput.value = displayBudgetValue(state.budget);
  }
  nodes.commuteWeightOutput.textContent = `${state.weights.commute}%`;
  nodes.costWeightOutput.textContent = `${state.weights.cost}%`;
  nodes.serviceWeightOutput.textContent = `${state.weights.service}%`;
  nodes.safetyWeightOutput.textContent = `${state.weights.safety}%`;
  if (nodes.candidateCount) {
    nodes.candidateCount.textContent = state.apiMeta?.totalCandidates || state.apartmentCandidates.length;
  }
  if (nodes.destinationInput && nodes.destinationInput.value !== state.destinationQuery) {
    nodes.destinationInput.value = state.destinationQuery;
  }
  if (nodes.destinationClearButton) {
    nodes.destinationClearButton.hidden = !String(state.destinationQuery || nodes.destinationInput?.value || "").trim();
  }
  if (nodes.matchButton) {
    nodes.matchButton.disabled = state.isLoading || !state.neighborhoods.length || !state.apartmentCandidates.length;
    nodes.matchButton.textContent = state.isLoading ? "매칭 중" : "매칭하기";
  }
  syncAllRangeProgress();
  renderLocationSuggestions("main");

  nodes.resultSummary.textContent = "";

  nodes.updatedAt.textContent = state.isLoading ? "매칭 계산 중…" : "";
}

function render() {
  renderControls();
  renderApiStatus();
  renderMap();
  renderMapSidebar();
  renderMapRouteChip();
  renderPropertyDashboard();
  renderBookmarkPanel();
  renderCards();
  renderDetail();
  renderRoutePanel();
  renderInfrastructurePanel();
  renderJeonseRiskPanel();
  renderDetailSubpanelState();
  renderEvidenceTable();
  renderAgentPanel();
}

function selectApartmentMatch(id, options = {}) {
  const changed = state.selectedId !== id;
  const panelWasOpen = state.detailPanelOpen;
  const shouldResetRoute = options.resetRoute ?? ["card", "map", "route"].includes(options.source);
  if (state.selectedId !== id || shouldResetRoute) {
    resetRouteState();
  }
  if (changed && state.property.selectedId) {
    state.property.selectedId = null;
    state.property.detail = null;
    state.property.error = "";
    state.property.isLoading = false;
  state.property.agentAnswer = null;
  state.property.agentError = "";
  state.property.trendMode = state.budgetMode === "sale" ? "sale" : "rent";
  state.property.requestId += 1;
  }
  state.selectedId = id;

  const rank = state.results.findIndex((item) => item.id === id);
  if (rank >= CARD_PREVIEW_COUNT && !state.showAllCards) {
    state.showAllCards = true;
  }

  if (options.openDetailPanel) {
    state.detailPanelOpen = true;
    if (changed || !panelWasOpen) state.detailSubpanelTab = "matching";
  }

  render();
  if (options.openDetailPanel) {
    selectProperty(id);
  }
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
  state.budget = 0;
  state.budgetMode = "monthly";
  state.destination = "gangnam";
  state.destinationQuery = "";
  state.destinationLocation = null;
  state.persona = "single";
  state.weights = { ...PERSONA_DEFAULT_WEIGHTS.single };
  state.results = [];
  state.selectedId = null;
  state.showAllCards = false;
  state.detailPanelOpen = false;
  state.detailSubpanelTab = "matching";
  state.hasMatched = false;
  state.matchValidationMessage = "";
  state.isLoading = false;
  state.apartments.enabled = true;
  state.apartments.labelMode = "sale";
  state.apartments.lastKey = "";
  state.property.selectedId = null;
  state.property.detail = null;
  state.property.error = "";
  state.bookmarks.panelOpen = false;
  state.evidenceRendered = false;
  state.locationSearch.open = false;
  state.locationSearch.items = [];
  state.locationSearch.error = "";
  state.locationSearch.isLoading = false;

  syncBudgetModeControls();
  nodes.budgetInput.value = state.budget;
  nodes.budgetOutput.value = displayBudgetValue(state.budget);
  nodes.destinationInput.value = state.destinationQuery;
  document.querySelector("input[name='persona'][value='single']").checked = true;
  syncWeightInputs();
  if (nodes.apartmentLayerToggle) nodes.apartmentLayerToggle.checked = true;
  if (nodes.mapLabelModeInput) nodes.mapLabelModeInput.value = "sale";
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
  resetMapToSeoul();

  try {
    await loadAreas();
    await loadApartmentCandidates();
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

function bindSidebarResize() {
  const handle = nodes.sidebarResizeHandle;
  if (!handle) return;

  let activePointerId = null;

  const resizeTo = (clientX, persist = false) => {
    setSidebarWidth(clientX, { persist });
  };

  handle.addEventListener("pointerdown", (event) => {
    if (window.innerWidth <= 860) return;
    activePointerId = event.pointerId;
    handle.setPointerCapture?.(event.pointerId);
    document.querySelector(".workspace")?.classList.add("is-resizing-sidebar");
    resizeTo(event.clientX);
    event.preventDefault();
  });

  handle.addEventListener("pointermove", (event) => {
    if (activePointerId !== event.pointerId) return;
    resizeTo(event.clientX);
  });

  const finishResize = (event) => {
    if (activePointerId !== event.pointerId) return;
    activePointerId = null;
    handle.releasePointerCapture?.(event.pointerId);
    document.querySelector(".workspace")?.classList.remove("is-resizing-sidebar");
    resizeTo(event.clientX, true);
  };

  handle.addEventListener("pointerup", finishResize);
  handle.addEventListener("pointercancel", finishResize);

  handle.addEventListener("keydown", (event) => {
    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
    const current = Number.parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--sidebar-width")) || 540;
    const { min, max } = sidebarWidthBounds();
    const step = event.shiftKey ? 40 : 16;
    if (event.key === "ArrowLeft") setSidebarWidth(current - step, { persist: true });
    if (event.key === "ArrowRight") setSidebarWidth(current + step, { persist: true });
    if (event.key === "Home") setSidebarWidth(min, { persist: true });
    if (event.key === "End") setSidebarWidth(max, { persist: true });
    event.preventDefault();
  });
}

function bindEvents() {
  bindSidebarResize();

  nodes.budgetInput.addEventListener("input", (event) => {
    setBudget(event.target.value);
  });

  document.querySelectorAll('input[name="budgetMode"]').forEach((input) => {
    input.addEventListener("change", (event) => {
      setBudgetMode(event.target.value);
    });
  });

  nodes.budgetOutput.addEventListener("input", (event) => {
    const nextValue = parseBudgetDisplayValue(event.target.value);
    if (!Number.isFinite(nextValue)) return;
    state.budget = normalizeBudgetValue(nextValue);
    nodes.budgetInput.value = state.budget;
    syncRangeProgress(nodes.budgetInput);
    scheduleRefresh();
  });

  nodes.budgetOutput.addEventListener("focus", (event) => {
    if (Number(event.target.value) === 0) {
      event.target.value = "";
    }
  });

  nodes.budgetOutput.addEventListener("change", (event) => {
    setBudget(parseBudgetDisplayValue(event.target.value));
  });

  nodes.budgetOutput.addEventListener("blur", (event) => {
    setBudget(parseBudgetDisplayValue(event.target.value), { refresh: false });
  });

  const updateDestinationFromInput = (value, delay = 180) => {
    const query = String(value || "");
    const normalizedQuery = query.trim();
    state.destinationQuery = query;
    state.destinationLocation = null;
    if (normalizedQuery) {
      state.destination = inferDestinationKey(normalizedQuery);
    }
    state.apartments.lastKey = "";
    resetRouteState();
    requestLocationSuggestions(query, "main");
    scheduleRefresh(delay);
    if (nodes.destinationClearButton) nodes.destinationClearButton.hidden = !normalizedQuery;
    if (state.apartments.enabled) {
      scheduleApartmentLayerLoad(true);
    }
  };

  nodes.destinationInput.addEventListener("input", (event) => {
    updateDestinationFromInput(event.target.value, 220);
  });

  nodes.destinationInput.addEventListener("focus", () => {
    if (nodes.destinationInput.value.trim()) {
      state.locationSearch.open = true;
      state.locationSearch.target = "main";
      requestLocationSuggestions(nodes.destinationInput.value, "main");
    }
  });

  nodes.destinationInput.addEventListener("blur", () => {
    window.setTimeout(hideLocationSuggestions, 120);
  });

  nodes.destinationInput.addEventListener("change", (event) => {
    updateDestinationFromInput(event.target.value, 0);
  });

  nodes.destinationClearButton?.addEventListener("click", clearDestinationInput);

  bindLocationSuggestionList("main");

  document.querySelectorAll("input[name='persona']").forEach((radio) => {
    radio.addEventListener("change", (event) => {
      if (event.target.checked) {
        state.persona = event.target.value;
        applyPersonaDefaultWeights(state.persona);
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
    if (!nodes.destinationInput.value.trim()) {
      state.destinationQuery = "";
      state.destinationLocation = null;
      nodes.destinationInput.value = "";
      state.hasMatched = false;
      state.matchValidationMessage = "주소를 입력해주세요.";
      state.results = [];
      state.selectedId = null;
      state.showAllCards = false;
      state.detailPanelOpen = false;
      render();
      nodes.destinationInput.focus();
      return;
    }

    const destinationValidation = validateDestinationInput(nodes.destinationInput.value, state.destinationLocation);
    if (!destinationValidation.ok) {
      state.hasMatched = false;
      state.matchValidationMessage = destinationValidation.message;
      state.results = [];
      state.selectedId = null;
      state.showAllCards = false;
      state.detailPanelOpen = false;
      state.locationSearch.open = true;
      state.locationSearch.target = "main";
      requestLocationSuggestions(nodes.destinationInput.value, "main");
      render();
      nodes.destinationInput.focus();
      return;
    }

    state.matchValidationMessage = "";
    window.clearTimeout(state.refreshTimer);
    state.showAllCards = false;
    state.detailPanelOpen = false;
    state.detailSubpanelTab = "matching";
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

  const subpanelTabs = [...(nodes.detailSubpanel?.querySelectorAll("[data-subpanel-tab]") || [])];
  subpanelTabs.forEach((button, index) => {
    button.addEventListener("click", () => {
      activateDetailSubpanelTab(button.dataset.subpanelTab);
    });
    button.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight"].includes(event.key)) return;
      event.preventDefault();
      const direction = event.key === "ArrowRight" ? 1 : -1;
      const next = subpanelTabs[(index + direction + subpanelTabs.length) % subpanelTabs.length];
      activateDetailSubpanelTab(next.dataset.subpanelTab);
      next.focus();
    });
  });

  [nodes.closeSubpanelButton, nodes.subpanelCloseXButton].forEach((button) => {
    button?.addEventListener("click", () => {
      state.detailPanelOpen = false;
      renderDetailSubpanelState();
      renderMap();
    });
  });

  nodes.refreshButton?.addEventListener("click", () => {
    refreshAllData();
  });

  nodes.bookmarkPanelButton?.addEventListener("click", () => {
    if (state.bookmarks.panelOpen) {
      closeBookmarkPanel();
    } else {
      openBookmarkPanel();
    }
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

}

async function init() {
  loadBookmarksFromStorage();
  restoreSidebarWidth();
  bindEvents();
  bindAgentPanelEvents();
  initNavigation();
  render();
  await loadAreas();
  await loadApartmentCandidates();
  render();
}

init().catch((error) => {
  nodes.cards.innerHTML = `<div class="empty-state">데이터를 불러오지 못했습니다.</div>`;
  nodes.detailContent.innerHTML = `<div class="callout"><p>데이터를 불러오지 못했습니다: ${error.message}</p></div>`;
});
