// 임차인 리포트에서 사용하는 등기부 가져오기와 집주인 서류 접수함.
window.fitHomeDocumentIntake = function ({ store, esc, money, copyText, render, toast, base, verdict, saveAddress, recalculate, renderChecklist }) {
  const kinds = { fixedDate: "선순위 임차보증금·확정일자 자료", moveIn: "전입세대확인서", nationalTax: "국세 납세증명서", localTax: "지방세 납세증명서" };
  const fields = { title: "문서명", entry: "개별 기재 내용", address: "주소", issuedAt: "발급일", issued: "발급일", issued_at: "발급일", date: "발급일", amount: "금액", amount10k: "금액", expiresOn: "유효기간" };
  const states = new Map();
  let provider;
  let providerCheck;
  const identityLabels = { unavailable: "인증 기관 미연결", unverified: "인증 가능", pending: "본인인증 진행 중", verified: "신청자 인증 완료" };
  let buildingProvider;
  let buildingCheck;
  const serviceTitles = {
    registry: "등기사항전부증명서", landlord: "집주인 서류 요청·확인", building: "건축물대장",
    price: "공시가격·실거래가", ownerId: "임대인 신분·대리권", broker: "공인중개사·확인설명서",
    guarantee: "반환보증 가입 조건", identity: "신청자 본인인증",
  };
  const report = () => base().key;
  const state = () => {
    const key = report();
    if (!states.has(key)) states.set(key, { results: [], busy: "", error: "", submitted: null, review: null });
    return states.get(key);
  };
  const request = () => store.get(report() + ".documentRequest", null);

  async function post(path, payload) {
    const response = await fetch("/api/" + path, {
      method: "POST", headers: { "Content-Type": "application/json" },
      cache: "no-store", body: JSON.stringify(payload),
    });
    let data;
    try { data = await response.json(); } catch { throw new Error("서류 서버에 연결할 수 없어요. 잠시 후 다시 시도하세요."); }
    if (!response.ok || data.ok === false) {
      const error = new Error(data.error || "서류 요청을 처리할 수 없어요.");
      error.status = response.status;
      throw error;
    }
    return data;
  }

  function loadProvider() {
    if (providerCheck) return;
    providerCheck = post("registry/status", {}).then((result) => {
      provider = result;
    }).catch(() => { provider = { available: false, reason: "등기부 조회 연결 상태를 확인하지 못했어요." }; })
      .finally(() => {
        const area = document.querySelector("[data-registry-provider]");
        if (area) area.innerHTML = providerOptions();
        const badge = document.querySelector('[data-service-status="registry"]');
        if (badge && base()) badge.textContent = registryStatus();
      });
  }

  function amountLabel(value) {
    if (Number.isFinite(value) && !Number.isInteger(value)) return Math.round(value * 10000).toLocaleString("ko-KR") + "원";
    return money(value);
  }

  function addressNeedsSaving() {
    const draft = state().draft;
    return draft && (draft.address.normalize("NFC").trim().replace(/\s+/g, " ") !== base().property.address.normalize("NFC").trim().replace(/\s+/g, " ")
      || draft.housingType !== verdict().property.housingType);
  }

  function evidence(items = []) {
    if (!items.length) return "";
    return `<details class="fh-evidence-lines" open><summary>원문 근거 ${items.length}줄</summary>
      <ol>${items.map(row => `<li><small>${esc(fields[row.field] || "")} ${esc(row.page ?? "–")}쪽 · ${esc(row.line ?? "–")}줄</small>
        <blockquote>${esc(row.text)}</blockquote></li>`).join("")}</ol></details>`;
  }

  function providerOptions() {
    const busy = state().busy ? "disabled" : "";
    return provider?.available ? `<p class="fh-sub">연동 기관의 요금제에 따라 주소 검색에도 비용이 발생할 수 있어요. 등기부를 유료 열람하기 전에는 별도로 동의를 받아요.</p><button type="button" class="fh-btn" data-intake="search" ${busy}>이 주소로 등기 검색</button>`
        : `<p class="fh-sub">${esc(provider?.reason || "등기부 조회 연결 상태를 확인하고 있어요.")} 등기부 PDF를 올리면 주소·발급일·채권최고액을 읽어와요.</p>`;
  }

  function registryEvidence() {
    const saved = store.get(report() + ".registryEvidence", null);
    const edits = store.get(report() + ".edits", {});
    return saved && edits.mortgageUnknown === false && edits.mortgageMax10k != null && edits.mortgageMax10k !== ""
      && Number(edits.mortgageMax10k) === saved.mortgageMax10k && edits.issuedAt === saved.issuedAt
      && saved.address === base().property.address ? saved : null;
  }

  function registryPanel() {
    const s = state();
    const result = s.review || registryEvidence();
    const canApply = result && !result.reviewRequired && Number.isFinite(result.mortgageMax10k) && result.mortgageMax10k >= 0;
    const busy = s.busy ? "disabled" : "";
    return `<section class="fh-doc-intake" data-intake-panel="registry">
      <h4 class="fh-group">이 매물 등기부 확인</h4>
      <p>${esc(base().property.address)}</p>
      <div data-registry-provider>${providerOptions()}</div>
      ${s.results.length ? `<form data-intake-form="fetch" class="fh-form">
        <label class="fh-field"><span>열람할 부동산</span><select name="propertyId" required>
          <option value="">주소·동·호와 부동산 종류를 확인해 선택하세요</option>
          ${s.results.map(item => `<option value="${esc(item.id)}">${esc(item.address)} · ${esc(item.kind || "")} ${esc(item.propertyId || "")}</option>`).join("")}
        </select></label>
        <label class="fh-inline"><input type="checkbox" name="consent" required>선택한 주소·동·호를 확인했고 유료 열람에 동의합니다.</label>
        <button class="fh-btn primary" type="submit" ${busy}>선택한 등기부 유료 열람</button></form>` : ""}
      <form data-intake-form="upload" class="fh-form"><label class="fh-field"><span>보유한 등기부 PDF (최대 4MB)</span>
        <input type="file" name="pdf" accept="application/pdf,.pdf" required></label>
        <button class="fh-btn" type="submit" ${busy}>PDF에서 등기부 읽기</button></form>
      ${result ? `<article class="fh-item">
        <strong>${s.review ? "가져온 등기부 확인" : "반영한 등기부 근거"}</strong>
        <dl class="fh-numbers">
          <div><dt>대상 주소</dt><dd>${esc(result.selectedAddress || result.address || "미확인")}</dd></div>
          <div><dt>발급·열람일</dt><dd>${esc(result.issuedAt || "미확인")}</dd></div>
          <div><dt>근저당 채권최고액</dt><dd>${esc(amountLabel(result.mortgageMax10k))}</dd></div>
        </dl>
        ${result.reason ? `<p class="fh-sub">${esc(result.reason)}</p>` : ""}
        ${evidence(result.evidence)}
        ${s.review && canApply ? `<button type="button" class="fh-btn primary" data-intake="apply-registry" ${busy}>원문·주소 확인 후 근저당 반영</button>` : ""}
        ${!canApply ? `<p>원문과 대상 주소를 확인한 뒤 정보 입력에서 직접 기록할 수 있어요.</p>` : ""}
      </article>` : ""}
      <button type="button" class="fh-btn" data-action="tab" data-tab="registry">등기부 값 직접 입력</button>
    </section>`;
  }

  function documentLabel(doc) {
    if (doc?.documentType === "landlordStatement") return "임대인 작성 선순위 보증금 확인서";
    if (doc?.documentType === "fixedDateRecord") return "제출된 확정일자 자료";
    return "집주인이 제출한 자료";
  }

  function confirmedSource() {
    const doc = state().submitted?.documents?.find(row => row.kind === "fixedDate" && row.status === "confirmed");
    return doc ? documentLabel(doc) : "집주인이 제출한 자료";
  }

  function requestPanel() {
    const v = verdict();
    const multi = v.property.housingType === "multi";
    const s = state();
    const record = request();
    const busy = s.busy ? "disabled" : "";
    if (!record || s.expired) {
      const outstanding = kind => v.requests?.some(row => row.id === kind && row.status !== "received");
      // 체납 없음은 납세증명서 두 장을 원문 확인해야 '서류 확인'이 된다. 직접 입력만 있으면 함께 요청한다.
      const needTax = v.checks.some(c => c.id === "taxArrears" && c.result !== "danger" && c.evidence !== "document");
      return `<section class="fh-doc-intake" data-intake-panel="landlord">
        <h4 class="fh-group">집주인에게 남은 서류 한 번에 요청</h4>
        ${s.expired ? "<p>기존 요청의 유효기간이 지났어요. 필요한 서류를 다시 요청하세요.</p>" : ""}
        <form class="fh-form" data-intake-form="create">
          <fieldset><legend>집주인에게 받을 자료</legend>
            ${Object.entries(kinds).map(([kind, label]) => `<label class="fh-inline"><input type="checkbox" name="kind" value="${kind}" ${kind === "fixedDate" ? (multi ? "checked disabled" : "") : (kind === "moveIn" ? multi || outstanding("moveIn") : needTax || !multi) ? "checked" : ""}>${esc(label)}</label>`).join("")}
          </fieldset>
          <p class="fh-sub">국세·지방세는 집주인이 발급받은 PDF를 여기에 제출해요. 전입세대확인서는 방문 발급한 서류를 제출해야 해요. 이미지로만 스캔한 서류는 원문을 자동으로 읽을 수 없어요.</p>
          <button class="fh-btn primary" type="submit" ${busy}>서류 요청 링크 만들기</button>
        </form></section>`;
    }
    const results = s.submitted?.documents || [];
    const remaining = Object.entries(kinds).filter(([id]) => !record.requested.includes(id));
    const link = new URL("/landlord.html", location.origin);
    link.hash = record.recipientToken;
    const localOnly = ["localhost", "127.0.0.1", "[::1]"].includes(location.hostname);
    return `<section class="fh-doc-intake" data-intake-panel="landlord">
      <h4 class="fh-group">집주인 서류 요청·확인</h4>
      <p class="fh-sub">집주인에게 아래 제출 링크를 공유하세요. 만료 ${esc(new Date(record.expiresAt).toLocaleDateString("ko-KR"))}</p>
      ${localOnly ? '<p class="fh-status">현재 로컬 서버의 링크는 이 컴퓨터에서만 열립니다. 다른 기기에서 제출받으려면 외부에서 접속 가능한 핏홈 주소가 필요합니다.</p>' : ""}
      <label class="fh-field"><span>집주인 제출 링크</span><input readonly value="${esc(link.href)}" data-recipient-link></label>
      <div class="fh-actions"><button type="button" class="fh-btn" data-intake="copy-link">제출 링크 복사</button>
      <button type="button" class="fh-btn" data-intake="refresh" ${busy}>접수함 새로고침</button></div>
      ${remaining.length ? `<details><summary>같은 링크에 서류 추가</summary><form class="fh-form" data-intake-form="extend">
        <fieldset><legend>추가 요청할 서류</legend>${remaining.map(([id,label]) => `<label class="fh-inline"><input type="checkbox" name="kind" value="${id}">${esc(label)}</label>`).join("")}</fieldset>
        <button class="fh-btn" type="submit" ${busy}>요청 항목 추가</button></form></details>` : ""}
      <div class="fh-list">${(record.requested || []).map(kind => {
        const doc = results.find(row => row.kind === kind);
        const labels = { ready: "원문 대조 필요", confirmed: "확인 완료", needs_review: "보완 필요" };
        return `<article class="fh-item"><div class="fh-row"><strong>${esc(kinds[kind])}</strong>
          <span class="src-chip">${doc ? esc(labels[doc.status] || doc.status) : s.submitted ? "제출 대기" : "접수 상태 조회 필요"}</span></div>
          ${doc ? `<p>${doc.addressStatus === "taxpayer_address" ? "납세자 주소 · 매물 주소와 별도" : doc.addressStatus === "whole_building" ? "건물 전체 주소 일치" : doc.addressMatched ? "대상 주소 일치" : "대상 주소 미확인"} · 발급일 ${esc(doc.issuedAt || "미확인")}${doc.expiresOn ? " · 유효기간 " + esc(doc.expiresOn) : ""}</p>
            ${kind === "fixedDate" ? `<p>${esc(documentLabel(doc))} · 선순위 보증금 합계 <strong>${esc(amountLabel(doc.amount10k))}</strong></p>` : ""}
            ${(doc.issues || []).map(issue => `<p class="fh-sub">${esc(issue)}</p>`).join("")}
            ${(doc.notes || []).map(note => `<p class="fh-sub">${esc(note)}</p>`).join("")}
            ${doc.status === "needs_review" && kind === "fixedDate" ? "<p>집주인에게 같은 제출 링크로 보완을 요청하세요. 건물 전체 선순위 보증금 합계와 기준일이 명시된 자료가 필요해요. 확정일자 자료의 개별 계약 금액만으로는 현재 선순위 총액을 확인할 수 없어요.</p>" : ""}
            ${evidence(doc.evidence)}
            ${doc.status === "ready" ? `<button type="button" class="fh-btn primary" data-intake="confirm" data-kind="${esc(kind)}" data-fingerprint="${esc(doc.fingerprint)}" ${busy}>${kind === "fixedDate" ? "주소·원문·총액 확인 후 판정에 반영" : kind === "nationalTax" || kind === "localTax" ? "원문 확인 후 체납 판정에 반영" : "원문 확인 완료"}</button>` : ""}` : ""}
          </article>`;
      }).join("")}</div></section>`;
  }

  function requestStatus() {
    const record = request();
    const s = state();
    if (!record) return "요청 전";
    if (s.expired || Date.parse(record.expiresAt) <= Date.now()) return "요청 만료";
    if (!s.submitted) return "접수 상태 확인 필요";
    const confirmed = s.submitted.documents.filter(doc => doc.status === "confirmed").length;
    return `제출 ${s.submitted.documents.length}/${record.requested.length} · 원문 확인 ${confirmed}건`;
  }

  function select(target = "hub") {
    const panels = { fixedDate: "landlord", moveIn: "landlord", tax: "landlord" };
    const panel = panels[target] || target;
    state().activePanel = Object.hasOwn(serviceTitles, panel) || panel === "address" ? panel : "hub";
  }

  function openPanel(node, target) {
    select(target);
    render();
    const panel = node.querySelector("[data-intake-panel='" + state().activePanel + "']");
    if (panel) {
      panel.setAttribute("tabindex", "-1");
      panel.focus({ preventScroll: true });
      panel.scrollIntoView({ block: "start" });
    }
  }

  function reviewedCheck(kind) {
    const saved = store.get(report() + ".documentCheck." + kind, null);
    return saved?.address === base().property.address ? saved : null;
  }

  function violationRecords(key = report(), address = base().property.address) {
    const saved = store.get(key + ".buildingViolationEvidence", null);
    if (!saved || saved.address !== address) return [];
    return saved.records || [saved];
  }

  function confirmedBuildingViolation() {
    return violationRecords().some(row => !row.resolutionIssuedAt);
  }

  function sameRegister(row, doc) {
    return ["building", "unit"].includes(doc.scope) && row.scope === doc.scope && row.addressStatus === doc.addressStatus;
  }

  function savePositive(key, address, doc, reviewedAt) {
    const records = violationRecords(key, address);
    const index = records.findIndex(row => (row.scope === doc.scope && row.addressStatus === doc.addressStatus)
      || (!row.scope && row.issuedAt === doc.issuedAt));
    const existing = records[index];
    if (existing && (existing.issuedAt > doc.issuedAt || existing.resolutionIssuedAt >= doc.issuedAt)) return;
    const mark = {scope: doc.scope, addressStatus: doc.addressStatus, issuedAt: doc.issuedAt, reviewedAt};
    if (index < 0) records.push(mark);
    else records[index] = mark;
    store.set(key + ".buildingViolationEvidence", {address, records});
  }

  function resolutionIndex(records, doc) {
    if (doc?.status !== "reviewed" || !doc.addressMatched || !doc.findings?.some(f => f.field === "violation" && f.code === "no")) return -1;
    return records.findIndex(row => !row.resolutionIssuedAt && row.issuedAt < doc.issuedAt && sameRegister(row, doc));
  }

  function reviewStatus(kind) {
    const item = state().pdfChecks?.[kind] || reviewedCheck(kind);
    return { ready: "원문 대조 필요", needs_review: "보완 필요", reviewed: "PDF 대조 기록 있음" }[item?.status] || "PDF 미제출";
  }

  function registryStatus() {
    if (registryEvidence() && verdict().registryEvidence?.status === "applied") return verdict().ltv.mortgagePending ? "근저당 재확인 필요" : "원문 확인됨";
    if (registryEvidence()) return "등기 근거 다시 대조 필요";
    if (verdict().ltv.mortgage10k != null) return "금액 직접 입력";
    if (provider?.available) return "기관 조회 가능";
    return "PDF 대조 가능";
  }

  function checkIdentityBadge() {
    const current = state();
    if (!window.FitHomeIdentity?.statusFor || current.identityChecking || (current.identityReadAt || 0) > Date.now() - 20000) return;
    const scope = { reportKey: report(), address: base().property.address };
    current.identityChecking = true;
    window.FitHomeIdentity.statusFor(scope).then(info => {
      current.identityLabel = identityLabels[info.status] || "인증 상태 확인 필요";
      current.identityExpires = Date.parse(info.expiresAt);
    }).catch(() => { current.identityLabel = "연결 상태 확인 필요"; })
      .finally(() => {
        current.identityChecking = false; current.identityReadAt = Date.now();
        const badge = document.querySelector('[data-service-status="identity"]');
        if (badge && base()?.key === scope.reportKey) badge.textContent = current.identityLabel;
      });
  }

  function hubPanel() {
    const v = verdict();
    if (state().identityExpires <= Date.now()) {
      delete state().identityLabel; delete state().identityExpires; delete state().identityReadAt;
    }
    checkIdentityBadge();
    const statuses = {
      identity: state().identityLabel || "인증 상태 확인 중",
      registry: registryStatus(),
      landlord: requestStatus(), building: confirmedBuildingViolation() ? "위반 표기 확인" : state().buildingLookup?.records?.length && !reviewedCheck("building") && !state().pdfChecks?.building
        ? "건축물 정보 조회됨" : reviewStatus("building"), broker: reviewStatus("broker"),
      price: v.depositGuide.price10k ? v.ltv.priceSourceLabel || "매물 가격 확인" : "가격 자료 없음",
      ownerId: "계약 상대 본인·원본 확인 필요", guarantee: "기관 심사 필요",
    };
    const primary = v.property.housingType === "multi" ? "선순위 보증금 · 전입세대 · 국세·지방세" : "전입세대 · 국세·지방세 · 확정일자 자료";
    const services = [
      ["registry", "주소 조회 · PDF 대조"], ["landlord", primary], ["building", "건축물 정보 조회 · PDF 대조"],
      ["price", "이 매물의 가격 근거"], ["identity", "기관 본인인증"], ["ownerId", "임대인·대리인 확인 항목"],
      ["broker", "중개대상물 확인·설명서 PDF 대조"], ["guarantee", "가입 조건과 추가 확인 항목"],
    ];
    return `<section class="fh-doc-intake" data-intake-panel="hub">
      <div class="fh-row"><div><h4 class="fh-group">계약 전 서류 확인</h4><p>${esc(base().property.address)}</p></div>
        <button type="button" class="fh-btn" data-intake-select="address">주소·주택 유형 변경</button></div>
      <div class="fh-list fh-service-list">${services.map(([kind, method]) => `<button type="button" class="fh-item fh-service-row" data-intake-select="${kind}">
        <span class="fh-row"><strong>${serviceTitles[kind]}</strong><span class="src-chip" data-service-status="${kind}">${esc(statuses[kind])}</span></span><small>${esc(method)}</small></button>`).join("")}</div>
    </section>`;
  }

  function buildingLookupControls() {
    if (buildingProvider?.available) return `<button type="button" class="fh-btn" data-intake="lookup-building" ${state().busy ? "disabled" : ""}>이 주소의 건축물 정보 조회</button>`;
    return `<p class="fh-sub">${esc(buildingProvider?.reason || "건축물 정보 연결 상태를 확인하고 있어요.")}</p>`;
  }

  function buildingLookup() {
    if (!buildingCheck) {
      buildingCheck = post("building-register/status", {}).then(result => { buildingProvider = result; })
        .catch(() => { buildingProvider = { available: false, reason: "건축물 정보에 연결할 수 없어요. 보유한 대장 PDF를 대조할 수 있어요." }; })
        .finally(() => {
          const area = document.querySelector("[data-building-provider]");
          if (area) area.innerHTML = buildingLookupControls();
        });
    }
    const result = state().buildingLookup;
    return `<div data-building-provider>${buildingLookupControls()}</div>
      ${result ? `<div class="fh-list"><p>${esc(result.source)} · 조회 ${esc(new Date(result.checkedAt).toLocaleString("ko-KR"))}</p>
        ${(result.records || []).map(rec => `<article class="fh-item"><strong>${esc([rec.buildingName, rec.dongName].filter(Boolean).join(" ") || "건축물 표제부")}</strong>
          <p>${esc(rec.address)}</p><p>주용도 ${esc(rec.mainUse || "미확인")} · 사용승인일 ${esc(rec.approvedAt || "미확인")}</p></article>`).join("") || "<p>일치하는 건축물 정보를 찾지 못했어요.</p>"}
        <p class="fh-sub">위반건축물 표기는 건축물대장 원문에서 확인하세요.</p></div>` : ""}`;
  }

  function pdfPanel(kind) {
    const s = state();
    const data = s.pdfChecks?.[kind] || reviewedCheck(kind);
    const records = kind === "building" ? violationRecords() : [];
    const eligibleIndex = resolutionIndex(records, s.pdfChecks?.building);
    const violationHistory = records.map(row => {
      const scope = ({building: "건물 대장", unit: "전유부"})[row.scope] || "대장";
      return row.resolutionIssuedAt
        ? `<p class="fh-sub">위반 표기 재확인 완료 · ${esc(scope)} ${esc(row.issuedAt)} 위반 표기, ${esc(row.resolutionIssuedAt)} 해당 없음 표기를 직접 대조했어요.</p>`
        : `<p class="fh-status">위반건축물 표기 확인 · ${esc(row.issuedAt)} 발급 ${esc(scope)} 기준. 현재 해소 여부는 확인이 필요해요.</p>`;
    }).join("");
    const label = kind === "building" ? serviceTitles[kind] : "중개대상물 확인·설명서";
    const display = data ? `<article class="fh-item">
      <strong>${esc(reviewStatus(kind))}</strong>
      <p>주소 ${esc(({ exact: "일치", matched: "일치", whole_building: "건물 전체 일치", different: "불일치", missing: "미확인" })[data.addressStatus] || "미확인")}
        · 발급·작성일 ${esc(data.issuedAt || "미확인")}</p>
      ${(data.findings || []).map(f => `<p>${esc(f.label)} · ${esc(f.value)}</p>`).join("")}
      ${[...(data.issues || []), ...(data.notes || [])].map(note => `<p class="fh-sub">${esc(note)}</p>`).join("")}
      ${evidence(data.evidence)}
      ${data.status === "ready" ? `<button type="button" class="fh-btn primary" data-intake="confirm-check" data-kind="${kind}">원문 대조 기록 저장</button>` : ""}
      ${data.status === "reviewed" ? `<small>사용자 대조일 ${esc(data.reviewedAt)}${data.evidence ? "" : " · 원문 줄을 다시 보려면 PDF를 올려 주세요."}</small>` : ""}
    </article>` : "";
    return `<section class="fh-doc-intake" data-intake-panel="${kind}"><h4 class="fh-group">${serviceTitles[kind]}</h4>
      ${violationHistory}
      ${kind === "building" ? buildingLookup() : "<p>확인·설명서에서 매물 주소와 작성일을 대조해요. 중개업 등록 상태와 공제 유효기간은 따로 확인해야 해요.</p>"}
      <form class="fh-form" data-intake-form="check-pdf" data-kind="${kind}"><label class="fh-field">
        <span>${label} PDF (최대 4MB)</span><input type="file" name="pdf" required accept=".pdf,application/pdf"></label>
        <p class="fh-sub">텍스트가 포함된 PDF에서 원문 근거를 찾아요.</p>
        <button type="submit" class="fh-btn" ${s.busy ? "disabled" : ""}>PDF 원문 대조</button></form>${display}
      ${eligibleIndex >= 0 ? `<form class="fh-form" data-intake-form="resolve-violation">
        <label class="fh-inline"><input type="checkbox" name="consent" required>같은 범위의 대장에서 기존 위반 표기와 최신 ‘해당 없음’ 표기를 직접 대조했습니다.</label>
        <button class="fh-btn" type="submit">재확인한 위반 표기 해소 기록</button></form>` : ""}</section>`;
  }

  function infoPanel(kind) {
    const v = verdict();
    let contents;
    if (kind === "identity") contents = `<div data-identity-host data-address="${esc(base().property.address)}" data-report-key="${esc(report())}"></div>`;
    if (kind === "ownerId") contents = `<p>계약 상대의 신분증 원본과 등기부 소유자 이름을 대조하세요. 대리인 계약은 위임장과 인감증명서도 확인하세요.</p>
      <p class="fh-sub">신청자 본인인증으로 임대인의 소유권이나 대리권을 확인할 수 없어요.</p>`;
    if (kind === "price") contents = `<dl class="fh-numbers">
      <div><dt>집값 기준</dt><dd>${esc(v.ltv.priceLabel || "미확인")}</dd></div>
      <div><dt>집값 · ${esc(v.ltv.priceSourceLabel || "근거 미확인")}</dt><dd>${esc(money(v.ltv.price10k))}</dd></div>
      <div><dt>주변 전세 시세</dt><dd>${esc(money(v.depositGuide.nearbyJeonse10k))}</dd></div></dl>
      ${v.depositGuide.marketSourceLabel ? `<p class="fh-sub">${esc(v.depositGuide.marketSourceLabel)}</p>` : ""}
      <button class="fh-btn" type="button" data-action="tab" data-tab="registry">가격 근거 직접 입력</button>`;
    if (kind === "guarantee") contents = `<p><strong>핏홈 예상 · ${esc(v.guarantees.statusLabel)}</strong></p>
      <p>${esc([...v.guarantees.blockers, ...v.guarantees.unknowns].join(" · ") || "보증기관의 심사 결과를 별도로 확인해야 해요.")}</p>
      <button class="fh-btn" type="button" data-action="tab" data-tab="support">보증 상품별 조건 확인</button>`;
    return `<section class="fh-doc-intake" data-intake-panel="${kind}">${kind === "identity" ? "" : `<h4 class="fh-group">${serviceTitles[kind]}</h4>`}${contents}</section>`;
  }

  function renderPanel() {
    loadProvider();
    const s = state();
    const v = verdict();
    const housing = [["apartment","아파트"],["multi","다가구"],["villa","빌라·다세대"],["officetel","오피스텔"]];
    const panel = s.activePanel || "hub";
    if (panel === "hub") return `<div class="fh-document-intake">${hubPanel()}</div>`;
    const addressPanel = `<form class="fh-form" data-intake-panel="address" data-intake-form="address">
        <h4 class="fh-group">점검할 주택</h4>
        <label class="fh-field"><span>주소와 동·호</span><input name="address" value="${esc(s.draft?.address ?? base().property.address)}" maxlength="220" required></label>
        <label class="fh-field"><span>주택 유형</span><select name="housingType">${housing.map(([id,label]) => `<option value="${id}" ${(s.draft?.housingType || v.property.housingType) === id ? "selected" : ""}>${label}</option>`).join("")}</select></label>
        <button class="fh-btn" type="submit" ${s.busy ? "disabled" : ""}>점검 주소·주택 유형 적용</button>
      </form>`;
    const ids = panel === "landlord" ? ["fixedDate", "moveIn", "tax"] : [panel];
    const checklist = renderChecklist && !["address", "identity"].includes(panel) ? renderChecklist(ids) : "";
    let body;
    if (panel === "registry") body = registryPanel();
    else if (panel === "landlord") body = requestPanel();
    else if (panel === "address") body = addressPanel;
    else if (["building", "broker"].includes(panel)) body = pdfPanel(panel);
    else body = infoPanel(panel);
    return `<div class="fh-document-intake"><div class="fh-row">
      <button class="fh-btn" type="button" data-intake-select="hub">전체 서류·인증</button>
      ${panel !== "address" ? '<button class="fh-btn" type="button" data-intake-select="address">주소·주택 유형 변경</button>' : ""}</div>
      <p class="fh-status" data-intake-status role="status" aria-live="polite" ${!s.busy && !s.error && !s.message ? "hidden" : ""}>${esc(s.busy || s.error || s.message || "")}</p>
      ${body}${checklist ? `<details class="fh-evidence-lines"><summary>서류별 확인 항목</summary>${checklist}</details>` : ""}
    </div>`;
  }

  async function refresh(token, local) {
    const old = JSON.stringify(local.submitted);
    try {
      const result = await post("document-requests/status", { ownerToken: token });
      local.submitted = result;
      return old !== JSON.stringify(result);
    } catch (error) {
      if (error.status === 404) { local.expired = true; local.submitted = null; return true; }
      throw error;
    }
  }

  async function poll() {
    if (!base()) return false;
    const current = state();
    const record = request();
    if (!record || current.expired || current.busy) return false;
    // 서류를 고르거나 정보를 입력 중일 때 갱신해서 파일 선택을 잃지 않도록 한다.
    const activeForm = document.activeElement?.closest("#reportOverlay form");
    if (activeForm || document.querySelector("#reportOverlay input[type=file]")?.files?.length) return false;
    try { return await refresh(record.ownerToken, current); }
    catch { return Boolean(current.expired); }
  }

  async function run(button, busy, task) {
    const key = report();
    const local = state();
    if (local.busy) return;
    local.busy = busy; local.error = ""; local.message = "";
    const formArea = button?.closest(".fh-document-intake");
    formArea?.querySelectorAll("button[type=submit], [data-intake], [data-intake-select]").forEach(control => { control.disabled = true; });
    const status = document.querySelector("[data-intake-status]");
    if (status) { status.hidden = false; status.textContent = busy; }
    try { await task(key, local); }
    catch (error) { local.error = error.message; }
    finally {
      local.busy = "";
      if (key === report() && !document.getElementById("reportOverlay").hidden) render();
    }
  }

  const maxPdfSize = 4 * 1024 * 1024;
  async function encodePdf(file) {
    if (!file || !file.size || file.size > maxPdfSize || await file.slice(0, 5).text() !== "%PDF-") throw new Error("텍스트가 포함된 4MB 이하 PDF를 선택하세요.");
    return new Promise((resolve,reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result.split(",")[1]);
      reader.onerror = () => reject(new Error("PDF를 읽지 못했어요. 다시 선택하세요."));
      reader.readAsDataURL(file);
    });
  }

  function bind(node) {
    function saveDraft(event) {
      const form = event.target.closest("[data-intake-form=address]");
      if (form) state().draft = { address: form.elements.address.value, housingType: form.elements.housingType.value };
    }
    node.addEventListener("fithome-identity-state", event => {
      const {status, reportKey} = event.detail || {};
      if (states.has(reportKey) && identityLabels[status]) {
        states.get(reportKey).identityLabel = identityLabels[status];
        delete states.get(reportKey).identityReadAt;
      }
    });
    node.addEventListener("input", saveDraft);
    node.addEventListener("change", saveDraft);
    node.addEventListener("submit", async (event) => {
      const form = event.target;
      const action = form.dataset.intakeForm;
      if (!action) return;
      event.preventDefault();
      const data = new FormData(form);
      if (action !== "address" && addressNeedsSaving()) {
        toast("먼저 점검 주소·주택 유형을 적용하세요.");
        return;
      }
      const currentAddress = base().property.address;
      const button = event.submitter || form.querySelector("[type=submit]");
      if (action === "resolve-violation") {
        if (data.get("consent") !== "on") return;
        await run(button, "대조 결과를 저장하고 있어요.", async (key, local) => {
          const doc = local.pdfChecks?.building;
          const records = violationRecords(key, currentAddress);
          const index = resolutionIndex(records, doc);
          if (index < 0) return;
          records[index] = { ...records[index], resolutionIssuedAt: doc.issuedAt, resolvedAt: new Date().toISOString() };
          store.set(key + ".buildingViolationEvidence", {address: currentAddress, records});
          if (key === report()) await recalculate();
        });
      } else if (action === "extend") {
        const record = request();
        const requested = data.getAll("kind");
        if (!record || !requested.length) { toast("추가할 서류를 선택하세요."); return; }
        await run(button, "같은 링크에 서류를 추가하고 있어요.", async (key, local) => {
          const result = await post("document-requests/extend", {ownerToken: record.ownerToken, requested});
          local.submitted = result;
          store.set(key + ".documentRequest", {...record, requested: result.requested});
          local.message = "기존 제출 링크에서 추가한 서류를 받을 수 있어요.";
        });
      } else if (action === "check-pdf") {
        const kind = form.dataset.kind;
        if (!["building", "broker"].includes(kind)) return;
        await run(button, "주소와 PDF 원문을 대조하고 있어요.", async (key, local) => {
          const result = await post("document-checks/read", {
            address: currentAddress, kind, fileBase64: await encodePdf(data.get("pdf")),
          });
          local.pdfChecks ||= {};
          local.pdfChecks[kind] = result;
          store.set(key + ".documentCheck." + kind, null);
        });
      } else if (action === "address") {
        const address = String(data.get("address") || "").trim();
        if (!address) return;
        await run(button, "점검 주소를 적용하고 있어요.", async (key, local) => {
          await saveAddress(address, data.get("housingType"));
          delete local.draft;
        });
      } else if (action === "create") {
        const requested = [...new Set([...(verdict().property.housingType === "multi" ? ["fixedDate"] : []), ...data.getAll("kind")])];
        if (!requested.length) { toast("요청할 서류를 한 가지 이상 선택하세요."); return; }
        await run(button, "요청 링크를 만들고 있어요.", async (key, local) => {
          const result = await post("document-requests/create", { address: currentAddress, requested });
          store.set(key + ".documentRequest", { ownerToken: result.ownerToken, recipientToken: result.recipientToken, requested: result.requested, expiresAt: result.expiresAt, address: result.address });
          local.expired = false; local.submitted = null;
          await refresh(result.ownerToken, local);
          if (key === report()) await recalculate();
        });
      } else if (action === "upload" || action === "fetch") {
        await run(button, "등기부를 확인하고 있어요.", async (key, local) => {
          local.review = null;
          if (action === "upload") {
            local.review = await post("registry/upload", {address: currentAddress, fileBase64: await encodePdf(data.get("pdf"))});
          } else {
            if (data.get("consent") !== "on") throw new Error("유료 열람 동의가 필요해요.");
            const propertyId = data.get("propertyId");
            local.results = []; // 유료 열람 재전송 방지. 다시 검색하면 새 선택을 받을 수 있다.
            local.review = await post("registry/fetch", {address: currentAddress, propertyId, confirmCharge: true});
          }
        });
      }
    });
    node.addEventListener("click", async event => {
      const opener = event.target.closest("[data-intake-select]");
      if (opener) { openPanel(node, opener.dataset.intakeSelect); return; }
      const t = event.target.closest("[data-intake]");
      if (!t) return;
      const action = t.dataset.intake;
      if (addressNeedsSaving() && ["search", "apply-registry", "confirm", "confirm-check", "lookup-building"].includes(action)) {
        toast("먼저 점검 주소·주택 유형을 적용하세요.");
        return;
      }
      const address = base().property.address;
      const record = request();
      if (action === "copy-link") { await copyText(node.querySelector("[data-recipient-link]").value); return; }
      await run(t, "서류 요청을 처리하고 있어요.", async (key, local) => {
        if (action === "lookup-building") {
          local.buildingLookup = null;
          local.buildingLookup = await post("building-register/lookup", { address });
        } else if (action === "confirm-check") {
          const kind = t.dataset.kind;
          const doc = local.pdfChecks?.[kind];
          if (!doc || doc.status !== "ready") return;
          const reviewedAt = new Date().toLocaleDateString("ko-KR");
          store.set(key + ".documentCheck." + kind, {
            kind, address, addressStatus: doc.addressStatus, issuedAt: doc.issuedAt,
            findings: doc.findings, status: "reviewed", reviewedAt,
          });
          local.pdfChecks[kind] = {...doc, status: "reviewed", reviewedAt};
          if (kind === "building" && doc.findings?.some(f => f.field === "violation" && f.code === "yes")) {
            savePositive(key, address, doc, reviewedAt);
            if (key === report()) await recalculate();
          }
          local.message = "이 매물에 PDF 원문 대조 기록을 저장했어요.";
        } else if (action === "search") {
          const result = await post("registry/search", { address });
          local.results = result.items || [];
          local.review = null;
          if (!local.results.length) local.message = "이 주소의 검색 결과가 없어요. 도로명·건물번호와 동·호를 확인하세요.";
        } else if (action === "apply-registry") {
          const item = local.review;
          if (!item || item.reviewRequired || !Number.isFinite(item.mortgageMax10k)) return;
          const e = store.get(key + ".edits", {});
          const overrides = store.get(key + ".overrides", {});
          delete overrides.registryIssuedAt;
          store.set(key + ".overrides", overrides);
          store.set(key + ".edits", { ...e, mortgageUnknown: false, mortgageMax10k: item.mortgageMax10k, issuedAt: item.issuedAt || "" });
          store.set(key + ".registryEvidence", { address: item.address, selectedAddress: item.selectedAddress, source: item.source, mortgageMax10k: item.mortgageMax10k, evidence: item.evidence, issuedAt: item.issuedAt, evidenceId: item.evidenceId || null });
          local.review = null;
          if (key === report()) { await recalculate(); toast("등기부 금액을 판정에 반영했어요."); }
        } else if (action === "refresh") {
          if (!record) return;
          await refresh(record.ownerToken, local);
          if (key === report()) await recalculate();
        } else if (action === "confirm") {
          if (!record) return;
          try {
            local.submitted = await post("document-requests/review", { ownerToken: record.ownerToken, kind: t.dataset.kind, fingerprint: t.dataset.fingerprint });
          } catch (error) {
            if (error.status === 404 || error.status === 409) {
              await refresh(record.ownerToken, local);
              if (key === report()) await recalculate();
            }
            throw error;
          }
          if (key === report()) { await recalculate(); toast("서류 확인 결과를 판정에 반영했어요."); }
        }
      });
    });
  }

  return { render: renderPanel, poll, bind, select, confirmedSource, amountLabel, requestStatus, registryEvidence, confirmedBuildingViolation };
};
