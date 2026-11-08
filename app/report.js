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
  const GRADE_COPY = { safe: "확인한 항목에서 위험 신호가 없어요", caution: "계약 전에 더 확인해야 해요", danger: "계약을 멈추고 확인하세요" };
  const AREA_ORDER = ["rights", "ratio", "landlord", "building", "reports"];
  const AREA_LABELS = { rights: "권리관계", ratio: "가격·비율", landlord: "임대인", building: "건물", reports: "제보" };
  const KIND_FILTER = { ownership: ["ownership"], mortgage: ["mortgage", "mortgageRelease"], caution: ["trust", "seizure", "auction", "leaseRegistration", "report"] };
  const TABS = [
    ["detail", "상세 판정"],
    ["registry", "등기부 입력"],
    ["requests", "확인 요청"],
    ["contract", "계약 단계·특약"],
    ["history", "이력·제보"],
  ];
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
    const live = String(price.sourceMode || "").startsWith("molit");
    const listing = opts.listing || null;
    return {
      key: listing ? `listing:${listing.id}` : `apt:${detail.id}`,
      property: {
        label: listing ? `${detail.name} · ${listing.title}` : detail.name,
        address: detail.address,
        housingType: "apartment",
      },
      deposit10k: opts.deposit10k ?? price.recentJeonse10k ?? null,
      price: { basis: "market", value10k: price.recentSale10k ?? null, official10k: price.officialPrice10k ?? null, source: live ? "trade" : "estimate" },
      registry: { source: "none", trust: "unknown", seizure: "unknown", auction: "unknown", leaseRegistration: "unknown", ownerMatches: "unknown" },
      landlord: { source: "input", taxArrears: "unknown", guaranteeEligible: "unknown" },
      building: { source: "public", use: "residential", violation: "unknown" },
      requests: {},
      inspection: { status: "none" },
      history: detail.approvalDate
        ? [{ date: detail.approvalDate, kind: "building", title: "사용승인", detail: `${detail.households || "-"}세대 · ${detail.buildingCount || "-"}개 동` }]
        : [],
    };
  }

  function currentInput() {
    const base = st.base;
    const key = base.key;
    const e = store.get(`${key}.edits`, {});
    const next = structuredClone(base);
    const num = (v) => (v === "" || v === null || v === undefined ? null : Number(v));
    if (num(e.deposit10k) !== null) next.deposit10k = num(e.deposit10k);
    if (e.priceBasis === "market" && num(e.priceValue10k) !== null) next.price = { ...next.price, basis: "market", value10k: num(e.priceValue10k), source: "input" };
    if (e.priceBasis === "official") next.price = { ...next.price, basis: "official", source: num(e.official10k) !== null ? "input" : next.price.source };
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
    if (touched) reg.source = "registry";
    if (e.taxArrears && e.taxArrears !== "unknown") next.landlord.taxArrears = e.taxArrears;
    if (e.guaranteeEligible && e.guaranteeEligible !== "unknown") next.landlord.guaranteeEligible = e.guaranteeEligible;
    if (e.violation && e.violation !== "unknown") next.building.violation = e.violation;

    // 확인 요청 기록과 받은 값
    next.requests = { ...next.requests, ...store.get(`${key}.requests`, {}) };
    const o = store.get(`${key}.overrides`, {});
    if (o.taxArrears) next.landlord.taxArrears = o.taxArrears;
    if (o.guaranteeEligible) next.landlord.guaranteeEligible = o.guaranteeEligible;
    if (o.ownerMatches) next.registry.ownerMatches = o.ownerMatches;
    if (o.registryIssuedAt) {
      next.registry.issuedAt = o.registryIssuedAt;
      next.registry.source = "registry";
    }
    if (store.get(`${key}.inspectionRequested`, false)) next.inspection = { status: "requested" };
    return next;
  }

  async function evaluate() {
    st.verdict = await api("/api/jeonse-verdict", { method: "POST", body: JSON.stringify(currentInput()) });
  }
  async function loadFeedback() {
    const payload = await api(`/api/property-feedback?key=${encodeURIComponent(st.base.key)}`);
    const changed = payload.items.length !== st.feedback.length;
    st.feedback = payload.items;
    return changed;
  }

  // ---------- 열고 닫기 ----------

  async function open({ id, deposit10k = null, listing = null } = {}) {
    const node = overlay();
    if (!node || !id) return;
    node.hidden = false;
    node.innerHTML = `<div class="fh-report-backdrop" data-action="close"></div><div class="fh-report-sheet"><div class="fh-report-loading">판정 리포트를 준비하고 있어요…</div></div>`;
    try {
      const payload = await api(`/api/property-detail?id=${encodeURIComponent(id)}`);
      st.detail = payload.detail;
      st.base = baseInput(st.detail, { deposit10k, listing });
      st.feedback = [];
      st.tab = "detail";
      st.filter = "all";
      await loadFeedback();
      await evaluate();
      render();
      startPolling();
    } catch (error) {
      node.querySelector(".fh-report-sheet").innerHTML = `<div class="fh-report-loading">리포트를 불러오지 못했어요: ${esc(error.message)} <button type="button" class="fh-btn" data-action="close">닫기</button></div>`;
    }
  }

  function close() {
    const node = overlay();
    if (node) node.hidden = true;
    clearInterval(st.poll);
  }

  function startPolling() {
    clearInterval(st.poll);
    st.poll = setInterval(async () => {
      if (overlay()?.hidden || !st.base) return;
      try {
        if (await loadFeedback()) {
          // 자동 갱신도 실패하면 이전 판정을 지우는 같은 경로를 쓴다(재점검 Astra-12).
          if (await rerender()) toast("새 제보가 반영됐어요");
        }
      } catch {
        /* 다음 주기에 다시 시도 */
      }
    }, POLL_MS);
  }

  // ---------- 렌더링 ----------

  function renderSummary(v) {
    const inspection = v.inspection || {};
    const registryEmpty = v.rights.filter((c) => c.result === "unknown").length >= 4;
    const inspectBox =
      inspection.status === "done"
        ? `<div class="fh-inspect done"><strong>✓ 핏홈 점검 완료</strong><p>${esc(inspection.by || "")} · ${esc(inspection.date || "")}</p></div>`
        : inspection.status === "requested"
          ? `<div class="fh-inspect"><strong>핏홈 점검 신청됨</strong><p>시연 단계라 실제 점검 연결은 준비 중이에요.</p></div>`
          : `<div class="fh-inspect"><strong>핏홈 점검 전</strong><p>지금은 공개 정보와 입력값 기준이에요. 핏홈이 등기부·현장·서류를 직접 대조하면 '핏홈 점검'으로 바뀝니다.</p>
               <button type="button" class="fh-btn" data-action="inspect">핏홈 점검 신청</button></div>`;
    return `
      <section class="fh-card fh-summary grade-${v.grade}">
        <div class="fh-grade">
          <div class="fh-grade-badge"><span>${esc(v.gradeLabel)}</span><small>판정 등급</small></div>
          <div class="fh-grade-text">
            <h3>${esc(GRADE_COPY[v.grade])}</h3>
            <p class="fh-meta">${esc(v.property.label)} · 보증금 ${esc(money(v.ltv.deposit10k))} · ${esc(v.asOf)} 기준</p>
            <p class="fh-headline">${esc(v.headline)}</p>
            <div class="fh-tags">${v.tags.map((t) => `<span>${esc(t)}</span>`).join("")}</div>
            ${registryEmpty ? `<button type="button" class="fh-btn primary" data-action="tab" data-tab="registry">등기부 값 입력하고 다시 판정</button>` : ""}
          </div>
        </div>
        ${inspectBox}
      </section>`;
  }

  function renderLtv(v) {
    const l = v.ltv;
    if (!l.price10k) return `<section class="fh-card"><h3>집값 대비 빚</h3><p class="fh-sub">집값이 없어 비율을 계산하지 못했어요. 등기부 입력 탭에서 집값을 넣어주세요.</p></section>`;
    const scale = Math.max(100, (l.ratioPct || 0) + 8);
    const pct = (x) => ((x || 0) / l.price10k) * 100;
    const seg = (cls, x, label) =>
      x > 0 ? `<div class="${cls}" style="width:${(pct(x) / scale) * 100}%" title="${esc(label)} ${esc(money(x))}">${pct(x) / scale > 0.1 ? esc(label) : ""}</div>` : "";
    const h80 = l.headroom10k["80"];
    const h90 = l.headroom10k["90"];
    // 근저당·선순위 보증금을 모르면(하한) 남은 여유를 확정처럼 말하지 않는다(전체 QA Astra-04).
    const headroom =
      h80 > 0 && l.isLowerBound
        ? ["caution", `입력한 값만으로는 80%까지 ${esc(money(h80))} 남아요. 근저당·선순위 보증금을 아직 모르는 계산이라 실제 여유는 이보다 적을 수 있어요.`]
        : h80 > 0
        ? ["safe", `근저당이 <b>${esc(money(h80))}</b> 더 잡혀도 80% 아래예요. 입력한 집값의 90%까지는 ${esc(money(h90))} 남았어요.`]
        : h90 >= 0
          ? ["caution", h90 > 0 ? `이미 깡통전세 경계(80%)를 넘었어요. 입력한 집값의 90%까지 ${esc(money(h90))}만 남았어요.` : `이미 깡통전세 경계(80%)를 넘었고 입력한 집값의 90%에 딱 닿았어요.`]
          : ["danger", `입력한 집값의 90%를 <b>${esc(money(-h90))}</b> 넘었어요. 전세보증보험 가입이 어려울 수 있는 수준이에요.`];
    // HUG 한도는 HUG가 인정한 주택가격 기준이라 입력한 집값과 다를 수 있다(재점검 Sol V06).
    headroom[1] += " HUG 보증 한도는 HUG가 인정한 주택가격 × 90%에서 선순위채권을 뺀 금액이라 이 계산과 다를 수 있어요.";
    // 근저당·선순위를 모르는 하한 계산이면 어느 단계든 남은 금액이 실제보다 많게 보일 수 있다(재점검 Astra-04).
    if (l.isLowerBound && headroom[0] !== "danger" && !(h80 > 0)) {
      headroom[1] += " 근저당·선순위 보증금을 모르는 계산이라 실제 남은 금액은 이보다 적을 수 있어요.";
    }
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
        ${l.isLowerBound ? `<p class="fh-sub">모르는 값은 0으로 계산했어요. 실제 비율은 이보다 높을 수 있어요.</p>` : ""}
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
      `<button type="button" class="fh-count is-${result}" data-action="tab" data-tab="${result === "unknown" ? "requests" : "detail"}">
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
            <div class="fh-row"><span>${esc(c.value)}</span>${srcChip(c.source, c.sourceLabel)}</div>
            <p>${esc(c.standard)}</p>${c.note ? `<p>${esc(c.note)}</p>` : ""}
          </div>`
        )
        .join("")}</div>`;
    }
    return `${sub}${AREA_ORDER.map((area) => {
      const rows = v.checks.filter((c) => c.area === area);
      if (!rows.length) return "";
      return `<h4 class="fh-group">${AREA_LABELS[area]}</h4>
        <table class="fh-table">
          <thead><tr><th>항목</th><th>기준</th><th>이 집</th><th>결과</th><th>출처</th></tr></thead>
          <tbody>${rows
            .map(
              (c) => `<tr><td>${esc(c.label)}${c.note ? `<small>${esc(c.note)}</small>` : ""}</td><td class="fh-std">${esc(c.standard)}</td><td>${esc(c.value)}</td><td>${chip(c.result)}</td><td>${srcChip(c.source, c.sourceLabel)}</td></tr>`
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
    const shown = (field, editField) => shownValue(e, o, field, editField) || "unknown";
    const priceBasis = e.priceBasis || "estimate";
    const field = (label, control, hint = "") => `<label class="fh-field"><span>${label}</span>${control}${hint ? `<small>${hint}</small>` : ""}</label>`;
    const numInput = (name, value, placeholder) =>
      `<input type="number" min="0" inputmode="numeric" name="${name}" value="${esc(value ?? "")}" placeholder="${esc(placeholder)}" data-money>`;
    return `
      <form class="fh-form" data-action="edits">
        <p class="fh-sub">등기부는 인터넷등기소에서 누구나 700원에 열람할 수 있어요. 값을 넣으면 바로 다시 판정해요. 모르는 칸은 '모름'으로 두세요.</p>
        <div class="fh-form-grid">
          ${field("내 보증금 (만원)", numInput("deposit10k", e.deposit10k, `현재 ${st.base.deposit10k ?? ""} (추정)`), `<span data-money-hint="deposit10k">${e.deposit10k ? esc(money(e.deposit10k)) : ""}</span>`)}
          <div class="fh-field"><span>집값 기준</span>${seg("priceBasis", [["estimate", "추정 시세"], ["market", "직접 입력"], ["official", "공시가격×140%"]], priceBasis)}</div>
          ${priceBasis === "market" ? field("시세·감정가 (만원)", numInput("priceValue10k", e.priceValue10k, "")) : ""}
          ${field("공시가격 (만원)", numInput("official10k", e.official10k, `현재 ${st.base.price.official10k ?? ""} (추정)`), "부동산공시가격알리미에서 확인")}
          ${field("등기부 열람일", `<input type="date" name="issuedAt" value="${esc(normValue(e.issuedAt) || normValue(o.registryIssuedAt))}">`)}
          ${field(
            "근저당 채권최고액 합계 (만원)",
            `${numInput("mortgageMax10k", e.mortgageMax10k, "을구 금액 합계")}<label class="fh-inline"><input type="checkbox" name="mortgageUnknown" ${e.mortgageUnknown ? "checked" : ""}>모름</label>`
          )}
          <div class="fh-field"><span>신탁등기 (갑구)</span>${seg("trust", TRI, e.trust || "unknown")}</div>
          <div class="fh-field"><span>압류·가압류 (갑구)</span>${seg("seizure", TRI, e.seizure || "unknown")}</div>
          <div class="fh-field"><span>경매개시결정</span>${seg("auction", TRI, e.auction || "unknown")}</div>
          <div class="fh-field"><span>임차권등기 (을구)</span>${seg("leaseRegistration", TRI, e.leaseRegistration || "unknown")}</div>
          <div class="fh-field"><span>등기부 소유자 = 계약 상대</span>${seg("ownerMatches", [["yes", "같음"], ["no", "다름"], ["unknown", "모름"]], shown("ownerMatches", "ownerMatches"))}</div>
          ${field("최근 소유권 이전일", `<input type="date" name="lastOwnershipChange" value="${esc(e.lastOwnershipChange || "")}">`, "갑구 마지막 '소유권 이전' 날짜")}
          <div class="fh-field"><span>임대인 세금 체납</span>${seg("taxArrears", TRI, shown("taxArrears", "taxArrears"))}</div>
          <div class="fh-field"><span>전세보증보험 가입</span>${seg("guaranteeEligible", [["yes", "가능"], ["no", "불가"], ["unknown", "모름"]], shown("guaranteeEligible", "guaranteeEligible"))}</div>
          <div class="fh-field"><span>위반건축물</span>${seg("violation", TRI, e.violation || "unknown")}</div>
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
      case "registryLatest":
        return `<button class="fh-btn" type="button" data-action="override-today" data-field="registryIssuedAt">오늘 열람함으로 기록</button>`;
      default:
        return "";
    }
  }

  function renderRequestsTab(v) {
    const statuses = [["none", "요청 전"], ["requested", "요청함"], ["received", "받음"], ["refused", "거절"], ["noResponse", "무응답"]];
    if (!v.requests.length) return `<p class="fh-sub">지금 따로 요청할 서류가 없어요.</p>`;
    return `
      <p class="fh-sub">집주인 동의가 있어야 볼 수 있는 정보예요. 요청문을 보내고 결과를 기록하면 판정에 반영돼요. <b>거절·무응답도 위험 신호로 반영</b>해요.</p>
      <div class="fh-list">${v.requests
        .map(
          (q) => `<div class="fh-item st-${q.status}">
            <div class="fh-row"><strong>${esc(q.title)}</strong><span class="src-chip">받을 곳 · ${esc(q.to)}</span></div>
            <p>${esc(q.why)}</p>
            <small>근거: ${esc(q.legal)}</small>
            <div class="fh-actions">
              <select data-action="req-status" data-id="${esc(q.id)}" aria-label="${esc(q.title)} 요청 상태">
                ${statuses.map(([value, label]) => `<option value="${value}" ${q.status === value ? "selected" : ""}>${label}</option>`).join("")}
              </select>
              <button class="fh-btn" type="button" data-action="copy" data-text="${esc(q.template)}">요청문 복사</button>
              ${q.status === "received" ? receivedInput(q) : ""}
            </div>
          </div>`
        )
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
        .join("")}</div>`;
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

  function render() {
    const node = overlay();
    if (!node || !st.verdict) return;
    const v = st.verdict;
    const tabBody = { detail: renderDetailTab, registry: renderRegistryTab, requests: renderRequestsTab, contract: renderContractTab, history: renderHistoryTab }[st.tab](v);
    const scroller = node.querySelector(".fh-report-body");
    const keepScroll = scroller ? scroller.scrollTop : 0;
    node.innerHTML = `
      <div class="fh-report-backdrop" data-action="close"></div>
      <div class="fh-report-sheet">
        <header class="fh-report-head">
          <div><strong>전세 안심 판정 리포트</strong><span>${esc(st.detail.name)} · ${esc(st.detail.address)}</span></div>
          <button type="button" class="fh-icon" data-action="close" aria-label="리포트 닫기">×</button>
        </header>
        <div class="fh-report-body">
          ${renderSummary(v)}
          ${renderLtv(v)}
          ${renderResults(v)}
          <section class="fh-card fh-tabcard">
            <nav class="fh-tabs" role="tablist">${TABS.map(
              ([key, label]) => `<button type="button" role="tab" class="${st.tab === key ? "is-active" : ""}" data-action="tab" data-tab="${key}">${label}${key === "requests" && v.requests.length ? ` <em>${v.requests.length}</em>` : ""}</button>`
            ).join("")}</nav>
            <div class="fh-tabbody">${tabBody}</div>
          </section>
          <p class="fh-notice">${esc(v.notice)} 가격이 '추정'인 항목은 국토부 실거래 연동 전 계산값이에요.</p>
        </div>
      </div>`;
    const nextScroller = node.querySelector(".fh-report-body");
    if (nextScroller) nextScroller.scrollTop = keepScroll;
  }

  // 재판정이 실패하면 이전 판정을 남기지 않는다. 입력이 바뀌었는데 예전 '안심'이 보이면 안 된다(전체 QA Astra-12).
  async function rerender() {
    // 다시 판정하는 동안 이전 판정(특히 '안심')을 그대로 보여 주지 않는다(재점검 Astra-12).
    st.verdict = null;
    const pendingSheet = overlay()?.querySelector(".fh-report-sheet");
    if (pendingSheet) pendingSheet.innerHTML = `<div class="fh-report-loading">입력값으로 다시 판정하고 있어요…</div>`;
    try {
      await evaluate();
      render();
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

  // 확인 요청에서 받은 값(overrides)과 등기부 입력(edits)이 같은 항목을 가리킬 때의 짝
  const OVERRIDE_EDIT_FIELDS = { taxArrears: "taxArrears", guaranteeEligible: "guaranteeEligible", ownerMatches: "ownerMatches", registryIssuedAt: "issuedAt" };
  // 등기부 폼에 보이는 값 = 직접 입력한 값(모름 제외) → 없으면 확인 요청에서 받은 값 → 없으면 모름.
  const normValue = (v) => (v === undefined || v === null || v === "" || v === "unknown" ? "" : String(v));
  function shownValue(e, o, field, editField) {
    return normValue(e[editField]) || normValue(o[field]);
  }
  // 폼 저장은 한 곳에서 한다. 사용자가 화면에 보이던 값을 실제로 바꾼 항목만 예전 확인 요청 값보다 앞선다.
  // 집값 기준을 바꿀 때 폼이 미리 저장돼 변경을 못 알아채던 문제(최종 재점검 N3)와, 받은 값 '없음'에서 '모름'으로
  // 다시 고른 것을 무시하던 문제(N4)를 함께 막는다.
  function saveEdits(key, edits) {
    const prevEdits = store.get(`${key}.edits`, {});
    const o = store.get(`${key}.overrides`, {});
    for (const [field, editField] of Object.entries(OVERRIDE_EDIT_FIELDS)) {
      if (field in o && normValue(edits[editField]) !== shownValue(prevEdits, o, field, editField)) delete o[field];
    }
    store.set(`${key}.edits`, edits);
    store.set(`${key}.overrides`, o);
  }
  function dropConflictingEdits(key, fields) {
    const e = store.get(`${key}.edits`, {});
    for (const field of fields) {
      const editField = OVERRIDE_EDIT_FIELDS[field];
      if (editField) delete e[editField];
    }
    store.set(`${key}.edits`, e);
  }

  function readEdits(form) {
    const data = new FormData(form);
    const e = {};
    for (const [key, value] of data.entries()) e[key] = String(value).trim();
    e.mortgageUnknown = data.get("mortgageUnknown") === "on";
    if (e.priceBasis === "estimate") delete e.priceBasis;
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

    node.addEventListener("click", async (event) => {
      const t = event.target.closest("[data-action]");
      if (!t) return;
      const key = st.base?.key;
      const action = t.dataset.action;
      if (action === "close") close();
      else if (action === "tab") {
        st.tab = t.dataset.tab;
        render();
        node.querySelector(".fh-tabcard")?.scrollIntoView({ behavior: "smooth", block: "start" });
      } else if (action === "rights-tab") {
        st.rightsTab = t.dataset.tab;
        render();
      } else if (action === "filter") {
        st.filter = t.dataset.filter;
        render();
      } else if (action === "copy") copyText(t.dataset.text);
      else if (action === "inspect") {
        store.set(`${key}.inspectionRequested`, true);
        if (await rerender()) toast("핏홈 점검 신청이 접수됐어요 (시연)");
      } else if (action === "override-today") {
        const o = store.get(`${key}.overrides`, {});
        o[t.dataset.field] = new Date().toISOString().slice(0, 10);
        store.set(`${key}.overrides`, o);
        dropConflictingEdits(key, [t.dataset.field]);
        await rerender();
      } else if (action === "reset-edits") {
        // 입력을 지우면 확인 요청 화면에서 받은 값(덮어쓰기)도 함께 지운다(Astra-10).
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
        dropConflictingEdits(key, [t.dataset.field]);
        await rerender();
      } else if (action === "stage") {
        const done = new Set(store.get(`${key}.stages`, []));
        t.checked ? done.add(t.dataset.id) : done.delete(t.dataset.id);
        store.set(`${key}.stages`, [...done]);
        render();
      } else if (t.form?.dataset.action === "edits" && t.name === "priceBasis") {
        saveEdits(key, { ...store.get(`${key}.edits`, {}), ...readEdits(t.form), priceBasis: t.value });
        render();
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

  window.FitHomeReport = { open, close };
  document.addEventListener("DOMContentLoaded", bind);
})();
