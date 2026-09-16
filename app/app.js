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
const MAP_MODES = ["normal", "sunlight"];
const SUNLIGHT_3D_BUILDING_LIMIT = 140;
const SUNLIGHT_3D_WORLD_SCALE = 12;
const RULE_SUMMARY_COMMUTE_THRESHOLD_MINUTES = 45;
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
    label: "여가",
    aliases: ["leisure", "park", "trail", "sports", "gym"],
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
  monthly: { label: "월 주거 예산", shortLabel: "월세", min: 0, max: 400, step: 1, defaultValue: 0, unit: "만원", displayScale: 1, displayStep: 1 },
  jeonse: { label: "전세 예산", shortLabel: "전세", min: 0, max: 200000, step: 1000, defaultValue: 0, unit: "억", displayScale: 10000, displayStep: 0.1 },
  sale: { label: "매매 예산", shortLabel: "매매", min: 0, max: 400000, step: 1000, defaultValue: 0, unit: "억", displayScale: 10000, displayStep: 0.1 }
};
const WEIGHT_AXES = ["commute", "cost", "service", "safety"];
const VOICE_WEIGHT_RULES = [
  {
    key: "commute",
    label: "통근",
    keywords: ["통근", "출퇴근", "출근", "퇴근", "직장", "회사", "교통", "대중교통", "지하철", "버스", "정류장", "역세권", "역 근처", "역 가까운", "회사 근처", "직장 근처", "이동", "가까운", "가까웠으면", "근처", "빠른", "빨리", "시간", "덜 걸리는", "안 막히는", "환승", "차로", "자동차"]
  },
  {
    key: "cost",
    label: "주거비",
    keywords: ["예산", "월세", "전세", "매매", "보증금", "가격", "돈", "비용", "주거비", "관리비", "저렴", "저렴한", "저렴했으면", "저렴하면", "저렴한 곳", "싼", "싼 곳", "싼데", "싼곳", "싸", "싸게", "싸면", "싸고", "쌌", "쌌으면", "합리적", "가성비", "아끼", "아낄", "절약", "부담", "부담없는", "대출"]
  },
  {
    key: "service",
    label: "생활 SOC",
    keywords: ["생활", "생활권", "인프라", "주변", "주변에", "많았으면", "많으면", "가까웠으면", "편의", "편의시설", "편의점", "마트", "상권", "카페", "병원", "의료", "약국", "학교", "교육", "학원", "어린이집", "유치원", "아이", "아기", "자녀", "공원", "산책", "운동", "복지", "문화", "시장"]
  },
  {
    key: "safety",
    label: "안전",
    keywords: ["안전", "안전한", "안전했으면", "안심", "치안", "위험", "위험하지", "범죄", "cctv", "씨씨티비", "전세사기", "전세 사기", "깡통", "사기", "등기", "권리", "보증보험", "환경", "대기", "공기", "조용", "밤길", "밝은", "여성", "경찰", "파출소"]
  }
];
const VOICE_PHRASE_RULES = [
  { pattern: /가격.{0,8}(싸|쌌|저렴|낮|부담|가성비)|싸.{0,8}(좋|원|곳|집)|저렴.{0,8}(좋|원|곳|집)|예산.{0,8}(맞|안|내|초과|부담)/, weights: { cost: 5 } },
  { pattern: /월세|전세|매매|보증금|관리비|주거비|대출/, weights: { cost: 3 } },
  { pattern: /회사|직장|출근|퇴근|출퇴근|통근/, weights: { commute: 4 } },
  { pattern: /역세권|지하철|버스|정류장|환승|대중교통|교통/, weights: { commute: 3, service: 1 } },
  { pattern: /가까.{0,8}(회사|직장|역|지하철|버스|정류장|목적지)|회사.{0,8}가까|직장.{0,8}가까|역.{0,8}가까/, weights: { commute: 4 } },
  { pattern: /편의점|마트|카페|상권|시장|병원|약국|학교|학원|어린이집|유치원|공원|산책|운동|복지|문화/, weights: { service: 4 } },
  { pattern: /주변.{0,10}(많|편의|인프라|시설|마트|병원|학교|공원)|생활권|생활.{0,8}(편|좋)/, weights: { service: 4 } },
  { pattern: /안전|안심|치안|밤길|범죄|cctv|씨씨티비|경찰|파출소|밝은/, weights: { safety: 4 } },
  { pattern: /전세.{0,8}(사기|안전|위험)|깡통|등기|권리|보증보험|근저당|압류/, weights: { safety: 5, cost: 1 } },
  { pattern: /조용|쾌적|공기|대기|환경|깨끗/, weights: { safety: 2, service: 2 } }
];
const VOICE_STT_CORRECTIONS = [
  [/썼으면|썻으면|쓸면|섰으면|썻음|썼음/g, "쌌으면"],
  [/가격이\s*(썼|썻|섰|쓸)/g, "가격이 쌌"],
  [/싸\s*슴|싸슴|쌓|쌋/g, "쌌"],
  [/편의\s*점|펴니점|편이점|편의전|편의 정/g, "편의점"],
  [/마트가|마트는/g, "마트"],
  [/병원이|병원은/g, "병원"],
  [/공원이|공원은/g, "공원"],
  [/시안|취안/g, "치안"],
  [/씨씨\s*티비|시시티비|씨시티비|c\s*c\s*t\s*v/g, "cctv"],
  [/전세\s*사끼|전세\s*사귀/g, "전세 사기"],
  [/깡통\s*주택|깡통집/g, "깡통"],
  [/총근|충근|통근이/g, "통근"],
  [/출근이|퇴근이/g, "출근 퇴근"],
  [/지하철이|지하철은/g, "지하철"],
  [/버스가|버스는/g, "버스"],
  [/정류장이|정류장은/g, "정류장"],
  [/가까우면|가까우면은|가까우면좋|가까우면 좋/g, "가까웠으면 좋"],
  [/많으면|많으면은|많으면좋|많으면 좋/g, "많았으면 좋"],
  [/골구루|골고로|고루고루/g, "골고루"],
  [/균형적|균형적인|균형잡힌|균형 잡힌|벨런스|밸런스/g, "균형"]
];
const VOICE_CONTEXT_RULES = [
  { pattern: /혼자|1인|원룸|오피스텔|사회초년|대학생|취준|자취/, weights: { commute: 1, cost: 2, safety: 1 } },
  { pattern: /신혼|부부|결혼|배우자|둘이/, weights: { cost: 1, service: 2, safety: 1 } },
  { pattern: /가족|애들|아이|아기|자녀|초등|중등|고등|등하교|학군|학교/, weights: { service: 3, safety: 2 } },
  { pattern: /부모님|어머니|아버지|어르신|노인|고령|병원|약국|의료/, weights: { service: 3, safety: 2, commute: 1 } },
  { pattern: /야근|늦게|밤|새벽|혼자\s*귀가|퇴근이\s*늦|밤길/, weights: { safety: 3, commute: 2 } },
  { pattern: /재택|집에\s*있는|동네|생활권|살기\s*좋|살기좋|쾌적|조용|깨끗/, weights: { service: 2, safety: 2 } },
  { pattern: /차\s*없|뚜벅|대중교통|환승|역|정류장|버스|지하철/, weights: { commute: 3, service: 1 } },
  { pattern: /차\s*있|운전|주차|자동차/, weights: { commute: 2, service: 1 } },
  { pattern: /대출|돈이\s*없|여유가\s*없|아껴|부담|월급|가성비|최대한\s*싸|저렴|싼/, weights: { cost: 3 } },
  { pattern: /전세|보증금|계약|등기|권리|깡통|사기|위험/, weights: { safety: 3, cost: 1 } },
  { pattern: /공원|산책|운동|헬스|문화|카페|마트|시장|상권|편의/, weights: { service: 3 } },
  { pattern: /추천|찾아|골라|보고\s*싶|좋은\s*곳|괜찮은\s*곳|살\s*곳|집|아파트/, weights: { commute: 1, cost: 1, service: 1, safety: 1 } }
];
const VOICE_PERSONA_FALLBACK_SCORES = {
  single: { commute: 2, cost: 3, service: 1, safety: 2 },
  newlywed: { commute: 2, cost: 2, service: 3, safety: 2 },
  family: { commute: 1, cost: 2, service: 4, safety: 3 },
  senior: { commute: 1, cost: 2, service: 4, safety: 4 }
};
const VOICE_LISTENING_MAX_MS = 18000;
const VOICE_SILENCE_SETTLE_MS = 3000;
let agentHintTimer = null;

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
  ruleSummaryRouteRequestId: 0,
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
  ruleSummaryRoute: {
    selectedId: null,
    isLoading: false,
    result: null,
    error: ""
  },
  mapMode: "normal",
  sunlightMinutes: currentDayMinutes(),
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
    agentError: ""
  },
  agent: {
    open: false,
    messages: [],
    followUps: [],
    targetId: null,
    targetName: "",
    isLoading: false,
    error: "",
    llmMode: null,
    llmReason: "",
    llmModel: ""
  },
  bookmarks: {
    ids: [],
    details: {},
    panelOpen: false,
    isLoading: false,
    error: ""
  },
  voiceWeights: {
    recognition: null,
    listening: false,
    status: "",
    transcript: "",
    settleTimer: null,
    maxTimer: null,
    errorStatus: ""
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
  cost: "선택한 예산 기준 대비 추정 가격을 반영한 주거비 점수",
  service: "의료·교통·생활편의·교육·여가복지·복지시설을 가구 유형별 비중으로 합산한 생활 SOC 점수",
  safety: "치안·환경 접근성과 단지 전세 위험 신호를 결합한 안전 점수"
};

