/* مِداد — واجهة الاستوديو (Vanilla JS) */
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const S = {
  meta: null,
  project: null,
  job: null,
  poll: null,
  tab: "studio",
  built: null,
  validation: null,
  rev: 0,
  modalPage: null,
  saveTimer: null,
  validationTimer: null,
  autoRefresh: null,
};

const API = {
  async call(path, opts = {}) {
    const res = await fetch(path, {
      headers: opts.body instanceof FormData ? {} : { "Content-Type": "application/json" },
      ...opts,
    });
    if (!res.ok) {
      let msg = `خطأ ${res.status}`;
      try {
        const data = await res.json();
        msg = data.detail || msg;
      } catch (_) {}
      throw new Error(msg);
    }
    return res.json();
  },
  get: (p) => API.call(p),
  post: (p, body) => API.call(p, { method: "POST", body: body ? JSON.stringify(body) : undefined }),
  patch: (p, body) => API.call(p, { method: "PATCH", body: JSON.stringify(body) }),
  del: (p) => API.call(p, { method: "DELETE" }),
};

/* ------------------------------- helpers -------------------------------- */
function toast(msg, kind = "") {
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.textContent = msg;
  $("#toasts").appendChild(el);
  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transition = "opacity .3s";
    setTimeout(() => el.remove(), 300);
  }, 3600);
}

function fmt(n, d = 2) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return "—";
  return Number(n).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d });
}

function getPath(obj, path) {
  return path.split(".").reduce((acc, k) => (acc == null ? acc : acc[k]), obj);
}

function setPath(obj, path, value) {
  const parts = path.split(".");
  let cur = obj;
  parts.forEach((k, i) => {
    if (i === parts.length - 1) cur[k] = value;
    else {
      cur[k] = cur[k] ?? {};
      cur = cur[k];
    }
  });
  return obj;
}

function setSaveState(text, cls = "") {
  const el = $("#saveState");
  el.textContent = text;
  el.className = `save-state ${cls}`;
}

/* --------------------------------- boot --------------------------------- */
async function boot() {
  try {
    S.meta = await API.get("/api/meta");
  } catch (e) {
    toast("تعذّر تحميل بيانات التطبيق", "err");
    return;
  }
  fillSelects();
  buildThemeChips();
  renderFacts();
  bindUI();

  renderDownloads();
  const projects = await API.get("/api/projects");
  renderProjectSelect(projects);
  const preferred = S.meta.settings.last_project;
  const pid = (projects.find((p) => p.id === preferred) || projects[0])?.id;
  if (pid) await loadProject(pid);
  else await createProject({});
}

async function renderDownloads() {
  try {
    const data = await API.get("/api/downloads");
    if (!data.items.length) return;
    const isWin = /Windows/i.test(navigator.userAgent);
    const offline = data.items.find((i) => i.name.includes("win64"));
    const universal = data.items.find((i) => !i.name.includes("win64"));
    const pick = (isWin && offline) || universal || data.items[0];
    const link = $("#downloadApp");
    link.href = pick.url;
    link.setAttribute("download", pick.name);
    link.textContent = `⬇ تحميل البرنامج (${(pick.size / 1048576).toFixed(1)} MB)`;
    link.title = `حزمة جاهزة: ${pick.name}`;
    link.hidden = false;
  } catch (_) {}
}

function fillSelects() {
  const m = S.meta;
  $("#trimSelect").innerHTML = Object.entries(m.trims)
    .map(([k, v]) => `<option value="${k}">${v.label} — ${v.note}</option>`)
    .join("");
  $("#paperSelect").innerHTML = Object.entries(m.papers)
    .map(([k, v]) => `<option value="${k}">${v.label}</option>`)
    .join("");
  $("#styleSelect").innerHTML = Object.entries(m.styles)
    .map(([k, v]) => `<option value="${k}">${v.label}</option>`)
    .join("");
  $("#audienceSelect").innerHTML = Object.entries(m.audiences)
    .map(([k, v]) => `<option value="${k}">${v}</option>`)
    .join("");
  $("#providerSelect").innerHTML = Object.entries(m.providers)
    .map(([k, v]) => `<option value="${k}">${v.label}</option>`)
    .join("");
}

function buildThemeChips() {
  const icons = {
    animals: "🐾", dinosaurs: "🦕", unicorns: "🦄", ocean: "🐠", space: "🚀",
    mandala: "🌀", flowers: "🌷", geometric: "◈", vehicles: "🚚", festive: "🎉",
  };
  $("#themeChips").innerHTML = Object.entries(S.meta.themes)
    .map(([k, v]) => `<button class="chip" data-theme="${k}"><span class="ico">${icons[k] || "✎"}</span>${v.label}</button>`)
    .join("");
}

function renderProjectSelect(projects) {
  const sel = $("#projectSelect");
  sel.innerHTML = projects
    .map((p) => `<option value="${p.id}">${p.title || "بدون عنوان"} · ${p.pages} رسمة</option>`)
    .join("") || `<option value="">لا يوجد مشروع</option>`;
  if (S.project) sel.value = S.project.id;
}

/* ------------------------------- project -------------------------------- */
async function loadProject(pid) {
  S.project = await API.get(`/api/projects/${pid}`);
  S.validation = null;
  if (S.project._meta?.has_output) {
    S.built = { files: S.project._meta.outputs, validation: null };
    S.builtAt = Date.now();
  } else {
    S.built = null;
  }
  fillProjectFields();
  renderAll();
  refreshValidation();
  refreshProjectList();
  if (S.project.pages.some((p) => ["queued", "generating"].includes(p.status))) startAutoRefresh();
}

async function refreshProjectList() {
  try {
    const projects = await API.get("/api/projects");
    renderProjectSelect(projects);
    if (S.project) $("#projectSelect").value = S.project.id;
  } catch (_) {}
}

async function createProject(extra = {}) {
  const project = await API.post("/api/projects", extra);
  renderDownloads();
  const projects = await API.get("/api/projects");
  renderProjectSelect(projects);
  await loadProject(project.id);
  toast("تم إنشاء مشروع جديد", "ok");
}

function fillProjectFields() {
  const p = S.project;
  $$("[data-field]").forEach((input) => {
    const path = input.dataset.field;
    let val = getPath(p, path);
    if (input.dataset.type === "list") val = (val || []).join("، ");
    if (input.type === "checkbox") input.checked = Boolean(val);
    else if (val !== undefined && val !== null) input.value = val;
  });
  $("#trimSelect").value = p.trim;
  $("#paperSelect").value = p.paper;
  $("#styleSelect").value = p.style;
  $("#audienceSelect").value = p.audience;
  $("#providerSelect").value = p.provider;
  $("#themeChips").querySelectorAll(".chip").forEach((c) =>
    c.classList.toggle("active", c.dataset.theme === p.theme)
  );
  $("#genCaptions").checked = Boolean(p.captions);
  document.title = `${p.title || "كتاب تلوين"} — مِداد`;
  renderCoverPageSelect();
  renderRoyalty();
}

