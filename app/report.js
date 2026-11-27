// 전세 안심 판정 리포트 (지도 위 패널). 판정 규칙은 서버 api/jeonse_verdict.py 한곳에만 둔다.
// 열기: [data-open-report="단지 id"] 버튼 또는 window.FitHomeReport.open({ id, deposit10k, listing }).
(() => {
  const LS = "fithome.report.";
  const POLL_MS = 15000;
  const st = { detail: null, base: null, verdict: null, feedback: [], tab: "detail", rightsTab: "rights", filter: "all", poll: null };

  const RESULT = {
    pass: ["통과", "r-pass", "✓"],
    caution: ["주의", "r-caution", "!"],
    danger: ["위험", "r-danger", "✕"],
    unknown: ["미확인", "r-unknown", "?"],
  };
  const GRADE_COPY = {
    safe: "핵심 항목을 서류로 확인했고 위험 신호가 없어요",
    check: "핵심 자료를 확인해야 판단할 수 있어요",
    caution: "계약 전에 주의 신호를 짚어 봐야 해요",
    danger: "계약을 멈추고 확인하세요",
  };
  const AREA_ORDER = ["rights", "ratio", "landlord", "building", "reports"];
  const AREA_LABELS = { rights: "권리관계", ratio: "가격·비율", landlord: "임대인", building: "건물", reports: "제보" };
  const KIND_FILTER = { ownership: ["ownership"], mortgage: ["mortgage", "mortgageRelease"], caution: ["trust", "seizure", "auction", "leaseRegistration", "report"] };
  const TABS = [
    ["detail", "상세 판정"],
    ["intake", "서류·인증"],
    ["registry", "정보 입력"],
    ["contract", "계약 일정"],
    ["support", "보증·지원 제도"],
    ["history", "이력·제보"],
  ];
  const HOUSING = [["apartment", "아파트"], ["villa", "빌라·다세대"], ["officetel", "오피스텔"], ["multi", "다가구"]];
  const LISTING_SOURCES = ["네이버 부동산", "직방", "다방", "피터팬", "중개사무소", "기타"];
  const TRI = [["no", "없음"], ["yes", "있음"], ["unknown", "모름"]];

  const overlay = () => document.getElementById("reportOverlay");
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const store = {
    get(key, fallback) {
      try {
        const raw = localStorage.getItem(LS + key);
        return raw === null ? fallback : JSON.parse(raw);
      } catch {
        return fallback;
      }
    },
    set(key, value) {
      localStorage.setItem(LS + key, JSON.stringify(value));
    },
  };

  function money(value) {
    if (value === null || value === undefined || value === "" || Number.isNaN(Number(value))) return "미확인";
    let amount = Math.round(Number(value));
    const sign = amount < 0 ? "-" : "";
    amount = Math.abs(amount);
    const eok = Math.floor(amount / 10000);
    const man = amount % 10000;
    if (eok && man) return `${sign}${eok}억 ${man.toLocaleString()}만원`;
    if (eok) return `${sign}${eok}억원`;
    return `${sign}${man.toLocaleString()}만원`;
  }
  const chip = (result) => {
    const [label, cls, mark] = RESULT[result] || RESULT.unknown;
    return `<span class="r-chip ${cls}"><b aria-hidden="true">${mark}</b>${label}</span>`;
  };
  const srcChip = (source, label) => `<span class="src-chip src-${esc(source)}">${esc(label)}</span>`;
  // 근거 수준: 서버가 확인한 값만 '서류 확인'이다(api/jeonse_verdict.py assign_evidence).
  // 출처 칩이 이미 '미확인'이거나 보조 항목이면 '미확인' 근거 칩을 겹쳐 보이지 않는다.
  const evChip = (c) => (c.evidence && !(c.evidence === "none" && (c.source === "none" || !c.core)) ? `<span class="ev-chip ev-${esc(c.evidence)}" title="근거 수준${c.core ? " · 핵심 항목" : ""}">${esc(c.evidenceLabel)}</span>` : "");

  async function api(path, options = {}) {
    const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
    const payload = await response.json();
    if (!response.ok || payload.ok === false) throw new Error(payload.error || `요청 실패 (${response.status})`);
    return payload;
  }

  function toast(message) {
    let node = document.getElementById("fhToast");
    if (!node) {
      node = document.createElement("div");
      node.id = "fhToast";
      node.className = "fh-toast";
      document.body.appendChild(node);
    }
    node.textContent = message;
    node.classList.add("is-on");
    clearTimeout(node.hideTimer);
    node.hideTimer = setTimeout(() => node.classList.remove("is-on"), 1700);
  }
  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
    } catch {
      const area = document.createElement("textarea");
      area.value = text;
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      area.remove();
    }
    toast("복사했어요");
  }

  // ---------- 입력 만들기 ----------

  function baseInput(detail, opts = {}) {
    const price = detail.price || {};
    const saleIsTrade = price.recentSale10k > 0 && (price.saleLive ?? (price.molitLatestTradeRecord?.amount10k === price.recentSale10k));
    const rentIsTrade = price.recentJeonse10k > 0 && (price.jeonseLive ?? (price.molitLatestJeonseRecord?.deposit10k === price.recentJeonse10k));
    const sale = saleIsTrade ? price.saleMedian10k ?? price.recentSale10k : price.recentSale10k;
    const rent = rentIsTrade ? price.jeonseMedian10k ?? price.recentJeonse10k : price.recentJeonse10k;
    const medianLabel = rentIsTrade && price.jeonseMedian10k && price.areaM2
      ? `국토교통부 전용 ${price.areaM2}㎡ 전세 실거래 중앙값` : "";
    const listing = opts.listing || null;
    return {
      key: listing ? `listing:${listing.id}` : `apt:${detail.id}`,
      property: {
        label: listing ? `${detail.name} · ${listing.title}` : detail.name,
        address: detail.address,
        housingType: "apartment",
      },
      deposit10k: opts.deposit10k ?? null,
      price: { basis: "market", value10k: sale ?? null, official10k: price.officialPrice10k ?? null, officialSource: price.liveStatus?.publicPrice?.mode === "live_api" ? "public" : "estimate", source: saleIsTrade ? "trade" : "estimate" },
      market: {
        jeonse10k: rent ?? null,
        surroundingJeonse10k: price.surroundingAverageJeonse10k ?? null,
        source: rentIsTrade ? "trade" : "estimate",
        sourceLabel: medianLabel || (rentIsTrade ? "국토교통부 전세 실거래" : "추정 전세 시세"),
      },
      center: detail.safeguard?.center || null,
      listing: listing ? { source: "핏홈 매물(시연)", url: "" } : {},
      schedule: {},
      registry: { source: "none", trust: "unknown", seizure: "unknown", auction: "unknown", leaseRegistration: "unknown", ownerMatches: "unknown" },
      landlord: { source: "input", taxArrears: "unknown", guaranteeEligible: "unknown" },
      building: { source: "public", use: detail.buildingLedger?.mode === "live_api" ? detail.buildingLedger.use : "unknown", violation: "unknown" },
      requests: {},
      inspection: { status: "none" },
      history: detail.approvalDate
        ? [{ date: detail.approvalDate, kind: "building", title: "사용승인", detail: `${detail.households || "-"}세대 · ${detail.buildingCount || "-"}개 동` }]
        : [],
    };
  }

  // 선택 단지와 다른 주소의 가격·권리·서류가 서로 섞이지 않게 주소별 리포트를 분리한다.
  function cleanAddress(value) {
    const address = String(value || "").normalize("NFC").trim().replace(/\s+/g, " ");
    if (address.length < 4 || address.length > 220) throw new Error("점검할 주택의 전체 주소를 입력해 주세요.");
    return address;
  }

  function setReportAddress(address, housingType) {
    const original = st.original;
    const choices = store.get("addressReports", []);
    const normalized = cleanAddress(address);
    const isOriginal = housingType === original.property.housingType && normalized === original.property.address.normalize("NFC").trim().replace(/\s+/g, " ");
    let match = choices.find((row) => row.address === normalized);
    if (!isOriginal && !match) {
      match = store.get(original.key + ".addresses", []).find(row => row.address === normalized);
      if (!match) {
        const random = Array.from(crypto.getRandomValues(new Uint8Array(16)), x => x.toString(16).padStart(2, "0")).join("");
        match = { address: normalized, key: "address:" + random };
      }
      store.set("addressReports", [...choices, match]);
    }
    st.base = structuredClone(original);
    if (!isOriginal) {
      Object.assign(st.base, {
        key: match.key, property: { label: normalized, address: normalized, housingType },
        price: {}, market: {}, deposit10k: null, listing: {}, center: null, history: [],
        building: { use: "unknown", violation: "unknown", source: "none" },
      });
    }
    const edits = store.get(st.base.key + ".edits", {});
    store.set(st.base.key + ".edits", { ...edits, housingType });
    st.feedback = [];
  }

  function currentInput() {
    const base = st.base;
    const key = base.key;
    const e = store.get(`${key}.edits`, {});
    const next = structuredClone(base);
    const num = (v) => (v === "" || v === null || v === undefined ? null : Number(v));
    if (num(e.deposit10k) !== null) next.deposit10k = num(e.deposit10k);
    if (e.priceBasis === "market" && num(e.priceValue10k) !== null) next.price = { ...next.price, basis: "market", value10k: num(e.priceValue10k), source: "input" };
    if (e.priceBasis === "official") next.price = { ...next.price, basis: "official", source: num(e.official10k) !== null ? "input" : next.price.officialSource || "none" };
    if (num(e.official10k) !== null) next.price.official10k = num(e.official10k);

    const reg = next.registry;
    let touched = false;
    for (const f of ["trust", "seizure", "auction", "leaseRegistration", "ownerMatches"]) {
      if (e[f] && e[f] !== "unknown") {
        reg[f] = e[f];
        touched = true;
      }
    }
    if (e.issuedAt) {
      reg.issuedAt = e.issuedAt;
      touched = true;
    }
    if (e.lastOwnershipChange) {
      reg.lastOwnershipChange = e.lastOwnershipChange;
      next.history.push({ date: e.lastOwnershipChange, kind: "ownership", title: "소유권 이전", detail: "등기부 갑구 입력값" });
      touched = true;
    }
    if (!e.mortgageUnknown && num(e.mortgageMax10k) !== null) {
      reg.mortgageMax10k = num(e.mortgageMax10k);
      if (reg.mortgageMax10k > 0) next.history.push({ date: e.issuedAt || "", kind: "mortgage", title: "근저당 (열람 기준)", detail: `채권최고액 합계 ${money(reg.mortgageMax10k)}` });
      touched = true;
    }
    if (touched) reg.source = "input";
    // '등기부' 근거는 서버가 발급한 근거 번호로만 붙는다. 화면은 번호만 전달한다.
    const registryEvidenceId = intake.registryEvidence()?.evidenceId;
    if (registryEvidenceId) next.registryEvidenceId = registryEvidenceId;
    if (e.violation && e.violation !== "unknown") next.building.violation = e.violation;
    if (e.useEdited || e.use === "nonresidential") {
      next.building.use = e.use;
      next.building.source = "input";
    }
    if (e.housingType) next.property.housingType = e.housingType;
    if (next.property.housingType !== "multi" && num(e.priorDeposits10k) !== null) next.landlord.priorDeposits10k = num(e.priorDeposits10k);
    const documentRequest = store.get(key + ".documentRequest", null);
    // 같은 주소의 서류 요청이 있으면 유형과 상관없이 보낸다(다가구 선순위, 납세증명서 확인).
    if (documentRequest?.address === next.property.address) {
      next.documentOwnerToken = documentRequest.ownerToken;
    }
    if (e.listingSource || e.listingUrl) next.listing = { source: e.listingSource || "", url: e.listingUrl || "" };
    next.schedule = { contractDate: e.contractDate || "", moveInDate: e.moveInDate || "", endDate: e.endDate || "" };
    if (num(e.auctionRatePct) !== null) next.auction = { ratePct: num(e.auctionRatePct) };

    // 확인 요청 기록과 받은 값
    next.requests = { ...next.requests, ...store.get(`${key}.requests`, {}) };
    const o = store.get(`${key}.overrides`, {});
    next.landlord.taxArrears = shownValue(e, o, "taxArrears");
    next.landlord.guaranteeEligible = shownValue(e, o, "guaranteeEligible");
    next.registry.ownerMatches = shownValue(e, o, "ownerMatches");
    if (intake.confirmedBuildingViolation()) {
      next.building.violation = "yes";
      next.building.violationSource = "reviewedPdf";
    } else if (e.violation && e.violation !== "unknown") {
      next.building.violationSource = "input";
    }
    return next;
  }

  let evaluation = 0;
  async function evaluate() {
    const request = ++evaluation;
    const input = currentInput();
    const base = st.base;
    const session = opening;
    const current = () => request === evaluation && session === opening && base === st.base;
    try {
      const result = await api("/api/jeonse-verdict", { method: "POST", body: JSON.stringify(input) });
      if (!current()) return false;
      st.verdict = result;
      st.depositKnown = input.deposit10k !== null && input.deposit10k !== undefined;
      return true;
    } catch (error) {
      if (!current()) return false;
      throw error;
    }
  }
  async function loadFeedback() {
    const key = st.base.key;
    const payload = await api(`/api/property-feedback?key=${encodeURIComponent(key)}`);
    if (st.base.key !== key) return false;
    const changed = payload.items.length !== st.feedback.length;
    st.feedback = payload.items;
    return changed;
  }

  // ---------- 열고 닫기 ----------

  let opening = 0;
  async function open({ id, deposit10k = null, listing = null, address, housingType } = {}) {
    const node = overlay();
    if (!node || (!id && !address)) return;
    const session = ++opening;
    clearInterval(st.poll);
    node.hidden = false;
    node.innerHTML = `<div class="fh-report-backdrop" data-action="close"></div><div class="fh-report-sheet"><div class="fh-report-loading">판정 리포트를 준비하고 있어요…</div></div>`;
    try {
      if (address) {
        st.original = baseInput({ id: "address-intake", name: "", address: "" });
        setReportAddress(address, housingType);
        st.tab = "intake";
        intake.select(housingType === "multi" ? "landlord" : "registry");
      } else {
        const payload = await api(`/api/property-detail?id=${encodeURIComponent(id)}`);
        if (session !== opening) return;
        st.detail = payload.detail;
        st.original = baseInput(st.detail, { deposit10k, listing });
        st.base = st.original;
        st.tab = "detail";
      }
      st.openArgs = id ? { id, deposit10k, listing: listing ? { id: listing.id, title: listing.title } : null } : null;
      st.feedback = [];
      st.filter = "all";
      await Promise.all([loadFeedback(), evaluate()]);
      if (session !== opening) return;
      await intake.poll();
      if (session !== opening) return;
      render();
      if (address) node.querySelector(`[data-intake-panel="${housingType === "multi" ? "landlord" : "registry"}"]`)?.scrollIntoView({ block: "start" });
      startPolling();
    } catch (error) {
      if (session !== opening) return;
      if (address) { close(); throw error; }
      node.querySelector(".fh-report-sheet").innerHTML = `<div class="fh-report-loading">리포트를 불러오지 못했어요: ${esc(error.message)} <button type="button" class="fh-btn" data-action="close">닫기</button></div>`;
    }
  }

  function openAddress(address, housingType) {
    if (!HOUSING.some(([key]) => key === housingType)) throw new Error("점검할 주택 유형을 선택하세요.");
    return open({ address: cleanAddress(address), housingType });
  }

  function identityReturnContext() {
    if (!st.base || overlay()?.hidden) return null;
    if (st.openArgs && st.base.key === st.original.key) return structuredClone(st.openArgs);
    return { address: st.base.property.address, housingType: st.verdict?.property.housingType || st.base.property.housingType };
  }

  async function resumeIdentity(context) {
    if (context?.id) await open(context);
    else if (context?.address) await openAddress(context.address, context.housingType);
    else return false;
    if (overlay()?.hidden || !overlay()?.querySelector(".fh-report-body")) return false;
    st.tab = "intake";
    intake.select("identity");
    render();
    overlay()?.querySelector("[data-identity-host]")?.scrollIntoView({ block: "start" });
    return true;
  }

  function close() {
    opening += 1;
    const node = overlay();
    if (node) node.hidden = true;
    clearInterval(st.poll);
  }

  function startPolling() {
    clearInterval(st.poll);
    st.poll = setInterval(async () => {
      if (overlay()?.hidden || !st.base) return;
      try {
        const session = opening;
        const base = st.base;
        const docChanged = await intake.poll();
        if (session !== opening || base !== st.base) return;
        const feedbackChanged = await loadFeedback();
        if (session === opening && base === st.base && (docChanged || feedbackChanged)) {
          if (await rerender()) toast(docChanged ? "요청한 서류가 업데이트됐어요" : "새 제보가 반영됐어요");
        }
      } catch {
        /* 다음 주기에 다시 시도 */
      }
    }, POLL_MS);
  }

  // ---------- 렌더링 ----------

  function renderSummary(v) {
    // 서버가 근거 번호를 실제로 적용했을 때만 '원문 대조'로 표시한다(만료·다른 주소면 입력값으로 본다).
    const original = v.registryEvidence?.status === "applied" ? intake.registryEvidence() : null;
    const needsRegistry = v.ltv.mortgagePending;
    const landlordStatus = v.property.housingType === "multi" ? intake.requestStatus() : "";
    const registryStatus = original
      ? `${original.source === "hyphen" ? "연동 등기부" : original.source === "uploaded_pdf" ? "제출 PDF" : "등기부"} 원문 대조 · 열람일 ${original.issuedAt}`
      : needsRegistry ? "등기부 미확인" : "근저당 직접 입력 · 원문 미확인";
    return `
      <section class="fh-card fh-summary grade-${v.grade}">
        <div class="fh-grade">
          <div class="fh-grade-badge"><span>${esc(v.gradeLabel)}</span><small>판정 등급</small></div>
          <div class="fh-grade-text">
            <h3>${esc(GRADE_COPY[v.grade])}</h3>
            <p class="fh-meta">보증금 ${st.depositKnown ? esc(money(v.ltv.deposit10k)) : "미입력"} · ${esc(v.asOf)} 기준</p>
            <p class="fh-headline">${esc(v.headline)}</p>
            ${v.grade === "check" && v.coreGaps?.length ? `<p class="fh-check-reasons">확인할 핵심 항목: ${v.coreGaps.slice(0, 3).map((g) => `<b>${esc(g.label)}</b>(${esc(g.evidenceLabel)})`).join(" · ")}${v.coreGaps.length > 3 ? ` 외 ${v.coreGaps.length - 3}개` : ""}</p>` : ""}
            ${intake.confirmedBuildingViolation() ? `<p class="fh-sub is-danger-text">제출한 건축물대장에서 위반건축물 표기를 확인했습니다.
              <button type="button" class="fh-btn" data-action="intake-tab" data-target="building">건축물대장 근거 보기</button></p>` : ""}
            ${v.property.housingType === "multi" && !v.ltv.priorDepositPending ? `<p class="fh-sub">선순위 보증금 ${esc(intake.amountLabel(v.ltv.prior10k))} · ${esc(intake.confirmedSource())} 기준</p>` : ""}
            <div class="fh-tags">${v.tags.map((t) => `<span>${esc(t)}</span>`).join("")}</div>
          </div>
        </div>
        <aside class="fh-inspect" aria-label="계약 전 서류 확인">
          <strong>계약 전 서류 확인</strong>
          <p>${esc(registryStatus)}${original && needsRegistry ? " · 최신본 필요" : ""}</p>
          ${!needsRegistry ? `<p>근저당 채권최고액 ${esc(intake.amountLabel(v.ltv.mortgage10k))}</p>` : ""}
          <button type="button" class="fh-btn primary" data-action="intake-tab" data-target="registry">${original && !needsRegistry ? "등기부 원문 근거 보기" : "이 매물 등기부 확인"}</button>
          ${landlordStatus ? `<p>${v.ltv.priorDepositPending ? "선순위 보증금 미확인" : "선순위 보증금 확인"} · ${esc(landlordStatus)}</p>
            <button type="button" class="fh-btn" data-action="intake-tab" data-target="landlord">${landlordStatus === "요청 전" || landlordStatus === "요청 만료" ? "집주인에게 남은 서류 한 번에 요청" : "집주인 서류 접수함"}</button>` : ""}
          <button type="button" class="fh-btn" data-action="intake-tab" data-target="hub">서류·인증 한눈에 보기</button>
        </aside>
      </section>`;
  }

  function renderLtv(v) {
    const l = v.ltv;
    if (l.mortgagePending || l.priorDepositPending || !st.depositKnown) return "";
    if (!l.price10k) return `<section class="fh-card"><h3>집값 대비 빚</h3><p class="fh-sub">집값이 없어 비율을 계산하지 못했어요. 정보 입력에서 집값을 입력하세요.</p></section>`;
    const scale = Math.max(100, (l.ratioPct || 0) + 8);
    const pct = (x) => ((x || 0) / l.price10k) * 100;
    const seg = (cls, x, label) =>
      x > 0 ? `<div class="${cls}" style="width:${(pct(x) / scale) * 100}%" title="${esc(label)} ${esc(money(x))}">${pct(x) / scale > 0.1 ? esc(label) : ""}</div>` : "";
    const h80 = l.headroom10k["80"];
    const h90 = l.headroom10k["90"];
    const headroom =
      h80 > 0
        ? ["safe", `현재 입력값은 집값의 80% 기준보다 <b>${esc(money(h80))}</b> 낮아요.`]
        : h90 >= 0
          ? ["caution", h90 === 0 ? "현재 입력값은 집값의 90%에 해당해요." : `집값의 80% 이상이에요. 90% 기준까지 ${esc(money(h90))} 남았어요.`]
          : ["danger", `현재 입력값이 집값의 90%를 <b>${esc(money(-h90))}</b> 넘었어요.`];
    headroom[1] += " 실제 보증 한도는 보증기관이 인정하는 주택가격과 선순위채권에 따라 달라져요.";
    return `
      <section class="fh-card">
        <div class="fh-card-head">
          <h3>집값 대비 빚 <em>LTV ${l.ratioPct}%${l.isLowerBound ? " 이상" : ""}</em></h3>
          ${srcChip(l.priceSource, `집값 근거 · ${l.priceSourceLabel}`)}
        </div>
        <div class="fh-ltv">
          ${l.lines.map((line) => `<div class="fh-ltv-line" style="left:${(line.pct / scale) * 100}%"><span>${line.pct}%</span></div>`).join("")}
          <div class="fh-ltv-price" style="left:${(100 / scale) * 100}%"></div>
          <div class="fh-ltv-bar">
            ${seg("seg-mortgage", l.mortgage10k, "근저당")}
            ${seg("seg-prior", l.prior10k, "선순위")}
            ${seg("seg-deposit", l.deposit10k, "내 보증금")}
            ${seg("seg-rest", Math.max(0, l.price10k - l.debt10k), "")}
          </div>
        </div>
        <div class="fh-legend">
          <span><i class="seg-mortgage"></i>근저당</span><span><i class="seg-prior"></i>선순위 보증금</span><span><i class="seg-deposit"></i>내 보증금</span><span><i class="seg-rest"></i>남는 집값</span>
          <span class="fh-legend-lines">${l.lines.map((line) => `${line.pct}% ${esc(line.label)}`).join(" · ")}</span>
        </div>
        <dl class="fh-numbers">
          <div><dt>집값</dt><dd>${esc(money(l.price10k))}</dd><dd class="fh-small">${esc(l.priceLabel)}</dd></div>
          <div><dt>근저당 채권최고액</dt><dd>${esc(money(l.mortgage10k))}</dd></div>
          <div><dt>선순위 보증금</dt><dd>${esc(money(l.prior10k))}</dd></div>
          <div><dt>내 보증금</dt><dd>${esc(money(l.deposit10k))}</dd></div>
        </dl>
        <p class="fh-headroom is-${headroom[0]}">${headroom[1]}</p>
      </section>`;
  }

  function areaBreakdown(checks, result) {
    return AREA_ORDER.map((area) => {
      const n = checks.filter((c) => c.area === area && c.result === result).length;
      return n ? `<span>${AREA_LABELS[area]} ${n}</span>` : "";
    }).join("");
  }

  function renderResults(v) {
    const c = v.counts;
    const cell = (result, label, n) =>
      `<button type="button" class="fh-count is-${result}" data-action="tab" data-tab="${result === "unknown" ? "intake" : "detail"}">
        <span>${label}</span><strong>${n}</strong><small>${areaBreakdown(v.checks, result) || "없음"}</small>
      </button>`;
    return `
      <section class="fh-card">
        <div class="fh-card-head"><h3>주요 판정 결과</h3><span class="fh-sub-inline">항목 ${v.checks.length}개를 기준과 비교</span></div>
        <div class="fh-counts">
          ${cell("pass", "통과", c.pass)}${cell("caution", "주의", c.caution)}${cell("danger", "위험", c.danger)}${cell("unknown", "미확인", c.unknown)}
        </div>
      </section>`;
  }

  function renderDetailTab(v) {
    const sub = `
      <div class="fh-subtabs">
        <button type="button" class="${st.rightsTab === "rights" ? "is-active" : ""}" data-action="rights-tab" data-tab="rights">권리 진단</button>
        <button type="button" class="${st.rightsTab === "all" ? "is-active" : ""}" data-action="rights-tab" data-tab="all">전체 항목 ${v.checks.length}</button>
      </div>`;
    if (st.rightsTab === "rights") {
      const rank = { danger: 0, caution: 1, unknown: 2, pass: 3 };
      return `${sub}<div class="fh-rights">${[...v.rights]
        .sort((a, b) => rank[a.result] - rank[b.result])
        .map(
          (c) => `<div class="fh-right is-${c.result}">
            <div class="fh-row"><strong>${esc(c.label)}</strong>${chip(c.result)}</div>
            <div class="fh-row"><span>${esc(c.value)}</span><span>${srcChip(c.source, c.sourceLabel)}${evChip(c)}</span></div>
            <p>${esc(c.standard)}</p>${c.note ? `<p>${esc(c.note)}</p>` : ""}
          </div>`
        )
        .join("")}</div>`;
    }
    return `${sub}${AREA_ORDER.map((area) => {
      const rows = v.checks.filter((c) => c.area === area);
      if (!rows.length) return "";
      return `<h4 class="fh-group">${AREA_LABELS[area]}</h4>
        <table class="fh-table fh-check-table">
          <thead><tr><th>항목</th><th>기준</th><th>이 집</th><th>결과</th><th>출처·근거</th></tr></thead>
          <tbody>${rows
            .map(
              (c) => `<tr><td>${esc(c.label)}${c.note ? `<small>${esc(c.note)}</small>` : ""}</td><td class="fh-std">${esc(c.standard)}</td><td>${esc(c.value)}</td><td>${chip(c.result)}</td><td>${srcChip(c.source, c.sourceLabel)}${evChip(c)}</td></tr>`
            )
            .join("")}</tbody>
        </table>`;
    }).join("")}`;
  }

  function seg(name, options, value) {
    return `<span class="fh-seg">${options
      .map(([v, label]) => `<label><input type="radio" name="${name}" value="${v}" ${value === v ? "checked" : ""}><span>${label}</span></label>`)
      .join("")}</span>`;
  }

  function renderRegistryTab() {
    const e = store.get(`${st.base.key}.edits`, {});
    const o = store.get(`${st.base.key}.overrides`, {});
    const shown = (field) => shownValue(e, o, field);
    const priceBasis = e.priceBasis || "estimate";
    const field = (label, control, hint = "") => `<label class="fh-field"><span>${label}</span>${control}${hint ? `<small>${hint}</small>` : ""}</label>`;
    const numInput = (name, value, placeholder) =>
      `<input type="number" min="0" step="0.0001" inputmode="decimal" name="${name}" value="${esc(value ?? "")}" placeholder="${esc(placeholder)}" data-money>`;
    const hint = (name) => `<span data-money-hint="${name}">${e[name] ? esc(money(e[name])) : ""}</span>`;
    const housing = e.housingType || st.base.property.housingType;
    return `
      <form class="fh-form" data-action="edits">
        <p class="fh-sub">모르는 칸은 비워 두거나 '모름'으로 두세요. 값을 넣을 때마다 판정·적정 보증금·반환 순위가 다시 계산돼요.</p>
        <h4 class="fh-group">매물</h4>
        <div class="fh-form-grid">
          ${field("매물 보증금 (만원)", numInput("deposit10k", e.deposit10k, `현재 ${st.base.deposit10k ?? ""} (추정)`), `${hint("deposit10k")} 네이버 부동산·직방 등에서 본 금액`)}
          <label class="fh-field"><span>본 곳</span><select name="listingSource"><option value="">선택 안 함</option>${LISTING_SOURCES.map((x) => `<option ${e.listingSource === x ? "selected" : ""}>${x}</option>`).join("")}</select><small>핏홈은 다른 플랫폼을 자동 수집하지 않아요</small></label>
          ${field("매물 링크 (선택)", `<input type="url" name="listingUrl" value="${esc(e.listingUrl || "")}" placeholder="https://">`, "리포트에 함께 남겨 두는 용도예요")}
          <div class="fh-field"><span>주택 유형</span>${seg("housingType", HOUSING, housing)}</div>
        </div>
        <h4 class="fh-group">집값</h4>
        <div class="fh-form-grid">
          <div class="fh-field"><span>집값 기준</span>${seg("priceBasis", [["estimate", "추정 시세"], ["market", "직접 입력"], ["official", "공시가격×140%"]], priceBasis)}</div>
          ${priceBasis === "market" ? field("시세·감정가 (만원)", numInput("priceValue10k", e.priceValue10k, "")) : ""}
          ${field("공시가격 (만원)", numInput("official10k", e.official10k, `현재 ${st.base.price.official10k ?? ""} (추정)`), "부동산공시가격알리미에서 확인")}
        </div>
        <h4 class="fh-group">등기부</h4>
        <div class="fh-form-grid">
          ${field("등기부 열람일", `<input type="date" name="issuedAt" value="${esc(e.issuedAt || "")}">`, "등기부에 적힌 발급·열람일")}
          ${field(
            "근저당 채권최고액 합계 (만원)",
            `${numInput("mortgageMax10k", e.mortgageMax10k, "을구 금액 합계")}<label class="fh-inline"><input type="checkbox" name="mortgageUnknown" ${e.mortgageUnknown ? "checked" : ""}>모름</label>`
          )}
          <div class="fh-field"><span>신탁등기 (갑구)</span>${seg("trust", TRI, e.trust || "unknown")}</div>
          <div class="fh-field"><span>압류·가압류 (갑구)</span>${seg("seizure", TRI, e.seizure || "unknown")}</div>
          <div class="fh-field"><span>경매개시결정</span>${seg("auction", TRI, e.auction || "unknown")}</div>
          <div class="fh-field"><span>임차권등기 (을구)</span>${seg("leaseRegistration", TRI, e.leaseRegistration || "unknown")}</div>
          <div class="fh-field"><span>등기부 소유자 = 계약 상대</span>${seg("ownerMatches", [["yes", "같음"], ["no", "다름"], ["unknown", "모름"]], shown("ownerMatches"))}</div>
          ${field("최근 소유권 이전일", `<input type="date" name="lastOwnershipChange" value="${esc(e.lastOwnershipChange || "")}">`, "갑구 마지막 '소유권 이전' 날짜")}
        </div>
        <h4 class="fh-group">임대인·건물</h4>
        <div class="fh-form-grid">
          ${housing === "multi" ? `<div class="fh-field"><span>선순위 보증금 합계</span><strong>${esc(money(st.verdict.ltv.prior10k))}</strong><button class="fh-btn" type="button" data-action="intake-tab" data-target="landlord">집주인 서류 확인</button></div>` : field("선순위 보증금 합계 (만원)", numInput("priorDeposits10k", e.priorDeposits10k, "확정일자 부여현황 기준"), hint("priorDeposits10k"))}
          <div class="fh-field"><span>임대인 세금 체납</span>${seg("taxArrears", TRI, shown("taxArrears"))}</div>
          <div class="fh-field"><span>전세보증보험 가입</span>${seg("guaranteeEligible", [["yes", "가능"], ["no", "불가"], ["unknown", "모름"]], shown("guaranteeEligible"))}</div>
          <div class="fh-field"><span>건축물 용도</span>${seg("use", [["residential", "주거용"], ["nonresidential", "근생 등 비주거"], ["unknown", "모름"]], (e.useEdited || e.use === "nonresidential" ? e.use : st.base.building.use) || "unknown")}</div>
          <div class="fh-field"><span>위반건축물</span>${seg("violation", TRI, e.violation || "unknown")}<small>건축물대장 첫 장 상단에 '위반건축물' 표시가 있는지 보세요 (정부24 무료)</small></div>
        </div>
        <h4 class="fh-group">계약 일정 · 계산 가정</h4>
        <div class="fh-form-grid">
          ${field("계약일", `<input type="date" name="contractDate" value="${esc(e.contractDate || "")}">`)}
          ${field("잔금·입주일", `<input type="date" name="moveInDate" value="${esc(e.moveInDate || "")}">`)}
          ${field("계약 만료일", `<input type="date" name="endDate" value="${esc(e.endDate || "")}">`, "비우면 입주일 + 2년")}
          ${field("경매 낙찰가율 가정 (%)", `<input type="number" min="30" max="120" name="auctionRatePct" value="${esc(e.auctionRatePct ?? "")}" placeholder="${esc(st.verdict?.repayment?.ratePct ?? "")}">`, "반환 순위 계산에 쓰는 값이에요")}
        </div>
        <div class="fh-form-actions">
          <button type="button" class="fh-btn" data-action="reset-edits">입력 초기화</button>
          <button type="submit" class="fh-btn primary">이 값으로 다시 판정</button>
        </div>
      </form>`;
  }

  function receivedInput(item) {
    const o = store.get(`${st.base.key}.overrides`, {});
    const radios = (field, options) =>
      `<span class="fh-seg">${options
        .map(([v, label]) => `<label><input type="radio" name="ov-${field}" value="${v}" data-action="override" data-field="${field}" ${o[field] === v ? "checked" : ""}><span>${label}</span></label>`)
        .join("")}</span>`;
    switch (item.id) {
      case "taxCert":
        return radios("taxArrears", [["no", "체납 없음"], ["yes", "체납 있음"]]);
      case "guarantee":
        return radios("guaranteeEligible", [["yes", "가입 가능"], ["no", "가입 불가"]]);
      case "ownerId":
        return radios("ownerMatches", [["yes", "소유자 일치"], ["no", "불일치"]]);
      default:
        return "";
    }
  }

  function renderChecklist(kinds) {
    const selected = Array.isArray(kinds) ? kinds : [kinds];
    const documents = st.verdict.documents.filter(doc => selected.includes(doc.id));
    const done = new Set(store.get(`${st.base.key}.docs`, []));
    const total = documents.reduce((n, d) => n + d.items.length, 0);
    const checked = documents.reduce((n, d) => n + d.items.filter((i) => done.has(i.id)).length, 0);
    const statuses = [["none", "요청 전"], ["requested", "요청함"], ["received", "받음"], ["refused", "거절"], ["noResponse", "무응답"]];
    return `
      <div class="fh-card-head" data-checklist="${esc(kinds.toString())}"><span class="src-chip">직접 확인 ${checked}/${total}</span></div>
      <div class="fh-docs">${documents
        .map((d) => {
          const q = d.request;
          const handledHere = ["registry", "building", "fixedDate", "moveIn", "tax"].includes(d.id);
          return `<article class="fh-doc is-${d.status}">
            <header class="fh-row">
              <div><strong>${esc(d.title)}</strong><small>${esc(d.id === "registry" ? "등기부 발급·열람" : d.cost)}${d.consent ? " · 동의 필요" : ""}</small></div>
              ${chip(d.status)}
            </header>
            <ul>${d.items
              .map(
                (i) => `<li><label><input type="checkbox" data-action="doc" data-id="${esc(i.id)}" ${done.has(i.id) ? "checked" : ""}>
                  <span><b>${esc(i.text)}</b><small>서류 위치 · ${esc(i.where)}</small></span></label>
                  ${i.result ? `<span class="fh-doc-state">${esc(i.value || "")} ${chip(i.result)}</span>` : `<span class="fh-doc-state is-manual">직접 확인</span>`}</li>`
              )
              .join("")}</ul>
            <footer class="fh-actions">
              ${!handledHere ? d.links.map((l) => `<a class="fh-btn" href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)} ↗</a>`).join("") : ""}
              ${q ? `<select data-action="req-status" data-id="${esc(q.id)}" aria-label="${esc(q.title)} 요청 상태">${statuses.map(([value, label]) => `<option value="${value}" ${q.status === value ? "selected" : ""}>${label}</option>`).join("")}</select>
                     ${!handledHere ? `<button class="fh-btn" type="button" data-action="copy" data-text="${esc(q.template)}">요청문 복사</button>` : ""}
                     ${q.status === "received" ? receivedInput(q) : ""}` : ""}
            </footer>
          </article>`;
        })
        .join("")}</div>`;
  }

  function renderContractTab(v) {
    const done = new Set(store.get(`${st.base.key}.stages`, []));
    const total = v.stages.reduce((sum, s) => sum + s.items.length, 0);
    const checked = v.stages.reduce((sum, s) => sum + s.items.filter((i) => done.has(`${s.id}.${i.id}`)).length, 0);
    return `
      <div class="fh-card-head"><h4 class="fh-group">단계별 재확인</h4><span class="src-chip">${checked}/${total} 완료</span></div>
      <div class="fh-progress"><div style="width:${total ? (checked / total) * 100 : 0}%"></div></div>
      <div class="fh-stages">${v.stages
        .map(
          (s, i) => `<div class="fh-stage"><h5>${i + 1}. ${esc(s.label)}</h5>${s.items
            .map((it) => `<label><input type="checkbox" data-action="stage" data-id="${esc(`${s.id}.${it.id}`)}" ${done.has(`${s.id}.${it.id}`) ? "checked" : ""}><span>${esc(it.text)}</span></label>`)
            .join("")}</div>`
        )
        .join("")}</div>
      <h4 class="fh-group">추천 특약</h4>
      <p class="fh-sub">판정 결과에 맞춰 골랐어요. 참고 문구이니 계약 전 전문가 검토를 권해요.</p>
      <div class="fh-list">${v.clauses
        .map(
          (c) => `<div class="fh-item"><div class="fh-row"><strong>${esc(c.title)}</strong><button class="fh-btn" type="button" data-action="copy" data-text="${esc(c.text)}">문구 복사</button></div>
            <p>${esc(c.text)}</p><small>${esc(c.reason)} · ${esc(c.basis)}</small></div>`
        )
        .join("")}</div>
      ${renderAftercare(v.aftercare)}`;
  }

  function renderAftercare(a) {
    const PHASE = { contract: "계약 직후", balance: "잔금·입주", after: "입주 후", trouble: "문제가 생기면" };
    return `
      <div class="fh-card-head"><h4 class="fh-group">계약 후 관리</h4>
        ${a.hasDates ? `<button class="fh-btn" type="button" data-action="ics">휴대폰 일정으로 저장</button>` : `<button class="fh-btn" type="button" data-action="tab" data-tab="registry">계약일·입주일 넣기</button>`}</div>
      <p class="fh-sub">${a.hasDates ? "넣은 날짜로 할 일을 계산했어요. 일정 파일(.ics)로 저장하면 알림을 받을 수 있어요." : "정보 입력 탭에 계약일·입주일을 넣으면 날짜가 계산돼요."} </p>
      <ol class="fh-after">${a.items
        .map(
          (i) => `<li class="ph-${esc(i.phase)}">
            <time>${esc(i.date || i.when || "")}</time>
            <div><strong>${esc(i.title)}</strong><span class="fh-phase">${esc(PHASE[i.phase] || "")}</span>
              <p>${esc(i.detail)}</p>
              <small>${i.basis ? `${esc(i.basis)} · ` : ""}${["registryBalance", "registryNext"].includes(i.id) ? '<button type="button" class="fh-btn" data-action="intake-tab" data-target="registry">이 매물 등기부 확인</button>' : i.link ? `<a href="${esc(i.link.url)}" target="_blank" rel="noopener">${esc(i.link.label)} ↗</a>` : ""}</small></div>
          </li>`
        )
        .join("")}</ol>`;
  }

  function renderSupportTab(v) {
    const g = v.guarantees;
    const cls = { likely: "pass", check: "unknown", unlikely: "danger" }[g.status];
    return `
      <div class="fh-guarantee is-${cls}">
        <div class="fh-row"><strong>전세보증금 반환보증 가입 가능성</strong>${chip(cls === "pass" ? "pass" : cls)}</div>
        <p class="fh-big">${esc(g.statusLabel)}</p>
        ${v.ltv.priorDepositPending || v.ltv.mortgagePending || !st.depositKnown ? "<p>보증금과 선순위 채권을 확인하면 예상 한도를 계산해요.</p>" : `<p>보증보험 가입선(최대 보증금): <b>${esc(money(g.hugMax10k))}</b> <small>${esc(g.hugBasis)}</small></p>`}
        ${g.blockers.length ? `<p class="is-danger-text">막히는 이유: ${esc(g.blockers.join(" · "))}</p>` : ""}
        ${g.unknowns.length ? `<p class="fh-sub">확인이 필요한 값: ${esc(g.unknowns.join(", "))}</p>` : ""}
      </div>
      <h4 class="fh-group">반환보증 상품</h4>
      <div class="fh-list">${g.products
        .map(
          (p) => `<div class="fh-item"><div class="fh-row"><strong>${esc(p.name)}</strong><span class="src-chip">${esc(p.statusLabel)}</span></div>
            <p>${esc(p.summary)}</p><div class="fh-actions"><a class="fh-btn" href="${esc(p.link.url)}" target="_blank" rel="noopener">${esc(p.link.label)} ↗</a></div></div>`
        )
        .join("")}</div>
      <h4 class="fh-group">예방·지원 제도</h4>
      <div class="fh-list">${g.programs
        .map(
          (p) => `<div class="fh-item"><div class="fh-row"><strong>${esc(p.name)}</strong><a class="fh-btn" href="${esc(p.link.url)}" target="_blank" rel="noopener">${esc(p.link.label)} ↗</a></div><p>${esc(p.what)}</p></div>`
        )
        .join("")}</div>
      <p class="fh-sub">상품 조건은 기관 사정에 따라 바뀌어요. 가입 전 각 기관에서 최종 확인하세요.</p>`;
  }

  function renderDepositGuide(v) {
    const g = v.depositGuide;
    const ltv = v.ltv;
    const missing = [];
    if (ltv.priorDepositPending) missing.push(["선순위 보증금 미확인", "집주인 서류의 선순위 보증금 총액"]);
    if (ltv.mortgagePending) missing.push(["근저당 금액 미확인", "등기부의 근저당 금액"]);
    if (!st.depositKnown) missing.push(["계약 보증금 미입력", "계약할 보증금"]);
    if (!ltv.price10k) missing.push(["집값 미확인", "집값"]);
    const pending = missing.length > 0;
    const priceBasis = { estimate: "추정", input: "입력가 기준", trade: "실거래가 기준" }[ltv.priceSource] || "";
    const rentRatio = ltv.rentToMarketPct;
    const gap = g.gapPct === null ? "" : `${g.gapPct > 0 ? "+" : ""}${g.gapPct}%`;
    return `
      <section class="fh-card">
        <div class="fh-card-head"><h3>${pending ? "시세와 보증금" : "시세·적정 보증금"}</h3>${g.marketJeonse10k || g.nearbyJeonse10k ? srcChip(g.marketIsEstimate ? "estimate" : "trade", g.marketIsEstimate ? "시세 · 추정" : "시세 · 실거래") : srcChip("none", "주변 시세 미확인")}</div>
        ${pending ? `<div class="fh-evidence-pending"><h4>${esc(missing[0][0])}</h4>
          <p>${esc(missing.map(item => item[1]).join(" · "))} 확인 후 안전선과 예상 회수액을 계산할 수 있어요.</p></div>`
          : `<p class="fh-headroom is-${g.lines[0].fits === false ? "caution" : "safe"}">${esc(g.headline)}</p>`}
        <dl class="fh-numbers">
          <div><dt>이 매물 보증금</dt><dd>${st.depositKnown ? esc(money(g.deposit10k)) : "미입력"}</dd><dd class="fh-small">${st.depositKnown ? esc(g.listingSource || "입력값") : '<button type="button" class="fh-btn" data-action="tab" data-tab="registry">보증금 입력</button>'}</dd></div>
          <div><dt>주변 전세 시세</dt><dd>${esc(money(g.marketJeonse10k ?? g.nearbyJeonse10k))}</dd><dd class="fh-small ${g.gapPct > 10 ? "is-danger-text" : ""}">${esc(gap ? `이 보증금은 ${gap}` : "비교 불가")}</dd>${g.marketSourceLabel ? `<dd class="fh-small">${esc(g.marketSourceLabel)}</dd>` : ""}</div>
          <div><dt>집값</dt><dd>${esc(money(g.price10k))}</dd><dd class="fh-small">${esc(ltv.priceSourceLabel)}</dd></div>
          ${Number.isFinite(rentRatio) ? `<div><dt>${esc(priceBasis)} 전세가율</dt><dd>${esc(rentRatio)}%</dd><dd class="fh-small">보증금 ÷ 집값</dd></div>` : ""}
          ${!pending ? `<div><dt>내 앞 순위 빚</dt><dd>${esc(money(g.senior10k))}</dd><dd class="fh-small">근저당 + 선순위 보증금</dd></div>` : ""}
        </dl>
        ${!pending ? `<table class="fh-table">
          <thead><tr><th>기준</th><th>최대 보증금</th><th>이 보증금</th></tr></thead>
          <tbody>${g.lines
            .map(
              (l) => `<tr><td>${esc(l.label)}<small>${esc(l.note)}</small></td><td>${esc(money(l.max10k))}</td>
                <td>${l.fits === null ? chip("unknown") : l.fits ? chip("pass") : `${chip("caution")}<small>${esc(money(g.deposit10k - l.max10k))} 초과</small>`}</td></tr>`
            )
            .join("")}</tbody>
        </table>` : ""}
        <p class="fh-sub">${esc(g.marketNote)}</p>
      </section>`;
  }

  function renderRepayment(v) {
    const r = v.repayment;
    if (v.ltv.mortgagePending || v.ltv.priorDepositPending || !st.depositKnown) return "";
    if (!r.available) return `<section class="fh-card"><h3>보증금 반환 순위</h3><p class="fh-sub">${esc(r.note)}</p></section>`;
    const max = Math.max(...r.steps.map((s) => s.claim10k || 0), 1);
    const deposit = v.depositGuide.deposit10k;
    return `
      <section class="fh-card">
        <div class="fh-card-head"><h3>보증금 반환 순위 <em>경매로 넘어가면</em></h3><span class="src-chip">낙찰가율 ${esc(r.ratePct)}% 가정</span></div>
        <p class="fh-sub">이 집이 <b>${esc(money(r.sale10k))}</b>에 낙찰되면 아래 순서대로 나눠 받아요. 위에 있을수록 먼저 받아요.</p>
        <ol class="fh-waterfall">${r.steps
          .map(
            (s, i) => `<li class="${s.isMine ? "is-mine" : ""} ${s.known ? "" : "is-unknown"}">
              <span class="fh-wf-no">${i + 1}</span>
              <div class="fh-wf-text"><strong>${esc(s.label)}</strong><small>${esc(s.note)}</small></div>
              <div class="fh-wf-amt">${s.claim10k === null ? "금액 미확인" : `${esc(money(s.paid10k))}<small> / ${esc(money(s.claim10k))}</small>`}</div>
              <div class="fh-wf-bar"><i style="width:${s.claim10k ? (s.claim10k / max) * 100 : 0}%"><b style="width:${s.claim10k ? (s.paid10k / s.claim10k) * 100 : 0}%"></b></i></div>
            </li>`
          )
          .join("")}</ol>
        <p class="fh-headroom is-${r.myLoss10k ? "danger" : r.isOptimistic ? "caution" : "safe"}">내 보증금 ${esc(money(deposit))} 중 <b>${esc(money(r.myRecovered10k))}</b> 회수 예상 (${esc(r.recoveryPct)}%)${r.myLoss10k ? ` · <b>${esc(money(r.myLoss10k))}</b> 못 받을 위험` : ""}</p>
        ${r.isOptimistic ? `<p class="fh-sub">${esc(r.unknown.length ? `${r.unknown.join(", ")}을(를) 몰라 0으로 계산했어요. ` : "")}실제 회수액은 이보다 적을 수 있어요.</p>` : ""}
        <details class="fh-basis"><summary>계산 기준</summary><ul>${r.basis.map((b) => `<li>${esc(b)}</li>`).join("")}<li>지역 구분: ${esc(r.region)}</li></ul></details>
      </section>`;
  }

  function renderHistoryTab(v) {
    const reports = st.feedback.map((f) => ({ date: (f.createdAt || "").slice(0, 10), kind: "report", title: `제보 · ${f.categoryLabel}`, detail: `${f.text} (${f.roleLabel} · 미검증)` }));
    const items = [...v.history, ...reports].sort((a, b) => (b.date || "").localeCompare(a.date || ""));
    const s = v.historySummary;
    const counts = {
      all: items.length,
      ownership: items.filter((e) => KIND_FILTER.ownership.includes(e.kind)).length,
      mortgage: items.filter((e) => KIND_FILTER.mortgage.includes(e.kind)).length,
      caution: items.filter((e) => KIND_FILTER.caution.includes(e.kind)).length,
    };
    const shown = st.filter === "all" ? items : items.filter((e) => KIND_FILTER[st.filter].includes(e.kind));
    const fbtn = (key, label) => `<button type="button" class="${st.filter === key ? "is-active" : ""}" data-action="filter" data-filter="${key}">${label} ${counts[key]}</button>`;
    const cautionTitles = [...s.cautionEvents, ...(st.feedback.length ? [`미검증 제보 ${st.feedback.length}건`] : [])];
    return `
      <dl class="fh-history-sum">
        <div><dt>소유자 변경</dt><dd>총 ${s.ownershipChanges}회${s.lastOwnershipChange ? ` · 최근 ${esc(s.lastOwnershipChange)}` : ""}</dd></div>
        <div><dt>근저당 기록</dt><dd>${s.mortgageEvents}건</dd></div>
        <div><dt>주의 이력</dt><dd class="${cautionTitles.length ? "is-danger" : ""}">${cautionTitles.length ? esc(cautionTitles.join(", ")) : "없음"}</dd></div>
      </dl>
      <div class="fh-filters">${fbtn("all", "전체")}${fbtn("ownership", "소유권")}${fbtn("mortgage", "근저당")}${fbtn("caution", "주의·제보")}</div>
      ${
        shown.length
          ? `<ul class="fh-timeline">${shown
              .map(
                (e) => `<li class="k-${esc(e.kind)} ${KIND_FILTER.caution.includes(e.kind) && e.kind !== "report" ? "k-caution" : ""}">
                  <time>${esc(e.date || "-")}</time><div><strong>${esc(e.title)}</strong><p>${esc(e.detail || "")}</p></div></li>`
              )
              .join("")}</ul>`
          : `<p class="fh-sub">기록이 없어요. 등기부 입력 탭에 값을 넣으면 이곳에 쌓여요.</p>`
      }
      <div class="fh-card-head fh-feedback-head"><h4 class="fh-group">문제 제보</h4><span class="src-chip"><span class="fh-live"></span>실시간 · 15초마다 갱신</span></div>
      <p class="fh-sub">살았거나 다녀온 분, 이웃·중개사의 제보를 받아요. 핏홈이 확인하기 전까지 '미검증'으로 표시되고, 판정에는 주의 신호 하나로만 반영돼요.</p>
      <div class="fh-feedback">
        <div class="fh-list">${
          st.feedback.length
            ? st.feedback
                .map((f) => `<div class="fh-item"><div class="fh-row"><strong>${esc(f.categoryLabel)} · ${esc(f.roleLabel)}</strong><span class="r-chip r-caution">${esc(f.statusLabel)}</span></div><p>${esc(f.text)}</p><small>${esc((f.createdAt || "").replace("T", " "))}</small></div>`)
                .join("")
            : `<p class="fh-sub">아직 제보가 없어요.</p>`
        }</div>
        ${window.FITHOME_STATIC ? `<p class="fh-sub">정적 데모(GitHub Pages)에서는 제보를 저장하지 않아요. 서버 버전에서 이용해 주세요.</p>` : `<form class="fh-feedback-form" data-action="feedback">
          <select name="category" aria-label="제보 종류">
            <option value="info">정보가 달라요</option><option value="condition">집 상태 문제 (누수·곰팡이 등)</option>
            <option value="landlord">임대인·중개사 문제</option><option value="other">기타</option>
          </select>
          <select name="role" aria-label="제보자">
            <option value="visitor">방문자</option><option value="tenant">세입자</option><option value="neighbor">이웃</option><option value="broker">중개사</option>
          </select>
          <textarea name="text" maxlength="500" placeholder="예) 욕실 천장에 누수 자국이 있어요" aria-label="제보 내용"></textarea>
          <button class="fh-btn primary" type="submit">제보 보내기</button>
        </form>`}
      </div>`;
  }

  function reportPosition(node) {
    return {
      keepScroll: node?.querySelector(".fh-report-body")?.scrollTop || 0,
      openedChecklist: node?.querySelector("details[open] [data-checklist]")?.dataset.checklist,
    };
  }

  function render(position = reportPosition(overlay())) {
    const node = overlay();
    if (!node || !st.verdict) return;
    const v = st.verdict;
    const { keepScroll, openedChecklist } = position;
    const tabBody = { intake: () => intake.render(), detail: renderDetailTab, registry: renderRegistryTab, contract: renderContractTab, support: renderSupportTab, history: renderHistoryTab }[st.tab](v);
    node.innerHTML = `
      <div class="fh-report-backdrop" data-action="close"></div>
      <div class="fh-report-sheet">
        <header class="fh-report-head">
          <div><strong>전세 안심 판정 리포트</strong><span>${esc(v.property.label === v.property.address ? v.property.address : v.property.label + " · " + v.property.address)}</span></div>
          <button type="button" class="fh-icon" data-action="close" aria-label="리포트 닫기">×</button>
        </header>
        <div class="fh-report-body">
          ${renderSummary(v)}
          ${st.tab === "detail" ? renderDepositGuide(v) + renderLtv(v) + renderRepayment(v) + renderResults(v) : ""}
          <section class="fh-card fh-tabcard">
            <nav class="fh-tabs" role="tablist">${TABS.map(
              ([key, label]) => `<button type="button" role="tab" aria-selected="${st.tab === key}" class="${st.tab === key ? "is-active" : ""}" data-action="tab" data-tab="${key}">${label}</button>`
            ).join("")}</nav>
            <div class="fh-tabbody">${tabBody}</div>
          </section>
          <p class="fh-notice">${esc(v.notice)} 가격이 '추정'인 항목은 국토부 실거래 연동 전 계산값이에요.</p>
        </div>
      </div>`;
    const nextScroller = node.querySelector(".fh-report-body");
    const nextChecklist = node.querySelector("[data-checklist]");
    if (nextChecklist && nextChecklist.dataset.checklist === openedChecklist) nextChecklist.closest("details").open = true;
    if (nextScroller) nextScroller.scrollTop = keepScroll;
  }

  function downloadIcs(items, name) {
    const stamp = new Date().toISOString().replace(/[-:]/g, "").slice(0, 15) + "Z";
    const clean = (text) => String(text || "").replace(/[\\,;]/g, (c) => `\\${c}`).replace(/\n/g, " ");
    const events = items
      .filter((i) => i.date)
      .map((i) => {
        const day = i.date.replace(/-/g, "");
        return ["BEGIN:VEVENT", `UID:fithome-${st.base.key}-${i.id}@fithome`, `DTSTAMP:${stamp}`, `DTSTART;VALUE=DATE:${day}`,
          `SUMMARY:${clean(`[핏홈] ${i.title}`)}`, `DESCRIPTION:${clean(`${name} · ${i.detail}${i.link ? ` ${i.link.url}` : ""}`)}`,
          "BEGIN:VALARM", "TRIGGER:-P1D", "ACTION:DISPLAY", `DESCRIPTION:${clean(i.title)}`, "END:VALARM", "END:VEVENT"].join("\r\n");
      });
    const body = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//FitHome//Jeonse//KO", ...events, "END:VCALENDAR"].join("\r\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([body], { type: "text/calendar" }));
    a.download = `핏홈_${name}_계약일정.ics`;
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    toast("일정 파일을 저장했어요");
  }

  async function rerender() {
    const position = reportPosition(overlay());
    st.verdict = null;
    const pendingSheet = overlay()?.querySelector(".fh-report-sheet");
    if (pendingSheet) pendingSheet.innerHTML = `<div class="fh-report-loading">입력값으로 다시 판정하고 있어요…</div>`;
    try {
      if (!await evaluate()) return false;
      render(position);
      return true;
    } catch (error) {
      st.verdict = null;
      const sheet = overlay()?.querySelector(".fh-report-sheet");
      if (sheet) {
        sheet.innerHTML = `<div class="fh-report-loading">다시 판정하지 못했어요: ${esc(error.message)}<br>이전 판정은 지웠어요. 입력값을 확인한 뒤 다시 시도해 주세요.
          <button type="button" class="fh-btn" data-action="retry">다시 시도</button> <button type="button" class="fh-btn" data-action="reset-edits">입력 초기화</button> <button type="button" class="fh-btn" data-action="close">닫기</button></div>`;
      }
      return false;
    }
  }

  const sharedEditFields = ["taxArrears", "guaranteeEligible", "ownerMatches"];

  function shownValue(edits, overrides, field) {
    const edit = edits[field];
    return edit && edit !== "unknown" ? edit : overrides[field] || "unknown";
  }

  function saveEdits(key, edits) {
    const previous = store.get(`${key}.edits`, {});
    const overrides = store.get(`${key}.overrides`, {});
    for (const field of sharedEditFields) {
      if (field in edits && field in overrides && edits[field] !== shownValue(previous, overrides, field)) delete overrides[field];
    }
    store.set(`${key}.edits`, edits);
    store.set(`${key}.overrides`, overrides);
  }

  function readEdits(form) {
    const data = new FormData(form);
    const e = {};
    for (const [key, value] of data.entries()) e[key] = String(value).trim();
    e.mortgageUnknown = data.get("mortgageUnknown") === "on";
    e.useEdited = form.dataset.useEdited === "true" || store.get(st.base.key + ".edits", {}).useEdited === true;
    return e;
  }

  function bind() {
    document.addEventListener("click", (event) => {
      const opener = event.target.closest("[data-open-report]");
      if (opener) open({ id: opener.dataset.openReport });
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape" && overlay() && !overlay().hidden) close();
    });
    const node = overlay();
    if (!node) return;

    intake.bind(node);
    node.addEventListener("click", async (event) => {
      const t = event.target.closest("[data-action]");
      if (!t) return;
      const key = st.base?.key;
      const action = t.dataset.action;
      if (action === "close") close();
      else if (action === "tab" || action === "intake-tab") {
        st.tab = action === "intake-tab" ? "intake" : t.dataset.tab;
        if (st.tab === "intake") intake.select(t.dataset.target || "hub");
        render();
        const target = action === "intake-tab" ? node.querySelector(`[data-intake-panel="${t.dataset.target}"]`) : null;
        (target || node.querySelector(".fh-tabcard"))?.scrollIntoView({ behavior: "smooth", block: "start" });
      } else if (action === "rights-tab") {
        st.rightsTab = t.dataset.tab;
        render();
      } else if (action === "filter") {
        st.filter = t.dataset.filter;
        render();
      } else if (action === "copy") copyText(t.dataset.text);
      else if (action === "ics") downloadIcs(st.verdict.aftercare.items, st.base.property.label);
      else if (action === "reset-edits") {
        store.set(`${key}.edits`, {});
        store.set(`${key}.overrides`, {});
        if (await rerender()) toast("입력값을 지웠어요");
      } else if (action === "retry") {
        await rerender();
      }
    });

    node.addEventListener("change", async (event) => {
      const t = event.target;
      const key = st.base?.key;
      const action = t.dataset.action;
      if (action === "req-status") {
        const requests = store.get(`${key}.requests`, {});
        requests[t.dataset.id] = t.value;
        store.set(`${key}.requests`, requests);
        if (await rerender()) toast(t.value === "refused" || t.value === "noResponse" ? "거절·무응답을 위험 신호로 반영했어요" : "요청 상태를 기록했어요");
      } else if (action === "override") {
        const o = store.get(`${key}.overrides`, {});
        o[t.dataset.field] = t.value;
        store.set(`${key}.overrides`, o);
        const edits = store.get(`${key}.edits`, {});
        delete edits[t.dataset.field];
        store.set(`${key}.edits`, edits);
        await rerender();
      } else if (action === "doc") {
        const done = new Set(store.get(`${key}.docs`, []));
        t.checked ? done.add(t.dataset.id) : done.delete(t.dataset.id);
        store.set(`${key}.docs`, [...done]);
        render();
      } else if (action === "stage") {
        const done = new Set(store.get(`${key}.stages`, []));
        t.checked ? done.add(t.dataset.id) : done.delete(t.dataset.id);
        store.set(`${key}.stages`, [...done]);
        render();
      } else if (t.form?.dataset.action === "edits" && t.name === "use") {
        t.form.dataset.useEdited = "true";
      } else if (t.form?.dataset.action === "edits" && ["priceBasis", "housingType"].includes(t.name)) {
        saveEdits(key, { ...store.get(`${key}.edits`, {}), ...readEdits(t.form) });
        await rerender();
      }
    });

    node.addEventListener("input", (event) => {
      const t = event.target;
      if (t.matches("[data-money]")) {
        const hint = node.querySelector(`[data-money-hint="${t.name}"]`);
        if (hint) hint.textContent = t.value ? money(t.value) : "";
      }
    });

    node.addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = event.target;
      const key = st.base?.key;
      if (form.dataset.action === "edits") {
        saveEdits(key, readEdits(form));
        st.tab = "detail";
        if (await rerender()) toast("입력값으로 다시 판정했어요");
      } else if (form.dataset.action === "feedback") {
        const data = new FormData(form);
        try {
          await api("/api/property-feedback", {
            method: "POST",
            body: JSON.stringify({ key, category: data.get("category"), role: data.get("role"), text: data.get("text") }),
          });
          await loadFeedback();
          if (await rerender()) toast("제보가 접수됐어요. 확인 전까지 '미검증'으로 표시돼요");
        } catch (error) {
          toast(error.message);
        }
      }
    });
  }

  const intake = window.fitHomeDocumentIntake({
    store, esc, money, copyText, render, toast, renderChecklist, base: () => st.base, verdict: () => st.verdict,
    saveAddress: async (address, housingType) => {
      setReportAddress(address, housingType);
      await loadFeedback();
      await rerender();
    },
    recalculate: async () => {
      if (!await rerender()) throw new Error("판정을 갱신하지 못했어요. 다시 시도해 주세요.");
    },
  });

  window.FitHomeReport = { open, openAddress, close, identityReturnContext, resumeIdentity };
  document.addEventListener("DOMContentLoaded", bind);
})();
