/* Interface local: apresentação no navegador, persistência e validação no Python. */
"use strict";
const $ = (id) => document.getElementById(id);
const video = $("video");
const labels = {
  chapters: "Capítulos",
  subtitles: "Legendas",
  casting: "Elenco",
  metadata: "Metadados",
  images: "Imagens",
};
let state = { data: {}, subtitles: [], revision: 0 },
  settings = { small_jump: 5, large_jump: 20, volume: 100 };
let tab = "chapters",
  selected = null,
  bridge = null,
  busy = false,
  editContext = null,
  cropImage = null,
  toastTimer,
  playbackFrame,
  menuTrigger = null;
let editSync = Promise.resolve();
function syncEditState(pending) {
  editSync = editSync
    .then(() => bridge?.set_edit_state(pending))
    .catch((error) => notify(String(error.message || error), true));
}
function markDirty() {
  $("edit-form").dataset.changed = "true";
  syncEditState(true);
}
const escapeHtml = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        character
      ],
  );
const uid = () => crypto.randomUUID();
function time(seconds, millis = false) {
  const total = Math.max(0, Math.round((Number(seconds) || 0) * 1000));
  const h = Math.floor(total / 3600000),
    m = Math.floor(total / 60000) % 60,
    s = Math.floor(total / 1000) % 60;
  return `${h ? String(h).padStart(2, "0") + ":" : ""}${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}${millis ? "." + String(total % 1000).padStart(3, "0") : ""}`;
}
function parseTime(value, millis = false) {
  const match = /^(?:(\d+):)?(\d{1,2}):(\d{2})(?:[.,](\d{1,3}))?$/.exec(
    value.trim(),
  );
  if (!match || Number(match[2]) > 59 || Number(match[3]) > 59)
    throw Error(
      "Informe um tempo válido: mm:ss ou hh:mm:ss, com milissegundos opcionais.",
    );
  const ms =
    ((Number(match[1] || 0) * 60 + Number(match[2])) * 60 + Number(match[3])) *
      1000 +
    Number((match[4] || "").padEnd(3, "0"));
  return millis ? ms : Math.floor(ms / 1000);
}
function chapterTime(seconds) {
  const formatted = time(seconds);
  return formatted.split(":").length === 2 ? `00:${formatted}` : formatted;
}
function applyTimeMask(input) {
  const suffixDigits = input.value
    .slice(input.selectionStart)
    .replace(/\D/g, "").length;
  const digits = input.value
    .replace(/\D/g, "")
    .replace(/^0+(?=\d)/, "")
    .padStart(6, "0");
  input.value = `${digits.slice(0, -4)}:${digits.slice(-4, -2)}:${digits.slice(-2)}`;
  let caret = input.value.length,
    remaining = suffixDigits;
  while (caret > 0 && remaining > 0) {
    caret--;
    if (/\d/.test(input.value[caret])) remaining--;
  }
  input.setSelectionRange(caret, caret);
  input.setCustomValidity(
    /^[0-9]{2,}:[0-5][0-9]:[0-5][0-9]$/.test(input.value)
      ? ""
      : "Minutos e segundos devem estar entre 00 e 59.",
  );
}
function notify(message, error = false) {
  clearTimeout(toastTimer);
  $("toast").textContent = message;
  $("toast").classList.toggle("error", error);
  $("toast").hidden = false;
  toastTimer = setTimeout(
    () => {
      $("toast").hidden = true;
    },
    error ? 12000 : 4500,
  );
}
function items(section = tab) {
  return section === "subtitles" ? state.subtitles : state.data[section] || [];
}
function flatten(nodes, depth = 0, parent = null, output = []) {
  nodes.forEach((node, index) => {
    output.push({ node, depth, parent, siblings: nodes, index });
    flatten(node.subs || node.children || [], depth + 1, node, output);
  });
  return output;
}
function rows() {
  return flatten(items());
}
function selection() {
  return rows().find(({ node }) => node.id === selected);
}
function title(node) {
  return node.title || node.name || node.key || node.text || "Sem título";
}
function accept(next, opening = false) {
  state = next;
  // SRT não possui identificadores persistentes; os IDs abaixo existem apenas nesta sessão.
  state.subtitles.forEach((node) => {
    node.id = uid();
  });
  $("filename").textContent = state.name || "Nenhum vídeo aberto";
  $("file-path").textContent = state.path || "PRONTO PARA COMEÇAR";
  $("file-path").title = state.path || "";
  $("empty-player").hidden = !!state.name;
  $("add").disabled = !state.name || busy;
  if (opening) {
    video.pause();
    video.src = state.media_url;
    $("media-error").hidden = true;
    selected = null;
  }
  render();
  updatePlayback();
}
function render() {
  closeActions();
  document
    .querySelectorAll("[data-tab]")
    .forEach((button) =>
      button.classList.toggle("active", button.dataset.tab === tab),
    );
  $("search").placeholder = `Buscar ${labels[tab].toLowerCase()}…`;
  $("list-label").textContent = labels[tab].toUpperCase();
  const all = rows(),
    query = $("search").value.trim().toLocaleLowerCase("pt-BR");
  const visible = all.filter(({ node }) =>
    `${title(node)} ${node.value || ""} ${node.description || ""}`
      .toLocaleLowerCase("pt-BR")
      .includes(query),
  );
  $("item-count").textContent =
    `${all.length} ${all.length === 1 ? "ITEM" : "ITENS"}`;
  $("records").innerHTML = visible.length
    ? visible
        .map(({ node, depth }, index) => {
          const detail =
            tab === "chapters"
              ? `${time(node.start)} — ${time(node.end)}${node.subs.length ? ` · ${node.subs.length} subcap.` : ""}`
              : tab === "subtitles"
                ? `${time(node.start / 1000, true)} — ${time(node.end / 1000, true)}`
                : tab === "metadata"
                  ? node.value || `${node.children.length} subitens`
                  : tab === "images"
                    ? `${node.width} × ${node.height} · ${node.description || "Imagem do projeto"}`
                    : `${(node.images || []).length} imagens associadas`;
          return `<div class="record ${selected === node.id ? "selected" : ""}" data-id="${escapeHtml(node.id)}" style="margin-left:${Math.min(depth, 8) * 14}px"><div class="record-select" role="button" tabindex="0" aria-pressed="${selected === node.id}">${tab === "images" ? `<img class="record-thumb" src="${escapeHtml(node.source)}" alt="">` : `<span class="record-number">${String(index + 1).padStart(2, "0")}</span>`}<div class="record-body"><div class="record-title">${escapeHtml(title(node))}</div><div class="record-detail">${escapeHtml(detail)}</div></div></div>${tab === "chapters" ? `<button class="record-menu" aria-label="Ações de ${escapeHtml(title(node))}" title="Ações do capítulo" aria-haspopup="menu" aria-expanded="false" aria-controls="action-menu" ${busy ? "disabled" : ""}>⋯</button>` : '<span class="record-tail">›</span>'}</div>`;
        })
        .join("")
    : `<div class="empty-list"><span>▤</span><strong>${query ? "Nenhum resultado" : `Seu espaço de ${labels[tab].toLowerCase()}`}</strong>${query ? "Tente buscar por outro termo." : state.name ? "Adicione o primeiro item usando o botão Novo." : "Abra um vídeo para começar a editar."}</div>`;
  updateSelectionControls();
  $("chapter-count").textContent =
    `${flatten(items("chapters")).length} capítulos`;
  renderTimeline();
}
function updateSelectionControls() {
  const chosen = selection();
  $("add").textContent = tab === "chapters" ? "＋ Capítulo" : "＋ Novo";
  $("add-options").hidden = tab !== "chapters";
  $("add-options").disabled = !state.name || busy;
  $("selection-label").textContent = chosen
    ? title(chosen.node)
    : "Selecione um item para editar";
  ["edit", "remove"].forEach((id) => {
    $(id).disabled = !chosen || busy;
  });
  $("child").disabled =
    !chosen || !["chapters", "metadata"].includes(tab) || busy;
  $("jump").disabled = !chosen || !["chapters", "subtitles"].includes(tab);
}
function selectRecord(id) {
  selected = id;
  // Preserva os elementos entre os cliques para o navegador reconhecer o duplo clique.
  document.querySelectorAll(".record").forEach((row) => {
    const active = row.dataset.id === id;
    row.classList.toggle("selected", active);
    row
      .querySelector(".record-select")
      .setAttribute("aria-pressed", String(active));
  });
  updateSelectionControls();
}
function closeActions(restoreFocus = false) {
  const trigger = menuTrigger;
  if ($("action-menu").matches(":popover-open")) $("action-menu").hidePopover();
  trigger?.setAttribute("aria-expanded", "false");
  menuTrigger = null;
  if (restoreFocus && trigger?.isConnected) trigger.focus();
}
function showActions(trigger, creation = false) {
  if (busy) return;
  const wasOpen =
    menuTrigger === trigger && $("action-menu").matches(":popover-open");
  closeActions();
  if (wasOpen) return;
  const chosen = selection();
  const actions = creation
    ? [
        ["new", "Criar capítulo", false],
        ["child", "Criar subcapítulo", !chosen],
      ]
    : [
        ["edit", "Editar", false],
        ["remove", "Excluir", false],
        ["child", "Criar subcapítulo", false],
      ];
  $("action-menu").innerHTML = actions
    .map(
      ([action, label, disabled]) =>
        `<button role="menuitem" data-action="${action}" ${disabled ? 'disabled title="Selecione um capítulo pai primeiro"' : ""} class="${action === "remove" ? "danger" : ""}">${label}</button>`,
    )
    .join("");
  menuTrigger = trigger;
  trigger.setAttribute("aria-expanded", "true");
  $("action-menu").showPopover();
  const anchor = trigger.getBoundingClientRect(),
    bounds = $("action-menu").getBoundingClientRect();
  $("action-menu").style.left =
    `${Math.max(8, Math.min(innerWidth - bounds.width - 8, anchor.right - bounds.width))}px`;
  $("action-menu").style.top =
    `${Math.max(8, Math.min(innerHeight - bounds.height - 8, anchor.bottom + bounds.height + 6 <= innerHeight ? anchor.bottom + 6 : anchor.top - bounds.height - 6))}px`;
  $("action-menu").querySelector("button:not(:disabled)")?.focus();
}
function renderTimeline() {
  const lanes = [];
  for (const root of [...items("chapters")].sort((a, b) => a.start - b.start)) {
    let lane = lanes.find((entry) => entry.end <= root.start);
    if (!lane) {
      lane = { end: 0, roots: [] };
      lanes.push(lane);
    }
    lane.roots.push(root);
    lane.end = Math.max(root.end, root.start);
  }
  const duration = Number.isFinite(video.duration) ? video.duration : 0;
  $("ruler").innerHTML = [0, 0.25, 0.5, 0.75, 1]
    .map(
      (fraction) =>
        `<span>${duration ? time(duration * fraction) : "—"}</span>`,
    )
    .join("");
  $("chapter-track").innerHTML =
    duration && lanes.length
      ? lanes
          .map((lane, index) => {
            const bars = flatten(lane.roots)
              .map(({ node, depth }) => {
                const start = Math.max(0, Math.min(duration, node.start));
                const end = Math.max(start, Math.min(duration, node.end));
                const description = `${node.title} · ${time(node.start)} — ${time(node.end)}`;
                return `<button data-time="${node.start}" data-chapter-id="${escapeHtml(node.id)}" data-depth="${depth}" style="--depth:${Math.min(depth, 3)};z-index:${depth + 1};left:${(start / duration) * 100}%;width:${((end - start) / duration) * 100}%" ${end === start ? 'class="instant"' : ""} title="${escapeHtml(description)}" aria-label="Ir para ${escapeHtml(description)}">${escapeHtml(node.title)}</button>`;
              })
              .join("");
            return `<div class="timeline-row"><div class="timeline-lane" role="group" aria-label="Faixa ${index + 1}">${bars}</div></div>`;
          })
          .join("")
      : '<span class="timeline-empty">Seus capítulos aparecerão aqui.</span>';
}
async function openVideo() {
  if (!bridge) {
    notify("Aguarde a conexão com a janela desktop.", true);
    return;
  }
  if (busy || $("editor-dialog").open) return;
  busy = true;
  $("open").disabled = true;
  try {
    const next = await bridge.open_video();
    if (next) accept(next, true);
  } catch (error) {
    notify(String(error.message || error), true);
  } finally {
    busy = false;
    $("open").disabled = false;
    $("add").disabled = !state.name;
    updateSelectionControls();
  }
}
function field(name, label, value = "", kind = "text", timing = false) {
  const input =
    kind === "textarea"
      ? `<textarea name="${name}">${escapeHtml(value)}</textarea>`
      : `<input name="${name}" type="${kind}" value="${escapeHtml(value)}" ${kind === "file" ? 'accept="image/*"' : ""} ${timing && tab === "chapters" ? 'data-time-mask inputmode="numeric" placeholder="00:00:00" autocomplete="off" aria-description="Digite os números de horas, minutos e segundos. Os dois-pontos são inseridos automaticamente."' : ""}>`;
  return `<label class="field">${label}${timing ? `<div class="field-inline">${input}<button type="button" data-capture="${name}">Tempo atual</button></div>` : input}</label>`;
}
function imageLinks(node) {
  const images = items("images");
  if (!images.length) return "";
  return `<div class="field">Imagens associadas<div class="image-links">${images.map((image) => `<label class="image-choice"><input type="checkbox" name="images" value="${escapeHtml(image.id)}" ${(node.images || []).includes(image.id) ? "checked" : ""}><img src="${escapeHtml(image.source)}" alt="">${escapeHtml(image.title || "Imagem")}</label>`).join("")}</div></div>`;
}
function showEditor(mode = "new") {
  if (!state.name || busy) return;
  const found = selection();
  if (mode !== "new" && !found) return;
  closeActions();
  const siblings =
    mode === "child" ? found.node.subs : found?.siblings || items();
  const isSubchapter = mode === "child" || !!found?.parent;
  const prefix = isSubchapter ? "Subcapítulo" : "Capítulo";
  let chapterNumber = 1;
  if (tab === "chapters")
    while (siblings.some((item) => item.title === `${prefix} ${chapterNumber}`))
      chapterNumber++;
  const seconds = Math.floor(video.currentTime || 0),
    milliseconds = Math.round((video.currentTime || 0) * 1000);
  const defaults = {
    id: uid(),
    title: tab === "chapters" ? `${prefix} ${chapterNumber}` : "",
    start: tab === "subtitles" ? milliseconds : seconds,
    end: tab === "subtitles" ? milliseconds + 2000 : seconds,
    subs: [],
    children: [],
    images: [],
    name: "",
    key: "",
    value: mode === "child" && tab === "metadata" ? found.node.value : "",
    text: "",
    description: "",
  };
  const node = mode === "edit" ? structuredClone(found.node) : defaults;
  editContext = {
    mode,
    section: tab,
    revision: state.revision,
    data: structuredClone(items()),
    selected,
    node,
  };
  let html = "";
  if (tab === "chapters")
    html =
      field("title", "Título do capítulo", node.title) +
      field(
        "start",
        "Início · hh:mm:ss",
        chapterTime(node.start),
        "text",
        true,
      ) +
      field("end", "Fim · hh:mm:ss", chapterTime(node.end), "text", true) +
      '<p class="muted">Digite apenas números: 1234 → 00:12:34. Minutos e segundos vão de 00 a 59.</p>';
  if (tab === "subtitles")
    html =
      field("text", "Texto da legenda", node.text, "textarea") +
      field(
        "start",
        "Início · mm:ss.mmm",
        time(node.start / 1000, true),
        "text",
        true,
      ) +
      field(
        "end",
        "Fim · mm:ss.mmm",
        time(node.end / 1000, true),
        "text",
        true,
      );
  if (tab === "casting") html = field("name", "Nome no elenco", node.name);
  if (tab === "metadata")
    html =
      field("key", "Chave", node.key) +
      (node.children.length
        ? '<p class="muted">O valor é definido nas folhas desta árvore.</p>'
        : field("value", "Valor", node.value, "textarea"));
  if (tab === "images") {
    html =
      field("title", "Título", node.title) +
      field("description", "Descrição", node.description, "textarea");
    if (mode === "new")
      html +=
        field("file", "Escolher imagem", "", "file") +
        '<canvas id="crop" class="crop-preview" width="600" height="400" hidden></canvas><label class="field">Recorte<select id="crop-ratio"><option value="original">Imagem inteira</option><option value="1">Quadrado · 1:1</option><option value="1.5">Paisagem · 3:2</option><option value="0.6666667">Retrato · 2:3</option></select></label><label class="field">Zoom<input type="range" id="crop-zoom" min="1" max="3" step="0.01" value="1"></label><label class="field">Posição horizontal<input type="range" id="crop-x" min="0" max="1" step="0.01" value="0.5"></label><label class="field">Posição vertical<input type="range" id="crop-y" min="0" max="1" step="0.01" value="0.5"></label><small class="muted">Apenas a imagem resultante será armazenada no .chp.</small>';
    else
      html += `<img class="crop-preview" src="${escapeHtml(node.source)}" alt="Imagem armazenada">`;
  }
  if (["chapters", "casting", "metadata"].includes(tab))
    html += imageLinks(node);
  $("fields").innerHTML = html;
  $("dialog-title").textContent =
    `${mode === "edit" ? "Editar" : mode === "child" ? "Adicionar filho ·" : "Adicionar"} ${labels[tab].toLowerCase()}`;
  $("form-error").textContent = "";
  cropImage = null;
  $("edit-form").dataset.changed = "false";
  $("editor-dialog").showModal();
  const firstField = $("fields").querySelector("input,textarea");
  firstField?.focus();
  if (tab === "chapters" && mode !== "edit") firstField?.select();
}
function cropDimensions() {
  const ratio =
    $("crop-ratio").value === "original"
      ? cropImage.width / cropImage.height
      : Number($("crop-ratio").value);
  const width =
    Math.min(cropImage.width, cropImage.height * ratio) /
    Number($("crop-zoom").value);
  const height = width / ratio;
  return {
    width,
    height,
    x: (cropImage.width - width) * Number($("crop-x").value),
    y: (cropImage.height - height) * Number($("crop-y").value),
  };
}
function drawCrop(exporting = false) {
  if (!cropImage) return;
  const { width, height, x, y } = cropDimensions(),
    canvas = exporting ? document.createElement("canvas") : $("crop");
  const scale = Math.min(1, (exporting ? 2400 : 600) / Math.max(width, height));
  canvas.width = Math.max(1, Math.round(width * scale));
  canvas.height = Math.max(1, Math.round(height * scale));
  const context = canvas.getContext("2d");
  context.fillStyle = "white";
  context.fillRect(0, 0, canvas.width, canvas.height);
  context.drawImage(
    cropImage,
    x,
    y,
    width,
    height,
    0,
    0,
    canvas.width,
    canvas.height,
  );
  canvas.hidden = false;
  return {
    source: canvas.toDataURL("image/jpeg", 0.92),
    width: canvas.width,
    height: canvas.height,
    mime_type: "image/jpeg",
  };
}
async function saveEditor(event) {
  event.preventDefault();
  if (busy) return;
  const context = editContext,
    form = new FormData($("edit-form")),
    node = context.node;
  try {
    for (const name of ["title", "name", "key", "value", "text", "description"])
      if (form.has(name)) node[name] = String(form.get(name)).trim();
    if (["chapters", "subtitles"].includes(tab)) {
      node.start = parseTime(form.get("start"), tab === "subtitles");
      node.end = parseTime(form.get("end"), tab === "subtitles");
      if (node.end < node.start)
        throw Error("O fim não pode ser anterior ao início.");
    }
    if (["chapters", "casting", "metadata"].includes(tab))
      node.images = form.getAll("images");
    if (tab === "images" && context.mode === "new") {
      if (!cropImage) throw Error("Escolha uma imagem válida.");
      Object.assign(node, drawCrop(true));
    }
    const found = flatten(context.data).find(
      ({ node: item }) => item.id === context.selected,
    );
    if (context.mode === "edit") found.siblings[found.index] = node;
    else if (context.mode === "child") {
      const children =
        tab === "chapters" ? found.node.subs : found.node.children;
      if (tab === "metadata") found.node.value = "";
      children.push(node);
    } else if (tab === "chapters" && found) found.siblings.push(node);
    else context.data.push(node);
    busy = true;
    $("submit").disabled = true;
    const next = await bridge.save_section(
      context.section,
      context.data,
      context.revision,
    );
    selected = node.id;
    accept(next);
    if (tab === "subtitles")
      selected = state.subtitles.find(
        (item) =>
          item.start === node.start &&
          item.end === node.end &&
          item.text === node.text,
      )?.id;
    $("editor-dialog").close();
    notify("Alterações salvas.");
  } catch (error) {
    // Reconstrói o rascunho para que uma nova tentativa não duplique registros.
    if (context) context.data = structuredClone(items(context.section));
    $("form-error").textContent = String(error.message || error);
  } finally {
    busy = false;
    $("submit").disabled = false;
    $("add").disabled = !state.name;
    render();
  }
}
async function removeItem() {
  const found = selection();
  if (
    !found ||
    busy ||
    !confirm(`Excluir “${title(found.node)}” e seus descendentes?`)
  )
    return;
  const data = structuredClone(items()),
    copy = flatten(data).find(({ node }) => node.id === selected);
  copy.siblings.splice(copy.index, 1);
  busy = true;
  render();
  try {
    accept(await bridge.save_section(tab, data, state.revision));
    selected = null;
    notify("Item excluído.");
  } catch (error) {
    notify(String(error.message || error), true);
  } finally {
    busy = false;
    render();
    $("add").disabled = !state.name;
  }
}
function seekTo(seconds) {
  if (Number.isFinite(video.duration))
    video.currentTime = Math.max(0, Math.min(video.duration, seconds));
}
async function togglePlay() {
  if (!state.name) return;
  try {
    if (video.paused) await video.play();
    else video.pause();
  } catch {
    showMediaError();
  }
}
function showMediaError() {
  $("media-error").textContent =
    "Este vídeo não pôde ser reproduzido pelo motor web. O suporte depende do contêiner e dos codecs instalados. Você pode abri-lo pela interface clássica com VLC; o arquivo original não foi alterado.";
  $("media-error").hidden = false;
}
function updatePlayback() {
  $("current").textContent = time(video.currentTime, true);
  $("duration").textContent = time(video.duration, true);
  $("seek").value =
    Number.isFinite(video.duration) && video.duration
      ? (video.currentTime / video.duration) * 1000
      : 0;
  $("play").textContent = video.paused ? "▶" : "Ⅱ";
  $("play").setAttribute("aria-label", video.paused ? "Reproduzir" : "Pausar");
  $("playback-state").textContent = !state.name
    ? "Sem vídeo"
    : video.ended
      ? "Finalizado"
      : video.paused
        ? "Pausado"
        : "Reproduzindo";
  const ms = video.currentTime * 1000;
  $("subtitle").textContent = state.subtitles
    .filter((node) => ms >= node.start && ms < node.end)
    .map((node) => node.text)
    .join("\n");
}
function closeEditor() {
  if (busy) return;
  const changed = editContext && $("edit-form").dataset.changed === "true";
  if (changed && !confirm("Descartar as alterações desta edição?")) return;
  $("editor-dialog").close();
}
$("open").onclick = $("open-empty").onclick = openVideo;
document.querySelectorAll("[data-tab]").forEach((button) => {
  button.onclick = () => {
    tab = button.dataset.tab;
    selected = null;
    $("search").value = "";
    render();
  };
});
$("search").oninput = render;
$("records").onclick = (event) => {
  const row = event.target.closest("[data-id]");
  if (row) {
    selectRecord(row.dataset.id);
    const menu = event.target.closest(".record-menu");
    if (menu) showActions(menu);
  }
};
$("records").ondblclick = (event) => {
  const target = event.target.closest(".record-select");
  if (target) {
    selectRecord(target.closest("[data-id]").dataset.id);
    showEditor("edit");
  }
};
$("records").onkeydown = (event) => {
  if (
    ["Enter", " "].includes(event.key) &&
    event.target.matches(".record-select")
  ) {
    const row = event.target.closest("[data-id]");
    if (row) {
      event.preventDefault();
      selectRecord(row.dataset.id);
      showEditor("edit");
    }
  }
};
$("add-options").onclick = () => showActions($("add-options"), true);
$("action-menu").onclick = (event) => {
  const button = event.target.closest("[data-action]");
  if (!button || button.disabled) return;
  const action = button.dataset.action;
  closeActions(true);
  if (action === "remove") removeItem();
  else showEditor(action);
};
$("action-menu").onkeydown = (event) => {
  const buttons = [
    ...$("action-menu").querySelectorAll("button:not(:disabled)"),
  ];
  const index = buttons.indexOf(document.activeElement);
  if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
    event.preventDefault();
    const target =
      event.key === "Home"
        ? 0
        : event.key === "End"
          ? buttons.length - 1
          : (index + (event.key === "ArrowDown" ? 1 : -1) + buttons.length) %
            buttons.length;
    buttons[target]?.focus();
  }
  if (event.key === "Escape") {
    event.preventDefault();
    closeActions(true);
  }
};
$("action-menu").addEventListener("toggle", () => {
  if (!$("action-menu").matches(":popover-open")) {
    menuTrigger?.setAttribute("aria-expanded", "false");
    menuTrigger = null;
  }
});
window.addEventListener("resize", () => closeActions());
$("records").addEventListener("scroll", () => closeActions());
document
  .querySelector(".workspace")
  .addEventListener("scroll", () => closeActions());
