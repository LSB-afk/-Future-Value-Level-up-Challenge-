(() => {
  "use strict";

  const documents = {
    fixedDate: ["확정일자 부여현황", "확정일자 자료 또는 건물 전체 선순위 보증금 총액과 기준일이 적힌 임대인 확인서를 선택해 주세요."],
    moveIn: ["전입세대확인서", "방문 발급한 전입세대확인서를 제출해 주세요. 스캔한 이미지만 있으면 자동 판독이 어려울 수 있습니다."],
    nationalTax: ["국세 납세증명서", "임대인의 국세 납세증명서를 선택해 주세요."],
    localTax: ["지방세 납세증명서", "임대인의 지방세 납세증명서를 선택해 주세요."],
  };
  const limit = 4 * 1024 * 1024;
  const form = document.getElementById("request");
  const notice = document.getElementById("notice");
  const retry = document.getElementById("retry");
  const submit = document.getElementById("send");
  const consent = document.getElementById("consent");
  const message = document.getElementById("upload-status");
  const rows = new Map();
  let busy = false;
  let consentVersion = null;

  function getToken() {
    // Only this history entry can resume the same link after a reload.
    const fragment = location.hash.slice(1);
    if (fragment) {
      const key = "fithome.recipient." + [...crypto.getRandomValues(new Uint8Array(16))]
        .map(n => n.toString(16).padStart(2, "0")).join("");
      try { sessionStorage.setItem(key, fragment); } catch { /* in-memory submission still works */ }
      history.replaceState({ recipientKey: key }, "", location.pathname);
      return fragment;
    }
    const key = history.state?.recipientKey;
    try { return key ? sessionStorage.getItem(key) : null; } catch { return null; }
  }

  const recipientToken = getToken();
  window.addEventListener("hashchange", () => { if (location.hash) location.reload(); });

  async function post(action, payload) {
    const response = await fetch("/api/document-requests/" + action, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "omit",
      referrerPolicy: "no-referrer",
      cache: "no-store",
      body: JSON.stringify({ recipientToken, ...payload }),
    });
    let result;
    try { result = await response.json(); } catch { /* preserve a useful server error below */ }
    if (!response.ok || !result?.ok) {
      throw new Error(result?.error || "요청 내용을 확인할 수 없습니다. 잠시 후 다시 시도해 주세요.");
    }
    return result;
  }

  function updateControls() {
    let sent = 0;
    let selected = 0;
    for (const row of rows.values()) {
      if (row.sent) sent++;
      if (row.input.files.length) selected++;
      row.input.disabled = busy;
    }
    consent.disabled = busy;
    submit.disabled = busy || !selected;
    submit.textContent = busy ? "제출 중…" : selected ? "선택한 서류 " + selected + "개 제출" : "선택한 서류 제출";
    document.getElementById("count").textContent = sent + " / " + rows.size + " 제출";
  }

  function addDocument(kind, sent) {
    const node = document.getElementById("document-template").content.firstElementChild.cloneNode(true);
    const input = node.querySelector("input");
    const label = node.querySelector("label");
    const hint = node.querySelector(".hint");
    const badge = node.querySelector(".badge");
    const error = node.querySelector(".error");
    const [title, detail] = documents[kind];
    const row = { input, badge, error, sent, sentLabel: "제출됨" };
    input.id = "file-" + kind;
    label.htmlFor = input.id;
    label.textContent = title;
    hint.id = "hint-" + kind;
    error.id = "error-" + kind;
    input.setAttribute("aria-describedby", hint.id + " " + error.id);
    hint.textContent = detail;
    badge.textContent = sent ? "제출됨" : "제출 전";
    badge.dataset.sent = String(sent);
    input.addEventListener("change", () => {
      const file = input.files[0];
      error.textContent = "";
      input.removeAttribute("aria-invalid");
      if (file && (!file.size || file.size > limit)) {
        input.value = "";
        error.textContent = "비어 있지 않은 4MB 이하 PDF를 선택해 주세요.";
        input.setAttribute("aria-invalid", "true");
      }
      badge.textContent = input.files.length ? (row.sent ? "교체할 파일 선택됨" : "파일 선택됨") : row.sent ? row.sentLabel : "제출 전";
      message.textContent = "";
      updateControls();
    });
    rows.set(kind, row);
    document.getElementById("documents").append(node);
  }

  async function load() {
    retry.hidden = true;
    if (!recipientToken) {
      notice.textContent = "제출 링크가 없습니다. 임차인에게 받은 링크 전체를 열어 주세요.";
      return;
    }
    notice.textContent = "요청 내용을 불러오는 중입니다.";
    try {
      const request = await post("recipient", {});
      const kinds = request.requested.filter(kind => Object.hasOwn(documents, kind));
      if (!kinds.length) throw new Error("이 링크에는 제출할 서류가 없습니다.");
      const terms = request.consent?.terms;
      if (!request.consent?.version || !Array.isArray(terms) || !terms.length) {
        throw new Error("제출 동의 내용을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.");
      }
      // 서버가 내려준 문안만 표시하고, 제출할 때 같은 버전으로 동의했음을 보낸다.
      consentVersion = request.consent.version;
      const list = document.getElementById("consent-terms");
      list.replaceChildren(...terms.map(term => {
        const item = document.createElement("li");
        const title = document.createElement("strong");
        title.textContent = term.title;
        item.append(title, " " + term.text);
        return item;
      }));
      document.getElementById("consent-version").textContent = "동의 문안 버전 " + consentVersion;
      document.getElementById("address").textContent = request.address;
      const expires = new Date(request.expiresAt);
      if (Number.isFinite(expires.getTime())) {
        document.getElementById("expires").textContent = "요청 만료일 " +
          new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "long", day: "numeric", timeZone: "Asia/Seoul" }).format(expires);
      }
      for (const kind of kinds) addDocument(kind, request.submitted.includes(kind));
      updateControls();
      notice.hidden = true;
      form.hidden = false;
    } catch (err) {
      notice.textContent = err.message;
      retry.hidden = false;
    }
  }

  async function readFile(file) {
    if (file.size > limit || await file.slice(0, 5).text() !== "%PDF-") {
      throw new Error("PDF 형식인지 확인한 후 4MB 이하 파일을 다시 선택해 주세요.");
    }
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onerror = () => reject(new Error("파일을 읽을 수 없습니다. 다시 선택해 주세요."));
      reader.onload = () => resolve(reader.result.split(",")[1]);
      reader.readAsDataURL(file);
    });
  }

  form.addEventListener("submit", async event => {
    event.preventDefault();
    if (busy || !consent.checked) return;
    const selected = [...rows].filter(([, row]) => row.input.files.length);
    if (!selected.length) return;
    busy = true;
    updateControls();
    message.classList.remove("error");
    let completed = 0;
    for (const [kind, row] of selected) {
      const title = documents[kind][0];
      const file = row.input.files[0];
      message.textContent = title + " 제출 중…";
      row.error.textContent = "";
      try {
        const fileBase64 = await readFile(file);
        const result = await post("submit", { kind, fileBase64, consent: { version: consentVersion, agreed: true } });
        row.input.value = "";
        row.input.removeAttribute("aria-invalid");
        row.sent = true;
        row.sentLabel = result.status === "needs_review" ? "제출됨 · 추가 확인 필요" : "제출됨";
        row.badge.textContent = row.sentLabel;
        row.badge.dataset.sent = "true";
        completed++;
      } catch (err) {
        row.input.setAttribute("aria-invalid", "true");
        row.error.textContent = err.message;
        row.badge.textContent = row.sent ? "교체 실패 · 기존 서류 제출됨" : "제출 실패";
      }
    }
    busy = false;
    updateControls();
    const failures = selected.length - completed;
    if (failures) {
      message.classList.add("error");
      message.textContent = completed + "개 제출, " + failures + "개 실패. 각 서류의 오류를 확인한 뒤 다시 제출해 주세요.";
    } else {
      consent.checked = false;
      message.textContent = completed + "개 서류를 제출했습니다. 요청자가 리포트에서 확인할 수 있습니다.";
    }
  });

  retry.addEventListener("click", load);
  load();
})();