function renderCoverPageSelect() {
  const sel = $("#coverPageSelect");
  const pages = S.project.pages.filter((p) => p.status === "ready");
  const current = S.project.cover?.cover_page_id || "";
  sel.innerHTML =
    `<option value="">تلقائي (أول رسمة)</option>` +
    pages.map((pg, i) => `<option value="${pg.id}">صفحة ${i + 1}${pg.caption ? " — " + pg.caption : ""}</option>`).join("");
  sel.value = pages.some((p) => p.id === current) ? current : "";
}

function renderAll() {
  renderSpecs();
  renderGallery();
  renderPageCount();
  renderCoverSpecs();
  renderRoyalty();
  renderProjectSelectOptions();
}

function renderProjectSelectOptions() {
  const opt = $(`#projectSelect option[value="${S.project.id}"]`);
  if (opt) opt.textContent = `${S.project.title || "بدون عنوان"} · ${S.project._meta.art_count} رسمة`;
  $("#projectSelect").value = S.project.id;
}

function renderSpecs() {
  const m = S.project._meta;
  const margin = m.margins;
  const items = [
    ["عدد صفحات الكتاب", `${m.page_count} صفحة`, true],
    ["الحد الأدنى للهامش الداخلي", `${fmt(m.gutter_min, 3)}"`, false],
    ["الهامش المستخدم", `${fmt(margin.inside, 2)}" داخلي · ${fmt(margin.outside, 2)}" خارجي`, false],
    ["مقاس صفحة الداخل", `${fmt(margin.page_w, 3)}" × ${fmt(margin.page_h, 3)}"`, true],
    ["عرض الكعب", `${fmt(m.spine, 4)}"`, false],
    ["مقاس الغلاف الكامل", `${fmt(m.cover.width, 3)}" × ${fmt(m.cover.height, 3)}"`, false],
  ];
  $("#specGrid").innerHTML = items
    .map(([label, value, wide]) => `<div class="spec-item ${wide ? "wide" : ""}"><span>${label}</span><strong>${value}</strong></div>`)
    .join("");
}

function renderCoverSpecs() {
  const m = S.project._meta;
  $("#coverSpecs").innerHTML = `
    <div class="spec-item wide"><span>الغلاف الكامل (مع النزف)</span><strong>${fmt(m.cover.width, 3)}" × ${fmt(m.cover.height, 3)}"</strong></div>
    <div class="spec-item"><span>الكعب</span><strong>${fmt(m.spine, 4)}"</strong></div>
    <div class="spec-item"><span>نص الكعب</span><strong>${m.page_count >= 80 ? "مسموح" : "غير مسموح (<80 ص)"}</strong></div>
    <div class="spec-item wide"><span>منطقة الباركود</span><strong>2" × 1.2" أسفل يمين الظهر</strong></div>`;
}

function renderRoyalty() {
  const p = S.project;
  const price = Number(p.price || 0);
  const cost = Number(p.printing_cost || 0);
  const royalty = Math.max(0, price * 0.6 - cost);
  $("#royaltyHint").innerHTML = `العمولة التقديرية لكل نسخة: <b>$${fmt(royalty)}</b> (60% × ${fmt(price)} − ${fmt(cost)} تكلفة طباعة). تُحسب نهائيًا داخل KDP.`;
}

function renderPageCount() {
  const m = S.project._meta;
  const pages = m.page_count;
  const tag = $("#pageCountTag");
  const min = S.meta.kdp.min_pages;
  if (pages < min) {
    tag.textContent = `${pages} / ${min} صفحة — أضف ${min - pages} صفحة للحد الأدنى`;
    tag.style.background = "var(--warn-soft)";
    tag.style.color = "var(--warn)";
  } else {
    tag.textContent = `${pages} صفحة · ${S.project.single_sided ? "وجه واحد" : "وجهان"} · جاهز`;
    tag.style.background = "";
    tag.style.color = "";
  }
  $("#artCount").textContent = m.art_count;
}

/* -------------------------------- gallery ------------------------------- */
function renderGallery() {
  const grid = $("#gallery");
  const pages = S.project.pages;
  $("#galleryCount").textContent = pages.length ? `· ${pages.length}` : "";
  $("#galleryEmpty").hidden = pages.length > 0;
  const coverId = S.project.cover?.cover_page_id;

  const tr = S.meta.trims[S.project.trim] || { w: 8.5, h: 11 };
  grid.innerHTML = pages
    .map((pg, i) => {
      const ready = pg.status === "ready";
      const thumb = ready
        ? `<img loading="lazy" src="/api/projects/${S.project.id}/pages/${pg.id}/thumb?v=${S.rev}" alt="صفحة ${i + 1}" />`
        : `<div class="skeleton"></div>`;
      const statusTag =
        pg.status === "error"
          ? `<span class="tag err" title="${escapeHtml(pg.error || "")}">فشل</span>`
          : pg.status === "ready"
          ? `<span class="tag ok">جاهزة</span>`
          : `<span class="tag work">قيد التوليد…</span>`;
      const tags = `<div class="page-tags">${statusTag}${
        coverId === pg.id ? `<span class="tag ok">غلاف</span>` : ""
      }${pg.provider_label ? `<span class="tag">${escapeHtml(pg.provider_label)}</span>` : ""}</div>`;
      return `
      <article class="page-card" data-id="${pg.id}">
        <div class="page-thumb" data-open style="aspect-ratio:${tr.w}/${tr.h}">
          ${thumb}
          <span class="page-num">${i + 1}</span>
          <div class="page-actions">
            <button class="mini-btn" data-act="cover" title="تعيين كغلاف">★</button>
            <button class="mini-btn" data-act="regen" title="إعادة التوليد">↻</button>
            <button class="mini-btn" data-act="left" title="تحريك لليمين">›</button>
            <button class="mini-btn" data-act="right" title="تحريك لليسار">‹</button>
            <button class="mini-btn danger" data-act="delete" title="حذف">✕</button>
          </div>
        </div>
        <div class="page-meta">
          <input data-caption value="${escapeHtml(pg.caption || "")}" placeholder="أضف تعليقًا…" />
          ${tags}
        </div>
      </article>`;
    })
    .join("");
}