$("add").onclick = () => {
  $("edit-form").dataset.changed = "false";
  showEditor();
};
$("edit").onclick = () => {
  $("edit-form").dataset.changed = "false";
  showEditor("edit");
};
$("child").onclick = () => {
  $("edit-form").dataset.changed = "false";
  showEditor("child");
};
$("remove").onclick = removeItem;
$("jump").onclick = () => {
  const chosen = selection();
  if (chosen) seekTo(chosen.node.start / (tab === "subtitles" ? 1000 : 1));
};
$("chapter-track").onclick = (event) => {
  const button = event.target.closest("[data-time]");
  if (button) seekTo(Number(button.dataset.time));
};
$("edit-form").onsubmit = saveEditor;
$("edit-form").oninput = (event) => {
  if (event.target.matches("[data-time-mask]")) applyTimeMask(event.target);
  markDirty();
  if (cropImage) drawCrop();
};
$("fields").onclick = (event) => {
  const name = event.target.dataset.capture;
  if (name) {
    const input = $("edit-form").elements[name];
    input.value =
      tab === "chapters"
        ? chapterTime(video.currentTime)
        : time(video.currentTime, true);
    input.setCustomValidity("");
    markDirty();
  }
};
$("fields").addEventListener("focusin", (event) => {
  if (event.target.matches("[data-time-mask]")) event.target.select();
});
$("fields").addEventListener("paste", (event) => {
  const input = event.target;
  if (!input.matches("[data-time-mask]")) return;
  const pasted = event.clipboardData.getData("text").trim();
  if (!pasted.includes(":")) return;
  event.preventDefault();
  try {
    input.value = chapterTime(parseTime(pasted));
    input.setCustomValidity("");
    input.setSelectionRange(input.value.length, input.value.length);
    markDirty();
  } catch (error) {
    $("form-error").textContent = String(error.message || error);
  }
});
async function loadImage(file) {
  if (!file) return;
  cropImage = null;
  $("crop").hidden = true;
  if (file.size > 20 * 1024 * 1024) {
    $("form-error").textContent = "A imagem deve ter no máximo 20 MB.";
    return;
  }
  const url = URL.createObjectURL(file),
    image = new Image();
  try {
    image.src = url;
    await image.decode();
    cropImage = image;
    drawCrop();
    $("form-error").textContent = "";
  } catch {
    cropImage = null;
    $("form-error").textContent = "Não foi possível ler a imagem.";
  } finally {
    URL.revokeObjectURL(url);
  }
}
$("fields").onchange = (event) => {
  if (event.target.type === "file") loadImage(event.target.files[0]);
  else if (cropImage) drawCrop();
};
document.addEventListener("paste", (event) => {
  if (
    !$("editor-dialog").open ||
    tab !== "images" ||
    editContext?.mode !== "new"
  )
    return;
  const image = [...event.clipboardData.items].find((item) =>
    item.type.startsWith("image/"),
  );
  if (image) {
    event.preventDefault();
    markDirty();
    loadImage(image.getAsFile());
  }
});
$("close-dialog").onclick = $("cancel-dialog").onclick = closeEditor;
$("editor-dialog").addEventListener("close", () => syncEditState(false));
$("editor-dialog").oncancel = (event) => {
  event.preventDefault();
  closeEditor();
};
$("help").onclick = () => $("help-dialog").showModal();
$("close-help").onclick = () => $("help-dialog").close();
$("play").onclick = togglePlay;
video.onclick = togglePlay;
$("back").onclick = () => seekTo(video.currentTime - settings.small_jump);
$("forward").onclick = () => seekTo(video.currentTime + settings.small_jump);
$("seek").oninput = () =>
  seekTo((Number($("seek").value) / 1000) * video.duration);
