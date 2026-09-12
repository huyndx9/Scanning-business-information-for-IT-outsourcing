/* Company Scanner UI — dùng chung cho 3 trang:
     /        quét mới + hiển thị kết quả
     /saved   danh sách công ty đã lưu
     /crm     CRM lead (phần riêng nằm trong crm.js, dùng lại helper ở đây)

   Mọi giá trị hiển thị đều đến từ /api/scan của đúng URL người dùng nhập,
   hoặc từ bản đã lưu trong database. Không có dữ liệu mẫu / mặc định /
   dự phòng ở bất kỳ đâu trong file này: thiếu dữ liệu thì hiện "Not found". */

// Chuỗi hiển thị đều lấy qua t() trong i18n.js (mặc định tiếng Hàn).
const NOT_FOUND = () => t("common.notFound");

// Mã lỗi server trả về; chữ hiển thị lấy theo ngôn ngữ đang chọn.
const ERROR_CODES = ["invalid_url", "unreachable", "timeout", "blocked", "internal"];

const ICONS = {
  globe: '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/><path d="M2 12h20"/>',
  search: '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
  sparkles: '<path d="M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z"/><path d="M20 3v4"/><path d="M22 5h-4"/><path d="M4 17v2"/><path d="M5 18H3"/>',
  loader: '<path d="M21 12a9 9 0 1 1-6.219-8.56"/>',
  check: '<path d="M20 6 9 17l-5-5"/>',
  building: '<path d="M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18Z"/><path d="M6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2"/><path d="M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2"/><path d="M10 6h4"/><path d="M10 10h4"/><path d="M10 14h4"/><path d="M10 18h4"/>',
  mappin: '<path d="M20 10c0 4.993-5.539 10.193-7.399 11.799a1 1 0 0 1-1.202 0C9.539 20.193 4 14.993 4 10a8 8 0 0 1 16 0"/><circle cx="12" cy="10" r="3"/>',
  phone: '<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
  briefcase: '<path d="M16 20V4a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/><rect width="20" height="14" x="2" y="6" rx="2"/>',
  external: '<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>',
  json: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M10 12a1 1 0 0 0-1 1v1a1 1 0 0 1-1 1 1 1 0 0 1 1 1v1a1 1 0 0 0 1 1"/><path d="M14 18a1 1 0 0 0 1-1v-1a1 1 0 0 1 1-1 1 1 0 0 1-1-1v-1a1 1 0 0 0-1-1"/>',
  sheet: '<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/><path d="M14 2v4a2 2 0 0 0 2 2h4"/><path d="M8 13h2"/><path d="M14 13h2"/><path d="M8 17h2"/><path d="M14 17h2"/>',
  chevron: '<path d="m6 9 6 6 6-6"/>',
  clock: '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
  shield: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/><path d="m9 12 2 2 4-4"/>',
  alert: '<circle cx="12" cy="12" r="10"/><path d="M12 8v4"/><path d="M12 16h.01"/>',
  link: '<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>',
  mail: '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
  database: '<ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5V19A9 3 0 0 0 21 19V5"/><path d="M3 12A9 3 0 0 0 21 12"/>',
  save: '<path d="M15.2 3a2 2 0 0 1 1.4.6l3.8 3.8a2 2 0 0 1 .6 1.4V19a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/><path d="M17 21v-7a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v7"/><path d="M7 3v4a1 1 0 0 0 1 1h7"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/>',
  plus: '<path d="M5 12h14"/><path d="M12 5v14"/>',
  x: '<path d="M18 6 6 18"/><path d="m6 6 12 12"/>',
  trash: '<path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/>',
  refresh: '<path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/><path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16"/><path d="M8 16H3v5"/>',
  eye: '<path d="M2.062 12.348a1 1 0 0 1 0-.696 10.75 10.75 0 0 1 19.876 0 1 1 0 0 1 0 .696 10.75 10.75 0 0 1-19.876 0"/><circle cx="12" cy="12" r="3"/>',
  userplus: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="19" x2="19" y1="8" y2="14"/><line x1="22" x2="16" y1="11" y2="11"/>',
};

