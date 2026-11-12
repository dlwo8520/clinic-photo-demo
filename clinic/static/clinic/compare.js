(() => {
  "use strict";
  const app = document.getElementById("compare-app");
  if (!app) return;
  const initial = JSON.parse(document.getElementById("compare-data").textContent);
  const visits = initial.visits || [];
  const state = {};
  const csrf = document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
  const errorBox = document.getElementById("compare-error");
  const pollStatus = document.getElementById("poll-status");
  const patientName = document.querySelector(".patient-summary h1").childNodes[0].textContent.trim();
  const chartNumber = document.querySelector(".patient-summary .chart-number").textContent.trim();
  let qrExpiry = null;
  function showError(message) { errorBox.textContent = message; errorBox.hidden = !message; }
  async function request(url, options = {}) {
    const response = await fetch(url, {credentials: "same-origin", ...options, headers: {"X-CSRFToken": csrf, ...options.headers}});
    if (response.redirected && response.url.includes("/login")) throw new Error("로그인이 만료되었습니다. 새로고침 후 다시 로그인해 주세요.");
    let data;
    try { data = await response.json(); } catch { throw new Error("서버 응답을 확인할 수 없습니다. 잠시 후 다시 시도해 주세요."); }
    if (!response.ok) throw new Error(data.error || data.message || "요청을 처리하지 못했습니다.");
    return data;
  }
  function visitFor(id) { return visits.find(visit => String(visit.id) === String(id)); }
  function setVisitCounts(id, count) {
    const visit = visitFor(id);
    if (visit) visit.photo_count = count;
    for (const side of ["left", "right"]) {
      const select = document.getElementById(`${side}-visit`);
      for (const option of select.options) {
        const v = visitFor(option.value);
        if (v) option.textContent = `${v.label} · 사진 ${v.photo_count || 0}장`;
      }
    }
  }
  function fillSelect(side) {
    const select = document.getElementById(`${side}-visit`);
    select.replaceChildren();
    if (!visits.length) {
      const option = new Option("아직 방문 기록이 없습니다", "");
      select.add(option); select.disabled = true;
    } else {
      select.disabled = false;
      visits.forEach(visit => select.add(new Option(`${visit.label} · 사진 ${visit.photo_count || 0}장`, visit.id)));
      select.value = state[side].visitId || "";
    }
  }
  function renderPhoto(side) {
    const panel = state[side];
    const stage = document.getElementById(`${side}-stage`);
    const photo = panel.photos.find(item => String(item.id) === String(panel.photoId));
    stage.replaceChildren();
    if (photo) {
      const img = new Image();
      img.alt = `${side === "left" ? "이전 방문" : "비교할 방문"} · ${photo.body_site || "촬영 부위 미입력"}`;
      img.src = photo.url;
      img.addEventListener("error", () => {
        if (stage.contains(img)) { const note = document.createElement("p"); note.className = "muted"; note.textContent = "사진을 불러오지 못했습니다. 로그인과 연결을 확인해 주세요."; stage.replaceChildren(note); }
      });
      stage.append(img);
    } else {
      const empty = document.createElement("div"); empty.className = "photo-empty";
      const icon = document.createElement("span"); icon.className = "empty-mark"; icon.textContent = "＋"; icon.setAttribute("aria-hidden", "true");
      const title = document.createElement("strong"); title.textContent = "사진 없음";
      const hint = document.createElement("p"); hint.textContent = panel.visitId ? (side === "right" ? "아이폰에서 이 방문에 사진을 추가해 보세요." : "선택한 방문에 저장된 사진이 없습니다.") : "새 방문을 만들어 사진을 저장해 보세요.";
      empty.append(icon, title, hint); stage.append(empty);
    }
    document.getElementById(`${side}-site`).textContent = photo?.body_site || "촬영 부위 미입력";
    document.getElementById(`${side}-position`).textContent = `${photo ? panel.photos.indexOf(photo) + 1 : 0} / ${panel.photos.length}`;
    document.querySelectorAll(`#${side}-thumbnails .thumbnail`).forEach(button => button.setAttribute("aria-pressed", String(button.dataset.photoId === String(panel.photoId))));
  }
  function render(side) {
    const panel = state[side];
    document.getElementById(`${side}-count`).textContent = `사진 ${panel.photos.length}장`;
    const thumbs = document.getElementById(`${side}-thumbnails`);
    thumbs.replaceChildren();
    panel.photos.forEach((photo, index) => {
      const button = document.createElement("button"); button.type = "button"; button.className = "thumbnail"; button.dataset.photoId = photo.id;
      button.setAttribute("aria-label", `${index + 1}번 사진 · ${photo.body_site || "촬영 부위 미입력"}`);
      const img = new Image(); img.src = photo.thumbnail_url; img.alt = ""; img.loading = "lazy";
      const site = document.createElement("span"); site.className = "thumb-site"; site.textContent = photo.body_site || "부위 미입력";
      button.append(img, site); button.addEventListener("click", () => { panel.photoId = photo.id; renderPhoto(side); }); thumbs.append(button);
    });
    renderPhoto(side);
  }
  function target() {
    const visit = visitFor(state.right.visitId);
    document.getElementById("upload-target").textContent = visit ? `${patientName} · ${chartNumber} / ${visit.label}` : "사진을 저장할 방문을 먼저 만들어 주세요.";
    document.getElementById("create-qr").disabled = !visit;
  }
  async function loadVisit(side, visitId) {
    const panel = state[side];
    const version = ++panel.version;
    panel.visitId = visitId; panel.photos = []; panel.photoId = null; panel.loading = true;
    render(side); target(); showError("");
    if (!visitId) { panel.loading = false; return; }
    try {
      const data = await request(`/api/visits/${visitId}/photos/`);
      if (version !== panel.version) return;
      panel.photos = data.photos || []; panel.photoId = panel.photos[0]?.id || null;
      setVisitCounts(visitId, panel.photos.length); render(side);
    } catch (error) { if (version === panel.version) showError(error.message); }
    finally { if (version === panel.version) panel.loading = false; }
  }
  for (const side of ["left", "right"]) {
    const source = initial[side] || {};
    state[side] = {visitId: source.visit_id || null, photos: source.photos || [], photoId: source.photos?.[0]?.id || null, version: 0, loading: false};
    fillSelect(side); render(side);
    document.getElementById(`${side}-visit`).addEventListener("change", event => loadVisit(side, event.target.value));
  }
  target();
  async function poll() {
    const panel = state.right;
    const visitId = panel.visitId;
    const version = panel.version;
    if (visitId && !panel.loading && !document.hidden) {
      try {
        const data = await request(`/api/visits/${visitId}/photos/`);
        if (version === panel.version && String(visitId) === String(panel.visitId)) {
          const photos = data.photos || [];
          const previous = new Set(panel.photos.map(photo => String(photo.id)));
          const added = photos.filter(photo => !previous.has(String(photo.id)));
          const changed = photos.length !== panel.photos.length || photos.some((photo, index) => String(photo.id) !== String(panel.photos[index]?.id));
          if (changed) {
            panel.photos = photos;
            if (added.length) panel.photoId = added[added.length - 1].id;
            else if (!photos.some(photo => String(photo.id) === String(panel.photoId))) panel.photoId = photos[0]?.id || null;
            setVisitCounts(visitId, photos.length); render("right");
            pollStatus.textContent = added.length ? `새 사진 ${added.length}장이 추가되었습니다 · 자동 갱신 중` : "사진 목록을 갱신했습니다 · 2초 간격";
          } else pollStatus.textContent = "새 사진을 자동으로 확인합니다 · 2초 간격";
        }
      } catch { pollStatus.textContent = "연결을 확인하는 중입니다 · 자동 재시도"; }
    }
    window.setTimeout(poll, 2000);
  }
  window.setTimeout(poll, 2000);
  const visitForm = document.getElementById("new-visit-form");
  document.getElementById("new-visit-toggle").addEventListener("click", event => {
    visitForm.hidden = !visitForm.hidden; event.currentTarget.setAttribute("aria-expanded", String(!visitForm.hidden));
    if (!visitForm.hidden) document.getElementById("new-week").focus();
  });
  const now = new Date();
  document.getElementById("new-date").value = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  visitForm.addEventListener("submit", async event => {
    event.preventDefault(); const button = visitForm.querySelector("button[type=submit]"); button.disabled = true;
    const error = document.getElementById("new-visit-error"); error.textContent = "";
    try {
      const data = await request(`/api/patients/${app.dataset.patientId}/visits/`, {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify({week: Number(document.getElementById("new-week").value), visited_on: document.getElementById("new-date").value})});
      visits.push(data.visit); visits.sort((a, b) => a.visited_on.localeCompare(b.visited_on) || a.id - b.id);
      state.right.visitId = data.visit.id; state.right.photos = []; state.right.photoId = null; state.right.version++; state.right.loading = false;
      for (const side of ["left", "right"]) fillSelect(side);
      render("right"); target(); document.getElementById("visit-total").textContent = `방문 ${visits.length}회`;
      visitForm.hidden = true; document.getElementById("new-visit-toggle").setAttribute("aria-expanded", "false");
    } catch (issue) { error.textContent = issue.message; }
    finally { button.disabled = false; }
  });
  document.getElementById("create-qr").addEventListener("click", async event => {
    const visitId = state.right.visitId; if (!visitId) return;
    const button = event.currentTarget; button.disabled = true; button.textContent = "QR 만드는 중…"; showError("");
    try {
      const data = await request(`/api/visits/${visitId}/upload-sessions/`, {method: "POST"});
      document.getElementById("qr-image").src = data.qr_url;
      document.getElementById("qr-target").textContent = `${data.patient_name} · ${data.chart_number} / ${data.visit_label}`;
      const link = document.getElementById("upload-open"); link.href = data.url;
      qrExpiry = new Date(data.expires_at); updateQRExpiry();
      document.getElementById("qr-section").hidden = false;
      document.getElementById("qr-section").scrollIntoView({behavior: "smooth", block: "nearest"});
    } catch (issue) { showError(issue.message); }
    finally { button.textContent = "아이폰으로 사진 추가 ↗"; target(); }
  });
  document.getElementById("qr-close").addEventListener("click", () => { document.getElementById("qr-section").hidden = true; });
  function updateQRExpiry() {
    if (!qrExpiry) return;
    const seconds = Math.max(0, Math.ceil((qrExpiry.getTime() - Date.now()) / 1000));
    document.getElementById("qr-expiry").textContent = seconds ? `만료 ${qrExpiry.toLocaleTimeString("ko-KR", {hour: "2-digit", minute: "2-digit"})} · 남은 시간 ${Math.floor(seconds / 60)}분 ${seconds % 60}초` : "QR 만료 · 새 QR을 만들어 주세요.";
    document.getElementById("upload-open").setAttribute("aria-disabled", String(!seconds));
  }
  window.setInterval(updateQRExpiry, 1000);
})();