$("seek").onwheel = (event) => {
  event.preventDefault();
  seekTo(video.currentTime + (event.deltaY < 0 ? 1 : -1) * settings.large_jump);
};
$("volume").oninput = () => {
  video.volume = Number($("volume").value) / 100;
  video.muted = false;
  $("mute").textContent = "♪";
};
$("mute").onclick = () => {
  video.muted = !video.muted;
  $("mute").textContent = video.muted ? "×" : "♪";
};
$("fullscreen").onclick = async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await $("stage").requestFullscreen();
  } catch {
    notify("Tela cheia indisponível neste motor web.", true);
  }
};
document.addEventListener("fullscreenchange", async () => {
  try {
    await bridge?.set_fullscreen(!!document.fullscreenElement);
  } catch {
    notify("Não foi possível ajustar a janela nativa para tela cheia.", true);
  }
});
function animatePlayback() {
  updatePlayback();
  if (!video.paused && !video.ended)
    playbackFrame = requestAnimationFrame(animatePlayback);
}
video.addEventListener("play", () => {
  cancelAnimationFrame(playbackFrame);
  animatePlayback();
});
video.addEventListener("pause", () => cancelAnimationFrame(playbackFrame));
for (const event of ["timeupdate", "play", "pause", "ended", "seeked"])
  video.addEventListener(event, updatePlayback);
