// 매물·중개사 탭. 실제 매물 연동 전이라 단지마다 '시연용 가상 매물'을 같은 규칙으로 만들어 보여준다.
// 핏홈은 중개 수수료를 받지 않고, 문의는 중개사와 직접 이어진다(광고 플랫폼 모델).
(() => {
  const BROKER_NAMES = ["가람", "한빛", "새솔", "온누리", "보람", "다온"];
  const DIRECTIONS = ["남향", "남동향", "남서향", "동향"];
  const NOTES = ["도배·장판 새로 했어요", "채광 좋고 조용한 동이에요", "입주 날짜 협의 가능해요", "역까지 걸어서 가까워요"];
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  function hash(text) {
    let h = 2166136261;
    for (const ch of String(text)) {
      h ^= ch.charCodeAt(0);
      h = Math.imul(h, 16777619);
    }
    return h >>> 0;
  }
  function seeded(seed) {
    let x = seed || 1;
    return () => {
      x ^= x << 13;
      x ^= x >>> 17;
      x ^= x << 5;
      return ((x >>> 0) % 10000) / 10000;
    };
  }
  function money(value) {
    const amount = Math.round(Number(value) || 0);
    const eok = Math.floor(amount / 10000);
    const man = amount % 10000;
    if (eok && man) return `${eok}억 ${man.toLocaleString()}`;
    if (eok) return `${eok}억`;
    return `${man.toLocaleString()}만`;
  }

  function listingsFor(detail) {
    const rand = seeded(hash(detail.id));
    const price = detail.price || {};
    const jeonse = Number(price.recentJeonse10k) || 20000;
    const sale = Number(price.recentSale10k) || 0;
    const areas = (detail.areaOptions || []).map((a) => Number(a.exclusiveM2)).filter(Boolean);
    const count = 2 + Math.floor(rand() * 3);
    const today = new Date();
    return Array.from({ length: count }, (_, i) => {
      const deposit10k = Math.round((jeonse * (0.9 + rand() * 0.2)) / 500) * 500;
      const area = areas.length ? areas[Math.floor(rand() * areas.length)] : [59, 84][i % 2];
      const total = 12 + Math.floor(rand() * 14);
      const floor = 2 + Math.floor(rand() * (total - 2));
      const checked = new Date(today.getTime() - Math.floor(rand() * 12) * 86400000);
      const name = BROKER_NAMES[Math.floor(rand() * BROKER_NAMES.length)];
      return {
        id: `${detail.id}-L${i + 1}`,
        title: `전세 ${money(deposit10k)} · ${Math.round(area)}㎡ ${floor}층`,
        deposit10k,
        area,
        floorLabel: `${floor}/${total}층`,
        direction: DIRECTIONS[Math.floor(rand() * DIRECTIONS.length)],
        note: NOTES[Math.floor(rand() * NOTES.length)],
        checkedAt: `${String(checked.getFullYear()).slice(2)}.${String(checked.getMonth() + 1).padStart(2, "0")}.${String(checked.getDate()).padStart(2, "0")}`,
        ratioPct: sale ? Math.round((deposit10k / sale) * 1000) / 10 : null,
        broker: {
          name: `${detail.dong || ""} ${name}공인중개사사무소`.trim(),
          ceo: `대표 ${["김", "이", "박", "최"][Math.floor(rand() * 4)]}○○`,
          regNo: `시연-${(detail.id || "").slice(-5)}-${100 + Math.floor(rand() * 899)}`,
          phone: `0507-0000-${String(1000 + Math.floor(rand() * 8999))}`,
        },
      };
    });
  }

  function ratioChip(pct) {
    if (pct === null) return "";
    const cls = pct >= 80 ? "is-danger" : pct >= 70 ? "is-caution" : "is-safe";
    return `<span class="fh-ratio ${cls}" title="근저당을 빼고 계산한 하한입니다">전세가율 ${pct}%</span>`;
  }

  function messageFor(detail, item) {
    return `안녕하세요. 핏홈에서 ${detail.name} ${item.title} 매물을 보고 연락드립니다. 계약 전에 등기부등본과 확정일자 부여현황, 임대인 납세증명서를 확인할 수 있을까요?`;
  }

  function render(container, { detail, isLoading, error } = {}) {
    if (isLoading) {
      container.innerHTML = `<div class="fh-empty">매물 정보를 불러오는 중이에요.</div>`;
      return;
    }
    if (error || !detail) {
      container.innerHTML = `<div class="fh-empty">${error ? esc(error) : "단지를 선택하면 매물과 중개사를 볼 수 있어요."}</div>`;
      return;
    }
    const items = listingsFor(detail);
    container.innerHTML = `
      <div class="fh-demo-note">ⓘ 시연용 가상 매물이에요. 실제 매물·중개사가 아니며, 매물 연동 후 화면 구성을 보여드리기 위한 예시입니다.</div>
      <div class="fh-listing-head">
        <strong>전세 매물 ${items.length}</strong>
        <span>핏홈은 중개 수수료를 받지 않아요. 문의는 중개사와 직접 연결돼요.</span>
      </div>
      <ul class="fh-listing-list">
        ${items
          .map(
            (item) => `<li class="fh-listing" data-listing="${esc(item.id)}">
              <div class="fh-listing-top">
                <strong class="fh-price">전세 ${esc(money(item.deposit10k))}</strong>
                <span class="fh-checked">확인 ${esc(item.checkedAt)}</span>
              </div>
              <p class="fh-spec">아파트 · ${esc(Math.round(item.area))}㎡ · ${esc(item.floorLabel)} · ${esc(item.direction)}</p>
              <p class="fh-note">${esc(item.note)}</p>
              <div class="fh-listing-tags">${ratioChip(item.ratioPct)}<span class="fh-tag">가상 매물</span></div>
              <div class="fh-broker">
                <div>
                  <strong>${esc(item.broker.name)}</strong>
                  <span>${esc(item.broker.ceo)} · 등록번호 ${esc(item.broker.regNo)}</span>
                </div>
                <span class="fh-verified" title="실서비스에서는 국토부 부동산중개업 정보로 등록번호·영업 상태·보증 기간을 확인합니다">등록·영업 확인(시연)</span>
              </div>
              <div class="fh-listing-actions">
                <button type="button" class="fh-btn" data-listing-action="call" data-phone="${esc(item.broker.phone)}">전화 문의</button>
                <button type="button" class="fh-btn" data-listing-action="sms" data-text="${esc(messageFor(detail, item))}">문자 문의</button>
                <button type="button" class="fh-btn primary" data-listing-action="report" data-id="${esc(detail.id)}" data-deposit="${item.deposit10k}" data-listing-id="${esc(item.id)}" data-title="${esc(item.title)}">이 매물 안심 판정</button>
              </div>
              <p class="fh-call" hidden></p>
            </li>`
          )
          .join("")}
      </ul>`;
  }

  async function copy(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      return false;
    }
  }

  document.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-listing-action]");
    if (!button) return;
    const card = button.closest(".fh-listing");
    const out = card?.querySelector(".fh-call");
    const action = button.dataset.listingAction;
    if (action === "call" && out) {
      out.hidden = false;
      out.textContent = `중개사 연결 번호 ${button.dataset.phone} (시연용 번호예요. 실서비스에서는 개인 번호 대신 안심번호로 연결됩니다.)`;
    } else if (action === "sms" && out) {
      const ok = await copy(button.dataset.text);
      out.hidden = false;
      out.textContent = ok ? "문의 문구를 복사했어요. 문자나 메신저에 붙여넣어 보내세요." : button.dataset.text;
    } else if (action === "report") {
      window.FitHomeReport?.open({
        id: button.dataset.id,
        deposit10k: Number(button.dataset.deposit),
        listing: { id: button.dataset.listingId, title: button.dataset.title },
      });
    }
  });

  window.FitHomeListings = { render };
})();
