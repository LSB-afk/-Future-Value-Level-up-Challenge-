// GitHub Pages static build shim: serves /api/* fetches from the Python backend
// running in Pyodide. Only the static build loads this file (scripts/build_pages.py
// injects the script tag); the local dev server never uses it.
(() => {
  const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.26.4/full/pyodide.js";
  const PY_FILES = [
    "env_loader.py",
    "route_adapters.py",
    "real_estate_price_adapters.py",
    "property_model.py",
    "apartment_adapters.py",
    "property_adapters.py",
    "movevalue_api.py",
    "static_dispatcher.py"
  ];
  const DATA_FILES = ["areas.actual.json", "apartments.seoul.snapshot.json"];
  const nativeFetch = window.fetch.bind(window);

  const banner = document.createElement("div");
  banner.textContent = "라이브 데모 엔진 로딩 중… 첫 접속은 10초 정도 걸립니다.";
  banner.style.cssText =
    "position:fixed;left:16px;bottom:16px;z-index:9999;background:#111827;color:#fff;" +
    "padding:10px 14px;border-radius:10px;font-size:13px;box-shadow:0 4px 12px rgba(0,0,0,.25);";
  if (document.body) {
    document.body.appendChild(banner);
  } else {
    document.addEventListener("DOMContentLoaded", () => document.body.appendChild(banner));
  }

  async function fetchText(path) {
    const response = await nativeFetch(path);
    if (!response.ok) {
      throw new Error(`${path}: ${response.status}`);
    }
    return response.text();
  }

  async function boot() {
    await new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = PYODIDE_URL;
      script.onload = resolve;
      script.onerror = () => reject(new Error("Pyodide CDN 로드 실패"));
      document.head.appendChild(script);
    });
    const pyodide = await loadPyodide();
    pyodide.FS.mkdirTree("/movevalue/api");
    pyodide.FS.mkdirTree("/movevalue/data");
    const files = await Promise.all([
      ...PY_FILES.map(async (name) => [`api/${name}`, await fetchText(`./py/${name}`)]),
      ...DATA_FILES.map(async (name) => [`data/${name}`, await fetchText(`./data/${name}`)])
    ]);
    for (const [path, text] of files) {
      pyodide.FS.writeFile(`/movevalue/${path}`, text);
    }
    return pyodide.runPython(
      'import sys\nsys.path.insert(0, "/movevalue/api")\nimport static_dispatcher\nstatic_dispatcher.handle'
    );
  }

  const ready = boot().then(
    (handle) => {
      banner.remove();
      return handle;
    },
    (error) => {
      banner.textContent = `데모 엔진 로드 실패: ${error.message} — 새로고침해 주세요.`;
      banner.style.background = "#b91c1c";
      throw error;
    }
  );

  window.fetch = async function (input, init) {
    const url = typeof input === "string" ? input : String((input && input.url) || input || "");
    if (!url.startsWith("/api/")) {
      return nativeFetch(input, init);
    }
    const handle = await ready;
    const result = handle(url);
    const [status, body] = result.toJs();
    result.destroy();
    return new Response(body, {
      status,
      headers: { "Content-Type": "application/json; charset=utf-8" }
    });
  };
})();