const nodes = {
  main: document.querySelector("main"),
  budgetLabel: document.querySelector("#budgetLabel"),
  budgetInput: document.querySelector("#budgetInput"),
  budgetOutput: document.querySelector("#budgetOutput"),
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
  voiceWeightButton: document.querySelector("#voiceWeightButton"),
  voiceWeightStatus: document.querySelector("#voiceWeightStatus"),
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
  sunlight3dCanvas: document.querySelector("#sunlight3dCanvas"),
  sunlight3dCompass: document.querySelector("#sunlight3dCompass"),
  mapModeControl: document.querySelector(".map-mode-control"),
  mapModeButtons: document.querySelectorAll("[data-map-mode]"),
  sunlightTimeControl: document.querySelector("#sunlightTimeControl"),
  sunlightNowButton: document.querySelector("#sunlightNowButton"),
  sunlightTimeInput: document.querySelector("#sunlightTimeInput"),
  sunlightTimeOutput: document.querySelector("#sunlightTimeOutput"),
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

const sunlight3d = {
  initialized: false,
  failed: false,
  renderer: null,
  scene: null,
  camera: null,
  cameraTarget: null,
  sunLight: null,
  hemisphereLight: null,
  mapGround: null,
  fallbackOverlayGroup: null,
  mapTextureRequestId: 0,
  mapCenterKey: "",
  windowTexture: null,
  windowFacades: [],
  cityGroup: null,
  buildingMeshes: [],
  sceneSignature: "",
  radius: 620,
  theta: 0,
  phi: Math.PI * 0.31,
  dragging: false,
  moved: false,
  pointerX: 0,
  pointerY: 0,
  resizeObserver: null
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
    resizeSunlight3dRenderer();
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

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function speechRecognitionConstructor() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null;
}

function compactVoiceText(value) {
  return String(value || "").toLowerCase().replace(/\s+/g, "");
}

function normalizeVoiceIntentText(value) {
  let text = String(value || "").toLowerCase();
  VOICE_STT_CORRECTIONS.forEach(([pattern, replacement]) => {
    text = text.replace(pattern, replacement);
  });
  return text.replace(/\s+/g, " ").trim();
}

function voiceIntentDisplayText(value) {
  return normalizeVoiceIntentText(value) || String(value || "").trim();
}

function voiceStatusDisplayText(value) {
  const text = String(value || "");
  if (text.startsWith("인식:")) {
    return `인식: ${voiceIntentDisplayText(text.slice(3))}`;
  }
  if (text.startsWith("듣는 중...")) {
    return `듣는 중... ${voiceIntentDisplayText(text.slice(7))}`;
  }
  return text;
}

function isBalancedVoiceIntent(value) {
  const text = normalizeVoiceIntentText(value);
  const compactText = compactVoiceText(text);
  return /골고루|균형|밸런스|전체적으로|고르게|무난|다\s*중요|모두\s*중요|전부\s*중요|비슷하게|반반/.test(text)
    || /골고루|균형|밸런스|전체적으로|고르게|무난|다중요|모두중요|전부중요|비슷하게|반반/.test(compactText);
}

function directlyMentionedVoiceAxes(value) {
  const text = normalizeVoiceIntentText(value);
  const compactText = compactVoiceText(text);
  const axisPatterns = {
    commute: /통근|출퇴근|출근|퇴근|교통|역세권|지하철|버스|회사|직장/,
    cost: /주거비|예산|가격|월세|전세|매매|보증금|관리비|가성비|저렴|싼|쌌/,
    service: /생활\s*soc|생활soc|soc|생활권|인프라|편의|편의점|마트|병원|학교|공원|상권/,
    safety: /안전|치안|cctv|씨씨티비|전세\s*사기|깡통|위험|밤길|보증보험/
  };
  return WEIGHT_AXES.filter((key) => (
    axisPatterns[key].test(text) || axisPatterns[key].test(compactText)
  ));
}

function directAxisWeights(transcript) {
  const axes = directlyMentionedVoiceAxes(transcript);
  if (axes.length < 2) return null;
  const text = normalizeVoiceIntentText(transcript);
  const compactText = compactVoiceText(text);
  const hasDirectPriorityIntent = /높은|높게|중요|우선|찾고|원해|좋겠|맞춰|반영/.test(text)
    || /높은|높게|중요|우선|찾고|원해|좋겠|맞춰|반영/.test(compactText);
  if (!hasDirectPriorityIntent) return null;
  const low = axes.length === 2 ? 15 : 10;
  const remaining = 100 - low * (WEIGHT_AXES.length - axes.length);
  const base = Math.floor(remaining / axes.length / 5) * 5;
  const weights = Object.fromEntries(WEIGHT_AXES.map((key) => [key, axes.includes(key) ? base : low]));
  let delta = 100 - WEIGHT_AXES.reduce((sum, key) => sum + weights[key], 0);
  axes.forEach((key) => {
    if (delta > 0) {
      weights[key] += 5;
      delta -= 5;
    }
  });
  return weights;
}

function scoreVoiceWeights(transcript) {
  const text = String(transcript || "").toLowerCase();
  const normalizedText = normalizeVoiceIntentText(text);
  const searchableText = `${text} ${normalizedText}`;
  const compactText = compactVoiceText(searchableText);
  const scores = Object.fromEntries(WEIGHT_AXES.map((key) => [key, 0]));

  VOICE_WEIGHT_RULES.forEach((rule) => {
    let matchedKeywords = 0;
    rule.keywords.forEach((keyword) => {
      const compactKeyword = compactVoiceText(keyword);
      if (searchableText.includes(keyword) || compactText.includes(compactKeyword)) {
        matchedKeywords += 1;
      }
    });
    scores[rule.key] += Math.min(matchedKeywords, 3);
  });

  VOICE_PHRASE_RULES.forEach((rule) => {
    if (!rule.pattern.test(searchableText) && !rule.pattern.test(compactText)) return;
    Object.entries(rule.weights).forEach(([key, value]) => {
      scores[key] += value;
    });
  });

  VOICE_CONTEXT_RULES.forEach((rule) => {
    if (!rule.pattern.test(searchableText) && !rule.pattern.test(compactText)) return;
    Object.entries(rule.weights).forEach(([key, value]) => {
      scores[key] += value;
    });
  });

  if (/아이|자녀|초등|유치|학교|교육/.test(searchableText)) {
    scores.service += 2;
    scores.safety += 1;
  }
  if (/부모님|어르신|노인|병원|의료|복지/.test(searchableText)) {
    scores.service += 2;
    scores.safety += 1;
  }
  if (/전세\s*사기|깡통|보증금|위험/.test(searchableText)) {
    scores.safety += 2;
    scores.cost += 1;
  }
  if (/제일|가장|최우선|우선|중요|먼저|신경/.test(searchableText)) {
    WEIGHT_AXES.forEach((key) => {
      if (scores[key] > 0) scores[key] += 1;
    });
  }
  if (/상관\s*없|괜찮|덜\s*중요|포기|낮춰|줄여/.test(searchableText)) {
    if (/통근|출퇴근|회사|교통|역/.test(searchableText)) scores.commute = Math.max(0, scores.commute - 2);
    if (/가격|예산|월세|전세|비용|돈/.test(searchableText)) scores.cost = Math.max(0, scores.cost - 2);
    if (/생활|편의|병원|학교|마트|공원/.test(searchableText)) scores.service = Math.max(0, scores.service - 2);
    if (/안전|치안|위험|환경|조용/.test(searchableText)) scores.safety = Math.max(0, scores.safety - 2);
  }

  WEIGHT_AXES.forEach((key) => {
    scores[key] = Math.min(scores[key], 10);
  });
  return scores;
}

function fallbackVoiceScores(transcript) {
  if (!String(transcript || "").trim()) return null;
  return {
    ...(VOICE_PERSONA_FALLBACK_SCORES[state.persona] || VOICE_PERSONA_FALLBACK_SCORES.single)
  };
}

function roundedWeightsFromScores(scores) {
  const totalScore = WEIGHT_AXES.reduce((sum, key) => sum + Number(scores[key] || 0), 0);
  if (!totalScore) return null;

  const weights = Object.fromEntries(WEIGHT_AXES.map((key) => {
    const raw = 10 + (Number(scores[key] || 0) / totalScore) * 60;
    return [key, clamp(Math.round(raw / 5) * 5, 0, 50)];
  }));

  let delta = 100 - WEIGHT_AXES.reduce((sum, key) => sum + weights[key], 0);
  let guard = 0;
  while (delta !== 0 && guard < 32) {
    const candidates = [...WEIGHT_AXES].sort((a, b) => (
      delta > 0
        ? weights[a] - weights[b] || Number(scores[b] || 0) - Number(scores[a] || 0)
        : weights[b] - weights[a] || Number(scores[a] || 0) - Number(scores[b] || 0)
    ));
    const key = candidates.find((axis) => delta > 0 ? weights[axis] <= 45 : weights[axis] >= 5);
    if (!key) break;
    weights[key] += delta > 0 ? 5 : -5;
    delta += delta > 0 ? -5 : 5;
    guard += 1;
  }

  return weights;
}

function voiceWeightSummary(weights) {
  return VOICE_WEIGHT_RULES
    .map((rule) => `${rule.label} ${weights[rule.key]}%`)
    .join(" · ");
}

function applyVoiceWeights(transcript) {
  if (isBalancedVoiceIntent(transcript)) {
    state.weights = { commute: 25, cost: 25, service: 25, safety: 25 };
    syncWeightInputs();
    state.voiceWeights.status = `인식: ${voiceIntentDisplayText(transcript)}`;
    scheduleRefresh(0);
    return;
  }

  const directWeights = directAxisWeights(transcript);
  if (directWeights) {
    state.weights = directWeights;
    syncWeightInputs();
    state.voiceWeights.status = `인식: ${voiceIntentDisplayText(transcript)}`;
    scheduleRefresh(0);
    return;
  }

  let scores = scoreVoiceWeights(transcript);
  let usedFallback = false;
  if (!WEIGHT_AXES.some((key) => Number(scores[key] || 0) > 0)) {
    scores = fallbackVoiceScores(transcript);
    usedFallback = Boolean(scores);
  }
  const weights = roundedWeightsFromScores(scores);
  if (!weights) {
    const spoken = String(transcript || "").trim();
    state.voiceWeights.status = spoken
      ? `인식: ${spoken} → 기준을 찾지 못했습니다. 통근, 예산, 생활, 안전처럼 말해보세요.`
      : "상황을 다시 말해주세요. 통근, 예산, 생활, 안전 중 중요한 기준을 반영합니다.";
    renderControls();
    return;
  }

  state.weights = weights;
  syncWeightInputs();
  state.voiceWeights.status = `인식: ${voiceIntentDisplayText(transcript)}`;
  scheduleRefresh(0);
}

function clearVoiceWeightTimers() {
  window.clearTimeout(state.voiceWeights.settleTimer);
  window.clearTimeout(state.voiceWeights.maxTimer);
  state.voiceWeights.settleTimer = null;
  state.voiceWeights.maxTimer = null;
}

function stopVoiceWeightRecognition() {
  clearVoiceWeightTimers();
  try {
    state.voiceWeights.recognition?.stop();
  } catch {
    // Some browsers throw when recognition has already stopped.
  }
}

function queueVoiceWeightAutoStop() {
  window.clearTimeout(state.voiceWeights.settleTimer);
  state.voiceWeights.settleTimer = window.setTimeout(() => {
    state.voiceWeights.status = "말한 내용을 정리하는 중...";
    renderControls();
    stopVoiceWeightRecognition();
  }, VOICE_SILENCE_SETTLE_MS);
}

function startVoiceWeightRecognition() {
  const Recognition = speechRecognitionConstructor();
  if (!Recognition) {
    state.voiceWeights.status = "이 브라우저는 음성 인식을 지원하지 않습니다. Chrome 또는 Edge에서 사용할 수 있습니다.";
    renderControls();
    return;
  }

  if (state.voiceWeights.listening) {
    state.voiceWeights.status = "지금까지 말한 내용을 반영합니다.";
    renderControls();
    stopVoiceWeightRecognition();
    return;
  }

  const recognition = new Recognition();
  state.voiceWeights.recognition = recognition;
  recognition.lang = "ko-KR";
  recognition.interimResults = true;
  recognition.continuous = true;
  recognition.maxAlternatives = 1;

  recognition.onstart = () => {
    clearVoiceWeightTimers();
    state.voiceWeights.listening = true;
    state.voiceWeights.transcript = "";
    state.voiceWeights.errorStatus = "";
    state.voiceWeights.status = "듣는 중... 어떤 집을 찾고 있는지 자연스럽게 말해주세요.";
    state.voiceWeights.maxTimer = window.setTimeout(() => {
      state.voiceWeights.status = "충분히 들었습니다. 말한 내용을 반영합니다.";
      renderControls();
      stopVoiceWeightRecognition();
    }, VOICE_LISTENING_MAX_MS);
    renderControls();
  };
  recognition.onerror = (event) => {
    const messages = {
      "not-allowed": "마이크 권한이 필요합니다.",
      "no-speech": "음성을 인식하지 못했습니다.",
      "audio-capture": "마이크를 찾을 수 없습니다."
    };
    state.voiceWeights.errorStatus = messages[event.error] || "음성 인식에 실패했습니다.";
    state.voiceWeights.status = state.voiceWeights.errorStatus;
    state.voiceWeights.listening = false;
    clearVoiceWeightTimers();
    renderControls();
  };
  recognition.onend = () => {
    clearVoiceWeightTimers();
    state.voiceWeights.listening = false;
    const transcript = state.voiceWeights.transcript.trim();
    if (transcript) {
      applyVoiceWeights(transcript);
    } else {
      state.voiceWeights.status = state.voiceWeights.errorStatus || "음성을 인식하지 못했습니다.";
      renderControls();
    }
  };
  recognition.onresult = (event) => {
    let finalText = "";
    let interimText = "";
    Array.from(event.results || []).forEach((result) => {
      const text = Array.from(result || [])
        .map((item) => item.transcript)
        .join(" ")
        .trim();
      if (!text) return;
      if (result.isFinal) {
        finalText += `${text} `;
      } else {
        interimText += `${text} `;
      }
    });

    const transcript = `${finalText}${interimText}`.replace(/\s+/g, " ").trim();
    if (transcript) {
      state.voiceWeights.transcript = transcript;
      state.voiceWeights.status = `듣는 중... ${voiceIntentDisplayText(transcript)}`;
      queueVoiceWeightAutoStop();
      renderControls();
    }
  };

  try {
    recognition.start();
  } catch {
    state.voiceWeights.listening = false;
    state.voiceWeights.status = "이미 음성 인식이 실행 중입니다.";
    renderControls();
  }
}

function formatDistance(value) {
  const meters = Math.round(Number(value || 0));
  if (meters >= 1000) {
    return `${(meters / 1000).toFixed(1)}km`;
  }
  return `${formatNumber(meters)}m`;
}

function greenAccessScoreFromDistance(distanceMeters) {
  const distance = Number(distanceMeters);
  if (!Number.isFinite(distance)) return 0;
  return Math.round(clamp(100 - (distance / KAKAO_SAFETY_RADIUS_METERS) * 60, 40, 100));
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
      state.locationSearch.items = Array.isArray(payload.suggestions) ? payload.suggestions : [];
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
    destination: state.destination,
    destinationQuery: state.destinationQuery.trim(),
    destinationAddress: destinationLocation?.address || state.destinationQuery.trim(),
    budgetMode: state.budgetMode,
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
  const budgetTarget = budgetTargetValue({
    rentMonthly10k: monthlyRent,
    monthlyRent10k: monthlyRent,
    jeonse10k: jeonse,
    sale10k: sale,
    pricePreview
  }, state.budgetMode);
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
  return "#14B8A6";
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
    sunlightLayer: L.layerGroup().addTo(instance),
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
    fillColor: "#14B8A6",
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
  leisure: { label: "여가", className: "park", source: "soc" },
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

function currentDayMinutes(date = new Date()) {
  return date.getHours() * 60 + date.getMinutes();
}

function clampSunlightMinutes(minutes = currentDayMinutes()) {
  return Math.round(clamp(Number(minutes) || 0, 0, 1439));
}

function formatSunlightTime(minutes = currentDayMinutes()) {
  const clamped = clampSunlightMinutes(minutes);
  const hour = Math.floor(clamped / 60);
  const minute = clamped % 60;
  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function sunlightStateForMinutes(minutes = currentDayMinutes()) {
  const clamped = clampSunlightMinutes(minutes);
  const hour = clamped / 60;
  const daylightRatio = clamp((hour - 6) / 12, 0, 1);
  const sunBearing = 100 + daylightRatio * 160;
  const shadowBearing = (sunBearing + 180) % 360;
  const phase = hour < 10.5 ? "오전 햇빛" : hour < 14.5 ? "정오권 햇빛" : "오후 햇빛";
  return {
    hourLabel: formatSunlightTime(clamped),
    hour,
    daylight: hour >= 6 && hour <= 18,
    altitude: hour >= 6 && hour <= 18 ? Math.max(5, Math.sin(daylightRatio * Math.PI) * 62) : 2,
    phase,
    sunBearing,
    shadowBearing,
    sunSide: sunBearing < 180 ? "동남향" : "서남향",
    shadeSide: "북향"
  };
}

function sunlight3dCenter() {
  const selected = selectedDetailItem();
  if (selected?.lat != null && selected?.lng != null) {
    return { lat: Number(selected.lat), lng: Number(selected.lng) };
  }
  const center = state.map?.instance?.getCenter?.();
  if (center?.lat != null && center?.lng != null) {
    return { lat: Number(center.lat), lng: Number(center.lng) };
  }
  return { lat: SEOUL_CENTER[0], lng: SEOUL_CENTER[1] };
}

function sunlight3dCandidates(center) {
  const source = state.results.length ? state.results : state.apartmentCandidates;
  const candidates = source
    .filter((item) => Number.isFinite(Number(item?.lat)) && Number.isFinite(Number(item?.lng)))
    .map((item) => ({
      item,
      distance: Math.hypot(
        (Number(item.lat) - center.lat) * 110540,
        (Number(item.lng) - center.lng) * 111320 * Math.cos(center.lat * Math.PI / 180)
      )
    }))
    .sort((a, b) => a.distance - b.distance)
    .slice(0, state.results.length ? MATCH_RESULT_LIMIT : SUNLIGHT_3D_BUILDING_LIMIT)
    .map((entry) => entry.item);

  const selected = selectedDetailItem();
  if (selected?.id && !candidates.some((item) => item.id === selected.id)) {
    candidates.unshift(selected);
  }
  return candidates.slice(0, state.results.length ? MATCH_RESULT_LIMIT : SUNLIGHT_3D_BUILDING_LIMIT);
}

function sunlight3dSeed(value) {
  let seed = 2166136261;
  const text = String(value || "building");
  for (let index = 0; index < text.length; index += 1) {
    seed ^= text.charCodeAt(index);
    seed = Math.imul(seed, 16777619);
  }
  return Math.abs(seed >>> 0);
}

function sunlight3dRandom(seed, offset = 0) {
  const value = Math.sin((seed + offset * 1013) * 0.0001) * 43758.5453;
  return value - Math.floor(value);
}

function sunlight3dEstimatedFloors(item) {
  const households = Math.max(0, Number(item?.households || 0));
  const buildings = Math.max(1, Number(item?.buildingCount || 1));
  if (!households) return 10;
  return Math.round(clamp(households / buildings / 4.2, 6, 36));
}

function updateSunlight3dCompass() {
  if (!nodes.sunlight3dCompass || !sunlight3d.camera || !sunlight3d.cameraTarget || !window.THREE) return;
  const THREE = window.THREE;
  sunlight3d.camera.updateMatrixWorld();
  const origin = sunlight3d.cameraTarget.clone().project(sunlight3d.camera);
  const north = sunlight3d.cameraTarget.clone().add(new THREE.Vector3(0, 0, -120)).project(sunlight3d.camera);
  const screenX = north.x - origin.x;
  const screenY = -(north.y - origin.y);
  const angle = Math.atan2(screenY, screenX) * 180 / Math.PI + 90;
  nodes.sunlight3dCompass.querySelector("i")?.style.setProperty("transform", `translateY(-1px) rotate(${angle.toFixed(1)}deg)`);
}

function updateSunlight3dCamera() {
  if (!sunlight3d.camera || !sunlight3d.cameraTarget) return;
  const horizontal = Math.sin(sunlight3d.phi) * sunlight3d.radius;
  sunlight3d.camera.position.set(
    sunlight3d.cameraTarget.x + Math.sin(sunlight3d.theta) * horizontal,
    sunlight3d.cameraTarget.y + Math.cos(sunlight3d.phi) * sunlight3d.radius,
    sunlight3d.cameraTarget.z + Math.cos(sunlight3d.theta) * horizontal
  );
  sunlight3d.camera.lookAt(sunlight3d.cameraTarget);
  updateSunlight3dCompass();
}

function resizeSunlight3dRenderer() {
  if (!sunlight3d.renderer || !sunlight3d.camera || !nodes.sunlight3dCanvas || nodes.sunlight3dCanvas.hidden) return;
  const width = Math.max(1, nodes.sunlight3dCanvas.clientWidth);
  const height = Math.max(1, nodes.sunlight3dCanvas.clientHeight);
  sunlight3d.renderer.setSize(width, height, false);
  sunlight3d.camera.aspect = width / height;
  sunlight3d.camera.updateProjectionMatrix();
  sunlight3d.renderer.render(sunlight3d.scene, sunlight3d.camera);
}

function renderSunlight3dFrame() {
  if (!sunlight3d.renderer || !sunlight3d.scene || !sunlight3d.camera) return;
  sunlight3d.renderer.render(sunlight3d.scene, sunlight3d.camera);
}

function pickSunlight3dBuilding(event) {
  if (sunlight3d.moved || !sunlight3d.renderer || !sunlight3d.camera || !sunlight3d.buildingMeshes.length) return;
  const THREE = window.THREE;
  const rect = sunlight3d.renderer.domElement.getBoundingClientRect();
  const pointer = new THREE.Vector2(
    ((event.clientX - rect.left) / rect.width) * 2 - 1,
    -((event.clientY - rect.top) / rect.height) * 2 + 1
  );
  const raycaster = new THREE.Raycaster();
  raycaster.setFromCamera(pointer, sunlight3d.camera);
  const hit = raycaster.intersectObjects(sunlight3d.buildingMeshes, false)[0];
  const item = hit?.object?.userData?.apartment;
  if (!item?.id) return;
  if (state.results.some((result) => result.id === item.id)) {
    selectApartmentMatch(item.id, { source: "map", openDetailPanel: true });
  } else {
    openApartmentFeatureDetail(item);
  }
}

function addSunlight3dRoad(parent, width, depth, x, z, rotation = 0) {
  const THREE = window.THREE;
  const road = new THREE.Mesh(
    new THREE.PlaneGeometry(width, depth),
    new THREE.MeshStandardMaterial({ color: 0xf4f5f2, roughness: 0.95, metalness: 0 })
  );
  road.rotation.x = -Math.PI / 2;
  road.rotation.z = rotation;
  road.position.set(x, 0.18, z);
  road.receiveShadow = true;
  parent.add(road);
}

function sunlight3dMercatorPixel(lat, lng, zoom) {
  const worldSize = 256 * (2 ** zoom);
  const clampedLat = clamp(Number(lat), -85.05112878, 85.05112878);
  const sinLat = Math.sin(clampedLat * Math.PI / 180);
  return {
    x: (Number(lng) + 180) / 360 * worldSize,
    y: (0.5 - Math.log((1 + sinLat) / (1 - sinLat)) / (4 * Math.PI)) * worldSize
  };
}

function loadSunlight3dMapTile(url) {
  return new Promise((resolve) => {
    const tile = new Image();
    tile.crossOrigin = "anonymous";
    tile.decoding = "async";
    tile.onload = () => resolve(tile);
    tile.onerror = () => resolve(null);
    tile.src = url;
  });
}

async function updateSunlight3dMapTexture(center) {
  if (!sunlight3d.mapGround || !sunlight3d.renderer || !window.THREE) return;
  const zoom = 13;
  const centerKey = `${zoom}:${center.lat.toFixed(3)}:${center.lng.toFixed(3)}`;
  if (sunlight3d.mapCenterKey === centerKey && sunlight3d.mapGround.material.map) return;

  sunlight3d.mapCenterKey = centerKey;
  const requestId = ++sunlight3d.mapTextureRequestId;
  sunlight3d.mapGround.material.map?.dispose?.();
  sunlight3d.mapGround.material.map = null;
  sunlight3d.mapGround.material.color.set(0xbfcfc5);
  sunlight3d.mapGround.material.needsUpdate = true;
  const canvasSize = 1024;
  const tileSize = 256;
  const tileCount = 2 ** zoom;
  const centerPixel = sunlight3dMercatorPixel(center.lat, center.lng, zoom);
  const topLeft = {
    x: centerPixel.x - canvasSize / 2,
    y: centerPixel.y - canvasSize / 2
  };
  const startX = Math.floor(topLeft.x / tileSize);
  const endX = Math.floor((topLeft.x + canvasSize - 1) / tileSize);
  const startY = Math.max(0, Math.floor(topLeft.y / tileSize));
  const endY = Math.min(tileCount - 1, Math.floor((topLeft.y + canvasSize - 1) / tileSize));
  const canvas = document.createElement("canvas");
  canvas.width = canvasSize;
  canvas.height = canvasSize;
  const context = canvas.getContext("2d");
  context.fillStyle = "#dce5df";
  context.fillRect(0, 0, canvasSize, canvasSize);

  sunlight3d.fallbackOverlayGroup.visible = true;
  const tileJobs = [];
  for (let tileY = startY; tileY <= endY; tileY += 1) {
    for (let tileX = startX; tileX <= endX; tileX += 1) {
      const wrappedX = ((tileX % tileCount) + tileCount) % tileCount;
      tileJobs.push((async () => {
        const image = await loadSunlight3dMapTile(`https://tile.openstreetmap.org/${zoom}/${wrappedX}/${tileY}.png`);
        if (!image) return false;
        const drawX = Math.round(tileX * tileSize - topLeft.x);
        const drawY = Math.round(tileY * tileSize - topLeft.y);
        context.drawImage(image, drawX, drawY, tileSize, tileSize);
        return true;
      })());
    }
  }

  const tileResults = await Promise.all(tileJobs);
  if (requestId !== sunlight3d.mapTextureRequestId || !tileResults.some(Boolean)) return;

  const THREE = window.THREE;
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.anisotropy = Math.min(8, sunlight3d.renderer.capabilities.getMaxAnisotropy());
  texture.needsUpdate = true;
  sunlight3d.mapGround.material.map?.dispose?.();
  sunlight3d.mapGround.material.map = texture;
  sunlight3d.mapGround.material.color.set(0xffffff);
  sunlight3d.mapGround.material.roughness = 0.92;
  sunlight3d.mapGround.material.needsUpdate = true;

  const metersPerPixel = 156543.03392 * Math.cos(center.lat * Math.PI / 180) / (2 ** zoom);
  const groundSize = canvasSize * metersPerPixel / SUNLIGHT_3D_WORLD_SCALE;
  sunlight3d.mapGround.geometry.dispose();
  sunlight3d.mapGround.geometry = new THREE.PlaneGeometry(groundSize, groundSize);
  sunlight3d.fallbackOverlayGroup.visible = false;
  renderSunlight3dFrame();
}

function initializeSunlight3d() {
  if (sunlight3d.initialized) return true;
  if (sunlight3d.failed || !nodes.sunlight3dCanvas) return false;
  if (!window.THREE) return false;

  try {
    const THREE = window.THREE;
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.6));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 0.9;
    renderer.domElement.setAttribute("aria-label", "3D 햇빛 분포 도시");
    renderer.domElement.tabIndex = 0;
    nodes.sunlight3dCanvas.append(renderer.domElement);

    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0xdbe8e5);
    scene.fog = new THREE.Fog(0xdbe8e5, 620, 1180);

    const camera = new THREE.PerspectiveCamera(42, 1, 0.5, 3000);
    const cameraTarget = new THREE.Vector3(0, 0, 0);
    const hemisphereLight = new THREE.HemisphereLight(0xfff7d6, 0x64748b, 1.6);
    scene.add(hemisphereLight);

    const sunLight = new THREE.DirectionalLight(0xfff1b8, 3.2);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.set(2048, 2048);
    sunLight.shadow.camera.left = -560;
    sunLight.shadow.camera.right = 560;
    sunLight.shadow.camera.top = 560;
    sunLight.shadow.camera.bottom = -560;
    sunLight.shadow.camera.near = 1;
    sunLight.shadow.camera.far = 1600;
    sunLight.shadow.bias = -0.0005;
    scene.add(sunLight);
    scene.add(sunLight.target);

    const ground = new THREE.Mesh(
      new THREE.PlaneGeometry(1120, 1120),
      new THREE.MeshStandardMaterial({ color: 0xbfcfc5, roughness: 1, metalness: 0 })
    );
    ground.rotation.x = -Math.PI / 2;
    ground.receiveShadow = true;
    scene.add(ground);

    const fallbackOverlayGroup = new THREE.Group();
    const river = new THREE.Mesh(
      new THREE.PlaneGeometry(1200, 92),
      new THREE.MeshStandardMaterial({ color: 0x82c8d2, roughness: 0.38, metalness: 0.06 })
    );
    river.rotation.x = -Math.PI / 2;
    river.rotation.z = -0.08;
    river.position.set(30, 0.25, 310);
    river.receiveShadow = true;
    fallbackOverlayGroup.add(river);

    for (let offset = -420; offset <= 420; offset += 70) {
      addSunlight3dRoad(fallbackOverlayGroup, 1040, offset % 140 === 0 ? 10 : 6, 0, offset, 0);
      addSunlight3dRoad(fallbackOverlayGroup, 1040, offset % 140 === 0 ? 10 : 6, offset, 0, Math.PI / 2);
    }
    addSunlight3dRoad(fallbackOverlayGroup, 1120, 12, 0, 0, Math.PI * 0.19);
    addSunlight3dRoad(fallbackOverlayGroup, 1120, 8, 0, -40, -Math.PI * 0.27);
    scene.add(fallbackOverlayGroup);

    sunlight3d.renderer = renderer;
    sunlight3d.scene = scene;
    sunlight3d.camera = camera;
    sunlight3d.cameraTarget = cameraTarget;
    sunlight3d.sunLight = sunLight;
    sunlight3d.hemisphereLight = hemisphereLight;
    sunlight3d.mapGround = ground;
    sunlight3d.fallbackOverlayGroup = fallbackOverlayGroup;
    sunlight3d.initialized = true;
    updateSunlight3dCamera();

    renderer.domElement.addEventListener("pointerdown", (event) => {
      sunlight3d.dragging = true;
      sunlight3d.moved = false;
      sunlight3d.pointerX = event.clientX;
      sunlight3d.pointerY = event.clientY;
      renderer.domElement.setPointerCapture?.(event.pointerId);
    });
    renderer.domElement.addEventListener("pointermove", (event) => {
      if (!sunlight3d.dragging) return;
      const deltaX = event.clientX - sunlight3d.pointerX;
      const deltaY = event.clientY - sunlight3d.pointerY;
      if (Math.abs(deltaX) + Math.abs(deltaY) > 2) sunlight3d.moved = true;
      sunlight3d.pointerX = event.clientX;
      sunlight3d.pointerY = event.clientY;
      sunlight3d.theta -= deltaX * 0.006;
      sunlight3d.phi = clamp(sunlight3d.phi + deltaY * 0.005, 0.32, 1.42);
      updateSunlight3dCamera();
      renderSunlight3dFrame();
    });
    renderer.domElement.addEventListener("pointerup", (event) => {
      const shouldPick = !sunlight3d.moved;
      sunlight3d.dragging = false;
      renderer.domElement.releasePointerCapture?.(event.pointerId);
      if (shouldPick) pickSunlight3dBuilding(event);
    });
    renderer.domElement.addEventListener("pointercancel", () => {
      sunlight3d.dragging = false;
    });
    renderer.domElement.addEventListener("wheel", (event) => {
      event.preventDefault();
      sunlight3d.radius = clamp(sunlight3d.radius * (event.deltaY > 0 ? 1.09 : 0.91), 180, 1050);
      updateSunlight3dCamera();
      renderSunlight3dFrame();
    }, { passive: false });

    if (window.ResizeObserver) {
      sunlight3d.resizeObserver = new ResizeObserver(resizeSunlight3dRenderer);
      sunlight3d.resizeObserver.observe(nodes.sunlight3dCanvas);
    }
    resizeSunlight3dRenderer();
    return true;
  } catch (error) {
    sunlight3d.failed = true;
    console.warn("3D sunlight view unavailable", error);
    return false;
  }
}