video.addEventListener("loadedmetadata", () => {
  updatePlayback();
  renderTimeline();
});
video.addEventListener("error", showMediaError);
function matchesShortcut(event, shortcut) {
  const parts = shortcut.replace(/[<>]/g, "").split("-");
  const key = parts.pop();
  const map = {
    space: " ",
    Left: "ArrowLeft",
    Right: "ArrowRight",
    Return: "Enter",
    Escape: "Escape",
  };
  return (
    event.key.toLowerCase() === (map[key] || key).toLowerCase() &&
    event.shiftKey === parts.includes("Shift") &&
    event.ctrlKey === parts.includes("Control") &&
    event.altKey === parts.includes("Alt")
  );
}
document.addEventListener("keydown", (event) => {
  if (
    event.target.closest(".action-menu") ||
    event.target.matches("button,[role=button]")
  )
    return;
  if (
    event.target.closest("input,textarea,select,[contenteditable=true]") ||
    document.querySelector("dialog[open]")
  )
    return;
  const keys = settings.keys || {
    play_pause: "<space>",
    back_small: "<Left>",
    fwd_small: "<Right>",
    back_large: "<Shift-Left>",
    fwd_large: "<Shift-Right>",
  };
  const actions = {
    play_pause: togglePlay,
    back_small: () => seekTo(video.currentTime - settings.small_jump),
    fwd_small: () => seekTo(video.currentTime + settings.small_jump),
    back_large: () => seekTo(video.currentTime - settings.large_jump),
    fwd_large: () => seekTo(video.currentTime + settings.large_jump),
  };
  for (const [name, shortcut] of Object.entries(keys))
    if (actions[name] && matchesShortcut(event, shortcut)) {
      event.preventDefault();
      actions[name]();
      return;
    }
  if (event.key.toLowerCase() === "f") $("fullscreen").click();
  if (event.key === "?") $("help").click();
});
async function initialize() {
  bridge = window.pywebview?.api;
  if (!bridge) return;
  try {
    const initial = await bridge.get_state();
    settings = { ...settings, ...initial.settings };
    video.volume = settings.volume / 100;
    $("volume").value = settings.volume;
    $("back-label").textContent = $("forward-label").textContent =
      `${settings.small_jump}s`;
    const keys = settings.keys || {};
    $("key-play").textContent = keys.play_pause || "Espaço";
    $("key-short").textContent =
      `${keys.back_small || "←"} / ${keys.fwd_small || "→"}`;
    $("key-long").textContent =
      `${keys.back_large || "Shift + ←"} / ${keys.fwd_large || "Shift + →"}`;
    accept(initial, !!initial.name);
    if (initial.startup_error) notify(initial.startup_error, true);
  } catch (error) {
    notify(String(error.message || error), true);
  }
}
window.addEventListener("pywebviewready", initialize);
if (window.pywebview?.api) initialize();
render();
