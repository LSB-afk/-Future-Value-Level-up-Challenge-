// Optional PortOne identity verification for the person using this report.
(() => {
  const selector = "[data-identity-host][data-address][data-report-key]";
  const returnKey = "fithome.identity.return";
  const stateByReport = new Map();
  const mounted = new WeakSet();
  let sdkPromise;

  function sessionGet(key) {
    try { return JSON.parse(sessionStorage.getItem(key)); } catch { return null; }
  }

  function receiptKey(scope) {
    return "fithome.identity.receipt." + scope.reportKey;
  }

  function stateFor(scope) {
    const key = JSON.stringify([scope.reportKey, scope.address]);
    if (!stateByReport.has(key)) stateByReport.set(key, {
      scope, info: null, receipt: sessionGet(receiptKey(scope)), error: "", busy: false,
    });
    return stateByReport.get(key);
  }

  async function api(action, state, extra = {}) {
    const response = await fetch("/api/identity/" + action, {
      method: "POST", headers: { "Content-Type": "application/json" }, cache: "no-store",
      body: JSON.stringify({ ...state.scope, challengeToken: state.receipt?.challengeToken, ...extra }),
    });
    const data = await response.json();
    if (!response.ok || data.ok === false) {
      const error = new Error(data.error || "본인인증 상태를 확인하지 못했어요.");
      error.status = response.status;
      throw error;
    }
    return data;
  }

  function loadSdk() {
    if (window.PortOne?.requestIdentityVerification) return Promise.resolve(window.PortOne);
    if (sdkPromise) return sdkPromise;
    sdkPromise = new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://cdn.portone.io/v2/browser-sdk.js";
      script.referrerPolicy = "no-referrer";
      script.onload = () => window.PortOne?.requestIdentityVerification ? resolve(window.PortOne) : script.onerror();
      script.onerror = () => {
        script.remove(); sdkPromise = null;
        reject(new Error("인증창을 불러오지 못했어요. 인터넷 연결을 확인해 주세요."));
      };
      document.head.append(script);
    });
    return sdkPromise;
  }

  function forget(state) {
    sessionStorage.removeItem(receiptKey(state.scope));
    state.receipt = null;
    state.info = { available: true, status: "unverified" };
  }

  function paint(state) {
    const host = state.host;
    if (!host?.isConnected) return;
    const info = state.info;
    const status = info?.status;
    const statusLabel = {
      unavailable: "본인인증 기관 미연결", unverified: "본인인증 전", pending: "인증 진행 중", verified: "신청자 본인인증 완료",
    };
    const title = document.createElement("h4");
    title.className = "fh-group";
    title.textContent = "신청자 본인확인";
    const message = document.createElement("p");
    message.className = "fh-sub";
    message.setAttribute("role", "status");
    message.textContent = state.error || info?.reason || statusLabel[status] || "인증 연결 상태를 확인하고 있어요.";
    if (status === "verified" && info.verifiedAt) message.textContent += " · " + new Date(info.verifiedAt).toLocaleString("ko-KR");
    host.replaceChildren(title, message);
    const addButton = (label, action) => {
      const button = document.createElement("button");
      button.type = "button"; button.className = "fh-btn"; button.textContent = label;
      button.disabled = state.busy;
      button.onclick = () => run(state, action);
      host.append(button);
    };
    if (info?.available && status !== "verified") {
      const note = document.createElement("p");
      note.className = "fh-sub";
      note.textContent = "포트원 인증창에서 본인이 직접 인증합니다. 이 매물에는 인증 완료 여부와 시각만 표시해요.";
      host.append(note);
      if (!state.receipt || !window.PortOne) addButton("동의하고 인증 준비", prepare);
      if (state.receipt && window.PortOne) addButton("본인인증 창 열기", launch);
      if (state.receipt) addButton("인증 결과 확인", confirm);
    } else if (!info && state.error) {
      addButton("연결 상태 다시 확인", check);
    }
    host.dataset.identityStatus = status || "loading";
    host.dispatchEvent(new CustomEvent("fithome-identity-state", { bubbles: true, detail: {
      status: status || "loading", reportKey: state.scope.reportKey,
    } }));
  }

  async function run(state, action) {
    if (state.busy) return;
    state.busy = true; state.error = "";
    paint(state);
    try { await action(state); }
    catch (error) {
      if (error.status === 404 || error.status === 409) forget(state);
      state.error = error.message || "인증을 다시 확인해 주세요.";
    } finally { state.busy = false; paint(state); }
  }

  async function check(state) {
    state.info = await api("status", state);
    if (state.info.status === "verified") setExpiry(state);
  }

  function setExpiry(state) {
    clearTimeout(state.expiryTimer);
    const remaining = Date.parse(state.info.expiresAt) - Date.now();
    if (Number.isFinite(remaining)) state.expiryTimer = setTimeout(() => {
      forget(state);
      paint(state);
    }, Math.max(0, remaining));
  }

  async function prepare(state) {
    // Wait for preparation first so opening a popup keeps the next user click's activation.
    await loadSdk();
    if (state.receipt) return;
    const result = await api("start", state, { consent: true });
    state.receipt = { challengeToken: result.challengeToken, sdk: result.sdk };
    sessionStorage.setItem(receiptKey(state.scope), JSON.stringify(state.receipt));
    state.info = { available: true, status: "pending", expiresAt: result.expiresAt };
    setExpiry(state);
  }

  async function confirm(state) {
    state.info = await api("confirm", state);
    if (state.info.status === "verified") {
      // A verified receipt can be queried but cannot launch another identity transaction.
      state.receipt = { challengeToken: state.receipt.challengeToken };
      sessionStorage.setItem(receiptKey(state.scope), JSON.stringify(state.receipt));
      setExpiry(state);
    } else {
      state.error = "인증 기관에서 완료 결과를 아직 받지 못했어요. 인증 후 결과를 다시 확인하세요.";
    }
  }

  async function launch(state) {
    const sdk = state.receipt?.sdk;
    if (!sdk) { await check(state); return; }
    const context = window.FitHomeReport?.identityReturnContext?.();
    if (!context) throw new Error("매물 리포트를 다시 열어 인증을 시작해 주세요.");
    sessionStorage.setItem(returnKey, JSON.stringify({ context, scope: state.scope,
      id: sdk.identityVerificationId, expiresAt: state.info.expiresAt }));
    const url = new URL(location.pathname, location.origin);
    url.searchParams.set("fhIdentityReturn", "1");
    const response = await window.PortOne.requestIdentityVerification({ ...sdk, redirectUrl: url.href });
    if (!response) return;  // Mobile redirect completes on a new load.
    sessionStorage.removeItem(returnKey);
    if (response.code !== undefined || response.identityVerificationId !== sdk.identityVerificationId) {
      throw new Error("인증창에서 본인인증이 완료되지 않았어요.");
    }
    await confirm(state);
  }

  function mount(host, scope) {
    if (!host || mounted.has(host) || !scope?.reportKey || !scope.address) return;
    mounted.add(host);
    const state = stateFor(scope);
    state.host = host;
    paint(state);
    run(state, check);
  }

  function discover(node) {
    if (node.nodeType !== 1) return;
    const hosts = node.matches(selector) ? [node] : node.querySelectorAll(selector);
    for (const host of hosts) mount(host, { address: host.dataset.address, reportKey: host.dataset.reportKey });
  }

  async function resume() {
    const url = new URL(location.href);
    if (url.searchParams.get("fhIdentityReturn") !== "1") return;
    const callbackId = url.searchParams.get("identityVerificationId");
    const cancelled = url.searchParams.has("code");
    const saved = sessionGet(returnKey);
    sessionStorage.removeItem(returnKey);
    history.replaceState(history.state, "", location.pathname + "#recommend");
    if (!saved?.scope || !(Date.parse(saved.expiresAt) > Date.now())) return;
    const state = stateFor(saved.scope);
    if (state.receipt && saved.id === callbackId && !cancelled) {
      await run(state, confirm);
    } else {
      state.error = "인증창에서 본인인증이 완료되지 않았어요.";
    }
    const message = state.error;
    await window.FitHomeReport?.resumeIdentity?.(saved.context);
    if (message) { state.error = message; paint(state); }
  }

  async function initialize() {
    try { await resume(); }
    catch { /* Reopen the report to retry a pending verification. */ }
    const root = document.getElementById("reportOverlay");
    if (root) {
      new MutationObserver(records => {
        for (const record of records) for (const node of record.addedNodes) discover(node);
      }).observe(root, { childList: true, subtree: true });
      discover(root);
    }
  }
  async function statusFor(scope) {
    const state = stateFor(scope);
    try { return await api("status", state); }
    catch (error) {
      if (error.status !== 404) throw error;
      forget(state);
      return state.info;
    }
  }

  window.FitHomeIdentity = { mount, statusFor };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", initialize);
  else initialize();
})();