function icon(name, size = 16, className = "") {
  const paths = ICONS[name] || "";
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="${className}">${paths}</svg>`;
}

function esc(value) {
  return String(value == null ? "" : value).replace(/[&<>"']/g, (c) => (
    { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
  ));
}

/* Giá trị thật, hoặc chỗ trống "Not found". */
function orNotFound(value, className = "") {
  if (value === null || value === undefined || value === "") {
    return `<span class="text-slate-400 italic ${className}">${esc(NOT_FOUND())}</span>`;
  }
  return `<span class="${className}">${esc(value)}</span>`;
}

function sourceLink(url, label) {
  if (!url) return "";
  label = label || t("common.source");
  return `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer"
    class="inline-flex items-center gap-1 text-[11px] font-medium text-blue-600 hover:text-blue-700 mt-1.5 break-all">
    ${icon("link", 11)} ${esc(label)}</a>`;
}

/* Icon khai báo bằng data-icon trong HTML. */
document.querySelectorAll("[data-icon]").forEach((element) => {
  element.innerHTML = icon(element.dataset.icon, Number(element.dataset.size || 16));
});

/* Số công ty / số lead trên nút điều hướng, hiện ở mọi trang. */
const navBadge = document.getElementById("nav-saved-count");
const navCrmBadge = document.getElementById("nav-crm-count");

function setNavBadge(count) {
  if (navBadge) navBadge.textContent = String(count);
}

function setNavCrmBadge(count) {
  if (navCrmBadge) navCrmBadge.textContent = String(count);
}

async function refreshNavCrmBadge() {
  if (!navCrmBadge) return;
  try {
    const response = await fetch("/api/leads");
    if (!response.ok) return;
    setNavCrmBadge(((await response.json()).leads || []).length);
  } catch (_) {
    // Không lấy được số lead thì badge giữ 0.
  }
}
refreshNavCrmBadge();

/* Trang không tự tải danh sách công ty (như /crm) vẫn cần số trên tab "Công ty đã lưu". */
async function refreshNavSavedBadge() {
  if (!navBadge || document.getElementById("url-input") || document.getElementById("saved-rows")) return;
  try {
    const response = await fetch("/api/companies");
    if (!response.ok) return;
    setNavBadge(((await response.json()).companies || []).length);
  } catch (_) {
    // Badge giữ 0.
  }
}
refreshNavSavedBadge();

/* Chuyển một công ty đã lưu thành lead CRM rồi mở lead đó.
   Đã có lead cho công ty này thì mở lead cũ, không tạo bản trùng. */
async function openAsLead(companyId) {
  const response = await fetch(`/api/leads/from-company/${encodeURIComponent(companyId)}`, { method: "POST" });
  if (!response.ok) throw new Error(String(response.status));
  const payload = await response.json();
  window.location.href = `/crm?lead=${payload.lead.id}`;
}

function download(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

const isScanPage = Boolean(document.getElementById("url-input"));
const isSavedPage = Boolean(document.getElementById("saved-rows"));

// =========================================================================
//  TRANG QUÉT MỚI
// =========================================================================

if (isScanPage) {
  const STAGE_IDS = ["homepage", "company", "contact", "management", "recruitment", "extract", "done"];
  const stageText = (id) => t("stage." + id);
  const saveLabel = (state) => t("result.save." + state);

  const SIGNAL_STYLES = {
    High: "bg-emerald-50 border-emerald-200 text-emerald-700",
    Medium: "bg-amber-50 border-amber-200 text-amber-700",
    Low: "bg-blue-50 border-blue-100 text-blue-700",
    None: "bg-slate-100 border-slate-200 text-slate-500",
  };

  const AVATAR_COLORS = ["bg-slate-900", "bg-blue-600", "bg-indigo-600", "bg-sky-600", "bg-violet-600", "bg-emerald-600"];

  const urlInput = document.getElementById("url-input");
  const scanBtn = document.getElementById("scan-btn");
  const scanBtnLabel = document.getElementById("scan-btn-label");
  const progressBox = document.getElementById("progress");
  const resultsBox = document.getElementById("results");
  const errorBox = document.getElementById("error-box");
  const errorTitle = document.getElementById("error-title");
  const errorDetail = document.getElementById("error-detail");
  const placeholder = document.getElementById("placeholder");

  let scanning = false;
  let result = null;          // kết quả thật của lần quét hiện tại, hoặc null
  let showJson = false;
  let saveState = "idle";     // idle | saving | saved | error
  let savedCompanyId = null;  // id trong database sau khi lưu / khi mở từ trang đã lưu
  let stageState = [];
  let eventSource = null;

  // -- Tiến trình ---------------------------------------------------------

  function renderProgress() {
    if (!scanning && !result) {
      progressBox.className = "stage-list hidden";
      progressBox.innerHTML = "";
      return;
    }
    progressBox.className = "stage-list";
    progressBox.innerHTML = stageState.map((stage, index) => {
      const tone = stage.active ? "stage-active" : stage.done ? "stage-done" : "stage-idle";
      const bullet = stage.done
        ? icon("check", 9)
        : stage.active
          ? icon("loader", 9, "animate-spin")
          : String(index + 1);
      return `<span class="stage ${tone}">
        <span class="stage-dot">${bullet}</span>${esc(stageText(stage.id))}</span>`;
    }).join("");
  }

  function markStage(stageId) {
    const index = stageState.findIndex((s) => s.id === stageId);
    if (index < 0) return;
    stageState = stageState.map((stage, i) => ({
      ...stage,
      done: i < index || (stageId === "done" && i <= index),
      active: i === index && stageId !== "done",
    }));
    renderProgress();
  }

  function setScanning(value) {
    scanning = value;
    scanBtn.disabled = value || !urlInput.value.trim();
    scanBtnLabel.textContent = value ? t("scan.buttonBusy") : t("scan.button");
    scanBtn.firstElementChild.innerHTML = value ? icon("loader", 16, "animate-spin") : icon("sparkles", 16);
  }

  function showError(message, detail) {
    errorBox.classList.remove("hidden");
    errorTitle.textContent = message;
    errorDetail.textContent = detail || "";
  }

  function clearError() {
    errorBox.classList.add("hidden");
    errorDetail.textContent = "";
  }

  // -- Hiển thị kết quả ---------------------------------------------------

  function initials(name) {
    const value = (name || "").trim();
    if (!value) return "?";
    if (value.includes(" ")) {
      const parts = value.split(" ");
      return ((parts[0][0] || "") + (parts[parts.length - 1][0] || "")).toUpperCase();
    }
    // Tên tiếng Hàn viết họ trước: 조준희 -> 조준.
    return value.slice(0, 2).toUpperCase();
  }

  function infoTile(iconName, label, value, source, wide = false, hint = null) {
    // Không có giá trị nhưng biết lý do (email là ảnh / chỉ có form liên hệ):
    // nói rõ lý do và trỏ tới trang đó thay vì chỉ "찾을 수 없음".
    const body = (value === null || value === undefined || value === "") && hint
      ? `<span class="text-amber-700">${esc(t("result.hint." + hint.type))}</span>`
      : orNotFound(value);
    return `<div class="rounded-xl bg-slate-50 border border-slate-200 p-3.5 ${wide ? "tile-wide" : ""}">
      <div class="flex items-center gap-2 text-[11px] font-semibold tracking-wide uppercase text-slate-500 mb-1.5">
        ${icon(iconName, 14)} ${esc(label)}
      </div>
      <div class="text-[13px] leading-snug font-medium break-all">${body}</div>
      ${sourceLink(source || (hint && hint.url), hint && !value ? t("result.hint.open") : undefined)}
    </div>`;
  }

  function renderCompanyCard(data) {
    const company = data.company || {};
    const sources = data.company_sources || {};
    const hints = data.company_hints || {};
    return `<div class="lg:col-span-7 rounded-[20px] border border-slate-200 bg-white p-5 md:p-6 shadow-sm">
      <div class="flex items-start justify-between gap-4 mb-5">
        <div class="flex items-center gap-3">
          <div class="h-9 w-9 rounded-xl bg-blue-600 text-white flex items-center justify-center">${icon("building", 20)}</div>
          <div>
            <h3 class="text-[15px] font-semibold leading-none">${esc(t("result.company.heading"))}</h3>
            <p class="text-[12px] text-slate-500 mt-1.5">${esc(t("result.company.desc", { pages: data.pages_crawled || 0 }))}</p>
          </div>
        </div>
        ${company.website ? `<a href="${esc(company.website)}" target="_blank" rel="noopener noreferrer"
          class="inline-flex items-center gap-1 text-[12px] font-medium text-blue-600 hover:text-blue-700">${esc(t("result.company.openSite"))} ${icon("external", 12)}</a>` : ""}
      </div>

      <div class="space-y-4">
        <div>
          <div class="text-[22px] font-bold tracking-tight leading-tight">${orNotFound(company.name)}</div>
          ${sourceLink(sources.name)}
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
          ${infoTile("mappin", t("result.company.address"), company.address, sources.address)}
          ${infoTile("phone", t("result.company.phone"), company.phone, sources.phone)}
          ${infoTile("mail", t("result.company.email"), company.email, sources.email, false, hints.email)}
          ${infoTile("briefcase", t("result.company.industry"), company.industry, sources.industry)}
          ${infoTile("shield", t("result.company.biz"), company.biz_number, sources.biz_number)}
          ${infoTile("users", t("result.company.ceo"), company.ceo, sources.ceo)}
          ${infoTile("globe", t("result.company.website"), company.website, null, true)}
        </div>
      </div>
    </div>`;
  }

  function renderContactsCard(data) {
    const contacts = data.key_contacts || [];
    const body = contacts.length === 0
      ? `<div class="rounded-xl border border-dashed border-slate-200 p-4 text-[12.5px] text-slate-400 italic">${esc(t("result.contacts.empty"))}</div>`
      : contacts.map((contact, index) => `
        <div class="flex items-center gap-3.5 rounded-xl border border-slate-200 p-3 hover:bg-slate-50 transition-colors group">
          <div class="h-11 w-11 rounded-full ${AVATAR_COLORS[index % AVATAR_COLORS.length]} text-white flex items-center justify-center text-[12px] font-bold tracking-wide shadow-sm">${esc(initials(contact.name))}</div>
          <div class="min-w-0 flex-1">
            <div class="text-[13.5px] font-semibold leading-tight truncate">${esc(contact.name)}</div>
            <div class="text-[12px] text-slate-500 mt-0.5 truncate">${esc(contact.position || "")}</div>
            ${sourceLink(contact.source_url)}
          </div>
        </div>`).join("");

    return `<div class="lg:col-span-5 rounded-[20px] border border-slate-200 bg-white p-5 md:p-6 shadow-sm">
      <div class="flex items-center gap-3 mb-5">
        <div class="h-9 w-9 rounded-xl bg-slate-900 text-white flex items-center justify-center">${icon("users", 20)}</div>
        <div>
          <h3 class="text-[15px] font-semibold leading-none">${esc(t("result.contacts.heading"))}</h3>
          <p class="text-[12px] text-slate-500 mt-1.5">${esc(t("result.contacts.desc"))}</p>
        </div>
      </div>
      <div class="space-y-3">${body}</div>
    </div>`;
  }

  function renderJobsCard(data) {
    const jobs = data.it_recruitment || [];
    const signal = (data.sales_signal && data.sales_signal.it_hiring) || "None";
    const chips = (job) => [job.position, job.location, job.employment_type, job.deadline]
      .filter(Boolean)
      .map((value, index) => `<span class="inline-flex items-center px-2 h-5 rounded-full ${index === 0 ? "bg-slate-900 text-white" : "bg-white border border-slate-200 text-slate-600"} text-[11px] font-medium">${esc(value)}</span>`)
      .join("");

    const body = jobs.length === 0
      ? `<div class="rounded-xl border border-dashed border-slate-200 p-4 text-[12.5px] text-slate-400 italic">${esc(t("result.jobs.empty"))}</div>`
      : `<div class="grid grid-cols-1 md:grid-cols-2 gap-3">${jobs.map((job) => `
          <a href="${esc(job.source_url)}" target="_blank" rel="noopener noreferrer"
            class="group rounded-xl border border-slate-200 p-4 hover:border-slate-900 hover:bg-slate-50 transition-all flex flex-col">
            <div class="flex items-start justify-between gap-3">
              <div class="text-[14px] font-semibold leading-tight group-hover:text-slate-900">${esc(job.title)}</div>
              ${icon("external", 16, "text-slate-400 group-hover:text-slate-900 shrink-0 mt-0.5")}
            </div>
            <div class="mt-2.5 flex flex-wrap gap-1.5">${chips(job)}</div>
            ${job.description ? `<div class="mt-2 text-[11.5px] text-slate-500 leading-relaxed truncate">${esc(job.description)}</div>` : ""}
            <div class="mt-3 text-[11px] text-slate-400 truncate">${esc(job.source_url)}</div>
          </a>`).join("")}</div>`;

    return `<div class="lg:col-span-12 rounded-[20px] border border-slate-200 bg-white p-5 md:p-6 shadow-sm">
      <div class="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div class="flex items-center gap-3">
          <div class="h-9 w-9 rounded-xl bg-emerald-600 text-white flex items-center justify-center">${icon("briefcase", 20)}</div>
          <div>
            <h3 class="text-[15px] font-semibold leading-none">${esc(t("result.jobs.heading"))}</h3>
            <p class="text-[12px] text-slate-500 mt-1.5">${esc(t("result.jobs.desc", { count: jobs.length }))}</p>
          </div>
        </div>
        <span class="inline-flex h-6 items-center px-2.5 rounded-full border text-[11px] font-semibold ${SIGNAL_STYLES[signal] || SIGNAL_STYLES.None}">${esc(t("signal.label", { level: t("signal." + signal) }))}</span>
      </div>
      ${body}
    </div>`;
  }

  function renderSourcesCard(data) {
    const sources = data.sources || [];
    if (sources.length === 0) return "";
    return `<div class="lg:col-span-12 rounded-[20px] border border-slate-200 bg-white p-5 md:p-6 shadow-sm">
      <div class="flex items-center gap-3 mb-4">
        <div class="h-9 w-9 rounded-xl bg-slate-100 text-slate-600 flex items-center justify-center">${icon("link", 18)}</div>
        <div>
          <h3 class="text-[15px] font-semibold leading-none">${esc(t("result.sources.heading"))}</h3>
          <p class="text-[12px] text-slate-500 mt-1.5">${esc(t("result.sources.desc", { count: sources.length }))}</p>
        </div>
      </div>
      <div class="space-y-1.5 max-h-[240px] overflow-y-auto">
        ${sources.map((url) => `<a href="${esc(url)}" target="_blank" rel="noopener noreferrer"
          class="block text-[12px] text-blue-600 hover:text-blue-700 break-all">${esc(url)}</a>`).join("")}
      </div>
    </div>`;
  }

  function renderResults() {
    if (!result) {
      resultsBox.classList.add("hidden");
      resultsBox.innerHTML = "";
      placeholder.classList.remove("hidden");
      return;
    }
    placeholder.classList.add("hidden");
    resultsBox.classList.remove("hidden");

    const json = JSON.stringify(result, null, 2);
    const website = (result.company && result.company.website) || result.scanned_url || "";

    const header = `<div class="flex flex-wrap items-center justify-between gap-3 mb-5">
      <div class="flex items-center gap-3">
        <div class="h-8 w-8 rounded-full bg-emerald-600 flex items-center justify-center text-white">${icon("check", 16)}</div>
        <div>
          <div class="text-[14px] font-semibold leading-none">${esc(t("result.done"))}</div>
          <div class="text-[12px] text-slate-500 mt-1">${esc(t("result.summary", { website: website, pages: result.pages_crawled || 0 }))}</div>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button id="save-btn" class="h-9 px-3.5 rounded-full border text-[13px] font-medium flex items-center gap-1.5 transition-colors ${saveState === "saved" ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-white border-slate-200 hover:bg-slate-50"}">
          ${icon(saveState === "saved" ? "check" : "save", 16)} ${esc(saveLabel(saveState))}
        </button>
        <button id="json-btn" class="h-9 px-3.5 rounded-full border text-[13px] font-medium flex items-center gap-1.5 transition-colors ${showJson ? "bg-slate-900 text-white border-slate-900" : "bg-white border-slate-200 hover:bg-slate-50"}">
          ${icon("json", 16)} ${esc(showJson ? t("result.json.hide") : t("result.json.show"))}
        </button>
        <button id="lead-btn" class="h-9 px-3.5 rounded-full bg-blue-600 hover:bg-blue-700 text-white text-[13px] font-semibold flex items-center gap-1.5 shadow-sm">
          ${icon("userplus", 16)} ${esc(t("crm.lead.addFromScan"))}
        </button>
      </div>
    </div>`;

    const body = showJson
      ? `<div class="rounded-[16px] border border-slate-200 bg-[#0b1220] overflow-hidden">
          <div class="flex items-center justify-between px-5 h-11 border-b border-white/10">
            <span class="text-[12px] font-medium text-white/70 tracking-wide uppercase">${esc(t("result.json.heading"))}</span>
            <button id="copy-json" class="text-[11px] px-2.5 h-7 rounded-full bg-white/10 hover:bg-white/15 text-white transition-colors">${esc(t("result.json.copy"))}</button>
          </div>
          <pre class="p-5 text-[12.5px] leading-6 text-blue-100/90 overflow-x-auto font-[JetBrains_Mono,monospace] max-h-[520px]">${esc(json)}</pre>
        </div>`
      : `<div class="grid grid-cols-1 lg:grid-cols-12 gap-5">
          ${renderCompanyCard(result)}
          ${renderContactsCard(result)}
          ${renderJobsCard(result)}
          ${renderSourcesCard(result)}
        </div>`;

    resultsBox.innerHTML = header + body;
    wireResultButtons(json);
  }

  function wireResultButtons(json) {
    const saveBtn = document.getElementById("save-btn");
    if (saveBtn) saveBtn.onclick = saveCurrentResult;

    const jsonBtn = document.getElementById("json-btn");
    if (jsonBtn) jsonBtn.onclick = () => { showJson = !showJson; renderResults(); };

    const copyBtn = document.getElementById("copy-json");
    if (copyBtn) copyBtn.onclick = () => navigator.clipboard.writeText(json);

    const leadBtn = document.getElementById("lead-btn");
    if (leadBtn) leadBtn.onclick = addLeadFromResult;
  }

  /* Lưu (nếu chưa) rồi chuyển sang CRM với lead điền sẵn từ kết quả quét. */
  async function addLeadFromResult() {
    if (!result) return;
    try {
      if (savedCompanyId === null) {
        await saveCurrentResult();
        if (savedCompanyId === null) return;   // lưu thất bại, lỗi đã hiện
      }
      await openAsLead(savedCompanyId);
    } catch (_) {
      showError(t("crm.error.saveFailed"), "");
    }
  }

  // -- Lưu vào database ---------------------------------------------------

  async function refreshNavBadge() {
    try {
      const response = await fetch("/api/companies");
      if (!response.ok) return;
      const payload = await response.json();
      setNavBadge((payload.companies || []).length);
    } catch (_) {
      // Không lấy được số lượng thì cũng không ảnh hưởng việc quét.
    }
  }

  async function saveCurrentResult() {
    if (!result || saveState === "saving") return;
    saveState = "saving";
    renderResults();
    try {
      const response = await fetch("/api/companies", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ result }),
      });
      if (!response.ok) throw new Error(String(response.status));
      savedCompanyId = (await response.json()).id;
      saveState = "saved";
      refreshNavBadge();
    } catch (_) {
      saveState = "error";
      showError(t("error.saveFailed"), t("error.saveFailedDetail"));
    }
    renderResults();
  }

  /* Mở lại một công ty đã lưu: trang /saved điều hướng sang "/?company=<id>". */
  async function loadSavedCompany(id) {
    try {
      const response = await fetch(`/api/companies/${encodeURIComponent(id)}`);
      if (!response.ok) throw new Error(String(response.status));
      const saved = await response.json();
      if (!saved.result) throw new Error("empty");
      result = saved.result;
      savedCompanyId = saved.id;
      saveState = "saved";     // đang xem đúng bản nằm trong database
      urlInput.value = "";     // sẵn sàng cho lần quét sau
      setScanning(false);
      renderResults();
    } catch (_) {
      showError(t("error.openSavedFailed"), t("error.openSavedFailedDetail"));
    }
  }

  // -- Chạy quét ----------------------------------------------------------

  function startScan() {
    const raw = urlInput.value.trim();
    if (!raw || scanning) return;

    clearError();
    result = null;
    showJson = false;
    saveState = "idle";
    savedCompanyId = null;
    renderResults();
    stageState = STAGE_IDS.map((id, index) => ({ id, done: false, active: index === 0 }));
    setScanning(true);
    renderProgress();

    if (eventSource) eventSource.close();
    eventSource = new EventSource(`/api/scan/stream?url=${encodeURIComponent(raw)}`);

    eventSource.addEventListener("progress", (event) => {
      markStage(JSON.parse(event.data).stage);
    });

    eventSource.addEventListener("result", (event) => {
      result = JSON.parse(event.data);
      markStage("done");
      // Quét xong thì dọn ô nhập để gõ URL tiếp theo mà không phải xoá tay.
      // URL vừa quét vẫn hiện ở dòng "Nguồn:" trong phần kết quả.
      urlInput.value = "";
      setScanning(false);
      eventSource.close();
      renderResults();
      resultsBox.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    const failed = (payload) => {
      setScanning(false);
      stageState = stageState.map((stage) => ({ ...stage, active: false }));
      renderProgress();
      eventSource.close();
      if (payload) {
        const known = payload.code && ERROR_CODES.includes(payload.code);
        showError(known ? t("error." + payload.code) : (payload.message || t("error.internal")),
                  payload.code ? "code: " + payload.code : "");
      } else {
        showError(t("error.unreachable"), t("error.disconnected"));
      }
    };

    // Sự kiện có tên: bản thân lần quét lỗi và server nói rõ lý do.
    eventSource.addEventListener("scan_error", (event) => {
      let payload = null;
      try { payload = JSON.parse(event.data); } catch (_) { payload = null; }
      failed(payload);
    });

    // Sự kiện không tên: mất kết nối.
    eventSource.addEventListener("error", () => {
      if (!scanning) return;
      failed(null);
    });
  }

  scanBtn.addEventListener("click", startScan);
  urlInput.addEventListener("keydown", (event) => { if (event.key === "Enter") startScan(); });
  urlInput.addEventListener("input", () => { scanBtn.disabled = scanning || !urlInput.value.trim(); });

  setScanning(false);
  renderProgress();
  refreshNavBadge();

  // Đổi ngôn ngữ: vẽ lại kết quả đang hiển thị thay vì bắt quét lại.
  window.addEventListener("langchange", () => {
    setScanning(scanning);
    renderProgress();
    renderResults();
  });

  const params = new URLSearchParams(window.location.search);
  const requestedCompany = params.get("company");
  if (requestedCompany) loadSavedCompany(requestedCompany);

  // /?url=<website>&autoscan=1 — nút "Quét lại" ở trang công ty đã lưu.
  if (params.get("url") && params.get("autoscan") === "1") {
    urlInput.value = params.get("url");
    window.history.replaceState({}, "", "/");
    startScan();
  }
}

// =========================================================================
//  TRANG CÔNG TY ĐÃ LƯU
// =========================================================================

if (isSavedPage) {
  const savedRows = document.getElementById("saved-rows");
  const savedCount = document.getElementById("saved-count");
  const savedEmpty = document.getElementById("saved-empty");
  const savedFilter = document.getElementById("saved-filter");

  let savedCompanies = [];   // bản đã tải về, dùng để lọc tại chỗ

  function signalPill(level, jobs) {
    const tone = { High: "high", Medium: "medium", Low: "low", None: "none" }[level] || "none";
    const levelText = t("signal." + (level || "None"));
    return `<span class="saved-pill saved-pill-${tone}">${esc(levelText)} · ${esc(t("saved.jobsUnit", { count: Number(jobs) || 0 }))}</span>`;
  }

  /* Thay đổi số tin IT so với lần quét trước: ▲ +3 là tín hiệu mua rõ nhất. */
  function trendBadge(company) {
    const delta = company.jobs_delta;
    if (delta === null || delta === undefined || delta === 0) return "";
    const up = delta > 0;
    const title = t("saved.trendTitle", { prev: company.prev_it_jobs, date: localDate(company.prev_scanned_at) });
    return `<span class="saved-trend ${up ? "saved-trend-up" : "saved-trend-down"}" title="${esc(title)}">${up ? "▲ +" : "▼ "}${delta}</span>`;
  }

  function cell(value, truncate = false) {
    if (value === null || value === undefined || value === "") {
      return `<span class="saved-muted">${esc(NOT_FOUND())}</span>`;
    }
    return truncate ? `<span class="saved-truncate" title="${esc(value)}">${esc(value)}</span>` : esc(value);
  }

  function localDate(value) {
    if (!value) return "";
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return "";
    const locale = i18n.getLang() === "ko" ? "ko-KR" : "vi-VN";
    return parsed.toLocaleDateString(locale, { day: "2-digit", month: "2-digit", year: "numeric" });
  }

  /* Danh sách đang hiển thị: toàn bộ, hoặc phần khớp ô tìm kiếm. */
  let trendOnly = false;   // chỉ công ty có số tin IT tăng so với lần quét trước

  function visibleCompanies() {
    const query = savedFilter.value.trim().toLowerCase();
    const pool = trendOnly ? savedCompanies.filter((company) => (company.jobs_delta || 0) > 0) : savedCompanies;
    if (!query) return pool;
    return pool.filter((company) =>
      [company.name, company.industry, company.website, company.domain, company.address, company.email, company.biz_number, company.ceo]
        .some((field) => (field || "").toLowerCase().includes(query)));
  }

  function renderSaved() {
    const query = savedFilter.value.trim().toLowerCase();
    const companies = visibleCompanies();

    setNavBadge(savedCompanies.length);
    savedCount.textContent = query
      ? t("saved.countFiltered", {
          shown: companies.length, total: savedCompanies.length, query: savedFilter.value.trim(),
        })
      : trendOnly
        ? t("saved.countTrend", { shown: companies.length, total: savedCompanies.length })
        : t("saved.count", { total: savedCompanies.length });

    savedEmpty.classList.toggle("hidden", companies.length > 0);
    if (companies.length === 0) {
      savedEmpty.textContent = savedCompanies.length === 0
        ? t("saved.empty")
        : t("saved.emptyFiltered");
      savedRows.innerHTML = "";
      return;
    }

    savedRows.innerHTML = companies.map((company) => `
      <tr data-id="${company.id}">
        <td class="saved-name">${cell(company.name)}${company.biz_number ? `<div class="saved-sub">${esc(company.biz_number)}</div>` : ""}</td>
        <td>${cell(company.address, true)}</td>
        <td>${cell(company.phone)}</td>
        <td>${company.email
          ? `<a href="mailto:${esc(company.email)}" class="saved-truncate text-blue-600 hover:text-blue-700" title="${esc(company.email)}">${esc(company.email)}</a>`
          : `<span class="saved-muted">${esc(NOT_FOUND())}</span>`}</td>
        <td>${cell(company.industry, true)}</td>
        <td>${company.website
          ? `<a href="${esc(company.website)}" target="_blank" rel="noopener noreferrer"
               class="saved-truncate text-blue-600 hover:text-blue-700" title="${esc(company.website)}">${esc(company.domain || company.website)}</a>`
          : `<span class="saved-muted">${esc(NOT_FOUND())}</span>`}</td>
        <td>${signalPill(company.it_hiring, company.it_jobs)}${trendBadge(company)}</td>
        <td class="saved-date">${esc(localDate(company.updated_at))}</td>
        <td>
          <div class="saved-actions">
            <button class="saved-btn saved-btn-icon" data-action="open" data-id="${company.id}" title="${esc(t("saved.action.view"))}" aria-label="${esc(t("saved.action.view"))}">${icon("eye", 14)}</button>
            <button class="saved-btn saved-btn-icon" data-action="rescan" data-id="${company.id}" data-url="${esc(company.website || "")}" title="${esc(t("saved.action.rescanTitle"))}" aria-label="${esc(t("saved.action.rescan"))}">${icon("refresh", 14)}</button>
            <button class="saved-btn saved-btn-icon saved-btn-lead" data-action="lead" data-id="${company.id}" title="${esc(t("crm.lead.addFromScan"))}" aria-label="${esc(t("saved.action.lead"))}">${icon("userplus", 14)}</button>
            <button class="saved-btn saved-btn-icon saved-btn-danger" data-action="delete" data-id="${company.id}" title="${esc(t("saved.action.delete"))}" aria-label="${esc(t("saved.action.delete"))}">${icon("trash", 14)}</button>
          </div>
        </td>
      </tr>`).join("");
  }

  async function loadSaved() {
    try {
      const response = await fetch("/api/companies");
      if (!response.ok) throw new Error(String(response.status));
      const payload = await response.json();
      savedCompanies = payload.companies || [];
      renderSaved();
    } catch (_) {
      savedCount.textContent = t("saved.loadFailed");
    }
  }

  async function deleteSaved(id, name) {
    if (!window.confirm(t("saved.confirmDelete", { name: name || t("saved.thisCompany") }))) return;
    try {
      const response = await fetch(`/api/companies/${id}`, { method: "DELETE" });
      if (!response.ok) throw new Error(String(response.status));
      await loadSaved();
    } catch (_) {
      savedCount.textContent = t("saved.deleteFailed");
    }
  }

  savedRows.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-action]");
    if (!button) {
      // Bấm vào dòng (không phải link/nút) cũng mở kết quả đầy đủ.
      const row = event.target.closest("tr[data-id]");
      if (row && !event.target.closest("a")) window.location.href = `/?company=${encodeURIComponent(row.dataset.id)}`;
      return;
    }
    const id = button.dataset.id;
    if (button.dataset.action === "open") {
      // Kết quả đầy đủ hiển thị ở trang quét.
      window.location.href = `/?company=${encodeURIComponent(id)}`;
    } else if (button.dataset.action === "lead") {
      openAsLead(id).catch(() => { savedCount.textContent = t("crm.error.saveFailed"); });
    } else if (button.dataset.action === "rescan") {
      // Trang quét tự bắt đầu với URL này; lưu lại sẽ ghi thêm một dòng lịch sử.
      window.location.href = `/?url=${encodeURIComponent(button.dataset.url)}&autoscan=1`;
    } else {
      deleteSaved(id, (button.closest("tr").querySelector(".saved-name").firstChild || {}).textContent?.trim());
    }
  });

  // -- Xuất file ----------------------------------------------------------
  // Xuất đúng những dòng đang hiển thị: đang lọc thì chỉ xuất phần khớp,
  // nên muốn lấy riêng một công ty thì lọc tên công ty đó rồi xuất.

  function exportFileName(extension) {
    const query = savedFilter.value.trim();
    const suffix = query ? `_${query.replace(/[^\p{L}\p{N}]+/gu, "_")}` : "";
    return `saved_companies${suffix}.${extension}`;
  }

  function exportCsv() {
    const companies = visibleCompanies();
    const rows = [[
      t("csv.name"), t("csv.biz"), t("csv.ceo"), t("csv.address"), t("csv.phone"), t("csv.email"), t("csv.industry"),
      t("csv.website"), t("csv.hiring"), t("csv.jobCount"), t("csv.jobDelta"), t("csv.contactCount"), t("csv.updated"),
    ]];
    companies.forEach((company) => rows.push([
      company.name || NOT_FOUND(),
      company.biz_number || NOT_FOUND(),
      company.ceo || NOT_FOUND(),
      company.address || NOT_FOUND(),
      company.phone || NOT_FOUND(),
      company.email || NOT_FOUND(),
      company.industry || NOT_FOUND(),
      company.website || NOT_FOUND(),
      t("signal." + (company.it_hiring || "None")),
      company.it_jobs ?? 0,
      company.jobs_delta === null || company.jobs_delta === undefined ? "" : company.jobs_delta,
      company.contacts ?? 0,
      localDate(company.updated_at),
    ]));
    const csv = rows.map((row) => row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",")).join("\n");
    // BOM để Excel mở đúng tiếng Hàn / tiếng Việt.
    download(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" }), exportFileName("csv"));
  }

  async function exportJson() {
    // Bản JSON kèm toàn bộ kết quả scan: key contacts, tin tuyển dụng, source URL.
    let detailed = [];
    try {
      const response = await fetch("/api/companies?full=1");
      if (!response.ok) throw new Error(String(response.status));
      detailed = (await response.json()).companies || [];
    } catch (_) {
      savedCount.textContent = t("saved.exportFailed");
      return;
    }
    const keep = new Set(visibleCompanies().map((company) => company.id));
    const payload = detailed.filter((company) => keep.has(company.id));
    download(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }), exportFileName("json"));
  }

  const exportBtn = document.getElementById("export-btn");
  const exportMenu = document.getElementById("export-menu");
  exportBtn.addEventListener("click", (event) => {
    event.stopPropagation();
    exportMenu.classList.toggle("hidden");
  });
  document.getElementById("export-csv").addEventListener("click", () => {
    exportCsv();
    exportMenu.classList.add("hidden");
  });
  document.getElementById("export-json").addEventListener("click", () => {
    exportJson();
    exportMenu.classList.add("hidden");
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest("#export-menu") && !event.target.closest("#export-btn")) {
      exportMenu.classList.add("hidden");
    }
  });

  document.getElementById("saved-refresh").addEventListener("click", loadSaved);
  savedFilter.addEventListener("input", renderSaved);
  const trendToggle = document.getElementById("saved-trend-toggle");
  if (trendToggle) {
    trendToggle.addEventListener("click", () => {
      trendOnly = !trendOnly;
      trendToggle.classList.toggle("saved-toggle-active", trendOnly);
      renderSaved();
    });
  }

  /* Câu mô tả có chèn tên nút "Xem" nên phải dựng bằng JS, không dùng data-i18n. */
  function renderDescription() {
    const description = document.getElementById("saved-description");
    if (!description) return;
    description.innerHTML = esc(t("saved.description", { view: "\u0000" }))
      .replace("\u0000", `<strong class="font-semibold text-slate-700">${esc(t("saved.action.view"))}</strong>`);
  }

  // Đổi ngôn ngữ: vẽ lại phần động (bảng, mô tả) chứ không phải tải lại trang.
  window.addEventListener("langchange", () => {
    renderDescription();
    renderSaved();
  });

  renderDescription();
  loadSaved();
}