window.addEventListener("fithome-three-ready", () => {
  if (state.mapMode === "sunlight") syncSunlight3dView({ rebuild: true });
});

function disposeSunlight3dCity() {
  if (!sunlight3d.cityGroup || !sunlight3d.scene) return;
  sunlight3d.cityGroup.traverse((object) => {
    object.geometry?.dispose?.();
    if (Array.isArray(object.material)) {
      object.material.forEach((material) => {
        if (material.map && material.map !== sunlight3d.windowTexture) material.map.dispose?.();
        material.dispose?.();
      });
    } else {
      if (object.material?.map && object.material.map !== sunlight3d.windowTexture) object.material.map.dispose?.();
      object.material?.dispose?.();
    }
  });
  sunlight3d.scene.remove(sunlight3d.cityGroup);
  sunlight3d.cityGroup = null;
  sunlight3d.buildingMeshes = [];
  sunlight3d.windowFacades = [];
}

function createSunlight3dApartmentLabel(item, rank, isSelected, x, z, height) {
  const THREE = window.THREE;
  const prefix = rank ? `${rank}. ` : "";
  let name = String(item?.name || "아파트");
  const measureCanvas = document.createElement("canvas");
  const measureContext = measureCanvas.getContext("2d");
  measureContext.font = "800 36px sans-serif";
  while (name.length > 4 && measureContext.measureText(`${prefix}${name}`).width > 570) {
    name = `${name.slice(0, -2)}…`;
  }
  const labelText = `${prefix}${name}`;
  const canvasWidth = Math.round(clamp(measureContext.measureText(labelText).width + 62, 220, 640));
  const canvas = document.createElement("canvas");
  canvas.width = canvasWidth;
  canvas.height = 112;
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = isSelected ? "rgba(250, 204, 21, 0.96)" : "rgba(15, 23, 42, 0.9)";
  context.beginPath();
  if (typeof context.roundRect === "function") {
    context.roundRect(8, 8, canvas.width - 16, canvas.height - 16, 24);
  } else {
    context.rect(8, 8, canvas.width - 16, canvas.height - 16);
  }
  context.fill();
  context.strokeStyle = isSelected ? "#ff8a00" : "rgba(255, 255, 255, 0.8)";
  context.lineWidth = 5;
  context.stroke();

  context.fillStyle = isSelected ? "#111827" : "#ffffff";
  context.font = "800 36px sans-serif";
  context.textBaseline = "middle";
  context.fillText(labelText, 30, canvas.height / 2 + 1);

  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.needsUpdate = true;
  const material = new THREE.SpriteMaterial({ map: texture, transparent: true, depthTest: false, depthWrite: false });
  const label = new THREE.Sprite(material);
  label.position.set(x, height + 18, z);
  label.scale.set(clamp(canvasWidth * 0.1375, 34, 88), 15.4, 1);
  label.renderOrder = 20;
  label.userData.apartment = item;
  return label;
}

