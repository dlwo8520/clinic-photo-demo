(() => {
  "use strict";
  const app = document.getElementById("upload-app");
  if (!app) return;
  const queue = [];
  const maxSize = 20 * 1024 * 1024;
  const queueElement = document.getElementById("upload-queue");
  const form = document.getElementById("upload-form");
  const submit = document.getElementById("upload-submit");
  const retry = document.getElementById("retry-failed");
  const message = document.getElementById("upload-message");
  const expiry = new Date(app.dataset.expires);
  let busy = false;
  let expired = false;
  function uuid() {
    if (globalThis.crypto?.randomUUID) return crypto.randomUUID();
    const bytes = new Uint8Array(16);
    if (globalThis.crypto?.getRandomValues) crypto.getRandomValues(bytes);
    else for (let index = 0; index < bytes.length; index++) bytes[index] = Math.floor(Math.random() * 256);
    bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
    const hex = [...bytes].map(byte => byte.toString(16).padStart(2, "0")).join("");
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }
  function notify(text, error = false) {
    message.textContent = text; message.hidden = !text;
    message.className = error ? "notice error" : "notice";
  }
  function updateExpiry() {
    if (Number.isNaN(expiry.getTime())) return;
    const seconds = Math.max(0, Math.ceil((expiry.getTime() - Date.now()) / 1000));
    const note = document.getElementById("mobile-expiry");
    if (!seconds || expired) {
      expired = true; note.className = "expiry-note expired";
      note.textContent = "QR 만료 · PC에서 새 QR을 만들어 다시 접속해 주세요.";
      updateButtons();
    } else note.textContent = `QR 남은 시간 ${Math.floor(seconds / 60)}분 ${seconds % 60}초 · 유효 시간 동안 여러 번 업로드할 수 있습니다.`;
  }
  function updateButtons() {
    const pending = queue.filter(item => item.status === "pending").length;
    const failed = queue.filter(item => item.status === "error").length;
    const saved = queue.filter(item => ["saved", "duplicate"].includes(item.status)).length;
    document.getElementById("selected-count").textContent = queue.length;
    document.getElementById("upload-empty").hidden = Boolean(queue.length);
    const clear = document.getElementById("clear-photos"); clear.hidden = !queue.length; clear.disabled = busy;
    document.getElementById("camera-input").disabled = busy || expired;
    document.getElementById("library-input").disabled = busy || expired;
    document.querySelectorAll(".file-actions .button").forEach(label => { label.setAttribute("aria-disabled", String(busy || expired)); label.style.opacity = busy || expired ? ".5" : "1"; });
    submit.disabled = busy || expired || !pending;
    submit.textContent = busy ? "업로드 중… 화면을 닫지 마세요" : expired ? "QR 만료 · 새 QR이 필요합니다" : pending ? `선택한 사진 ${pending}장 한 번에 올리기` : saved && !failed ? "저장 완료 · 사진을 더 선택할 수 있습니다" : failed ? "아래에서 실패한 사진을 다시 시도하세요" : "사진을 선택해 주세요";
    retry.hidden = !failed; retry.disabled = busy || expired;
    retry.textContent = `실패한 사진 ${failed}장만 다시 시도`;
    const summary = document.getElementById("upload-summary");
    summary.hidden = !saved && !failed;
    summary.textContent = `저장 완료 ${saved}장${failed ? ` · 업로드 실패 ${failed}장` : ""}${pending ? ` · 전송 대기 ${pending}장` : ""}`;
    for (const item of queue) {
      item.remove.disabled = busy;
      item.siteInput.disabled = busy || item.status === "saved" || item.status === "duplicate";
    }
  }
  function setItemStatus(item, status, reason = "") {
    item.status = status; item.element.dataset.status = status;
    const texts = {pending: "전송 대기 · 사진을 확인한 뒤 올려 주세요", uploading: "↥ 업로드 중 · 서버에서 사진을 확인하고 있습니다", saved: "✓ 저장 완료", duplicate: "✓ 저장 완료 · 이미 저장된 요청입니다", error: `! 업로드 실패 · ${reason || "다시 시도해 주세요."}`};
    item.statusElement.textContent = texts[status];
    item.remove.setAttribute("aria-label", `${item.file.name} ${status === "saved" || status === "duplicate" ? "목록에서 제거" : "선택 취소"}`);
  }
  function removeItem(item) {
    if (busy) return;
    const index = queue.indexOf(item); if (index >= 0) queue.splice(index, 1);
    URL.revokeObjectURL(item.objectURL); item.element.remove(); updateButtons();
  }
  function buildItem(file) {
    const item = {file, clientId: uuid(), status: "pending", objectURL: URL.createObjectURL(file)};
    const article = document.createElement("article"); article.className = "upload-item";
    const preview = document.createElement("div"); preview.className = "upload-preview";
    const image = new Image(); image.src = item.objectURL; image.alt = `${file.name} 선택 미리보기`;
    image.addEventListener("error", () => { const fallback = document.createElement("span"); fallback.className = "preview-fallback"; fallback.textContent = "미리보기 불가 · 서버에서 이미지 확인 후 변환"; preview.replaceChildren(fallback); });
    preview.append(image);
    const info = document.createElement("div"); info.className = "upload-item-info";
    const name = document.createElement("p"); name.className = "upload-filename"; name.textContent = file.name;
    const size = document.createElement("p"); size.className = "upload-size"; size.textContent = `${(file.size / 1024 / 1024).toFixed(1)} MB`;
    const label = document.createElement("label"); label.htmlFor = `site-${item.clientId}`; label.textContent = "촬영 부위 (선택)";
    const site = document.createElement("input"); site.id = label.htmlFor; site.type = "text"; site.className = "body-site"; site.placeholder = "정수리, 헤어라인, 측면 등"; site.maxLength = 40; site.autocomplete = "off";
    const remove = document.createElement("button"); remove.className = "remove-photo"; remove.type = "button"; remove.textContent = "×";
    remove.addEventListener("click", () => removeItem(item));
    const status = document.createElement("div"); status.className = "item-status"; status.setAttribute("role", "status");
    info.append(name, size, label, site); article.append(preview, info, remove, status); queueElement.append(article);
    item.element = article; item.statusElement = status; item.siteInput = site; item.remove = remove;
    setItemStatus(item, "pending");
    return item;
  }
  function addFiles(event) {
    if (busy || expired) return;
    const files = [...event.target.files];
    let excess = false;
    for (const file of files) {
      if (queue.filter(item => !["saved", "duplicate"].includes(item.status)).length >= 20) { excess = true; break; }
      const item = buildItem(file); queue.push(item);
      if (!file.size) setItemStatus(item, "error", "빈 파일은 올릴 수 없습니다. 다른 사진을 선택해 주세요.");
      else if (file.size > maxSize) setItemStatus(item, "error", "한 장당 최대 20MB입니다. 크기를 줄인 사진을 선택해 주세요.");
    }
    event.target.value = "";
    notify(excess ? "한 번에 최대 20장까지 선택할 수 있습니다. 먼저 저장한 뒤 나머지 사진을 추가해 주세요." : "", excess);
    updateButtons();
  }
  document.getElementById("camera-input").addEventListener("change", addFiles);
  document.getElementById("library-input").addEventListener("change", addFiles);
  document.getElementById("clear-photos").addEventListener("click", () => {
    if (busy) return;
    [...queue].forEach(removeItem); notify(""); updateButtons();
  });
  async function upload(items) {
    if (busy || expired || !items.length) return;
    if (items.reduce((total, item) => total + item.file.size, 0) > 100 * 1024 * 1024) {
      notify("한 번에 최대 100MB까지 전송할 수 있습니다. 일부 사진의 선택을 취소하고 나눠서 올려 주세요.", true);
      return;
    }
    busy = true; notify("");
    const data = new FormData();
    for (const item of items) {
      setItemStatus(item, "uploading");
      data.append("photos", item.file, item.file.name);
      data.append("client_ids", item.clientId);
      data.append("body_sites", item.siteInput.value.trim());
    }
    updateButtons();
    try {
      const response = await fetch(`/api/uploads/${encodeURIComponent(app.dataset.token)}/photos/`, {method: "POST", credentials: "same-origin", headers: {"X-CSRFToken": form.querySelector("[name=csrfmiddlewaretoken]").value}, body: data});
      if (response.redirected && response.url.includes("/login")) throw new Error("LOGIN_REQUIRED");
      let result;
      try { result = await response.json(); } catch { throw new Error("INVALID_RESPONSE"); }
      if (!response.ok) {
        if (response.status === 410) { expired = true; document.getElementById("mobile-expiry").textContent = "QR 만료 · PC에서 새 QR을 만들어 다시 접속해 주세요."; document.getElementById("mobile-expiry").className = "expiry-note expired"; }
        throw new Error(result.error || result.message || "서버가 요청을 처리하지 못했습니다.");
      }
      const results = new Map((result.results || []).map(row => [String(row.client_id), row]));
      for (const item of items) {
        const row = results.get(item.clientId);
        if (row && ["saved", "duplicate"].includes(row.status)) setItemStatus(item, row.status);
        else setItemStatus(item, "error", row?.error || "저장 결과를 확인하지 못했습니다. 같은 사진을 다시 시도해 주세요.");
      }
      const saved = items.filter(item => ["saved", "duplicate"].includes(item.status)).length;
      const failed = items.length - saved;
      notify(failed ? `${saved}장 저장 완료, ${failed}장 업로드 실패. 사진별 이유를 확인하고 실패한 사진만 다시 시도해 주세요.` : `${saved}장 저장 완료. PC의 해당 방문에 자동으로 나타납니다.`, Boolean(failed));
    } catch (error) {
      let text = error.message;
      if (text === "LOGIN_REQUIRED") text = "로그인이 만료되었습니다. 이 화면을 새로고침해 다시 로그인해 주세요.";
      else if (text === "INVALID_RESPONSE") text = "서버 응답을 확인하지 못했습니다. 연결을 확인하고 다시 시도해 주세요.";
      else if (error instanceof TypeError) text = "연결이 끊겨 저장 결과를 확인하지 못했습니다. 다시 시도해도 중복 저장되지 않습니다.";
      items.forEach(item => { if (item.status === "uploading") setItemStatus(item, "error", text); });
      notify(text, true);
    } finally { busy = false; updateButtons(); }
  }
  form.addEventListener("submit", event => { event.preventDefault(); upload(queue.filter(item => item.status === "pending")); });
  retry.addEventListener("click", () => upload(queue.filter(item => item.status === "error")));
  window.addEventListener("beforeunload", event => { if (busy) { event.preventDefault(); event.returnValue = ""; } });
  updateButtons(); updateExpiry(); window.setInterval(updateExpiry, 1000);
})();
