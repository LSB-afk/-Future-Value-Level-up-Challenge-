// 전세 안심 판정 화면 (#verdict). 판정 규칙은 서버 api/jeonse_verdict.py 한곳에만 둔다.
(() => {
  const LS = "fithome.verdict.";
  const POLL_MS = 15000;
  const state = {
    cases: [],
    notice: "",
    loaded: null,
    pending: null,
    mode: "picker", // picker | form | report
    current: null,
    verdict: null,
    feedback: [],
    tab: "rights",
    filter: "all",
    pollTimer: null,
    form: null,
  };

  const RESULT = {
    pass: ["통과", "r-pass", "✓"],
    caution: ["주의", "r-caution", "!"],
    danger: ["위험", "r-danger", "✕"],
    unknown: ["미확인", "r-unknown", "?"],
  };
  const GRADE_COPY = {
    safe: "확인한 항목에서 위험 신호가 없어요",
    caution: "계약 전에 더 확인해야 해요",
    danger: "계약을 멈추고 확인하세요",
  };
  const AREA_ORDER = ["rights", "ratio", "landlord", "building", "reports"];
  const AREA_LABELS = { rights: "권리관계", ratio: "가격·비율", landlord: "임대인", building: "건물", reports: "제보" };
  const KIND_FILTER = {
    ownership: ["ownership"],
    mortgage: ["mortgage", "mortgageRelease"],
    caution: ["trust", "seizure", "auction", "leaseRegistration", "report"],
  };

  const root = () => document.getElementById("verdictRoot");
  const esc = (value) =>
    String(value ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
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
    if (value === null || value === undefined || Number.isNaN(Number(value))) return "미확인";
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
    const response = await fetch(path, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    const payload = await response.json();
    if (!response.ok || payload.ok === false) throw new Error(payload.error || `요청 실패 (${response.status})`);
    return payload;
  }

  function toast(message) {
    let node = document.getElementById("verdictToast");
    if (!node) {
      node = document.createElement("div");
      node.id = "verdictToast";
      node.style.cssText =
        "position:fixed;left:50%;bottom:28px;transform:translateX(-50%);background:#0f172a;color:#fff;padding:10px 18px;border-radius:999px;font-size:14px;z-index:60;transition:opacity .2s";
      document.body.appendChild(node);
    }
    node.textContent = message;
    node.style.opacity = "1";
    clearTimeout(node.hideTimer);
    node.hideTimer = setTimeout(() => (node.style.opacity = "0"), 1600);
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

  // ---------- 데이터 흐름 ----------

  function ensureLoaded() {
    state.loaded ||= api("/api/jeonse-demo-cases").then((payload) => {
      state.cases = payload.cases || [];
      state.notice = payload.notice || "";
    });
    return state.loaded;
  }

  function withOverrides(input) {
    const key = input.key;
    const requests = { ...(input.requests || {}), ...store.get(`${key}.requests`, {}) };
    const o = store.get(`${key}.overrides`, {});
    const next = structuredClone(input);
    next.requests = requests;
    next.registry ||= {};
    next.landlord ||= {};
    if (o.priorDeposits10k !== undefined && o.priorDeposits10k !== "") next.landlord.priorDeposits10k = Number(o.priorDeposits10k);
    if (o.taxArrears) next.landlord.taxArrears = o.taxArrears;
    if (o.guaranteeEligible) next.landlord.guaranteeEligible = o.guaranteeEligible;
    if (o.ownerMatches) next.registry.ownerMatches = o.ownerMatches;
    if (o.registryIssuedAt) {
      next.registry.issuedAt = o.registryIssuedAt;
      if (next.registry.source === "none") next.registry.source = "registry";
    }
    return next;
  }

  async function evaluateCurrent() {
    state.verdict = await api("/api/jeonse-verdict", { method: "POST", body: JSON.stringify(withOverrides(state.current)) });
  }

  async function loadFeedback() {
    const payload = await api(`/api/property-feedback?key=${encodeURIComponent(state.current.key)}`);
    const changed = payload.items.length !== state.feedback.length;
    state.feedback = payload.items;
    return changed;
  }

  async function openCase(key) {
    const found = state.cases.find((item) => item.key === key);
    if (!found) return;
    state.mode = "report";
    state.current = found;
    state.feedback = [];
    state.tab = "rights";
    state.filter = "all";
    await Promise.all([loadFeedback()]);
    await evaluateCurrent();
    render();
    root()?.closest(".verdict-screen")?.scrollTo({ top: 0, behavior: "smooth" });
  }

  function openForm() {
    state.mode = "form";
    state.form = store.get("custom.form", null) || {
      address: "",
      housingType: "villa",
      deposit10k: "",
      priceBasis: "official",
      priceValue10k: "",
      official10k: "",
      issuedAt: "",
      mortgageMax10k: "",
      mortgageUnknown: false,
      trust: "unknown",
      seizure: "unknown",
      auction: "unknown",
      leaseRegistration: "unknown",
      ownerMatches: "unknown",
      lastOwnershipChange: "",
      priorDeposits10k: "",
      priorUnknown: true,
      taxArrears: "unknown",
      guaranteeEligible: "unknown",
      use: "unknown",
      violation: "unknown",
    };
    render();
  }

  async function openPending() {
    await ensureLoaded();
    const pending = state.pending;
    state.pending = null;
    if (pending === "form") return openForm();
    if (pending) return openCase(pending);
    if (!state.current && state.mode !== "form") return openCase(state.cases[0]?.key);
    render();
  }

  function startPolling() {
    clearInterval(state.pollTimer);
    state.pollTimer = setInterval(async () => {
      if (window.location.hash !== "#verdict" || state.mode !== "report" || !state.current) return;
      try {
        if (await loadFeedback()) {
          await evaluateCurrent();
          render();
          toast("새 제보가 반영됐어요");
        }
      } catch {
        /* 다음 주기에 다시 시도 */
      }
    }, POLL_MS);
  }

  // ---------- 렌더링 ----------

  function renderPicker() {
    const active = state.mode === "report" ? state.current?.key : null;
    const cases = state.cases
      .map(
        (item) => `
        <button class="verdict-chip-button ${item.key === active ? "is-active" : ""}" type="button" data-action="case" data-key="${esc(item.key)}">
          <span><strong>${esc(item.title)}</strong><small>${esc(item.summary)}</small></span>
        </button>`
      )
      .join("");
    return `
      <div class="verdict-picker">
        <span>예시 리포트</span>${cases}
        <button class="verdict-chip-button is-primary" type="button" data-action="form">+ 내 집 판정하기</button>
      </div>`;
  }

  function renderSummary(v) {
    const inspection = v.inspection || {};
    const requested = store.get(`${v.key}.inspectionRequested`, false);
    const inspectionBox =
      inspection.status === "done"
        ? `<div class="inspection-box done">
             <strong>✓ 핏홈 점검 완료</strong>
             <p>${esc(inspection.by)} · ${esc(inspection.date)}</p>
             <p>${esc(inspection.note || "")}</p>
           </div>`
        : `<div class="inspection-box none">
             <strong>핏홈 점검 전</strong>
             <p>지금 판정은 입력값과 공개 정보 기준이에요. 핏홈이 등기부·현장·서류를 직접 대조하면 항목마다 '핏홈 점검'으로 바뀝니다.</p>
             ${
               requested
                 ? `<p><b>점검 신청이 접수됐어요.</b> (시연: 실제 점검 연결은 준비 중)</p>`
                 : `<button class="small-button primary" type="button" data-action="inspect">핏홈 점검 신청</button>`
             }
           </div>`;
    return `
      <section class="verdict-card grade-${v.grade}">
        <div class="verdict-summary">
          <div class="grade-block">
            <div class="grade-badge"><span>${esc(v.gradeLabel)}<small>판정 등급</small></span></div>
            <div class="grade-text">
              <h2>${esc(GRADE_COPY[v.grade])}</h2>
              <p class="meta">${esc(v.property.label || v.property.address)} · ${esc(v.property.housingLabel)} · 내 보증금 ${esc(money(v.ltv.deposit10k))} · ${esc(v.asOf)} 기준</p>
              <p class="meta"><b>${esc(v.headline)}</b></p>
              <div class="tag-row">${v.tags.map((tag) => `<span>${esc(tag)}</span>`).join("")}</div>
            </div>
          </div>
          ${inspectionBox}
        </div>
      </section>`;
  }

  function renderLtv(v) {
    const l = v.ltv;
    if (!l.price10k) {
      return `<section class="verdict-card"><h2>집값 대비 빚</h2><p class="sub">집값을 입력하면 근저당·선순위 보증금·내 보증금이 집값의 몇 %인지 보여드려요.</p></section>`;
    }
    const scale = Math.max(100, (l.ratioPct || 0) + 8);
    const pct = (value) => ((value || 0) / l.price10k) * 100;
    const width = (value) => `${(pct(value) / scale) * 100}%`;
    const seg = (cls, value, label) =>
      value > 0 ? `<div class="${cls}" style="width:${width(value)}" title="${esc(label)} ${esc(money(value))}">${pct(value) / scale > 0.09 ? esc(label) : ""}</div>` : "";
    const lines = l.lines
      .map((line) => `<div class="ltv-line" style="left:${(line.pct / scale) * 100}%"><span>${line.pct}%</span></div>`)
      .join("");
    const h80 = l.headroom10k["80"];
    const h90 = l.headroom10k["90"];
    let headroom;
    if (h80 > 0) {
      headroom = `<div class="ltv-headroom" style="background:var(--safe-soft)">근저당이 <b>${esc(money(h80))}</b> 더 잡혀도 80% 아래예요. HUG 보증 한도(90%)까지는 ${esc(money(h90))} 남았어요.</div>`;
    } else if (h90 > 0) {
      headroom = `<div class="ltv-headroom" style="background:var(--caution-soft)">이미 깡통전세 경계(80%)를 넘었어요. HUG 보증 한도(90%)까지 ${esc(money(h90))}만 남았어요.</div>`;
    } else {
      headroom = `<div class="ltv-headroom" style="background:var(--danger-soft)">HUG 보증 한도(90%)를 <b>${esc(money(-h90))}</b> 넘었어요. 전세보증보험 가입이 안 되는 수준입니다.</div>`;
    }
    return `
      <section class="verdict-card">
        <div class="verdict-card-head">
          <h2>집값 대비 빚 <span style="font-size:15px;color:var(--muted)">LTV ${l.ratioPct}%${l.isLowerBound ? " 이상" : ""}</span></h2>
          ${srcChip(l.priceSource, `집값 근거: ${l.priceSourceLabel}`)}
        </div>
        <div class="ltv-bar-wrap">
          ${lines}
          <div class="ltv-price-mark" style="left:${(100 / scale) * 100}%"></div>
          <div class="ltv-bar">
            ${seg("seg-mortgage", l.mortgage10k, "근저당")}
            ${seg("seg-prior", l.prior10k, "선순위")}
            ${seg("seg-deposit", l.deposit10k, "내 보증금")}
            ${seg("seg-rest", Math.max(0, l.price10k - l.debt10k), "")}
          </div>
        </div>
        <div class="ltv-legend">
          <span><i style="background:#475569"></i>근저당 채권최고액</span>
          <span><i style="background:#f59e0b"></i>선순위 보증금</span>
          <span><i style="background:var(--naver)"></i>내 보증금</span>
          <span><i style="background:#e2e8f0"></i>남는 집값</span>
          <span>굵은 선 = 집값 100%</span>
        </div>
        <div class="ltv-legend">${l.lines.map((line) => `<span><b>${line.pct}%</b> ${esc(line.label)} (${esc(line.basis)})</span>`).join("")}</div>
        <div class="ltv-numbers">
          <div><span>집값</span><strong>${esc(money(l.price10k))}</strong><span>${esc(l.priceLabel)}</span></div>
          <div><span>근저당 채권최고액</span><strong>${esc(money(l.mortgage10k))}</strong></div>
          <div><span>선순위 보증금</span><strong>${esc(money(l.prior10k))}</strong></div>
          <div><span>내 보증금</span><strong>${esc(money(l.deposit10k))}</strong></div>
        </div>
        ${headroom}
        ${l.isLowerBound ? `<p class="sub" style="margin:10px 0 0">모르는 값은 0으로 계산했어요. 실제 비율은 이보다 높을 수 있습니다.</p>` : ""}
      </section>`;
  }

  function areaBreakdown(checks, result) {
    return AREA_ORDER.map((area) => {
      const n = checks.filter((c) => c.area === area && c.result === result).length;
      return n ? `<span>${AREA_LABELS[area]}<b>${n}건</b></span>` : "";
    }).join("");
  }

  function renderResults(v) {
    const rights = v.rights;
    const rDanger = rights.filter((c) => c.result === "danger").length;
    const rUnknown = rights.filter((c) => c.result === "unknown").length;
    const rCaution = rights.filter((c) => c.result === "caution").length;
    const rightsResult = rDanger ? "danger" : rCaution || rUnknown ? (rCaution ? "caution" : "unknown") : "pass";
    const rightsText = rDanger || rCaution || rUnknown
      ? [rDanger && `위험 ${rDanger}건`, rCaution && `주의 ${rCaution}건`, rUnknown && `미확인 ${rUnknown}건`].filter(Boolean).join(" · ")
      : "신탁·압류·경매·임차권등기 없음";
    const row = (icon, name, detail, result, action = "") => `
      <div class="result-row">
        <div class="icon" aria-hidden="true"><i data-lucide="${icon}"></i></div>
        <div class="name">${name}</div>
        <div class="detail">${detail || '<span class="muted">없음</span>'}</div>
        <div class="action">${action || chip(result)}</div>
      </div>`;
    return `
      <section class="verdict-card">
        <h2>주요 판정 결과</h2>
        <p class="sub">항목 ${v.checks.length}개를 기준과 비교했어요.</p>
        <div class="result-table">
          ${row("shield-check", "권리 진단", `<span>${esc(rightsText)}</span>`, rightsResult)}
          ${row("check", `판정 통과 ${v.counts.pass}건`, areaBreakdown(v.checks, "pass"), "pass")}
          ${row("triangle-alert", `주의 ${v.counts.caution}건`, areaBreakdown(v.checks, "caution"), v.counts.caution ? "caution" : "pass")}
          ${row("octagon-x", `위험 ${v.counts.danger}건`, areaBreakdown(v.checks, "danger"), v.counts.danger ? "danger" : "pass")}
          ${row(
            "circle-help",
            `미확인 ${v.counts.unknown}건`,
            areaBreakdown(v.checks, "unknown"),
            "unknown",
            v.counts.unknown ? `<button class="small-button primary" type="button" data-action="goto" data-target="verdictRequests">확인 요청 보기</button>` : chip("pass")
          )}
        </div>
      </section>`;
  }

  function renderDetail(v) {
    const tabs = `
      <div class="verdict-tabs" role="tablist">
        <button type="button" role="tab" class="${state.tab === "rights" ? "is-active" : ""}" data-action="tab" data-tab="rights">권리 진단</button>
        <button type="button" role="tab" class="${state.tab === "all" ? "is-active" : ""}" data-action="tab" data-tab="all">판정 항목 전체 (${v.checks.length})</button>
      </div>`;
    if (state.tab === "rights") {
      const rank = { danger: 0, caution: 1, unknown: 2, pass: 3 };
      const tiles = [...v.rights]
        .sort((a, b) => rank[a.result] - rank[b.result])
        .map(
          (c) => `
          <div class="rights-tile is-${c.result}">
            <div class="top"><strong>${esc(c.label)}</strong>${chip(c.result)}</div>
            <div class="top"><span>${esc(c.value)}</span>${srcChip(c.source, c.sourceLabel)}</div>
            <p>${esc(c.standard)}</p>
            ${c.note ? `<p>${esc(c.note)}</p>` : ""}
          </div>`
        )
        .join("");
      return `<section class="verdict-card"><h2>상세 판정</h2>${tabs}<div class="rights-grid">${tiles}</div></section>`;
    }
    const groups = AREA_ORDER.map((area) => {
      const rows = v.checks.filter((c) => c.area === area);
      if (!rows.length) return "";
      return `
        <div class="check-group">
          <h4>${AREA_LABELS[area]}</h4>
          <table class="check-table">
            <thead><tr><th>항목</th><th>기준</th><th>이 집</th><th>결과</th><th>출처</th></tr></thead>
            <tbody>
              ${rows
                .map(
                  (c) => `<tr>
                    <td><b>${esc(c.label)}</b>${c.note ? `<span class="note">${esc(c.note)}</span>` : ""}</td>
                    <td class="std">${esc(c.standard)}</td>
                    <td>${esc(c.value)}</td>
                    <td>${chip(c.result)}</td>
                    <td>${srcChip(c.source, c.sourceLabel)}</td>
                  </tr>`
                )
                .join("")}
            </tbody>
          </table>
        </div>`;
    }).join("");
    return `<section class="verdict-card"><h2>상세 판정</h2>${tabs}${groups}</section>`;
  }

  function timelineItems(v) {
    const reports = state.feedback.map((f) => ({
      date: (f.createdAt || "").slice(0, 10),
      kind: "report",
      title: `제보 · ${f.categoryLabel}`,
      detail: `${f.text} (${f.roleLabel} · 미검증)`,
    }));
    return [...v.history, ...reports].sort((a, b) => (b.date || "").localeCompare(a.date || ""));
  }

  function renderHistory(v) {
    const s = v.historySummary;
    const items = timelineItems(v);
    const cautionTitles = [...s.cautionEvents, ...(state.feedback.length ? [`미검증 제보 ${state.feedback.length}건`] : [])];
    const counts = {
      all: items.length,
      ownership: items.filter((e) => KIND_FILTER.ownership.includes(e.kind)).length,
      mortgage: items.filter((e) => KIND_FILTER.mortgage.includes(e.kind)).length,
      caution: items.filter((e) => KIND_FILTER.caution.includes(e.kind)).length,
    };
    const shown = state.filter === "all" ? items : items.filter((e) => KIND_FILTER[state.filter].includes(e.kind));
    const filterButton = (key, label) =>
      `<button type="button" class="${state.filter === key ? "is-active" : ""}" data-action="filter" data-filter="${key}">${label} ${counts[key]}</button>`;
    const kindClass = (kind) => (KIND_FILTER.caution.includes(kind) && kind !== "report" ? "k-caution" : `k-${kind}`);
    return `
      <section class="verdict-card">
        <h2>등기 이력</h2>
        <p class="sub">등기부 갑구(소유권)·을구(근저당) 기록과 들어온 제보를 날짜순으로 모았어요.</p>
        <div class="history-summary">
          <div><span>소유자 변경</span><b>총 ${s.ownershipChanges}회${s.lastOwnershipChange ? ` · 최근 ${esc(s.lastOwnershipChange)}` : ""}</b></div>
          <div><span>근저당 기록</span><b>${s.mortgageEvents}건</b></div>
          <div><span>주의 이력</span><b style="color:${cautionTitles.length ? "var(--danger-v)" : "inherit"}">${cautionTitles.length ? esc(cautionTitles.join(", ")) : "없음"}</b></div>
        </div>
        <div class="filter-row">
          ${filterButton("all", "전체")}${filterButton("ownership", "소유권")}${filterButton("mortgage", "근저당")}${filterButton("caution", "주의·제보")}
        </div>
        ${
          shown.length
            ? `<ul class="timeline">${shown
                .map(
                  (e) => `<li>
                    <div class="when">${esc(e.date)}</div>
                    <div class="what ${kindClass(e.kind)}"><header><span>${esc(e.title)}</span></header><p>${esc(e.detail || "")}</p></div>
                  </li>`
                )
                .join("")}</ul>`
            : `<p class="sub">기록이 없어요. 등기부를 열람하면 이곳에 쌓입니다.</p>`
        }
      </section>`;
  }

  function receivedInput(item) {
    const o = store.get(`${state.current.key}.overrides`, {});
    const seg = (field, options) =>
      `<span class="seg">${options
        .map(([value, label]) => `<label><input type="radio" name="ov-${field}" value="${value}" data-action="override" data-field="${field}" ${o[field] === value ? "checked" : ""}><span>${label}</span></label>`)
        .join("")}</span>`;
    switch (item.id) {
      case "fixedDate":
        return `<label class="unknown-toggle">받은 선순위 보증금 합계(만원) <input type="number" min="0" style="width:120px" value="${esc(o.priorDeposits10k ?? "")}" data-action="override-number" data-field="priorDeposits10k"></label>`;
      case "taxCert":
        return seg("taxArrears", [["no", "체납 없음"], ["yes", "체납 있음"]]);
      case "guarantee":
        return seg("guaranteeEligible", [["yes", "가입 가능"], ["no", "가입 불가"]]);
      case "ownerId":
        return seg("ownerMatches", [["yes", "소유자 일치"], ["no", "불일치"]]);
      case "registryLatest":
        return `<button class="small-button" type="button" data-action="override-today" data-field="registryIssuedAt">오늘 열람함으로 기록</button>`;
      default:
        return "";
    }
  }

  function renderRequests(v) {
    const statuses = [["none", "요청 전"], ["requested", "요청함"], ["received", "받음"], ["refused", "거절"], ["noResponse", "무응답"]];
    const list = v.requests.length
      ? v.requests
          .map(
            (q) => `
          <div class="req-item st-${q.status}">
            <div class="top"><strong>${esc(q.title)}</strong><span class="src-chip">받을 곳: ${esc(q.to)}</span></div>
            <p>${esc(q.why)}</p>
            <span class="legal">근거: ${esc(q.legal)}</span>
            <div class="req-actions">
              <select data-action="req-status" data-id="${esc(q.id)}" aria-label="${esc(q.title)} 요청 상태">
                ${statuses.map(([value, label]) => `<option value="${value}" ${q.status === value ? "selected" : ""}>${label}</option>`).join("")}
              </select>
              <button class="small-button" type="button" data-action="copy" data-text="${esc(q.template)}">요청문 복사</button>
              ${q.status === "received" ? receivedInput(q) : ""}
            </div>
          </div>`
          )
          .join("")
      : `<p class="sub">지금 따로 요청할 서류가 없어요.</p>`;
    return `
      <section class="verdict-card" id="verdictRequests">
        <h2>확인 요청</h2>
        <p class="sub">집주인 동의가 있어야 볼 수 있는 정보예요. 요청문을 복사해 보내고 결과를 기록하면 판정에 바로 반영돼요. <b>거절·무응답도 위험 신호로 반영</b>합니다.</p>
        <div class="req-list">${list}</div>
      </section>`;
  }

  function renderStages(v) {
    const done = new Set(store.get(`${v.key}.stages`, []));
    const total = v.stages.reduce((sum, s) => sum + s.items.length, 0);
    const checked = v.stages.reduce((sum, s) => sum + s.items.filter((i) => done.has(`${s.id}.${i.id}`)).length, 0);
    return `
      <section class="verdict-card">
        <div class="verdict-card-head"><h2>단계별 재확인</h2><span class="src-chip">${checked}/${total} 완료</span></div>
        <div class="stage-progress"><div style="width:${total ? (checked / total) * 100 : 0}%"></div></div>
        <div class="stage-grid">
          ${v.stages
            .map((s, index) => {
              const n = s.items.filter((i) => done.has(`${s.id}.${i.id}`)).length;
              return `<div class="stage">
                <h4><span>${index + 1}. ${esc(s.label)}</span><span>${n}/${s.items.length}</span></h4>
                ${s.items
                  .map(
                    (i) => `<label><input type="checkbox" data-action="stage" data-id="${esc(`${s.id}.${i.id}`)}" ${done.has(`${s.id}.${i.id}`) ? "checked" : ""}><span>${esc(i.text)}</span></label>`
                  )
                  .join("")}
              </div>`;
            })
            .join("")}
        </div>
      </section>`;
  }

  function renderClauses(v) {
    return `
      <section class="verdict-card">
        <h2>추천 특약</h2>
        <p class="sub">판정 결과에 맞춰 골랐어요. 참고 문구이니 계약 전 전문가 검토를 권해요.</p>
        <div class="clause-list">
          ${v.clauses
            .map(
              (c) => `<div class="clause-item">
                <div class="top"><strong>${esc(c.title)}</strong><button class="small-button" type="button" data-action="copy" data-text="${esc(c.text)}">문구 복사</button></div>
                <p>${esc(c.text)}</p>
                <span class="basis">${esc(c.reason)} · ${esc(c.basis)}</span>
              </div>`
            )
            .join("")}
        </div>
      </section>`;
  }

  function renderFeedback() {
    const list = state.feedback.length
      ? state.feedback
          .map(
            (f) => `<div class="feedback-item">
              <header><span>${esc(f.categoryLabel)} · ${esc(f.roleLabel)}</span><span class="r-chip r-caution">${esc(f.statusLabel)}</span></header>
              <div>${esc(f.text)}</div>
              <time>${esc((f.createdAt || "").replace("T", " "))}</time>
            </div>`
          )
          .join("")
      : `<p class="sub">아직 제보가 없어요.</p>`;
    return `
      <section class="verdict-card">
        <div class="verdict-card-head">
          <h2>문제 제보</h2>
          <span class="src-chip"><span class="live-dot"></span>실시간 · 15초마다 갱신</span>
        </div>
        <p class="sub">이 집에 살았거나 다녀온 분, 중개사·이웃의 제보를 받아요. 핏홈이 확인하기 전까지는 '미검증'으로 표시되고, 판정에는 주의 신호 하나로만 반영돼요.</p>
        <div class="feedback-grid">
          <div class="feedback-list">${list}</div>
          <form class="feedback-form" data-action="feedback-form">
            <select name="category" aria-label="제보 종류">
              <option value="info">정보가 달라요</option>
              <option value="condition">집 상태 문제 (누수·곰팡이 등)</option>
              <option value="landlord">임대인·중개사 문제</option>
              <option value="other">기타</option>
            </select>
            <select name="role" aria-label="제보자">
              <option value="visitor">방문자</option>
              <option value="tenant">세입자</option>
              <option value="neighbor">이웃</option>
              <option value="broker">중개사</option>
            </select>
            <textarea name="text" maxlength="500" placeholder="예) 욕실 천장에 누수 자국이 있어요" aria-label="제보 내용"></textarea>
            <button class="small-button primary" type="submit">제보 보내기</button>
          </form>
        </div>
      </section>`;
  }

  function renderReport() {
    const v = state.verdict;
    return `
      ${state.current.isDemo ? `<div class="demo-banner">ⓘ ${esc(state.notice)}</div>` : ""}
      ${renderSummary(v)}
      ${renderLtv(v)}
      ${renderResults(v)}
      ${renderDetail(v)}
      ${renderHistory(v)}
      ${renderRequests(v)}
      ${renderStages(v)}
      ${renderClauses(v)}
      ${renderFeedback()}
      <p class="verdict-notice">${esc(v.notice)}</p>
      ${state.current.isDemo ? "" : `<div class="verdict-picker" style="justify-content:center"><button class="verdict-chip-button" type="button" data-action="form">입력 수정하기</button></div>`}`;
  }

  // ---------- 입력 폼 ----------

  function seg(name, options, value) {
    return `<span class="seg" role="radiogroup">${options
      .map(([v, label]) => `<label><input type="radio" name="${name}" value="${v}" ${value === v ? "checked" : ""}><span>${label}</span></label>`)
      .join("")}</span>`;
  }
  const TRI = [["no", "없음"], ["yes", "있음"], ["unknown", "모름"]];

  function moneyField(name, label, value, hint, extra = "") {
    return `<label class="field"><span>${label}</span>
      <input type="number" min="0" inputmode="numeric" name="${name}" value="${esc(value)}" placeholder="만원 단위" data-money>
      <small data-money-hint="${name}">${value ? esc(money(value)) : esc(hint)}</small>${extra}</label>`;
  }

  function renderForm() {
    const f = state.form;
    const priceLabel = { market: "시세·감정가 (만원)", trade: "실거래가 (만원)" }[f.priceBasis];
    return `
      <form class="verdict-form" data-action="verdict-form" novalidate>
        <section class="form-step">
          <h2><span class="num">1</span>집 정보</h2>
          <p class="sub">서울 아파트는 단지 이름으로 찾을 수 있고, 빌라·오피스텔은 주소를 그대로 적으면 돼요.</p>
          <div class="form-grid">
            <label class="field full"><span>주소 또는 단지명</span>
              <input type="text" name="address" value="${esc(f.address)}" placeholder="예) 서울 강서구 화곡동 ○○빌라" autocomplete="off" data-addr>
              <div class="addr-suggest" data-addr-list hidden></div>
            </label>
            <div class="field full"><span>주택 유형</span>${seg("housingType", [["apartment", "아파트"], ["villa", "빌라·다세대"], ["multi", "다가구"], ["officetel", "오피스텔"]], f.housingType)}</div>
            ${moneyField("deposit10k", "내 보증금 (만원)", f.deposit10k, "예) 16000 = 1억 6천만원")}
            <div class="field"><span>집값 기준</span>${seg("priceBasis", [["official", "공시가격×140%"], ["market", "시세·감정가"], ["trade", "실거래가"]], f.priceBasis)}
              <small>빌라는 시세가 없어 HUG처럼 공시가격의 140%로 봐요.</small></div>
            ${f.priceBasis === "official" ? "" : moneyField("priceValue10k", priceLabel, f.priceValue10k, "")}
            ${moneyField("official10k", f.priceBasis === "official" ? "공시가격 (만원)" : "공시가격 (선택, 만원)", f.official10k, "부동산공시가격알리미에서 확인")}
          </div>
        </section>

        <section class="form-step">
          <h2><span class="num">2</span>등기부 값</h2>
          <p class="sub">등기부는 인터넷등기소에서 누구나 700원에 열람할 수 있어요. 모르는 칸은 '모름'으로 두면 판정이 '주의'까지만 나옵니다.</p>
          <div class="form-grid">
            <label class="field"><span>등기부 열람일</span><input type="date" name="issuedAt" value="${esc(f.issuedAt)}"></label>
            ${moneyField("mortgageMax10k", "근저당 채권최고액 합계 (만원)", f.mortgageMax10k, "을구에 적힌 금액을 모두 더해요",
              `<label class="unknown-toggle"><input type="checkbox" name="mortgageUnknown" ${f.mortgageUnknown ? "checked" : ""}>모름</label>`)}
            <div class="field"><span>신탁등기 (갑구)</span>${seg("trust", TRI, f.trust)}</div>
            <div class="field"><span>압류·가압류 (갑구)</span>${seg("seizure", TRI, f.seizure)}</div>
            <div class="field"><span>경매개시결정</span>${seg("auction", TRI, f.auction)}</div>
            <div class="field"><span>임차권등기 (을구)</span>${seg("leaseRegistration", TRI, f.leaseRegistration)}</div>
            <div class="field"><span>등기부 소유자 = 계약 상대</span>${seg("ownerMatches", [["yes", "같음"], ["no", "다름"], ["unknown", "모름"]], f.ownerMatches)}</div>
            <label class="field"><span>최근 소유권 이전일</span><input type="date" name="lastOwnershipChange" value="${esc(f.lastOwnershipChange)}"><small>갑구 마지막 '소유권 이전' 날짜</small></label>
          </div>
        </section>

        <section class="form-step">
          <h2><span class="num">3</span>임대인·건물</h2>
          <p class="sub">집주인 동의가 필요한 정보는 몰라도 괜찮아요. 리포트에서 확인 요청으로 받아낼 수 있어요.</p>
          <div class="form-grid">
            ${f.housingType === "multi" ? moneyField("priorDeposits10k", "선순위 보증금 합계 (만원, 다가구)", f.priorDeposits10k, "확정일자 부여현황으로 확인",
              `<label class="unknown-toggle"><input type="checkbox" name="priorUnknown" ${f.priorUnknown ? "checked" : ""}>모름</label>`) : ""}
            <div class="field"><span>임대인 세금 체납</span>${seg("taxArrears", TRI, f.taxArrears)}</div>
            <div class="field"><span>전세보증보험 가입</span>${seg("guaranteeEligible", [["yes", "가능"], ["no", "불가"], ["unknown", "모름"]], f.guaranteeEligible)}</div>
            <div class="field"><span>건축물 용도</span>${seg("use", [["residential", "주거용"], ["nonresidential", "비주거"], ["unknown", "모름"]], f.use)}</div>
            <div class="field"><span>위반건축물</span>${seg("violation", TRI, f.violation)}</div>
          </div>
          <div class="tip">건축물 용도·위반건축물은 정부24 건축물대장에서 무료로 확인할 수 있어요.</div>
        </section>
        <p class="sub" data-form-error style="color:var(--danger-v);text-align:center;margin:0"></p>
        <div class="form-submit"><button type="submit">판정 보기</button></div>
      </form>`;
  }

  function readForm(form) {
    const data = new FormData(form);
    const f = { ...state.form };
    for (const key of Object.keys(f)) {
      if (typeof f[key] === "boolean") f[key] = data.get(key) === "on";
      else if (data.has(key)) f[key] = String(data.get(key)).trim();
    }
    return f;
  }

  function formToInput(f) {
    const n = (v) => (v === "" || v === null || v === undefined ? null : Number(v));
    const address = f.address || "직접 입력한 집";
    const history = [];
    if (f.lastOwnershipChange) history.push({ date: f.lastOwnershipChange, kind: "ownership", title: "소유권 이전", detail: "입력한 최근 소유권 이전일" });
    if (f.issuedAt) history.push({ date: f.issuedAt, kind: "inspection", title: "등기부 열람", detail: "사용자 열람" });
    return {
      key: `addr:${address.replace(/\s+/g, "")}`.slice(0, 80),
      isDemo: false,
      title: address,
      property: { label: address, address, housingType: f.housingType },
      deposit10k: n(f.deposit10k),
      price: { basis: f.priceBasis, value10k: n(f.priceValue10k), official10k: n(f.official10k), source: "input" },
      registry: {
        source: f.issuedAt ? "registry" : "input",
        issuedAt: f.issuedAt || null,
        mortgageMax10k: f.mortgageUnknown ? null : n(f.mortgageMax10k),
        trust: f.trust,
        seizure: f.seizure,
        auction: f.auction,
        leaseRegistration: f.leaseRegistration,
        ownerMatches: f.ownerMatches,
        lastOwnershipChange: f.lastOwnershipChange || null,
      },
      landlord: {
        source: "input",
        priorDeposits10k: f.housingType === "multi" && !f.priorUnknown ? n(f.priorDeposits10k) : null,
        taxArrears: f.taxArrears,
        guaranteeEligible: f.guaranteeEligible,
      },
      building: { source: "input", use: f.use, violation: f.violation },
      requests: {},
      inspection: { status: "none" },
      history,
    };
  }

  async function submitForm(form) {
    const f = readForm(form);
    state.form = f;
    store.set("custom.form", f);
    const error = form.querySelector("[data-form-error]");
    const priceMissing = f.priceBasis === "official" ? !Number(f.official10k) : !Number(f.priceValue10k);
    if (!Number(f.deposit10k)) return (error.textContent = "내 보증금을 입력해주세요.");
    if (priceMissing) return (error.textContent = "집값 기준에 맞는 금액(공시가격 또는 시세)을 입력해주세요.");
    const input = formToInput(f);
    state.current = input;
    state.mode = "report";
    state.feedback = [];
    state.tab = "rights";
    state.filter = "all";
    await loadFeedback();
    await evaluateCurrent();
    render();
    root()?.closest(".verdict-screen")?.scrollTo({ top: 0, behavior: "smooth" });
  }

  let addrTimer = null;
  function suggestAddress(input) {
    clearTimeout(addrTimer);
    const list = input.parentElement.querySelector("[data-addr-list]");
    const query = input.value.trim();
    if (query.length < 2) return (list.hidden = true);
    addrTimer = setTimeout(async () => {
      try {
        const payload = await api(`/api/location-suggestions?query=${encodeURIComponent(query)}&limit=6`);
        const items = (payload.suggestions || []).filter((s) => s.selectable !== false);
        list.innerHTML = items
          .map((s) => `<button type="button" data-action="addr-pick" data-address="${esc(s.address || s.label)}" data-type="${esc(s.type)}">${esc(s.label)} <small style="color:var(--muted)">${esc(s.address || "")}</small></button>`)
          .join("");
        list.hidden = !items.length;
      } catch {
        list.hidden = true;
      }
    }, 250);
  }

  // ---------- 렌더 진입점과 이벤트 ----------

  function render() {
    const node = root();
    if (!node) return;
    let body = "";
    if (state.mode === "form") body = renderForm();
    else if (state.mode === "report" && state.verdict) body = renderReport();
    else body = `<section class="verdict-card"><p class="sub">예시 리포트를 고르거나 내 집 판정을 시작하세요.</p></section>`;
    node.innerHTML = renderPicker() + body;
    window.lucide?.createIcons();
  }

  async function rerender() {
    await evaluateCurrent();
    render();
  }

  function bind() {
    document.querySelectorAll("[data-start-verdict]").forEach((button) => {
      button.addEventListener("click", () => {
        state.pending = button.dataset.startVerdict || null;
        if (window.location.hash === "#verdict") openPending();
        else window.location.hash = "#verdict";
      });
    });
    document.querySelectorAll("[data-verdict-nav]").forEach((button) => {
      button.addEventListener("click", () => (window.location.hash = button.dataset.verdictNav));
    });
    window.addEventListener("hashchange", () => {
      if (window.location.hash === "#verdict") openPending();
    });
    if (window.location.hash === "#verdict") openPending();

    const node = root();
    node.addEventListener("click", async (event) => {
      const target = event.target.closest("[data-action]");
      if (!target) return;
      const action = target.dataset.action;
      const key = state.current?.key;
      if (action === "case") await openCase(target.dataset.key);
      else if (action === "form") openForm();
      else if (action === "tab") {
        state.tab = target.dataset.tab;
        render();
      } else if (action === "filter") {
        state.filter = target.dataset.filter;
        render();
      } else if (action === "copy") copyText(target.dataset.text);
      else if (action === "goto") document.getElementById(target.dataset.target)?.scrollIntoView({ behavior: "smooth", block: "start" });
      else if (action === "inspect") {
        store.set(`${key}.inspectionRequested`, true);
        render();
        toast("핏홈 점검 신청이 접수됐어요 (시연)");
      } else if (action === "override-today") {
        const o = store.get(`${key}.overrides`, {});
        o[target.dataset.field] = new Date().toISOString().slice(0, 10);
        store.set(`${key}.overrides`, o);
        await rerender();
      } else if (action === "addr-pick") {
        const input = node.querySelector("[data-addr]");
        input.value = target.dataset.address;
        state.form.address = target.dataset.address;
        if (target.dataset.type === "apartment") {
          state.form = { ...readForm(input.form), housingType: "apartment", priceBasis: "market" };
          render();
        } else target.parentElement.hidden = true;
      }
    });

    node.addEventListener("change", async (event) => {
      const target = event.target;
      const key = state.current?.key;
      const action = target.dataset.action;
      if (action === "req-status") {
        const requests = store.get(`${key}.requests`, {});
        requests[target.dataset.id] = target.value;
        store.set(`${key}.requests`, requests);
        await rerender();
        toast(target.value === "refused" || target.value === "noResponse" ? "거절·무응답을 위험 신호로 반영했어요" : "요청 상태를 기록했어요");
      } else if (action === "override" || action === "override-number") {
        const o = store.get(`${key}.overrides`, {});
        o[target.dataset.field] = target.value;
        store.set(`${key}.overrides`, o);
        await rerender();
      } else if (action === "stage") {
        const done = new Set(store.get(`${key}.stages`, []));
        target.checked ? done.add(target.dataset.id) : done.delete(target.dataset.id);
        store.set(`${key}.stages`, [...done]);
        render();
      } else if (target.form?.dataset.action === "verdict-form" && (target.name === "housingType" || target.name === "priceBasis")) {
        state.form = readForm(target.form);
        render();
      }
    });

    node.addEventListener("input", (event) => {
      const target = event.target;
      if (target.matches("[data-addr]")) suggestAddress(target);
      if (target.matches("[data-money]")) {
        const hint = node.querySelector(`[data-money-hint="${target.name}"]`);
        if (hint) hint.textContent = target.value ? money(target.value) : "";
      }
    });

    node.addEventListener("submit", async (event) => {
      event.preventDefault();
      const form = event.target;
      if (form.dataset.action === "verdict-form") {
        try {
          await submitForm(form);
        } catch (error) {
          form.querySelector("[data-form-error]").textContent = error.message;
        }
      } else if (form.dataset.action === "feedback-form") {
        const data = new FormData(form);
        try {
          await api("/api/property-feedback", {
            method: "POST",
            body: JSON.stringify({ key: state.current.key, category: data.get("category"), role: data.get("role"), text: data.get("text") }),
          });
          await loadFeedback();
          await rerender();
          toast("제보가 접수됐어요. 핏홈 확인 전까지 '미검증'으로 표시돼요");
        } catch (error) {
          toast(error.message);
        }
      }
    });
    startPolling();
  }

  document.addEventListener("DOMContentLoaded", bind);
})();