function sunlight3dWindowTexture() {
  if (sunlight3d.windowTexture) return sunlight3d.windowTexture;
  const THREE = window.THREE;
  const canvas = document.createElement("canvas");
  canvas.width = 128;
  canvas.height = 256;
  const context = canvas.getContext("2d");
  context.clearRect(0, 0, canvas.width, canvas.height);
  context.fillStyle = "rgba(255, 255, 255, 0.96)";
  const columns = 4;
  const rows = 12;
  const windowWidth = 19;
  const windowHeight = 12;
  const gapX = 9;
  const gapY = 8;
  const startX = (canvas.width - (columns * windowWidth + (columns - 1) * gapX)) / 2;
  const startY = 10;
  for (let row = 0; row < rows; row += 1) {
    for (let column = 0; column < columns; column += 1) {
      context.fillRect(
        startX + column * (windowWidth + gapX),
        startY + row * (windowHeight + gapY),
        windowWidth,
        windowHeight
      );
    }
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.magFilter = THREE.NearestFilter;
  texture.minFilter = THREE.LinearFilter;
  texture.needsUpdate = true;
  sunlight3d.windowTexture = texture;
  return texture;
}

function addSunlight3dWindows(building, width, height, depth, rotation, isSelected) {
  const THREE = window.THREE;
  const rotationDegrees = rotation * 180 / Math.PI;
  const facades = [
    { width, x: 0, z: depth / 2 + 0.08, rotationY: 0, baseBearing: 180 },
    { width, x: 0, z: -depth / 2 - 0.08, rotationY: Math.PI, baseBearing: 0 },
    { width: depth, x: width / 2 + 0.08, z: 0, rotationY: Math.PI / 2, baseBearing: 90 },
    { width: depth, x: -width / 2 - 0.08, z: 0, rotationY: -Math.PI / 2, baseBearing: 270 }
  ];
  facades.forEach((facade) => {
    const material = new THREE.MeshBasicMaterial({
      map: sunlight3dWindowTexture(),
      color: isSelected ? 0xff8a00 : 0x64748b,
      transparent: true,
      opacity: 0.88,
      depthWrite: false,
      side: THREE.DoubleSide
    });
    const windows = new THREE.Mesh(
      new THREE.PlaneGeometry(Math.max(3.5, facade.width * 0.78), Math.max(7, height * 0.82)),
      material
    );
    windows.position.set(facade.x, 0, facade.z);
    windows.rotation.y = facade.rotationY;
    windows.renderOrder = 4;
    building.add(windows);
    sunlight3d.windowFacades.push({
      material,
      bearing: (facade.baseBearing - rotationDegrees + 360) % 360,
      isSelected
    });
  });
}

function rebuildSunlight3dCity(center, candidates) {
  const THREE = window.THREE;
  disposeSunlight3dCity();
  const group = new THREE.Group();
  const metersPerLng = 111320 * Math.cos(center.lat * Math.PI / 180);
  const resultIds = new Set(state.results.map((item) => item.id));
  const materials = [0xb8c2c8, 0xc9c3b7, 0xaebcc1, 0xd1cec5].map((color) => new THREE.MeshStandardMaterial({
    color,
    roughness: 0.82,
    metalness: 0.02
  }));
  const resultMaterial = new THREE.MeshStandardMaterial({ color: 0x16a394, roughness: 0.72, metalness: 0.02 });
  const selectedMaterial = new THREE.MeshStandardMaterial({ color: 0xfacc15, roughness: 0.62, metalness: 0.03 });

  candidates.forEach((item, itemIndex) => {
    const baseX = (Number(item.lng) - center.lng) * metersPerLng / SUNLIGHT_3D_WORLD_SCALE;
    const baseZ = -(Number(item.lat) - center.lat) * 110540 / SUNLIGHT_3D_WORLD_SCALE;
    if (Math.abs(baseX) > 510 || Math.abs(baseZ) > 510) return;

    const seed = sunlight3dSeed(item.id || item.name || itemIndex);
    const sourceBuildingCount = Math.max(1, Number(item.buildingCount || 1));
    const blockCount = Math.round(clamp(sourceBuildingCount, 1, state.results.length ? 4 : 2));
    const floors = sunlight3dEstimatedFloors(item);
    const isSelected = item.id === state.selectedId;
    const material = isSelected
      ? selectedMaterial
      : resultIds.has(item.id)
        ? resultMaterial
        : materials[seed % materials.length];
    let maxHeight = 0;

    for (let blockIndex = 0; blockIndex < blockCount; blockIndex += 1) {
      const angle = sunlight3dRandom(seed, blockIndex + 1) * Math.PI * 2;
      const spread = blockCount === 1 ? 0 : 8 + sunlight3dRandom(seed, blockIndex + 3) * 12;
      const width = 7 + sunlight3dRandom(seed, blockIndex + 5) * 7;
      const depth = 7 + sunlight3dRandom(seed, blockIndex + 7) * 8;
      const height = Math.max(9, floors * (1.25 + sunlight3dRandom(seed, blockIndex + 9) * 0.35));
      maxHeight = Math.max(maxHeight, height);
      const geometry = new THREE.BoxGeometry(width, height, depth);
      const building = new THREE.Mesh(geometry, material);
      building.position.set(baseX + Math.cos(angle) * spread, height / 2, baseZ + Math.sin(angle) * spread);
      const buildingRotation = angle * 0.5;
      building.rotation.y = buildingRotation;
      building.castShadow = true;
      building.receiveShadow = true;
      building.userData.apartment = item;
      addSunlight3dWindows(building, width, height, depth, buildingRotation, isSelected);
      group.add(building);
      sunlight3d.buildingMeshes.push(building);
    }

    const rank = state.results.findIndex((result) => result.id === item.id) + 1;
    const label = createSunlight3dApartmentLabel(item, rank, isSelected, baseX, baseZ, maxHeight);
    group.add(label);
    sunlight3d.buildingMeshes.push(label);

    if (isSelected) {
      const marker = new THREE.Mesh(
        new THREE.RingGeometry(16, 21, 48),
        new THREE.MeshBasicMaterial({ color: 0xff8a00, side: THREE.DoubleSide, transparent: true, opacity: 0.94 })
      );
      marker.rotation.x = -Math.PI / 2;
      marker.position.set(baseX, 0.55, baseZ);
      group.add(marker);
    }
  });

  sunlight3d.cityGroup = group;
  sunlight3d.scene.add(group);
  void updateSunlight3dMapTexture(center);
}

function updateSunlight3dLighting() {
  if (!sunlight3d.initialized) return;
  const THREE = window.THREE;
  const sunlight = sunlightStateForMinutes(state.sunlightMinutes);
  const altitude = sunlight.altitude * Math.PI / 180;
  const bearing = sunlight.sunBearing * Math.PI / 180;
  const sunDistance = 720;
  sunlight3d.sunLight.position.set(
    Math.sin(bearing) * Math.cos(altitude) * sunDistance,
    Math.sin(altitude) * sunDistance,
    -Math.cos(bearing) * Math.cos(altitude) * sunDistance
  );
  sunlight3d.sunLight.target.position.set(0, 0, 0);
  sunlight3d.sunLight.target.updateMatrixWorld();

  const daylightStrength = sunlight.daylight ? Math.max(0.18, Math.sin(altitude)) : 0;
  sunlight3d.sunLight.intensity = sunlight.daylight ? 0.95 + daylightStrength * 2.2 : 0.04;
  sunlight3d.hemisphereLight.intensity = sunlight.daylight ? 0.72 + daylightStrength * 0.62 : 0.22;
  const skyColor = new THREE.Color(sunlight.daylight ? 0xdbe9e7 : 0x18202f);
  sunlight3d.scene.background = skyColor;
  sunlight3d.scene.fog.color.copy(skyColor);

  const coolWindow = new THREE.Color(0x2563eb);
  const warmWindow = new THREE.Color(0xffc928);
  sunlight3d.windowFacades.forEach((facade) => {
    const angleDifference = ((facade.bearing - sunlight.sunBearing + 540) % 360) - 180;
    const exposure = sunlight.daylight ? Math.max(0, Math.cos(angleDifference * Math.PI / 180)) : 0;
    facade.material.color.copy(coolWindow).lerp(warmWindow, exposure);
    facade.material.opacity = sunlight.daylight ? 0.72 + exposure * 0.28 : 0.55;
  });

  renderSunlight3dFrame();
}

function syncSunlight3dView({ rebuild = false } = {}) {
  const active = state.mapMode === "sunlight";
  if (!nodes.sunlight3dCanvas || !nodes.mapCanvas) return;
  if (!active) {
    nodes.sunlight3dCanvas.hidden = true;
    nodes.mapCanvas.classList.remove("is-hidden-for-3d");
    window.setTimeout(() => state.map?.instance?.invalidateSize?.({ pan: false }), 0);
    return;
  }

  dismissAgentHint();
  nodes.sunlight3dCanvas.hidden = false;
  nodes.mapCanvas.classList.add("is-hidden-for-3d");
  if (!window.THREE && !sunlight3d.failed) {
    nodes.sunlight3dCanvas.hidden = true;
    nodes.mapCanvas.classList.remove("is-hidden-for-3d");
    return;
  }
  if (!initializeSunlight3d()) {
    nodes.sunlight3dCanvas.hidden = true;
    nodes.mapCanvas.classList.remove("is-hidden-for-3d");
    return;
  }

  const center = sunlight3dCenter();
  const candidates = sunlight3dCandidates(center);
  const signature = [
    center.lat.toFixed(3),
    center.lng.toFixed(3),
    state.selectedId || "",
    candidates.map((item) => item.id).join(",")
  ].join("|");
  if (rebuild || signature !== sunlight3d.sceneSignature) {
    sunlight3d.sceneSignature = signature;
    sunlight3d.radius = selectedDetailItem() ? 300 : 620;
    updateSunlight3dCamera();
    rebuildSunlight3dCity(center, candidates);
  }
  updateSunlight3dLighting();
  window.requestAnimationFrame(resizeSunlight3dRenderer);
}

function renderSunlightOverlay(visibleResults = []) {
  if (!state.map?.sunlightLayer || !window.L) return;
  state.map.sunlightLayer.clearLayers();
  const active = state.mapMode === "sunlight" && canUseMapModeControls();
  nodes.mapCanvas?.classList.toggle("is-sunlight-map", active);
  if (!active) return;

  const sunlight = sunlightStateForMinutes(state.sunlightMinutes);
  const candidates = (visibleResults.length ? visibleResults : state.results).slice(0, MATCH_RESULT_LIMIT);
  const selected = candidates.find((item) => item.id === state.selectedId) || selectedMatchResult();
  const targets = selected
    ? [selected, ...candidates.filter((item) => item.id !== selected.id)].slice(0, MATCH_RESULT_LIMIT)
    : candidates.slice(0, MATCH_RESULT_LIMIT);

  targets.forEach((item, index) => {
    if (item?.lat == null || item?.lng == null) return;
    const lat = Number(item.lat);
    const lng = Number(item.lng);
    const isSelected = item.id === state.selectedId;
    const distance = isSelected ? 210 : 150;
    const shadeEnd = offsetLatLng(lat, lng, distance, sunlight.shadowBearing);
    const shadeLeft = offsetLatLng(lat, lng, isSelected ? 42 : 30, sunlight.shadowBearing - 90);
    const shadeRight = offsetLatLng(lat, lng, isSelected ? 42 : 30, sunlight.shadowBearing + 90);
    const shadeTipLeft = offsetLatLng(shadeEnd[0], shadeEnd[1], isSelected ? 58 : 42, sunlight.shadowBearing - 90);
    const shadeTipRight = offsetLatLng(shadeEnd[0], shadeEnd[1], isSelected ? 58 : 42, sunlight.shadowBearing + 90);

    L.polygon([shadeLeft, shadeRight, shadeTipRight, shadeTipLeft], {
      className: `sunlight-shadow-shape${isSelected ? " is-selected" : ""}`,
      fillColor: "#334155",
      stroke: false,
      fillOpacity: isSelected ? 0.42 : 0.28,
      interactive: false
    }).addTo(state.map.sunlightLayer);

    L.circle([lat, lng], {
      radius: isSelected ? 75 : 52,
      className: `sunlight-sun-zone${isSelected ? " is-selected" : ""}`,
      fillColor: "#facc15",
      stroke: false,
      fillOpacity: isSelected ? 0.28 : 0.16,
      interactive: false
    }).addTo(state.map.sunlightLayer);

  });

  const sourcePoint = selected || targets[0];
  if (sourcePoint?.lat != null && sourcePoint?.lng != null) {
    const sunPoint = offsetLatLng(Number(sourcePoint.lat), Number(sourcePoint.lng), 260, sunlight.sunBearing);
    L.polyline([[sourcePoint.lat, sourcePoint.lng], sunPoint], {
      className: "sunlight-direction-line",
      color: "#f59e0b",
      weight: 3,
      interactive: false
    }).addTo(state.map.sunlightLayer);
  }

}

function canUseMapModeControls() {
  return Boolean(state.hasMatched && state.results.length);
}

function syncMapModeControls() {
  const available = canUseMapModeControls();
  if (!available && state.mapMode !== "normal") {
    state.mapMode = "normal";
    renderSunlightOverlay(mapResultsForCurrentView());
    syncSunlight3dView();
  }
  if (nodes.mapModeControl) nodes.mapModeControl.hidden = !available;
  nodes.mapModeButtons?.forEach((button) => {
    const active = button.dataset.mapMode === state.mapMode;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
    button.disabled = !available;
  });
  syncSunlightTimeControls();
}

function syncSunlightTimeControls() {
  const visible = state.mapMode === "sunlight" && canUseMapModeControls();
  if (nodes.sunlightTimeControl) nodes.sunlightTimeControl.hidden = !visible;
  if (nodes.sunlightTimeInput) nodes.sunlightTimeInput.value = String(clampSunlightMinutes(state.sunlightMinutes));
  if (nodes.sunlightTimeOutput) nodes.sunlightTimeOutput.textContent = formatSunlightTime(state.sunlightMinutes);
}

function setMapMode(mode) {
  if (!MAP_MODES.includes(mode) || state.mapMode === mode) return;
  if (mode === "sunlight" && !canUseMapModeControls()) return;
  state.mapMode = mode;
  if (mode === "sunlight") {
    sunlight3d.theta = 0;
    sunlight3d.phi = Math.PI * 0.31;
    updateSunlight3dCamera();
  }
  syncMapModeControls();
  renderSunlightOverlay(mapResultsForCurrentView());
  syncSunlight3dView({ rebuild: mode === "sunlight" });
}

function setSunlightMinutes(minutes, { rerender = true } = {}) {
  state.sunlightMinutes = clampSunlightMinutes(minutes);
  syncSunlightTimeControls();
  if (rerender) {
    renderSunlightOverlay(mapResultsForCurrentView());
    syncSunlight3dView();
  }
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
        name: liveAir.nearest?.name || `${liveAir.station || districtNameForAir(selected)} 대기측정소`,
        description: airDescription(liveAir),
        lat: liveAir.nearest?.lat,
        lng: liveAir.nearest?.lng,
        distanceMeters: liveAir.nearest?.distanceMeters ?? 900
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
    leisure: `<svg class="park-tree-icon" viewBox="0 0 24 24" aria-hidden="true"><path class="tree-trunk" d="M10 15h4v5a1 1 0 0 1-1 1h-2a1 1 0 0 1-1-1v-5Z"/><path class="tree-leaf" d="M12 3 5.8 9.2a1 1 0 0 0 .7 1.8H8l-3.2 3.2a1 1 0 0 0 .7 1.8h13a1 1 0 0 0 .7-1.8L16 11h1.5a1 1 0 0 0 .7-1.8L12 3Z"/></svg>`,
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
  renderSunlightOverlay(visibleResults);
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
    syncSunlight3dView();
    return;
  }

  if (!renderLeafletMap()) {
    renderFallbackMap();
  }
  syncSunlight3dView();
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

function statusText(status) {
  if (status === "high") return "집중 확인";
  if (status === "warning") return "주의";
  if (status === "unknown") return "미확인";
  return "양호";
}

function renderTrendChart(rows) {
  const liveRows = Array.isArray(rows) ? rows.filter((row) => row.sourceMode !== "trend_estimate") : [];
  const saleData = liveRows
    .map((row) => ({ month: row.month || "", value: Number(row.sale10k || 0), volume: Number(row.saleVolume || 0) }))
    .filter((row) => row.month && row.value > 0);
  const jeonseData = liveRows
    .map((row) => ({ month: row.month || "", value: Number(row.jeonse10k || 0), volume: Number(row.jeonseVolume || 0) }))
    .filter((row) => row.month && row.value > 0);
  const pointCount = saleData.length + jeonseData.length;
  if (liveRows.length < 2 || pointCount < 2) {
    return `<div class="chart-empty">실거래 기반 월별 추이 정보 없음</div>`;
  }
  const values = [...saleData, ...jeonseData].map((row) => row.value);
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
  const x = (index) => left + (index / (liveRows.length - 1)) * usableWidth;
  const indexedRows = liveRows.map((row, index) => ({ ...row, index }));
  const pointFor = (row) => `${x(row.index).toFixed(1)},${y(row.value).toFixed(1)}`;
  const seriesRows = (field, volumeField) => indexedRows
    .map((row) => ({
      month: row.month || "",
      value: Number(row[field] || 0),
      volume: Number(row[volumeField] || 0),
      index: row.index
    }))
    .filter((row) => row.month && row.value > 0);
  const saleRows = seriesRows("sale10k", "saleVolume");
  const jeonseRows = seriesRows("jeonse10k", "jeonseVolume");
  const salePoints = saleRows.map(pointFor).join(" ");
  const jeonsePoints = jeonseRows.map(pointFor).join(" ");
  const pointSvg = (rows, className, label) => rows.map((row) => `
    <circle class="${className}-point" cx="${x(row.index).toFixed(1)}" cy="${y(row.value).toFixed(1)}" r="3.2">
      <title>${escapeHtml(`${row.month} ${label} ${formatMoney10k(row.value)}${row.volume ? ` · ${row.volume}건` : ""}`)}</title>
    </circle>
  `).join("");
  const first = liveRows[0]?.month || "";
  const last = liveRows[liveRows.length - 1]?.month || "";
  return `
    <svg class="property-trend-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="최근 거래 추이 그래프">
      <line x1="${left}" y1="${top}" x2="${left}" y2="${height - bottom}" />
      <line x1="${left}" y1="${height - bottom}" x2="${width - right}" y2="${height - bottom}" />
      ${saleRows.length > 1 ? `<polyline class="sale-line" points="${salePoints}" />` : ""}
      ${jeonseRows.length > 1 ? `<polyline class="jeonse-line" points="${jeonsePoints}" />` : ""}
      ${pointSvg(saleRows, "sale", "매매")}
      ${pointSvg(jeonseRows, "jeonse", "전세")}
      <text x="${left}" y="${height - 10}">${escapeHtml(first)}</text>
      <text x="${width - right}" y="${height - 10}" text-anchor="end">${escapeHtml(last)}</text>
      <text x="${left}" y="12">${escapeHtml(formatMoney10k(max))}</text>
      <text x="${width - right}" y="12" text-anchor="end">매매 / 전세</text>
    </svg>
    <div class="chart-legend">
      <span><i class="chart-dot sale"></i>매매 실거래</span>
      <span><i class="chart-dot jeonse"></i>전세 실거래</span>
    </div>
  `;
}

function latestRecord(records, predicate) {
  return (Array.isArray(records) ? records : [])
    .filter(predicate)
    .sort((a, b) => {
      const left = `${a.dealYear || ""}${String(a.dealMonth || "").padStart(2, "0")}${String(a.dealDay || "").padStart(2, "0")}`;
      const right = `${b.dealYear || ""}${String(b.dealMonth || "").padStart(2, "0")}${String(b.dealDay || "").padStart(2, "0")}`;
      return right.localeCompare(left);
    })[0] || null;
}

function livePriceRecords(price = {}) {
  const trade = price.molitLatestTradeRecord || latestRecord(
    price.molitTradeRecords,
    (item) => Number(item.amount10k || 0) > 0
  );
  const jeonse = price.molitLatestJeonseRecord || latestRecord(
    price.molitRentRecords,
    (item) => Number(item.deposit10k || 0) > 0 && !Number(item.monthlyRent10k || 0)
  );
  const monthly = price.molitLatestMonthlyRecord || latestRecord(
    price.molitRentRecords,
    (item) => Number(item.monthlyRent10k || 0) > 0
  );
  return { trade, jeonse, monthly };
}

function liveBudgetPrice(price = {}, mode = state.budgetMode) {
  const liveStatus = price.liveStatus || {};
  const records = livePriceRecords(price);
  if (mode === "sale" && isLiveStatus(liveStatus.molitTrade) && records.trade) {
    return { label: "매매 실거래가", value: Number(records.trade.amount10k || 0) };
  }
  if (mode === "jeonse" && isLiveStatus(liveStatus.molitRent) && records.jeonse) {
    return { label: "전세 보증금", value: Number(records.jeonse.deposit10k || 0) };
  }
  if (mode === "monthly" && isLiveStatus(liveStatus.molitRent) && records.monthly) {
    return { label: "월세", value: Number(records.monthly.monthlyRent10k || 0) };
  }
  return null;
}

function buildRuleBasedAiSummary(selected, detail) {
  if (!selected || !detail) return null;
  const strengths = [];
  const neutral = [];
  const cautions = [];
  const route = state.ruleSummaryRoute.selectedId === selected.id
    ? state.ruleSummaryRoute.result
    : null;

  if (
    route?.provider === "tmap"
    && route?.mode === "live_api"
    && route?.transportMode === "car"
  ) {
    const minutes = Math.round(Number(route.summary?.totalMinutes || 0));
    if (minutes > 0 && minutes <= RULE_SUMMARY_COMMUTE_THRESHOLD_MINUTES) {
      strengths.push(`자차 기준 약 ${formatNumber(minutes)}분으로 이동이 편리합니다.`);
    } else if (minutes > RULE_SUMMARY_COMMUTE_THRESHOLD_MINUTES) {
      cautions.push(`자차 기준 약 ${formatNumber(minutes)}분이 소요되어 이동 부담이 있을 수 있습니다.`);
    }
  }

  const price = detail.price || {};
  const actualPrice = liveBudgetPrice(price);
  const budget = Number(state.budget || 0);
  if (actualPrice?.value > 0 && budget > 0) {
    const difference = Math.round(actualPrice.value - budget);
    const priceText = formatBudgetValue(actualPrice.value, state.budgetMode);
    const differenceText = formatBudgetValue(Math.abs(difference), state.budgetMode);
    if (difference < 0) {
      strengths.push(`${actualPrice.label}는 ${priceText}으로, 설정하신 예산보다 약 ${differenceText} 저렴합니다.`);
    } else if (difference === 0) {
      neutral.push(`${actualPrice.label}는 설정하신 예산과 비슷한 수준입니다.`);
    } else {
      cautions.push(`${actualPrice.label}는 ${priceText}으로, 설정하신 예산보다 약 ${differenceText} 높습니다.`);
    }
  }

  const liveStatus = price.liveStatus || {};
  const records = livePriceRecords(price);
  if (
    isLiveStatus(liveStatus.molitTrade)
    && isLiveStatus(liveStatus.molitRent)
    && records.trade
    && records.jeonse
  ) {
    const sale = Number(records.trade.amount10k || 0);
    const jeonse = Number(records.jeonse.deposit10k || 0);
    if (sale > 0 && jeonse > 0) {
      const ratio = (jeonse / sale) * 100;
      if (ratio < 80) {
        strengths.push(`전세가율은 ${formatPercent(ratio)}로, 깡통주택 위험 기준인 80%보다 낮습니다.`);
      } else {
        cautions.push(`전세가율은 ${formatPercent(ratio)}로, 깡통주택 위험 기준인 80% 이상입니다. 계약 전 추가 확인이 필요합니다.`);
      }
    }
  }

  if (!strengths.length && !neutral.length && !cautions.length) return null;
  return {
    headline: `${detail.name || selected.name || "선택한 아파트"}의 확인된 API 데이터를 기준으로 정리했습니다.`,
    strengths,
    neutral,
    cautions
  };
}

function renderAiSummaryCard(summary = {}) {
  const sections = [
    { label: "장점", items: summary.strengths || [] },
    { label: "중립", items: summary.neutral || [] },
    { label: "주의", items: summary.cautions || [] }
  ].filter((section) => section.items.length);
  return `
    <section class="property-card ai-summary-card">
      <div class="property-card-title">
        <h4>AI 요약</h4>
      </div>
      <p class="ai-headline">${escapeHtml(summary.headline || "확인된 API 데이터를 기준으로 정리했습니다.")}</p>
      <div class="ai-summary-grid${sections.length === 3 ? " is-three" : ""}">
        ${sections.map((section) => `
          <div>
            <strong>${escapeHtml(section.label)}</strong>
            <ul>${section.items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>
          </div>
        `).join("")}
      </div>
    </section>
  `;
}

function renderAiSummaryPendingCard() {
  return `
    <section class="property-card ai-summary-card ai-summary-card-pending">
      <div class="property-card-title">
        <h4>AI 요약</h4>
        <span>실데이터 확인 중</span>
      </div>
      <p class="ai-headline">실거래 가격과 실제 자차 경로를 불러오고 있습니다.</p>
    </section>
  `;
}

function renderAiSummaryEmptyCard() {
  return `
    <section class="property-card ai-summary-card">
      <div class="property-card-title">
        <h4>AI 요약</h4>
      </div>
      <p class="ai-headline">실제 API에서 확인된 통근·가격 데이터가 없어 요약할 항목이 없습니다.</p>
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

function renderRiskSignalDetails(risk) {
  const signals = Array.isArray(risk?.signals) ? risk.signals : [];
  if (!signals.length) return "";
  return `
    <details class="risk-detail-toggle">
      <summary>
        <span class="risk-detail-open">세부 점검 보기 ▼</span>
        <span class="risk-detail-close">세부 점검 접기 ▲</span>
      </summary>
      <ul class="risk-list">${renderRiskSignals(risk)}</ul>
    </details>
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

function renderGaptongVerdict(safeguard) {
  const verdict = safeguard?.gaptong;
  if (!verdict) return "";
  return `
    <div class="gaptong-verdict tone-${escapeHtml(verdict.verdictKey || "unknown")}">
      <div class="gaptong-head">
        <strong>깡통주택 위험 요약</strong>
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
      <p>공인중개사(안전계약 컨설턴트)가 등기부등본·건축물대장을 함께 검토합니다.</p>
      <small class="property-note">상담은 참고용이며 법적 책임을 부담하지 않습니다.</small>
      <a class="support-center-link" href="${escapeHtml(center.reserveUrl)}" target="_blank" rel="noopener noreferrer">안전계약 컨설팅 예약</a>
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

const AGENT_TOOL_LABELS = {
  lookup_apartment: "단지 조회",
  apartment_snapshot: "가격·위험 신호",
  jeonse_safeguard: "전세사기 안전장치",
  contract_checklist: "계약 체크리스트",
  safer_alternatives: "더 안전한 대안",
  commute_route: "통근 경로",
  web_search: "공공기관 웹 검색"
};

function renderAgentToolTrace(message) {
  const trace = Array.isArray(message.toolTrace) ? message.toolTrace : [];
  if (!trace.length) return "";
  const names = [...new Set(trace.map((item) => AGENT_TOOL_LABELS[item.name] || item.name))];
  return `<div class="agent-tooltrace">조회한 데이터: ${names.map((name) => escapeHtml(name)).join(" · ")}</div>`;
}

function renderAgentSources(message) {
  const sources = Array.isArray(message.sources) ? message.sources : [];
  if (!sources.length) return "";
  const links = sources
    .filter((item) => typeof item?.url === "string" && /^https?:\/\//.test(item.url))
    .map((item) => `<li><a href="${escapeHtml(item.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.title || item.url)}</a></li>`);
  if (!links.length) return "";
  return `<div class="agent-sources"><span>출처</span><ul>${links.join("")}</ul></div>`;
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
      ${renderAgentToolTrace(message)}
      ${renderAgentSources(message)}
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

  panel.hidden = !state.agent.open;
  launcher.setAttribute("aria-expanded", String(state.agent.open));
  launcher.classList.toggle("is-active", state.agent.open);
  if (!state.agent.open) return;

  const target = agentTarget();
  const context = document.querySelector("#agentContextLabel");
  if (context) {
    const engine = state.agent.llmMode === true
      ? ` · ${state.agent.llmModel || "Claude"} 연동`
      : "";
    context.textContent = (target
      ? `${target.name} 기준으로 답변합니다`
      : "매칭을 실행하거나 단지를 선택하면 그 단지 기준으로 답변합니다") + engine;
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
  dismissAgentHint();
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

function dismissAgentHint() {
  const launcher = document.querySelector("#agentLauncher");
  document.querySelector(".agent-hint")?.remove();
  if (agentHintTimer) {
    window.clearTimeout(agentHintTimer);
    agentHintTimer = null;
  }
  launcher?.classList.remove("is-hinting");
  launcher?.classList.add("is-hinted");
}

function showAgentHint() {
  const launcher = document.querySelector("#agentLauncher");
  if (
    !launcher
    || state.agent.open
    || state.bookmarks.panelOpen
    || launcher.classList.contains("is-hinted")
    || document.querySelector(".agent-hint")
  ) return;

  const hint = document.createElement("div");
  hint.className = "agent-hint";
  hint.innerHTML = `
    <p><strong>AI Agent</strong><br>전세 안전성이나 계약 전 확인 서류를 질문할 수 있어요.</p>
    <button class="agent-hint-close" type="button" aria-label="AI Agent 안내 닫기">×</button>
  `;

  const rect = launcher.getBoundingClientRect();
  hint.style.top = `${Math.round(rect.bottom + 12)}px`;
  hint.style.right = `${Math.max(18, Math.round(window.innerWidth - rect.right))}px`;
  hint.style.setProperty("--tail-right", `${Math.round(rect.width / 2)}px`);

  launcher.classList.add("is-hinting");
  launcher.insertAdjacentElement("afterend", hint);
  hint.querySelector(".agent-hint-close")?.addEventListener("click", dismissAgentHint);
  agentHintTimer = window.setTimeout(dismissAgentHint, 6500);
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
    if (await agentLlmAvailable()) {
      await sendAgentMessageViaLlm(target);
    } else {
      await sendAgentMessageViaRules(target, text);
    }
  } catch (error) {
    state.agent.error = `AI Agent 응답 실패: ${error.message}`;
  } finally {
    state.agent.isLoading = false;
    renderAgentPanel();
  }
}

async function agentLlmAvailable() {
  if (state.agent.llmMode !== null) return state.agent.llmMode;
  try {
    const status = await fetchJson("/api/agent-status");
    state.agent.llmMode = Boolean(status.available);
    state.agent.llmReason = status.reason || "";
    state.agent.llmModel = status.model || "";
  } catch {
    state.agent.llmMode = false;
    state.agent.llmReason = "AI 상태를 확인하지 못해 기본 답변으로 안내합니다.";
  }
  return state.agent.llmMode;
}

function agentHistoryForLlm() {
  return state.agent.messages
    .map((message) => ({
      role: message.role === "user" ? "user" : "assistant",
      content: message.role === "user" ? message.text : message.answer?.answer || message.text || ""
    }))
    .filter((message) => message.content);
}

async function sendAgentMessageViaLlm(target) {
  const response = await fetch("/api/agent-chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages: agentHistoryForLlm(),
      context: `사용자가 현재 보고 있는 단지: ${target.name} (id: ${target.id})`
    })
  });
  const payload = await response.json().catch(() => ({}));

  if (!response.ok || !payload.ok) {
    state.agent.llmMode = false;
    state.agent.llmReason = payload.error || `LLM 응답 실패 (${response.status})`;
    await sendAgentMessageViaRules(target, state.agent.messages.at(-1)?.text || "");
    return;
  }

  state.agent.messages.push({
    role: "agent",
    answer: { answer: payload.answer, disclaimer: agentDisclaimer() },
    target: target.name,
    toolTrace: payload.toolTrace || [],
    sources: payload.sources || [],
    engine: "llm"
  });
  state.agent.followUps = AGENT_DEFAULT_FOLLOW_UPS;
}

async function sendAgentMessageViaRules(target, text) {
  const params = new URLSearchParams({ id: target.id, question: text });
  const payload = await fetchJson(`/api/property-agent?${params.toString()}`);
  const answer = payload.agent || null;
  state.agent.messages.push({ role: "agent", answer, target: target.name, engine: "rules" });
  state.agent.followUps = answer?.followUps || [];
}

function agentDisclaimer() {
  return "전세 위험 신호는 법적 판정이 아니며, 등기부등본·건축물대장·임대인 세금 체납 여부 확인을 대체하지 않습니다.";
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
  document.body.classList.toggle("bookmark-panel-open", state.bookmarks.panelOpen);
  if (state.bookmarks.panelOpen) {
    dismissAgentHint();
  }
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
  state.detailPanelOpen = false;
  closePropertyDashboard();
  renderDetailSubpanelState();
  renderBookmarkPanel();
  loadBookmarkDetails();
}

function closeBookmarkPanel() {
  state.bookmarks.panelOpen = false;
  renderBookmarkPanel();
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
          ${propertyMetric("주차대수", parkingCount ? `${formatNumber(parkingCount)}대` : "정보 없음", parkingCount ? parkingPerHousehold : "제공 정보 없음")}
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
          <span>최근 12개월</span>
        </div>
        ${renderTrendChart(detail.transactions)}
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
      <section class="property-card wide jeonse-risk-card">
        <div class="property-card-title">
          <h4>전세 위험 신호 점검</h4>
        </div>
        ${renderGaptongVerdict(safeguard)}
        <p class="risk-summary">${escapeHtml(risk.disclaimer || "")}</p>
        ${renderRiskSignalDetails(risk)}
      </section>

      <section class="property-card wide">
        <div class="property-card-title">
          <h4>계약 전 확인 체크리스트</h4>
        </div>
        ${renderContractChecklist(risk)}
      </section>

      <section class="property-card wide">
        <div class="property-card-title">
          <h4>정보 사각지대</h4>
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
        </div>
        ${renderTenancyTimeline(safeguard)}
        <h5 class="safeguard-subtitle">공백을 막는 특약 문구</h5>
        ${renderSpecialClauses(safeguard)}
      </section>

      <section class="property-card wide">
        <div class="property-card-title">
          <h4>가까운 안전계약 컨설팅</h4>
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
      const selected = selectedMatchResult();
      if (state.property.detail && selected?.id === id) {
        loadRuleSummaryCarRoute(selected);
      }
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
      <li style="--route-color:#14B8A6">
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
  const aiSummary = selectedDetail ? buildRuleBasedAiSummary(selected, selectedDetail) : null;
  const aiSummaryPending = state.property.selectedId === selected.id && (
    state.property.isLoading
    || (state.ruleSummaryRoute.selectedId === selected.id && state.ruleSummaryRoute.isLoading)
  );
  const aiSummaryContent = aiSummaryPending
    ? renderAiSummaryPendingCard()
    : aiSummary
      ? renderAiSummaryCard(aiSummary)
      : renderAiSummaryEmptyCard();
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
      ${aiSummaryContent}
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
        ${scoreRow("통근", selected.adjusted.commute, scoreTips.commute)}
        ${scoreRow("주거비", selected.adjusted.cost, scoreTips.cost)}
        ${scoreRow("생활 SOC", selected.adjusted.service, scoreTips.service)}
        ${scoreRow("안전", selected.adjusted.safety, scoreTips.safety)}
      </div>
    </section>
    ${aiSummaryContent}
    ${renderAgentCtaCard()}
  `;
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
  return `
    <button class="infrastructure-item${state.infrastructureFocus.category === category ? " is-active" : ""}" type="button" data-infrastructure-category="${escapeHtml(category)}">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
      <small>${escapeHtml(name)}${distance ? ` · ${escapeHtml(distance)}` : ""}</small>
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
  state.ruleSummaryRouteRequestId += 1;
  state.route = {
    selectedId: null,
    isLoading: false,
    result: null,
    error: "",
    focusMap: false,
    transportMode
  };
  state.ruleSummaryRoute = {
    selectedId: null,
    isLoading: false,
    result: null,
    error: ""
  };
  if (state.map?.routeLayer) {
    state.map.routeLayer.clearLayers();
  }
}

async function loadRuleSummaryCarRoute(selected) {
  if (!selected?.id) return;
  const current = state.ruleSummaryRoute;
  if (current.selectedId === selected.id && (current.isLoading || current.result)) return;

  const requestId = state.ruleSummaryRouteRequestId + 1;
  state.ruleSummaryRouteRequestId = requestId;
  const origin = representativeAddressFor(selected);
  if (!origin) {
    state.ruleSummaryRoute = {
      selectedId: selected.id,
      isLoading: false,
      result: null,
      error: "아파트 주소를 확인할 수 없습니다."
    };
    return;
  }

  const destinationLocation = selectedDestinationLocation();
  const destinationText = selected.destinationAddress || destinationAddressFor();
  const params = new URLSearchParams({
    origin,
    provider: "tmap",
    transportMode: "car",
    destinationAddress: destinationLocation?.address || destinationText
  });
  const destination = destinationCoordinatesForRequest();
  if (destination) {
    params.set("destinationLat", destination.lat);
    params.set("destinationLng", destination.lng);
  }
  if (state.destinationQuery.trim()) {
    params.set("destinationQuery", state.destinationQuery.trim());
  } else {
    params.set("destination", state.destination);
  }

  state.ruleSummaryRoute = {
    selectedId: selected.id,
    isLoading: true,
    result: null,
    error: ""
  };
  renderDetail();

  try {
    const payload = await fetchJson(`/api/commute-route?${params.toString()}`);
    if (requestId !== state.ruleSummaryRouteRequestId) return;
    state.ruleSummaryRoute = {
      selectedId: selected.id,
      isLoading: false,
      result: payload,
      error: ""
    };
  } catch (error) {
    if (requestId !== state.ruleSummaryRouteRequestId) return;
    state.ruleSummaryRoute = {
      selectedId: selected.id,
      isLoading: false,
      result: null,
      error: error.message || "자동차 경로를 불러오지 못했습니다."
    };
  } finally {
    if (requestId === state.ruleSummaryRouteRequestId) renderDetail();
  }
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

function budgetTargetValue(item = {}, mode = state.budgetMode) {
  const pricePreview = item.pricePreview || {};
  if (mode === "sale") return Math.round(Number(item.sale10k || pricePreview.sale10k || 0));
  if (mode === "jeonse") return Math.round(Number(item.jeonse10k || pricePreview.jeonse10k || 0));
  return Math.round(Number(item.rentMonthly10k || item.monthlyRent10k || pricePreview.monthlyRent10k || 0));
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
  syncMapModeControls();
  if (nodes.budgetOutput && document.activeElement !== nodes.budgetOutput) {
    nodes.budgetOutput.value = displayBudgetValue(state.budget);
  }
  nodes.commuteWeightOutput.textContent = `${state.weights.commute}%`;
  nodes.costWeightOutput.textContent = `${state.weights.cost}%`;
  nodes.serviceWeightOutput.textContent = `${state.weights.service}%`;
  nodes.safetyWeightOutput.textContent = `${state.weights.safety}%`;
  if (nodes.voiceWeightButton) {
    const supported = Boolean(speechRecognitionConstructor());
    nodes.voiceWeightButton.disabled = false;
    nodes.voiceWeightButton.setAttribute("aria-disabled", supported ? "false" : "true");
    nodes.voiceWeightButton.classList.toggle("is-listening", state.voiceWeights.listening);
    nodes.voiceWeightButton.setAttribute("aria-pressed", state.voiceWeights.listening ? "true" : "false");
    nodes.voiceWeightButton.title = supported ? "상황 말하기" : "음성 인식 미지원";
    nodes.voiceWeightButton.onclick = startVoiceWeightRecognition;
  }
  if (nodes.voiceWeightStatus) {
    nodes.voiceWeightStatus.hidden = !state.voiceWeights.status;
    nodes.voiceWeightStatus.textContent = voiceStatusDisplayText(state.voiceWeights.status);
  }
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
  const target = document.getElementById(sectionId) ? sectionId : "home";
  state.activeSection = target;
  document.body.classList.toggle("is-map-view", target === "map");
  document.querySelectorAll("main > .anchor-target").forEach((section) => {
    section.classList.toggle("is-active-view", section.id === target);
  });
  setActiveNav(target);

  if (options.updateHash && window.location.hash !== `#${target}`) {
    window.history.pushState(null, "", `#${target}`);
  }

  if ((target === "map" || target === "recommend") && state.map?.instance) {
    window.setTimeout(() => {
      state.map.instance.invalidateSize();
      if (state.apartments.enabled) {
        scheduleApartmentLayerLoad();
      }
      focusSelectedMarker();
    }, 80);
  }

  if (target === "recommend") {
    window.setTimeout(showAgentHint, 260);
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
    activateSection(window.location.hash.replace("#", "") || "home");
  });
  activateSection(window.location.hash.replace("#", "") || "home");
}

function openRecommendFromHome({ agent = false } = {}) {
  activateSection("recommend", { updateHash: true });
  window.setTimeout(() => {
    state.map?.instance?.invalidateSize({ pan: false });
    if (agent) {
      openAgentPanel();
      return;
    }
    nodes.destinationInput?.focus();
  }, 100);
}

function resetUserSettings() {
  clearVoiceWeightTimers();
  try {
    state.voiceWeights.recognition?.abort?.();
  } catch {
    // Ignore cleanup failures while resetting UI state.
  }
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
  state.mapMode = "normal";
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
  state.voiceWeights.status = "";
  state.voiceWeights.listening = false;
  state.voiceWeights.transcript = "";
  state.voiceWeights.errorStatus = "";

  nodes.budgetInput.value = state.budget;
  nodes.budgetOutput.value = displayBudgetValue(state.budget);
  nodes.destinationInput.value = state.destinationQuery;
  document.querySelector("input[name='budgetMode'][value='monthly']").checked = true;
  syncBudgetModeControls();
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

function initHomeShowcaseCarousel() {
  document.querySelectorAll("[data-showcase-carousel]").forEach((carousel) => {
    const slides = Array.from(carousel.querySelectorAll(".home-showcase-slide"));
    const captions = Array.from(carousel.querySelectorAll(".home-showcase-caption-item"));
    if (slides.length < 2) return;
    let carouselTimer = null;
    const dots = document.createElement("div");
    dots.className = "home-showcase-dots";
    dots.setAttribute("aria-label", "화면 미리보기 선택");

    const dotButtons = slides.map((slide, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "home-showcase-dot";
      button.setAttribute("aria-label", `${slide.alt || "미리보기"} 보기`);
      button.addEventListener("click", () => {
        activeIndex = index;
        setActiveShowcaseItem(activeIndex);
        restartCarouselTimer();
      });
      dots.append(button);
      return button;
    });

    carousel.append(dots);

    const setActiveShowcaseItem = (index) => {
      slides.forEach((slide, slideIndex) => {
        const isActive = slideIndex === index;
        slide.classList.toggle("is-active", isActive);
        slide.setAttribute("aria-hidden", isActive ? "false" : "true");
      });

      captions.forEach((caption, captionIndex) => {
        caption.classList.toggle("is-active", captionIndex === index);
      });

      dotButtons.forEach((button, buttonIndex) => {
        const isActive = buttonIndex === index;
        button.classList.toggle("is-active", isActive);
        button.setAttribute("aria-current", isActive ? "true" : "false");
      });
    };

    const restartCarouselTimer = () => {
      if (carouselTimer) {
        window.clearInterval(carouselTimer);
      }
      carouselTimer = window.setInterval(() => {
        activeIndex = (activeIndex + 1) % slides.length;
        setActiveShowcaseItem(activeIndex);
      }, 5000);
    };

    let activeIndex = Math.max(0, slides.findIndex((slide) => slide.classList.contains("is-active")));
    setActiveShowcaseItem(activeIndex);
    restartCarouselTimer();
  });
}

function bindEvents() {
  bindSidebarResize();
  initHomeShowcaseCarousel();

  document.querySelectorAll("[data-start-recommend]").forEach((button) => {
    button.addEventListener("click", () => openRecommendFromHome());
  });

  document.querySelectorAll("[data-start-agent]").forEach((button) => {
    button.addEventListener("click", () => openRecommendFromHome({ agent: true }));
  });

  nodes.budgetInput.addEventListener("input", (event) => {
    setBudget(event.target.value);
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

  document.querySelectorAll("input[name='budgetMode']").forEach((radio) => {
    radio.addEventListener("change", (event) => {
      if (event.target.checked) {
        setBudgetMode(event.target.value, { refresh: true });
      }
    });
  });

  document.querySelectorAll("input[name='persona']").forEach((radio) => {
    radio.addEventListener("change", (event) => {
      if (event.target.checked) {
        state.persona = event.target.value;
        applyPersonaDefaultWeights(state.persona);
        state.voiceWeights.status = "";
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
      state.voiceWeights.status = "";
      scheduleRefresh();
    });
  });

  nodes.voiceWeightButton?.addEventListener("click", startVoiceWeightRecognition);

  nodes.mapModeButtons?.forEach((button) => {
    button.addEventListener("click", () => setMapMode(button.dataset.mapMode));
  });

  nodes.sunlightTimeInput?.addEventListener("input", (event) => {
    setSunlightMinutes(event.target.value);
  });

  nodes.sunlightNowButton?.addEventListener("click", () => {
    setSunlightMinutes(currentDayMinutes());
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

    if (!Number(state.budget)) {
      state.hasMatched = false;
      state.matchValidationMessage = `${budgetConfig().label}을 입력해주세요.`;
      state.results = [];
      state.selectedId = null;
      state.showAllCards = false;
      state.detailPanelOpen = false;
      render();
      nodes.budgetInput?.focus();
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
  window.lucide?.createIcons();
  await loadAreas();
  await loadApartmentCandidates();
  render();
  window.lucide?.createIcons();
}

init().catch((error) => {
  nodes.cards.innerHTML = `<div class="empty-state">데이터를 불러오지 못했습니다.</div>`;
  nodes.detailContent.innerHTML = `<div class="callout"><p>데이터를 불러오지 못했습니다: ${error.message}</p></div>`;
});