function escapeHtml(str) {
  return String(str || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/* ------------------------------- validation ----------------------------- */
async function refreshValidation() {
  if (!S.project) return;
  try {
    const v = await API.get(`/api/projects/${S.project.id}/validate`);
    S.validation = v;
    renderValidation(v);
    renderScorePill(v);
  } catch (e) {
    /* صامت */
  }
}

function renderScorePill(v) {
  const pill = $("#scorePill");
  $("#scoreText").textContent = `${v.score}/100`;
  pill.className = `score-pill ${v.status === "fail" ? "fail" : v.status === "warn" ? "warn" : ""}`;
}

function renderValidation(v) {
  const ring = $("#scoreRing");
  ring.style.setProperty("--p", v.score);
  ring.style.setProperty("--c", v.status === "fail" ? "var(--err)" : v.status === "warn" ? "var(--warn)" : "var(--ok)");
  $("#scoreNumber").textContent = v.score;
  $("#scoreTitle").textContent =
    v.status === "fail" ? "توجد مشكلات تمنع النشر" : v.status === "warn" ? "جاهز مع تنبيهات" : "مطابق لمعايير KDP";
  $("#scoreSub").textContent = `${v.checks.length} فحصًا · ${v.fails} مشكلة حرجة · ${v.warns} تنبيه · ${v.pages} صفحة`;
  const badge = $("#checkCount");
  const issues = v.fails + v.warns;
  badge.textContent = issues;
  badge.style.display = issues ? "" : "none";

  const icons = { pass: "✓", warn: "!", fail: "✕" };
  const labels = { pass: "سليم", warn: "تنبيه", fail: "مشكلة" };
  $("#checkList").innerHTML = v.checks
    .map(
      (c) => `<div class="check-item ${c.status}">
        <div class="badge">${icons[c.status]}</div>
        <div>
          <h4>${escapeHtml(c.label)}</h4>
          <p>${escapeHtml(c.detail || "")}</p>
          ${c.status !== "pass" && c.fix ? `<div class="fix">↳ ${escapeHtml(c.fix)}</div>` : ""}
        </div>
        <span class="status-text">${labels[c.status]}</span>
      </div>`
    )
    .join("");
}

function renderFacts() {
  const k = S.meta.kdp;
  const gutters = k.gutter_table.map(([a, b, v]) => `${a}–${b}: ${v}"`).join(" · ");
  const facts = [
    ["الحد الأدنى للصفحات", `${k.min_pages} صفحة (زوجي)`],
    ["الدقة المطلوبة", `${k.dpi} DPI`],
    ["النزف", `${k.bleed}" من الخارج والأعلى والأسفل`],
    ["الهوامش الخارجية", `${k.min_outside_no_bleed}" بدون نزف · ${k.min_outside_bleed}" مع النزف`],
    ["الهوامش الداخلية (gutter)", gutters],
    ["الباركود", `${k.barcode[0]}" × ${k.barcode[1]}" أسفل يمين الظهر`],
    ["نص الكعب", `${k.spine_text_pages}+ صفحة`],
    ["مقاس الغلاف", `(2 × عرض القطع) + الكعب + 0.25"`],
  ];
  $("#kdpFacts").innerHTML = facts
    .map(([label, value]) => `<div class="fact"><span>${label}</span><strong>${value}</strong></div>`)
    .join("");
}

/* ------------------------------- generator ------------------------------ */
function providerNote() {
  const provider = $("#providerSelect").value;
  const has = S.meta.settings.has_keys || {};
  const notes = {
    procedural: "المحرّك المحلي يرسم صفحات ماندالا وزهور وأشكالًا هندسية داخل جهازك — بدون إنترنت أو مفاتيح، وجودة طباعة كاملة 300 DPI.",
    openai: has.openai
      ? "سيُستخدم مفتاح OpenAI المحفوظ لتوليد رسومات مخصّصة (gpt-image-1)."
      : "أضف مفتاح OpenAI من زر «مفاتيح الذكاء الاصطناعي» في الأعلى لتوليد رسومات مخصّصة.",
    stability: has.stability ? "سيُستخدم مفتاح Stability AI المحفوظ." : "أضف مفتاح Stability AI أولًا من زر المفاتيح.",
    replicate: has.replicate ? "سيُستخدم مفتاح Replicate (FLUX) المحفوظ." : "أضف مفتاح Replicate أولًا من زر المفاتيح.",
    local_sd: "يتصل بخادم Stable Diffusion المحلي على http://127.0.0.1:7860 (شغّل A1111 مع --api). كل شيء يبقى على جهازك.",
  };
  $("#providerNote").innerHTML = notes[provider] || "";
}

async function generate() {
  const provider = $("#providerSelect").value;
  const payload = {
    count: Math.max(1, Math.min(40, Number($("#genCount").value) || 6)),
    theme: S.project.theme || "flowers",
    subject: $("#subjectInput").value.trim(),
    style: $("#styleSelect").value,
    audience: $("#audienceSelect").value,
    provider,
    with_captions: $("#genCaptions").checked,
    caption_prefix: "",
    thickness: S.project.thickness ?? 2,
    mode: "auto",
  };
  const btn = $("#generateBtn");
  btn.disabled = true;
  try {
    const job = await API.post(`/api/projects/${S.project.id}/generate`, payload);
    S.job = job;
    $("#jobBox").hidden = false;
    pollJob(job.id);
  } catch (e) {
    toast(e.message, "err");
  } finally {
    btn.disabled = false;
  }
}

function pollJob(jobId) {
  clearInterval(S.poll);
  const tick = async () => {
    let job;
    try {
      job = await API.get(`/api/jobs/${jobId}`);
    } catch (_) {
      clearInterval(S.poll);
      return;
    }
    S.job = job;
    const pct = job.total ? Math.round((job.done / job.total) * 100) : 0;
    $("#jobMessage").textContent = job.message || "جارٍ التوليد…";
    $("#jobCounter").textContent = `${job.done} / ${job.total}`;
    $("#jobBar").style.width = `${pct}%`;
    const errs = job.items.filter((i) => i.status === "error");
    $("#jobNote").textContent = errs.length ? errs[errs.length - 1].error : "";
    if (job.done > 0 && job.done % 2 === 0) await softRefresh();
    if (["done", "error", "cancelled"].includes(job.status)) {
      clearInterval(S.poll);
      await loadProject(S.project.id);
      refreshValidation();
      if (S.wantCoverOptions && job.status === "done") {
        S.wantCoverOptions = false;
        setTimeout(() => openCoverOptions(S.project.id), 600);
      }
      if (job.status === "error") toast(job.message, "err");
      else toast("تم توليد الصفحات بنجاح", "ok");
      setTimeout(() => ($("#jobBox").hidden = true), 4000);
    }
  };
  tick();
  S.poll = setInterval(tick, 1100);
}

async function softRefresh() {
  try {
    S.project = await API.get(`/api/projects/${S.project.id}`);
    S.rev += 1;
    renderGallery();
    renderSpecs();
    renderPageCount();
    renderCoverPageSelect();
  } catch (_) {}
}

function startAutoRefresh() {
  clearInterval(S.autoRefresh);
  S.autoRefresh = setInterval(async () => {
    if (!S.project) return;
    await softRefresh();
    const busy = S.project.pages.some((p) => ["queued", "generating"].includes(p.status));
    if (!busy) {
      clearInterval(S.autoRefresh);
      refreshValidation();
    }
  }, 2600);
}

/* -------------------------------- actions ------------------------------- */
async function patchProject(patch, { silent = false } = {}) {
  if (!S.project) return;
  setSaveState("جارٍ الحفظ…", "saving");
  try {
    S.project = await API.patch(`/api/projects/${S.project.id}`, patch);
    setSaveState("محفوظ");
    renderSpecs();
    renderPageCount();
    renderCoverSpecs();
    renderRoyalty();
    renderProjectSelectOptions();
    document.title = `${S.project.title || "كتاب تلوين"} — مِداد`;
    clearTimeout(S.validationTimer);
    S.validationTimer = setTimeout(refreshValidation, 900);
  } catch (e) {
    setSaveState("تعذّر الحفظ", "error");
    if (!silent) toast(e.message, "err");
  }
}

function debounceProjectSave(path, value) {
  clearTimeout(S.saveTimer);
  setSaveState("جارٍ الحفظ…", "saving");
  S.saveTimer = setTimeout(() => {
    const patch = {};
    setPath(patch, path, value);
    patchProject(patch, { silent: true });
  }, 500);
}

async function reorderPage(id, dir) {
  const pages = S.project.pages;
  const idx = pages.findIndex((p) => p.id === id);
  const target = dir === "left" ? idx - 1 : idx + 1;
  if (idx < 0 || target < 0 || target >= pages.length) return;
  const order = pages.map((p) => p.id);
  [order[idx], order[target]] = [order[target], order[idx]];
  try {
    S.project = await API.post(`/api/projects/${S.project.id}/pages/reorder`, { order });
    renderGallery();
    refreshValidation();
  } catch (e) {
    toast(e.message, "err");
  }
}

async function pageAction(id, action, card) {
  const pid = S.project.id;
  if (action === "delete") {
    if (!confirm("حذف هذه الصفحة؟")) return;
    try {
      S.project = await API.del(`/api/projects/${pid}/pages/${id}`);
      renderGallery();
      renderSpecs();
      renderPageCount();
      renderCoverPageSelect();
      refreshValidation();
      toast("تم حذف الصفحة");
    } catch (e) { toast(e.message, "err"); }
    return;
  }
  if (action === "cover") {
    await patchProject({ cover: { ...S.project.cover, cover_page_id: id } });
    renderGallery();
    toast("تم تعيين الرسمة كغلاف", "ok");
    return;
  }
  if (action === "left" || action === "right") {
    await reorderPage(id, action);
    return;
  }
  if (action === "regen") {
    const pg = S.project.pages.find((p) => p.id === id);
    if (pg) pg.status = "generating";
    renderGallery();
    toast("جارٍ إعادة التوليد…");
    try {
      S.project = await API.post(`/api/projects/${pid}/pages/${id}/regenerate`);
      S.rev += 1;
      renderGallery();
      refreshValidation();
      toast("تمت إعادة التوليد", "ok");
    } catch (e) {
      toast(e.message, "err");
      await softRefresh();
    }
  }
}

/* --------------------------------- modal -------------------------------- */
function openPageModal(id) {
  const pg = S.project.pages.find((p) => p.id === id);
  if (!pg) return;
  S.modalPage = pg;
  const idx = S.project.pages.indexOf(pg) + 1;
  $("#modalTitle").textContent = `الصفحة ${idx}`;
  $("#modalImage").src = `/api/projects/${S.project.id}/pages/${id}/full?v=${S.rev}`;
  $("#modalCaption").value = pg.caption || "";
  const thick = pg.settings?.thickness ?? 2;
  const thresh = pg.settings?.threshold ?? 150;
  $("#modalThickness").value = thick;
  $("#modalThickness").min = -1;
  $("#modalThreshold").value = thresh;
  $("#modalMode").value = pg.settings?.mode || "auto";
  $("#thickVal").textContent = thick;
  $("#threshVal").textContent = thresh;
  $("#pageModal").hidden = false;
}

function closeModals() {
  $$(".modal").forEach((m) => (m.hidden = true));
}

async function applyPageSettings() {
  const pg = S.modalPage;
  if (!pg) return;
  const payload = {
    caption: $("#modalCaption").value,
    settings: {
      thickness: Number($("#modalThickness").value),
      threshold: Number($("#modalThreshold").value),
      mode: $("#modalMode").value,
    },
  };
  try {
    await API.patch(`/api/projects/${S.project.id}/pages/${pg.id}`, payload);
    await API.post(`/api/projects/${S.project.id}/pages/${pg.id}/reprocess`, payload);
    S.rev += 1;
    await softRefresh();
    $("#modalImage").src = `/api/projects/${S.project.id}/pages/${pg.id}/full?v=${S.rev}`;
    toast("تم تحديث الصفحة", "ok");
    refreshValidation();
  } catch (e) {
    toast(e.message, "err");
  }
}

/* --------------------------------- build -------------------------------- */
async function buildBook() {
  if (!S.project._meta.art_count) {
    toast("أضف رسمة واحدة على الأقل قبل التصدير", "err");
    return;
  }
  const modal = $("#buildModal");
  modal.hidden = false;
  $("#buildResult").hidden = true;
  $("#buildTitle").textContent = "جارٍ تجهيز الملفات…";
  const steps = $$("#buildSteps li");
  steps.forEach((s) => s.classList.remove("done"));
  let step = 0;
  const stepper = setInterval(() => {
    if (step < steps.length) steps[step++].classList.add("done");
  }, 1400);

  try {
    const result = await API.post(`/api/projects/${S.project.id}/build`);
    clearInterval(stepper);
    steps.forEach((s) => s.classList.add("done"));
    S.built = result;
    S.builtAt = Date.now();
    $("#buildTitle").textContent = "الملفات جاهزة للنشر";
    renderBuildResult(result);
    renderPreview(true);
    renderValidation(result.validation);
    renderScorePill(result.validation);
    toast("تم إنشاء الحزمة الكاملة", "ok");
  } catch (e) {
    clearInterval(stepper);
    $("#buildTitle").textContent = "تعذّر التصدير";
    $("#buildResult").hidden = false;
    $("#buildResult").innerHTML = `<div class="result-row" style="color:var(--err)">${escapeHtml(e.message)}</div>`;
  }
}

function renderBuildResult(result) {
  const files = [
    ["interior.pdf", "ملف الداخل (300 DPI)", result.files.interior],
    ["cover.pdf", "الغلاف الكامل مع النزف", result.files.cover],
    ["cover-proof.pdf", "غلاف الإثبات بالخطوط", result.files.cover_proof],
    ["metadata.txt", "بيانات النشر", result.files.metadata],
    ["kdp-checklist.md", "قائمة التحقق", result.files.checklist],
  ];
  const size = (n) => (n > 1048576 ? `${fmt(n / 1048576, 2)} MB` : `${fmt(n / 1024, 0)} KB`);
  const rows = files
    .map(
      ([name, label, href]) =>
        `<div class="result-row"><span>${label}<br><small class="muted">${name}</small></span><a href="${href}" target="_blank">فتح</a></div>`
    )
    .join("");
  const zip = `<a class="btn primary" style="width:100%" href="${result.files.zip}" download="${result.zip_name}">تحميل الحزمة الكاملة (ZIP)</a>`;
  $("#buildResult").hidden = false;
  $("#buildResult").innerHTML = rows + zip +
    `<p class="hint">درجة المطابقة: <b>${result.validation.score}/100</b> — ${result.validation.fails} مشكلة حرجة، ${result.validation.warns} تنبيه.</p>`;
}

/* -------------------------------- preview ------------------------------- */
function renderPreview(force = false) {
  if (!S.built) {
    $("#coverStage").innerHTML = `<div class="placeholder">لم يُبنَ الغلاف بعد — اضغط «تصدير ملفات KDP» لإنشاء الغلاف ومعاينته.</div>`;
    return;
  }
  const v = S.built.validation;
  const m = S.project._meta;
  const pid = S.project.id;
  const stamp = S.builtAt || Date.now();
  $("#coverDims").textContent = `${fmt(v?.cover?.width ?? m.cover.width, 3)}" × ${fmt(v?.cover?.height ?? m.cover.height, 3)}" · كعب ${fmt(m.spine, 3)}"`;
  $("#interiorDims").textContent = `${v?.pages ?? m.page_count} صفحة · ${fmt(m.margins.page_w, 2)}" × ${fmt(m.margins.page_h, 2)}"`;
  $("#coverStage").innerHTML = `<img src="/api/projects/${pid}/file/preview-cover.png?t=${stamp}" alt="معاينة الغلاف" />`;
  const pages = [0, 4, 6, 8]
    .map((i) => `<img src="/api/projects/${pid}/file/preview-page-${i}.png?t=${stamp}" onerror="this.remove()" alt="صفحة ${i + 1}" />`)
    .join("");
  $("#pagesStrip").innerHTML = pages || `<div class="placeholder">لا توجد معاينة.</div>`;
  const setLink = (id, href, show) => {
    const a = $(id);
    a.href = href;
    a.hidden = !show;
  };
  setLink("#coverOpen", S.built.files.cover, true);
  setLink("#proofOpen", S.built.files.cover_proof, true);
  setLink("#interiorOpen", S.built.files.interior, true);
  setLink("#metaOpen", S.built.files.metadata, true);
}



/* ======================== معالج إنشاء الكتاب ========================= */
const WIZ = { step: 1, plan: null, palette: null, planning: false, busy: false };

const WIZ_IDEAS = [
  { title: "عالم الديناصورات الصغيرة", idea: "كتاب تلوين للأطفال من 4 إلى 8 سنوات عن ديناصورات لطيفة في مواقف مضحكة، بخطوط سميكة وسهلة التلوين" },
  { title: "حديقة الحيوانات المرحة", idea: "حيوانات لطيفة (أسد، فيل، باندا، أرنب) في مشاهد بسيطة جدًا للأطفال من 3 إلى 6 سنوات" },
  { title: "أعماق البحر", idea: "كائنات البحر والسلاحف والأسماك والشعاب المرجانية للأطفال من 6 إلى 10 سنوات" },
  { title: "رحلة إلى الفضاء", idea: "رواد فضاء وصواريخ وكواكب وكائنات فضائية لطيفة، مع نجوم وتفاصيل ممتعة للأطفال" },
  { title: "ماندالا الورد", idea: "ماندالا زهور وأشكال هندسية دقيقة للبالغين، للاسترخاء وتخفيف التوتر" },
  { title: "شاحنات ومركبات", idea: "شاحنات وسيارات وطائرات وقوارب للأطفال الصغار بخطوط سميكة ومساحات واسعة" },
];

function fillWizardSelects() {
  const m = S.meta;
  $("#wzAudience").innerHTML = Object.entries(m.audiences)
    .map(([k, v]) => `<option value="${k}">${v}</option>`).join("");
  $("#wzStyle").innerHTML = Object.entries(m.styles)
    .map(([k, v]) => `<option value="${k}">${v.label}</option>`).join("");
  $("#wzPaper").innerHTML = Object.entries(m.papers)
    .map(([k, v]) => `<option value="${k}">${v.label}</option>`).join("");
  $("#wzIdeas").innerHTML = `<span class="muted">أفكار جاهزة:</span>` +
    WIZ_IDEAS.map((i, n) => `<button class="chip" data-idea="${n}">${i.title}</button>`).join("");
}

function resetWizard() {
  WIZ.step = 1; WIZ.plan = null; WIZ.palette = null; WIZ.planning = false; WIZ.busy = false;
  $("#wzTitle").value = "";
  $("#wzAuthor").value = S.project?.author && S.project.author !== "اسم المؤلف" ? S.project.author : "";
  $("#wzIdea").value = "";
  $("#wzLanguage").value = S.project?.language || "ar";
  $("#wzAudience").value = S.project?.audience || "kids_mid";
  $("#wzStyle").value = S.project?.style || "medium";
  $("#wzPaper").value = S.project?.paper || "white";
  $("#wzPages").value = 12;
  $("#wzPagesVal").textContent = "12";
  $("#wzSingle").checked = true;
  $("#wzCaptions").checked = false;
  $("#wzCoverOptions").checked = true;
  $("#wzPlanBody").hidden = true;
  $("#wzPlanLoading").hidden = false;
  $("#wzBlurb").value = "";
  $("#wizError").textContent = "";
  S.wizTrim = S.project?.trim || "8.5x11";
  $("#wizSteps").querySelectorAll("li").forEach((li) => li.classList.remove("done"));
  renderTrimGrid();
  updateWizStats();
  setWizardStep(1);
}

function openWizard() {
  fillWizardSelects();
  resetWizard();
  $("#wizardModal").hidden = false;
}

function setWizardStep(step) {
  WIZ.step = step;
  $$(".wiz-pane").forEach((p) => p.classList.toggle("active", Number(p.dataset.pane) === step));
  $$("#wizSteps li").forEach((li) => {
    const n = Number(li.dataset.step);
    li.classList.toggle("active", n === step);
    li.classList.toggle("done", n < step);
  });
  $("#wizBack").style.visibility = step === 1 ? "hidden" : "visible";
  const labels = { 1: "التالي", 2: "تخطيط بالذكاء الاصطناعي ✦", 3: "التالي", 4: "ابدأ توليد الكتاب ✦" };
  $("#wizNext").textContent = labels[step] || "التالي";
  $("#wizNext").disabled = WIZ.busy;
  $("#wizError").textContent = "";
  updateEngineNote();
  if (step === 3 && !WIZ.plan && !WIZ.planning) fetchWizardPlan();
  if (step === 4) renderPalettes();
}

function renderTrimGrid() {
  const grid = $("#wzTrimGrid");
  const trims = Object.entries(S.meta.trims);
  grid.innerHTML = trims.map(([key, t]) => {
    const ratio = t.w / t.h;
    const width = Math.round(Math.max(24, Math.min(52, 52 * ratio)));
    const height = t.w >= t.h ? width : 64;
    const w2 = t.w >= t.h ? width : width;
    return `<button class="trim-card ${key === S.wizTrim ? "active" : ""}" data-trim="${key}">
      <div class="shape"><i style="width:${w2}px;height:${height}px"></i></div>
      <strong>${t.label}</strong><span>${t.note}</span></button>`;
  }).join("");
}

function wizPaperThickness() {
  const paper = $("#wzPaper").value;
  return S.meta.papers[paper]?.thickness || 0.002252;
}

function wizNumbers() {
  const art = Number($("#wzPages").value) || 12;
  const single = $("#wzSingle").checked;
  const trim = S.meta.trims[S.wizTrim] || S.meta.trims["8.5x11"];
  let pages = 4 + art * (single ? 2 : 1);
  if (pages % 2) pages += 1;
  pages = Math.max(24, pages);
  const spine = pages * wizPaperThickness();
  return {
    art, pages, spine, single,
    coverW: 0.25 + trim.w * 2 + spine,
    coverH: trim.h + 0.25,
    valid: pages >= 24,
  };
}

function updateWizStats() {
  const n = wizNumbers();
  const trim = S.meta.trims[S.wizTrim] || S.meta.trims["8.5x11"];
  $("#wzPagesVal").textContent = n.art;
  $("#wzStats").innerHTML = `
    <div class="wiz-stat"><span>صفحات الكتاب</span><strong>${n.pages}</strong></div>
    <div class="wiz-stat"><span>عرض الكعب</span><strong>${fmt(n.spine, 3)}"</strong></div>
    <div class="wiz-stat"><span>مقاس الغلاف</span><strong>${fmt(n.coverW, 2)}" × ${fmt(n.coverH, 2)}"</strong></div>
    <div class="wiz-stat ${n.valid ? "ok" : "warn"}"><span>مطابقة KDP</span><strong>${n.valid ? "✓ مطابق" : "أقل من 24"}</strong></div>`;
  $("#wzSummary").innerHTML = `
    <div class="wiz-stat"><span>المقاس</span><strong>${trim.label}</strong></div>
    <div class="wiz-stat"><span>صفحات التلوين</span><strong>${n.art}</strong></div>
    <div class="wiz-stat"><span>إجمالي الصفحات</span><strong>${n.pages}</strong></div>
    <div class="wiz-stat"><span>المحرّك</span><strong>${S.meta.providers[$("#providerSelect")?.value || "procedural"]?.label?.split("—")[0] || "محلي"}</strong></div>`;
}

function wizardPayload(extra = {}) {
  return {
    title: $("#wzTitle").value.trim(),
    author: $("#wzAuthor").value.trim(),
    idea: $("#wzIdea").value.trim(),
    language: $("#wzLanguage").value,
    audience: $("#wzAudience").value,
    style: $("#wzStyle").value,
    trim: S.wizTrim,
    paper: $("#wzPaper").value,
    art_pages: Number($("#wzPages").value),
    single_sided: $("#wzSingle").checked,
    captions: $("#wzCaptions").checked,
    provider: $("#providerSelect")?.value || "procedural",
    use_ai_planner: true,
    ...extra,
  };
}

async function fetchWizardPlan() {
  WIZ.planning = true;
  $("#wzPlanLoading").hidden = false;
  $("#wzPlanBody").hidden = true;
  $("#wizError").textContent = "";
  $("#wizNext").disabled = true;
  try {
    const res = await API.post("/api/wizard/plan", wizardPayload());
    WIZ.plan = res.plan;
    WIZ.palette = (res.plan.palettes || [])[0] || { background: "#F6F1E7", accent: "#B4562F", name: "دافئ كلاسيكي" };
    renderPlan();
  } catch (e) {
    $("#wizError").textContent = e.message;
    $("#wzPlanLoading").hidden = true;
  } finally {
    WIZ.planning = false;
    $("#wizNext").disabled = false;
  }
}

function renderPlan() {
  const p = WIZ.plan;
  if (!p) return;
  $("#wzPlanLoading").hidden = true;
  $("#wzPlanBody").hidden = false;
  $("#wzPlanTitle").textContent = p.title;
  $("#wzPlanSubtitle").textContent = p.subtitle || "";
  $("#wzPlanDesc").value = p.description || "";
  $("#wzPlanKeywords").value = (p.keywords || []).join("، ");
  $("#wzPlanPagesCount").textContent = `· ${(p.pages || []).length} صفحة`;
  $("#wzPlanPages").innerHTML = (p.pages || [])
    .map((pg, i) => `<span>${i + 1}. ${escapeHtml(pg.caption || "رسمة")}</span>`).join("");
  const badge = $("#wzPlannerBadge");
  const isAi = p.planner === "openai";
  badge.textContent = isAi ? "مُخطط بالذكاء الاصطناعي" : "مُخطط محلي";
  badge.className = `planner-badge ${isAi ? "" : "local"}`;
  $("#wzPlannerNote").textContent = p.notes || "";
  if (!$("#wzTitle").value.trim()) $("#wzTitle").value = p.title;
  if (!$("#wzBlurb").value.trim()) $("#wzBlurb").value = (p.cover && p.cover.blurb) || "";
}

function updateEngineNote() {
  const box = $("#wzEngineNote");
  const provider = $("#providerSelect")?.value || "procedural";
  const hasOpenAi = S.meta?.settings?.has_keys?.openai;
  if (provider === "procedural") {
    box.className = "wiz-notice";
    box.innerHTML = "⚠︎ <b>المحرّك المحلي</b> يرسم أنماطًا زخرفية فقط (ماندالا / زهور / هندسي) — لن تظهر حيوانات "
      + "أو ديناصورات أو مركبات. للحصول على رسومات مطابقة لفكرتك أضف مفتاح ذكاء اصطناعي من زر "
      + "«مفاتيح الذكاء الاصطناعي» ثم أعد المحاولة.";
    box.hidden = false;
  } else if (provider === "local_sd") {
    box.className = "wiz-notice info";
    box.textContent = "سيُستخدم Stable Diffusion المحلي على جهازك لتوليد الرسومات — تأكد من تشغيل A1111 مع الخيار --api.";
    box.hidden = false;
  } else {
    box.className = "wiz-notice info";
    box.textContent = (hasOpenAi ? "تم العثور على مفتاح OpenAI — " : "")
      + `سيُستخدم ${S.meta?.providers?.[provider]?.label || provider} لتوليد الرسومات وتخطيط الكتاب.`;
    box.hidden = false;
  }
}

function renderPalettes() {
  const palettes = (WIZ.plan && WIZ.plan.palettes) || [
    { name: "دافئ كلاسيكي", background: "#F6F1E7", accent: "#B4562F" },
    { name: "طبيعي هادئ", background: "#EAF0E6", accent: "#3F6B4A" },
    { name: "حديث نظيف", background: "#F5F5F2", accent: "#2A2A2E" },
    { name: "ليلي فخم", background: "#212A36", accent: "#D9A441" },
  ];
  const current = WIZ.palette || palettes[0];
  $("#wzPalettes").innerHTML = palettes.map((pal, i) => {
    const active = pal.background === current.background && pal.accent === current.accent;
    return `<button class="palette-card ${active ? "active" : ""}" data-pal="${i}">
      <div class="palette-preview" style="background:${pal.background}">
        <div class="bar title" style="background:${pal.accent}"></div>
        <div class="bar sub" style="background:${pal.accent};opacity:.45"></div>
        <div class="art"></div>
        <div class="bar" style="background:${pal.accent};opacity:.25;width:70%"></div>
      </div>
      <div class="palette-meta"><strong>${pal.name}</strong><span class="dot" style="background:${pal.accent}"></span></div>
    </button>`;
  }).join("");
  WIZ.palettes = palettes;
}

async function createBookFromWizard() {
  if (!WIZ.plan) { fetchWizardPlan(); return; }
  WIZ.busy = true;
  $("#wizNext").disabled = true;
  $("#wizNext").textContent = "جارٍ تجهيز الكتاب…";
  $("#wizError").textContent = "";
  const payload = wizardPayload({
    plan: {
      ...WIZ.plan,
      description: $("#wzPlanDesc").value,
      keywords: $("#wzPlanKeywords").value.split(/[,،]/).map((s) => s.trim()).filter(Boolean).slice(0, 7),
      cover: { blurb: $("#wzBlurb").value },
    },
    palette: WIZ.palette || (WIZ.plan.palettes || [])[0],
    generate_cover_options: $("#wzCoverOptions").checked,
  });
  try {
    const res = await API.post("/api/wizard/create", payload);
    S.wantCoverOptions = payload.generate_cover_options;
    $("#wizardModal").hidden = true;
    S.tab = "studio";
    $$(".tab").forEach((t) => t.classList.toggle("active", t.dataset.tab === "studio"));
    $$(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === "tab-studio"));
    await loadProject(res.project.id);
    await refreshProjectList();
    S.job = res.job;
    $("#jobBox").hidden = false;
    pollJob(res.job.id);
    toast(`بدأ توليد الكتاب «${res.project.title}»`, "ok");
  } catch (e) {
    $("#wizError").textContent = e.message;
  } finally {
    WIZ.busy = false;
    $("#wizNext").disabled = false;
    $("#wizNext").textContent = "ابدأ توليد الكتاب ✦";
  }
}

async function openCoverOptions(pid) {
  try {
    const res = await API.post(`/api/projects/${pid}/cover-options`);
    if (!res.items.length) return;
    $("#coverOptionsGrid").innerHTML = res.items.map((o, i) => `
      <div class="cover-option">
        <img src="${o.png}?t=${Date.now()}" alt="${o.name}" />
        <div class="co-meta"><strong>${o.name}</strong>
          <button class="btn primary small" data-cover-apply="${i}">اختيار</button></div>
      </div>`).join("");
    $("#coverOptionsGrid").dataset.items = JSON.stringify(res.items);
    $("#coverOptionsModal").hidden = false;
  } catch (e) {
    /* لا نعطّل التجربة إن فشلت الأغلفة البديلة */
  }
}

async function applyCoverOption(index) {
  const items = JSON.parse($("#coverOptionsGrid").dataset.items || "[]");
  const item = items[index];
  if (!item) return;
  try {
    const res = await API.post(`/api/projects/${S.project.id}/cover-apply`, {
      background: item.background, accent: item.accent,
    });
    S.project = res.project;
    S.built = { files: S.project._meta.outputs || (S.built && S.built.files), validation: S.built && S.built.validation };
    S.builtAt = Date.now();
    $("#coverOptionsModal").hidden = true;
    toast(`تم تطبيق غلاف «${item.name}»`, "ok");
    refreshValidation();
    renderPreview(true);
  } catch (e) {
    toast(e.message, "err");
  }
}

function bindWizard() {
  $("#openWizard").addEventListener("click", openWizard);
  $("#wizBack").addEventListener("click", () => setWizardStep(Math.max(1, WIZ.step - 1)));
  $("#wizNext").addEventListener("click", async () => {
    $("#wizError").textContent = "";
    if (WIZ.step === 1) {
      if (!$("#wzTitle").value.trim() && !$("#wzIdea").value.trim()) {
        $("#wizError").textContent = "اكتب عنوانًا أو فكرة للكتاب أولًا.";
        return;
      }
      setWizardStep(2);
    } else if (WIZ.step === 2) {
      setWizardStep(3);
    } else if (WIZ.step === 3) {
      if (!WIZ.plan) { fetchWizardPlan(); return; }
      setWizardStep(4);
    } else {
      createBookFromWizard();
    }
  });
  $("#wzTrimGrid").addEventListener("click", (e) => {
    const card = e.target.closest("[data-trim]");
    if (!card) return;
    S.wizTrim = card.dataset.trim;
    renderTrimGrid();
    updateWizStats();
  });
  $("#wzPages").addEventListener("input", updateWizStats);
  $("#wzPaper").addEventListener("change", updateWizStats);
  $("#wzSingle").addEventListener("change", updateWizStats);
  $("#wzIdeas").addEventListener("click", (e) => {
    const chip = e.target.closest("[data-idea]");
    if (!chip) return;
    const idea = WIZ_IDEAS[Number(chip.dataset.idea)];
    $("#wzTitle").value = idea.title;
    $("#wzIdea").value = idea.idea;
  });
  $("#wzReplan").addEventListener("click", fetchWizardPlan);
  $("#wzPalettes").addEventListener("click", (e) => {
    const card = e.target.closest("[data-pal]");
    if (!card) return;
    WIZ.palette = (WIZ.palettes || [])[Number(card.dataset.pal)];
    renderPalettes();
  });
  $("#coverOptionsGrid").addEventListener("click", (e) => {
    const btn = e.target.closest("[data-cover-apply]");
    if (btn) applyCoverOption(Number(btn.dataset.coverApply));
  });
  $("#newProjectBtn").addEventListener("click", openWizard);
  $("#wizBlank").addEventListener("click", async () => {
    const title = $("#wzTitle").value.trim() || "كتاب تلوين جديد";
    $("#wizardModal").hidden = true;
    await createProject({ title, author: $("#wzAuthor").value.trim() || "اسم المؤلف",
                          trim: S.wizTrim || "8.5x11", paper: $("#wzPaper").value,
                          language: $("#wzLanguage").value });
    await refreshProjectList();
  });
}

/* ------------------------------- bind UI -------------------------------- */
function bindUI() {
  // التبويبات
  $("#tabs").addEventListener("click", (e) => {
    const btn = e.target.closest(".tab");
    if (!btn) return;
    S.tab = btn.dataset.tab;
    $$(".tab").forEach((t) => t.classList.toggle("active", t === btn));
    $$(".tab-panel").forEach((p) => p.classList.toggle("active", p.id === `tab-${S.tab}`));
    if (S.tab === "check") refreshValidation();
    if (S.tab === "preview") renderPreview();
  });

  // أقسام قابلة للطي
  $$(".card-head").forEach((head) => {
    head.addEventListener("click", () => head.closest(".card").classList.toggle("open"));
  });

  // حقول المشروع
  $$("[data-field]").forEach((input) => {
    const path = input.dataset.field;
    const type = input.dataset.type;
    const handler = () => {
      let value;
      if (type === "bool") value = input.checked;
      else if (type === "number") value = Number(input.value);
      else if (type === "list") value = input.value.split(/[,،]/).map((s) => s.trim()).filter(Boolean);
      else value = input.value;
      debounceProjectSave(path, value);
      if (path === "cover.background" || path === "cover.accent") {
        S.project.cover[path.split(".")[1]] = value;
      }
      if (path === "captions" || path === "trim" || path === "paper" || path === "bleed" || path === "single_sided") {
        S.project[path] = value;
        setTimeout(() => {
          softRefresh();
          refreshValidation();
        }, 700);
      }
    };
    input.addEventListener(input.type === "checkbox" || input.tagName === "SELECT" ? "change" : "input", handler);
  });

  $("#themeChips").addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    $$(".chip").forEach((c) => c.classList.toggle("active", c === chip));
    S.project.theme = chip.dataset.theme;
    patchProject({ theme: chip.dataset.theme }, { silent: true });
    // اختيار المحرّك المحلي يغيّر نمط الرسم تلقائيًا
    providerNote();
  });

  $("#providerSelect").addEventListener("change", () => {
    patchProject({ provider: $("#providerSelect").value }, { silent: true });
    providerNote();
  });
  $("#styleSelect").addEventListener("change", () => patchProject({ style: $("#styleSelect").value }, { silent: true }));
  $("#audienceSelect").addEventListener("change", () => patchProject({ audience: $("#audienceSelect").value }, { silent: true }));
  $("#coverPageSelect").addEventListener("change", (e) =>
    patchProject({ cover: { ...S.project.cover, cover_page_id: e.target.value || null } }, { silent: true })
  );

  $("#generateBtn").addEventListener("click", generate);
  $("#cancelJobBtn").addEventListener("click", async () => {
    if (!S.job) return;
    await API.post(`/api/jobs/${S.job.id}/cancel`);
    toast("تم إلغاء المهمة");
  });
  $("#buildBtn").addEventListener("click", buildBook);
  $("#recheckBtn").addEventListener("click", async () => {
    await refreshValidation();
    toast("تم إعادة الفحص");
  });

  $("#projectSelect").addEventListener("change", (e) => loadProject(e.target.value));
  $("#newProjectBtn").addEventListener("click", () => {
    const title = prompt("عنوان الكتاب الجديد:", "كتاب تلوين جديد");
    if (title === null) return;
    createProject({ title: title || "كتاب تلوين جديد" });
  });

  // الاستيراد
  $("#importBtn").addEventListener("click", () => $("#importInput").click());
  $("#importInput").addEventListener("change", async (e) => {
    const files = e.target.files;
    if (!files.length) return;
    const fd = new FormData();
    Array.from(files).forEach((f) => fd.append("files", f));
    toast("جارٍ استيراد الصور…");
    try {
      const res = await API.call(`/api/projects/${S.project.id}/import`, { method: "POST", body: fd });
      S.rev += 1;
      await loadProject(S.project.id);
      toast(`تم استيراد ${res.created.length} صورة`, "ok");
    } catch (err) {
      toast(err.message, "err");
    }
    e.target.value = "";
  });

  // معرض الصفحات
  $("#gallery").addEventListener("click", (e) => {
    const card = e.target.closest(".page-card");
    if (!card) return;
    const id = card.dataset.id;
    const btn = e.target.closest("[data-act]");
    if (btn) {
      e.stopPropagation();
      pageAction(id, btn.dataset.act, card);
      return;
    }
    if (e.target.closest("[data-open]")) openPageModal(id);
  });
  $("#gallery").addEventListener("change", (e) => {
    if (!e.target.matches("[data-caption]")) return;
    const card = e.target.closest(".page-card");
    API.patch(`/api/projects/${S.project.id}/pages/${card.dataset.id}`, { caption: e.target.value })
      .then((proj) => {
        S.project = proj;
        renderCoverPageSelect();
      })
      .catch((err) => toast(err.message, "err"));
  });

  // المودالات
  $$("[data-close]").forEach((b) => b.addEventListener("click", closeModals));
  $$(".modal").forEach((m) =>
    m.addEventListener("click", (e) => {
      if (e.target === m && m.id !== "buildModal") closeModals();
    })
  );
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModals();
  });

  $("#modalThickness").addEventListener("input", (e) => ($("#thickVal").textContent = e.target.value));
  $("#modalThreshold").addEventListener("input", (e) => ($("#threshVal").textContent = e.target.value));
  $("#modalApply").addEventListener("click", applyPageSettings);
  $("#modalRegen").addEventListener("click", async () => {
    const pg = S.modalPage;
    if (!pg) return;
    closeModals();
    await pageAction(pg.id, "regen");
  });
  $("#modalDelete").addEventListener("click", async () => {
    const pg = S.modalPage;
    if (!pg) return;
    closeModals();
    await pageAction(pg.id, "delete");
  });
  $("#modalCover").addEventListener("click", async () => {
    const pg = S.modalPage;
    if (!pg) return;
    await patchProject({ cover: { ...S.project.cover, cover_page_id: pg.id } });
    renderGallery();
    closeModals();
    toast("تم تعيين الرسمة كغلاف", "ok");
  });

  // المفاتيح
  $("#settingsBtn").addEventListener("click", async () => {
    const settings = await API.get("/api/settings");
    $("#localSdUrl").value = settings.local_sd_url || "http://127.0.0.1:7860";
    $("#keysModal").hidden = false;
  });
  $("#saveKeys").addEventListener("click", async () => {
    const keys = {};
    $$("[data-key]").forEach((i) => (keys[i.dataset.key] = i.value));
    try {
      await API.post("/api/settings", { api_keys: keys, local_sd_url: $("#localSdUrl").value });
      S.meta = await API.get("/api/meta");
      providerNote();
      toast("تم حفظ المفاتيح على جهازك", "ok");
      closeModals();
    } catch (e) {
      toast(e.message, "err");
    }
  });

  $("#providerSelect").addEventListener("change", providerNote);
  providerNote();
  bindWizard();
}

boot();
