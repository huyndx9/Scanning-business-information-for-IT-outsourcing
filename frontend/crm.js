/* CRM 리드 — trang /crm. Dùng icon(), esc(), download() từ app.js và t() từ i18n.js.

   Mọi lead đều nằm trong SQLite (/api/leads); không có dữ liệu mẫu. Lead có
   thể tạo tay, nhập từ CSV/JSON, hoặc chuyển từ kết quả quét (company_id). */

(function () {
  const STATUSES = ["new", "contacted", "meeting", "proposal", "negotiation", "won", "lost", "hold"];
  const OPEN_STATUSES = ["new", "contacted", "meeting", "proposal", "negotiation"];
  const KANBAN_COLUMNS = ["new", "contacted", "meeting", "proposal", "negotiation", "won"];
  const STATUS_TONE = {
    new: "slate", contacted: "blue", meeting: "indigo", proposal: "amber",
    negotiation: "violet", won: "emerald", lost: "rose", hold: "stone",
  };
  const OPTION_LISTS = {
    status: STATUSES,
    rank: ["staff", "assistant", "manager", "deputy", "general", "director", "md", "evp", "svp", "ceo", "cto", "cio", "other"],
    source: ["scanner", "referral", "exhibition", "linkedin", "wanted", "saramin", "jobkorea", "coldcall", "website", "naver", "customer", "other"],
    project: ["dispatch", "contract", "si", "sm", "odc", "other"],
    size: ["enterprise", "midsize", "sme", "startup", "public"],
    lost: ["price", "schedule", "competitor", "inhouse", "budget", "language", "other"],
    activity: ["call", "email", "kakao", "meeting", "proposal", "quote", "other"],
  };
  const HOT_SCORE = 80;
  // Cột có thể ẩn; 기술스택 ẩn mặc định để bảng vừa laptop 13" (tech hiện ở tooltip tên công ty).
  const TOGGLABLE_COLUMNS = ["source", "tech", "budget", "timing", "score", "status", "next"];
  const COLUMNS_KEY = "company-scanner-crm-columns";
  const DEFAULT_HIDDEN = ["tech"];

  const $ = (id) => document.getElementById(id);

  /* Thông báo ngắn góc dưới, thay cho alert() để không chặn thao tác. */
  function toast(message, tone = "ok") {
    let host = $("crm-toast");
    if (!host) {
      host = document.createElement("div");
      host.id = "crm-toast";
      document.body.appendChild(host);
    }
    const item = document.createElement("div");
    item.className = `crm-toast-item crm-toast-${tone}`;
    item.textContent = message;
    host.appendChild(item);
    setTimeout(() => item.classList.add("crm-toast-show"), 10);
    setTimeout(() => { item.classList.remove("crm-toast-show"); setTimeout(() => item.remove(), 300); }, 3500);
  }
  const rows = $("crm-rows");
  const emptyBox = $("crm-empty");
  const searchInput = $("crm-search");
  const assigneeSelect = $("crm-assignee");
  const kanban = $("crm-kanban");
  const tableWrap = $("crm-table-wrap");

  let leads = [];
  let hiddenColumns = new Set(DEFAULT_HIDDEN);
  try {
    const stored = JSON.parse(localStorage.getItem(COLUMNS_KEY) || "null");
    if (Array.isArray(stored)) hiddenColumns = new Set(stored.filter((c) => TOGGLABLE_COLUMNS.includes(c)));
  } catch (_) { /* mặc định */ }
  let customersByKey = {};    // khách đã ký, khoá domain / tên thường: để gắn "기존 고객" lên lead
  let quick = "all";          // all | hot | overdue | week
  let statusFilter = "";      // "" = tất cả
  let view = "table";
  let selected = new Set();
  let editing = null;         // lead đang mở trong modal, hoặc null khi thêm mới
  let importFile = null;      // { filename, content_base64 }

  // -- Nhãn / định dạng ----------------------------------------------------------

  const label = (group, code) => (code ? t(`crm.${group}.${code}`) : "");
  const statusLabel = (code) => label("status", code);

  const fmtKRW = (amount) => formatKRW(amount);

  function todayIso() {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  }

  function isOverdue(lead) {
    return Boolean(lead.next_date && OPEN_STATUSES.includes(lead.status) && lead.next_date < todayIso());
  }

  function withinWeek(lead) {
    if (!lead.next_date || !OPEN_STATUSES.includes(lead.status)) return false;
    const end = new Date();
    end.setDate(end.getDate() + 7);
    const endIso = `${end.getFullYear()}-${String(end.getMonth() + 1).padStart(2, "0")}-${String(end.getDate()).padStart(2, "0")}`;
    return lead.next_date >= todayIso() && lead.next_date <= endIso;
  }

  function initial(name) {
    const value = (name || "").trim();
    return value ? value[0].toUpperCase() : "?";
  }

  function scoreTone(score) {
    return score >= HOT_SCORE ? "emerald" : score >= 50 ? "amber" : "rose";
  }

  function breakdownText(lead) {
    const parts = (lead.score_breakdown || []).map((part) => `${t("crm.score." + part.key)} +${part.points}`);
    return parts.length ? `${t("crm.form.scoreWhy")}: ${parts.join(" · ")}` : "";
  }

  function fullWon(amount) {
    const value = Number(amount);
    return Number.isFinite(value) && value > 0 ? `${value.toLocaleString()}원` : "";
  }

  function pill(text, tone = "slate") {
    return `<span class="crm-pill crm-pill-${tone}">${esc(text)}</span>`;
  }

  function statusSelect(lead) {
    const options = STATUSES.map((code) =>
      `<option value="${code}" ${code === lead.status ? "selected" : ""}>${esc(statusLabel(code))}</option>`).join("");
    return `<span class="crm-status-wrap crm-status-${STATUS_TONE[lead.status]}"><select class="crm-status" data-status-for="${lead.id}" title="${esc(t("crm.statusChange"))}">${options}</select></span>`;
  }

  function fillSelect(select, group, blank) {
    const current = select.value;
    select.innerHTML = (blank ? `<option value="">—</option>` : "") +
      OPTION_LISTS[group].map((code) => `<option value="${code}">${esc(label(group, code))}</option>`).join("");
    if (current) select.value = current;
  }

  function fillAllSelects() {
    document.querySelectorAll("select[data-options]").forEach((select) => {
      fillSelect(select, select.dataset.options, select.dataset.blank === "1");
    });
    const bulk = $("crm-bulk-status");
    bulk.innerHTML = `<option value="">${esc(t("crm.bulk.status"))}</option>` +
      STATUSES.map((code) => `<option value="${code}">${esc(statusLabel(code))}</option>`).join("");
  }

  // -- Lọc ----------------------------------------------------------------------

  function visibleLeads() {
    const query = searchInput.value.trim().toLowerCase();
    const assignee = assigneeSelect.value;
    return leads.filter((lead) => {
      if (quick === "hot" && lead.score < HOT_SCORE) return false;
      if (quick === "overdue" && !isOverdue(lead)) return false;
      if (quick === "week" && !withinWeek(lead)) return false;
      if (statusFilter && lead.status !== statusFilter) return false;
      if (assignee && (lead.assignee || "") !== assignee) return false;
      if (query) {
        const haystack = [lead.company_name, lead.contact_name, lead.phone, lead.mobile, lead.email,
          lead.kakao, lead.biz_number, lead.industry, lead.website, lead.memo, lead.competitor,
          ...(lead.tech || [])].join(" ").toLowerCase();
        if (!haystack.includes(query)) return false;
      }
      return true;
    });
  }

  /* Khách đã ký khớp với lead này (theo domain, không có thì theo tên công ty). */
  function customerOf(lead) {
    if (!lead) return null;
    if (lead.domain && customersByKey[lead.domain]) return customersByKey[lead.domain];
    const name = (lead.company_name || "").trim().toLowerCase();
    return name ? customersByKey[name] || null : null;
  }

  function customerLink(customer) {
    return `/crm/customers?q=${encodeURIComponent(customer.company_name)}`;
  }

  async function loadCustomers() {
    try {
      const payload = await api("/api/customers");
      customersByKey = {};
      (payload.customers || []).forEach((customer) => {
        customersByKey[customer.key] = customer;
        customersByKey[(customer.company_name || "").trim().toLowerCase()] = customer;
      });
      refreshSubnavCounts({ leads: leads.length, customers: (payload.customers || []).length });
    } catch (_) {
      // Không có thông tin khách thì lead vẫn hiển thị bình thường.
    }
  }

  // -- Phễu (funnel) -----------------------------------------------------------------

  let stats = null;

  async function loadStats() {
    try {
      stats = await api("/api/leads/stats");
    } catch (_) {
      stats = null;
    }
    renderFunnel();
  }

  function renderFunnel() {
    const box = $("crm-funnel-body");
    if (!box) return;
    if (!stats || !stats.total) {
      box.innerHTML = `<div class="crm-empty">${esc(t("crm.funnel.empty"))}</div>`;
      return;
    }
    const max = Math.max(1, ...stats.stages.map((s) => s.reached));
    box.innerHTML = `<div class="crm-funnel-grid">${stats.stages.map((row, index) => {
      const width = Math.max(4, Math.round((row.reached / max) * 100));
      const dropNote = row.lost || row.hold
        ? `<span class="crm-funnel-lost" title="${esc(t("crm.funnel.lostTitle"))}">${esc(t("crm.funnel.lost", { lost: row.lost, hold: row.hold }))}</span>` : "";
      return `<div class="crm-funnel-row">
        <div class="crm-funnel-label"><span class="crm-dot crm-dot-${STATUS_TONE[row.stage]}"></span>${esc(statusLabel(row.stage))}</div>
        <div class="crm-funnel-bar-wrap"><div class="crm-funnel-bar crm-funnel-bar-${STATUS_TONE[row.stage]}" style="width:${width}%"></div>
          <span class="crm-funnel-count">${esc(t("crm.funnel.reached", { count: row.reached, now: row.now }))}</span></div>
        <div class="crm-funnel-meta">
          ${row.conversion !== null && row.conversion !== undefined ? `<span class="crm-funnel-conv">→ ${row.conversion}%</span>` : `<span class="crm-funnel-conv crm-funnel-won">${esc(t("crm.funnel.goal"))}</span>`}
          ${row.avg_days !== null && row.avg_days !== undefined ? `<span class="crm-meta">${esc(t("crm.funnel.avgDays", { days: row.avg_days }))}</span>` : ""}
          ${dropNote}
        </div>
      </div>`;
    }).join("")}</div>
    <div class="crm-funnel-foot">${esc(stats.velocity_days !== null && stats.velocity_days !== undefined
      ? t("crm.funnel.velocity", { days: stats.velocity_days, won: stats.won })
      : t("crm.funnel.velocityNone"))}</div>`;
  }

  // -- KPI ----------------------------------------------------------------------

  function renderKpis() {
    const open = leads.filter((lead) => OPEN_STATUSES.includes(lead.status));
    const pipeline = open.reduce((sum, lead) => sum + (Number(lead.budget) || 0), 0);
    const won = leads.filter((lead) => lead.status === "won").length;
    const lost = leads.filter((lead) => lead.status === "lost").length;
    const closed = won + lost;
    const month = todayIso().slice(0, 7);
    const newThisMonth = leads.filter((lead) => (lead.created_at || "").slice(0, 7) === month);
    const hot = newThisMonth.filter((lead) => lead.score >= HOT_SCORE).length;
    const overdue = leads.filter(isOverdue).length;

    // Ô KPI bấm được: đặt luôn bộ lọc tương ứng (연체 -> chỉ lead quá hạn...).
    const tile = (labelText, value, sub, tone = "", quickKey = "") => `<div class="crm-kpi ${quickKey ? "crm-kpi-click" : ""}" ${quickKey ? `data-kpi-quick="${quickKey}" title="${esc(t("crm.kpi.clickHint"))}"` : ""}>
      <div class="crm-kpi-label">${esc(labelText)}</div>
      <div class="crm-kpi-value ${tone === "danger" ? "crm-kpi-danger" : ""}">${esc(value)}</div>
      <div class="crm-kpi-sub ${tone === "danger" ? "crm-kpi-danger" : "crm-kpi-ok"}">${esc(sub)}</div>
    </div>`;

    $("crm-kpis").innerHTML =
      tile(t("crm.kpi.pipeline"), fmtKRW(pipeline) || "₩ 0", t("crm.kpi.pipelineSub", { count: open.length }), "", "all") +
      tile(t("crm.kpi.winRate"), closed ? `${Math.round((won / closed) * 100)}%` : "—",
        stats && stats.velocity_days !== null && stats.velocity_days !== undefined
          ? t("crm.kpi.winRateVelocity", { won, closed, days: stats.velocity_days })
          : t("crm.kpi.winRateSub", { won, closed })) +
      tile(t("crm.kpi.newMonth"), String(newThisMonth.length), t("crm.kpi.newMonthSub", { count: hot }), "", "hot") +
      tile(t("crm.kpi.overdue"), String(overdue), overdue ? t("crm.kpi.overdueSub") : t("crm.kpi.overdueNone"), overdue ? "danger" : "", "overdue");
  }

  // -- Bảng ---------------------------------------------------------------------

  function renderStatusFilters() {
    $("crm-status-filters").innerHTML = STATUSES.map((code) => {
      const count = leads.filter((lead) => lead.status === code).length;
      const active = statusFilter === code;
      return `<button class="crm-chip crm-chip-${STATUS_TONE[code]} ${active ? "crm-chip-active" : ""}" data-status-filter="${code}">
        ${esc(statusLabel(code))}<span class="crm-chip-count">${count}</span></button>`;
    }).join("");
  }

  function renderAssignees() {
    const names = [...new Set(leads.map((lead) => lead.assignee).filter(Boolean))].sort();
    const current = assigneeSelect.value;
    assigneeSelect.innerHTML = `<option value="">${esc(t("crm.filter.allAssignees"))}</option>` +
      names.map((name) => `<option value="${esc(name)}">${esc(name)}</option>`).join("");
    if (names.includes(current)) assigneeSelect.value = current;
    $("crm-assignee-list").innerHTML = names.map((name) => `<option value="${esc(name)}">`).join("");
  }

  function renderRow(lead) {
    const overdue = isOverdue(lead);
    const tech = (lead.tech || []).slice(0, 3).map((item) => pill(item, "tech")).join("");
    const meta = [lead.biz_number, lead.mobile || lead.phone].filter(Boolean).join(" · ");
    const contactMeta = [label("rank", lead.rank), lead.department].filter(Boolean).join(" · ");
    const timing = lead.expected_start
      ? `<div class="crm-strong">${esc(lead.expected_start)}</div>`
      : `<span class="saved-muted">—</span>`;
    const timingMeta = [
      lead.team_size ? t("crm.people", { count: lead.team_size }) : "",
      lead.bridge_se ? t("crm.bridge") : "",
      label("project", lead.project_type),
    ].filter(Boolean).join(" · ");

    const techTitle = (lead.tech || []).length ? `${t("crm.col.tech")}: ${lead.tech.join(", ")}` : "";
    const col = (name) => (hiddenColumns.has(name) ? ' class="crm-col-hidden"' : "");
    const phoneHref = lead.mobile || lead.phone ? `tel:${(lead.mobile || lead.phone).replace(/[^\d+]/g, "")}` : "";
    return `<tr data-id="${lead.id}" class="${overdue ? "crm-row-overdue" : ""} ${selected.has(lead.id) ? "crm-row-selected" : ""}">
      <td class="crm-td-check"><input type="checkbox" data-select="${lead.id}" ${selected.has(lead.id) ? "checked" : ""}></td>
      <td>
        <div class="crm-strong crm-clip" title="${esc([lead.company_name, techTitle].filter(Boolean).join("\n"))}">${esc(lead.company_name)}</div>
        <div class="crm-meta">${esc(meta)}${customerOf(lead) ? ` <a href="${customerLink(customerOf(lead))}" class="crm-customer-pill" title="${esc(t("crm.existingCustomerTitle"))}">${esc(t("crm.existingCustomer", { grade: customerOf(lead).grade }))}</a>` : ""}</div>
      </td>
      <td>
        <div class="crm-contact">
          <span class="crm-avatar">${esc(initial(lead.contact_name))}</span>
          <div class="min-w-0">
            <div class="crm-clip">${lead.contact_name ? esc(lead.contact_name) : `<span class="saved-muted">—</span>`}</div>
            <div class="crm-meta crm-clip">${esc(contactMeta)}</div>
          </div>
        </div>
      </td>
      <td${col("source")}>${lead.source === "scanner" && lead.company_id
        ? `<a href="/?company=${lead.company_id}" class="crm-pill crm-pill-source crm-pill-link" title="${esc(t("crm.sourceScanLink"))}">${esc(label("source", lead.source))} ${icon("external", 10)}</a>`
        : pill(label("source", lead.source), "source")}</td>
      <td${col("tech")}><div class="crm-pills">${tech || `<span class="saved-muted">—</span>`}</div></td>
      <td class="crm-strong crm-nowrap${hiddenColumns.has("budget") ? " crm-col-hidden" : ""}" title="${esc(fullWon(lead.budget))}">${fmtKRW(lead.budget) || `<span class="saved-muted">—</span>`}</td>
      <td${col("timing")}>${timing}<div class="crm-meta">${esc(timingMeta)}</div></td>
      <td${col("score")}>
        <span class="crm-ring crm-ring-${scoreTone(lead.score)}" title="${esc(breakdownText(lead))}">${lead.score}</span>
      </td>
      <td${col("status")}>${statusSelect(lead)}${lead.days_in_stage !== null && lead.days_in_stage !== undefined && OPEN_STATUSES.includes(lead.status)
        ? `<div class="crm-meta crm-stage-days ${lead.days_in_stage >= 14 ? "crm-stage-stale" : ""}" title="${esc(t("crm.stageSinceTitle", { date: (lead.stage_since || "").slice(0, 10) }))}">${esc(t("crm.stageDays", { days: lead.days_in_stage }))}</div>` : ""}</td>
      <td class="${overdue ? "crm-next-overdue" : "crm-next"}${hiddenColumns.has("next") ? " crm-col-hidden" : ""}">
        ${overdue ? `${icon("alert", 13)} ${esc(t("crm.overdueTag"))} · ` : ""}${lead.next_date ? esc(lead.next_date) : `<span class="saved-muted">—</span>`}
        ${lead.next_action ? `<div class="crm-meta crm-clip" title="${esc(lead.next_action)}">${esc(lead.next_action)}</div>` : ""}
      </td>
      <td class="crm-td-actions">
        <div class="crm-quick">
          ${phoneHref ? `<a href="${esc(phoneHref)}" class="crm-quick-btn" title="${esc(t("crm.quick.call", { number: lead.mobile || lead.phone }))}">${icon("phone", 14)}</a>` : ""}
          ${lead.email ? `<button type="button" class="crm-quick-btn" data-quick-mail="${lead.id}" title="${esc(t("crm.quick.mail", { email: lead.email }))}">${icon("mail", 14)}</button>` : ""}
          ${lead.kakao ? `<button type="button" class="crm-quick-btn" data-quick-kakao="${esc(lead.kakao)}" title="${esc(t("crm.quick.kakao", { id: lead.kakao }))}">${icon("chat", 14)}</button>` : ""}
          <button type="button" class="crm-quick-btn" data-quick-log="${lead.id}" title="${esc(t("crm.quick.log"))}">${icon("note", 14)}</button>
        </div>
      </td>
    </tr>`;
  }

  function applyColumnVisibility() {
    document.querySelectorAll(".crm-table th[data-col]").forEach((th) => {
      th.classList.toggle("crm-col-hidden", hiddenColumns.has(th.dataset.col));
    });
  }

  function renderColumnsMenu() {
    $("crm-columns-menu").innerHTML = TOGGLABLE_COLUMNS.map((name) => `<label class="crm-menu-item crm-menu-check">
      <input type="checkbox" data-col-toggle="${name}" ${hiddenColumns.has(name) ? "" : "checked"}> ${esc(t("crm.col." + name))}</label>`).join("");
  }

  function renderTable(list) {
    applyColumnVisibility();
    rows.innerHTML = list.map(renderRow).join("");
    emptyBox.classList.toggle("hidden", list.length > 0);
    if (list.length === 0) {
      emptyBox.innerHTML = leads.length === 0
        ? `<div class="crm-empty-title">${esc(t("crm.empty"))}</div><div>${esc(t("crm.emptyDesc"))}</div>`
        : esc(t("crm.emptyFiltered"));
    }
    $("crm-check-all").checked = list.length > 0 && list.every((lead) => selected.has(lead.id));
  }

  // -- Kanban -------------------------------------------------------------------

  let expandedClosed = new Set();   // cột 실패/보류 đang mở rộng

  function renderKanban(list) {
    const card = (lead) => {
      const overdue = isOverdue(lead);
      return `<div class="crm-kcard" draggable="true" data-id="${lead.id}">
      <div class="crm-kcard-top">
        <span class="crm-grip" title="${esc(t("crm.kanban.drag"))}">${icon("grip", 12)}</span>
        <div class="crm-strong crm-clip">${esc(lead.company_name)}</div>
        ${lead.assignee ? `<span class="crm-assignee" title="${esc(lead.assignee)}">${esc(initial(lead.assignee))}</span>` : ""}
      </div>
      <div class="crm-meta crm-clip">${esc([lead.contact_name, label("rank", lead.rank)].filter(Boolean).join(" · ") || "—")}</div>
      ${lead.next_action || lead.next_date ? `<div class="crm-kcard-next ${overdue ? "crm-next-overdue" : ""}">${overdue ? icon("alert", 11) + " " : ""}${esc([lead.next_date, lead.next_action].filter(Boolean).join(" · "))}</div>` : ""}
      <div class="crm-kcard-foot">
        <span class="crm-strong" title="${esc(fullWon(lead.budget))}">${fmtKRW(lead.budget) || "—"}</span>
        <span class="crm-ring crm-ring-sm crm-ring-${scoreTone(lead.score)}" title="${esc(breakdownText(lead))}">${lead.score}</span>
      </div>
    </div>`;
    };

    const column = (code, collapsed) => {
      const items = list.filter((lead) => lead.status === code);
      const total = items.reduce((sum, lead) => sum + (Number(lead.budget) || 0), 0);
      const empty = items.length === 0;
      const open = !collapsed || expandedClosed.has(code);
      return `<div class="crm-kcol ${empty ? "crm-kcol-empty" : ""} ${collapsed ? "crm-kcol-closed" : ""} ${collapsed && !open ? "crm-kcol-collapsed" : ""}" data-column="${code}">
        <div class="crm-kcol-head" ${collapsed ? `data-expand="${code}" title="${esc(t("crm.kanban.toggle"))}"` : ""}>
          <span class="crm-dot crm-dot-${STATUS_TONE[code]}"></span>${esc(statusLabel(code))}
          <span class="crm-chip-count">${items.length}</span>
        </div>
        ${open ? `<div class="crm-kcol-body">${items.map(card).join("")}</div>
        <div class="crm-kcol-foot">${esc(t("crm.kanban.total", { count: items.length, value: fmtKRW(total) || "₩ 0" }))}</div>` : ""}
      </div>`;
    };

    // 실패 / 보류 xếp dọc trong một cột hẹp ở cuối: vẫn kéo thả vào được, bấm để mở.
    kanban.innerHTML = KANBAN_COLUMNS.map((code) => column(code, false)).join("") +
      `<div class="crm-kcol-stack">${["lost", "hold"].map((code) => column(code, true)).join("")}</div>`;
  }

  kanban.addEventListener("dragstart", (event) => {
    const card = event.target.closest(".crm-kcard");
    if (!card) return;
    event.dataTransfer.setData("text/plain", card.dataset.id);
    card.classList.add("crm-dragging");
  });
  kanban.addEventListener("dragend", (event) => {
    const card = event.target.closest(".crm-kcard");
    if (card) card.classList.remove("crm-dragging");
  });
  kanban.addEventListener("dragover", (event) => {
    const column = event.target.closest(".crm-kcol");
    if (!column) return;
    event.preventDefault();
    column.classList.add("crm-kcol-over");
  });
  kanban.addEventListener("dragleave", (event) => {
    const column = event.target.closest(".crm-kcol");
    if (column && !column.contains(event.relatedTarget)) column.classList.remove("crm-kcol-over");
  });
  kanban.addEventListener("drop", async (event) => {
    const column = event.target.closest(".crm-kcol");
    if (!column) return;
    event.preventDefault();
    column.classList.remove("crm-kcol-over");
    const id = Number(event.dataTransfer.getData("text/plain"));
    await changeStatus(id, column.dataset.column);
  });
  kanban.addEventListener("click", (event) => {
    const head = event.target.closest("[data-expand]");
    if (head) {
      const code = head.dataset.expand;
      if (expandedClosed.has(code)) expandedClosed.delete(code); else expandedClosed.add(code);
      render();
      return;
    }
    const card = event.target.closest(".crm-kcard");
    if (card) openLead(Number(card.dataset.id));
  });

  // -- Render tổng -------------------------------------------------------------

  function render() {
    const list = visibleLeads();
    renderKpis();
    renderStatusFilters();
    renderAssignees();
    const filtered = quick !== "all" || statusFilter || searchInput.value.trim() || assigneeSelect.value;
    $("crm-count").textContent = filtered
      ? t("crm.countFiltered", { shown: list.length, total: leads.length })
      : t("crm.count", { total: leads.length });
    tableWrap.classList.toggle("hidden", view !== "table");
    kanban.classList.toggle("hidden", view !== "kanban");
    if (view === "table") renderTable(list); else renderKanban(list);
    renderBulk();
    if (typeof setNavCrmBadge === "function") setNavCrmBadge(leads.length);
    const subLeads = $("sub-leads-count");
    if (subLeads) subLeads.textContent = String(leads.length);
  }

  function renderBulk() {
    const bar = $("crm-bulk");
    bar.classList.toggle("hidden", selected.size === 0);
    $("crm-bulk-count").textContent = t("crm.bulk.selected", { count: selected.size });
  }

  // -- API ----------------------------------------------------------------------

  async function api(path, options) {
    const response = await fetch(path, options);
    let payload = null;
    try { payload = await response.json(); } catch (_) { payload = null; }
    if (!response.ok) {
      const error = new Error((payload && payload.error && payload.error.code) || String(response.status));
      error.code = payload && payload.error && payload.error.code;
      throw error;
    }
    return payload;
  }

  const jsonBody = (body) => ({ method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  async function loadLeads() {
    try {
      leads = (await api("/api/leads")).leads || [];
      selected = new Set([...selected].filter((id) => leads.some((lead) => lead.id === id)));
      render();
      loadStats().then(render);
    } catch (_) {
      $("crm-count").textContent = t("crm.error.loadFailed");
    }
  }

  async function changeStatus(id, status) {
    const lead = leads.find((item) => item.id === id);
    if (!lead || lead.status === status) return;
    if (status === "lost" && !lead.lost_reason) {
      // Thua thì phải ghi lý do — mở form để chọn.
      openLead(id, { status: "lost" });
      return;
    }
    try {
      await api(`/api/leads/${id}`, { ...jsonBody({ lead: { status } }), method: "PUT" });
      await loadLeads();
      if (status === "won") offerContract(id);
    } catch (_) {
      toast(t("crm.error.saveFailed"), "error");
      render();
    }
  }

  /* Lead vừa 수주: hỏi ghi hợp đồng ngay (form điền sẵn ở trang 고객). */
  async function offerContract(id) {
    if (await askConfirm(t("crm.wonRegisterContract"), t("cust.add"))) {
      window.location.href = `/crm/customers?from_lead=${id}`;
    }
  }

  // -- Modal lead ---------------------------------------------------------------

  const leadModal = $("lead-modal");
  const form = $("lead-form");
  const leadError = $("lead-error");

  function showModal(id) { $(id).classList.remove("hidden"); document.body.classList.add("crm-lock"); }
  function hideModal(id) { $(id).classList.add("hidden"); document.body.classList.remove("crm-lock"); }

  document.querySelectorAll("[data-close]").forEach((button) => {
    button.addEventListener("click", () => hideModal(button.dataset.close));
  });
  document.querySelectorAll(".crm-overlay").forEach((overlay) => {
    overlay.addEventListener("mousedown", (event) => { if (event.target === overlay) hideModal(overlay.id); });
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") document.querySelectorAll(".crm-overlay:not(.hidden)").forEach((overlay) => hideModal(overlay.id));
  });

  function setForm(lead) {
    form.reset();
    for (const element of form.elements) {
      if (!element.name) continue;
      const value = lead[element.name];
      if (element.type === "checkbox") element.checked = Boolean(value);
      else if (element.name === "tech") element.value = (value || []).join(", ");
      else element.value = value === null || value === undefined ? "" : value;
    }
    toggleLostReason();
  }

  function readForm() {
    const data = {};
    for (const element of form.elements) {
      if (!element.name) continue;
      data[element.name] = element.type === "checkbox" ? (element.checked ? 1 : 0) : element.value.trim();
    }
    if (editing && editing.company_id) data.company_id = editing.company_id;
    return data;
  }

  function toggleLostReason() {
    $("lost-reason-row").classList.toggle("hidden", form.elements.status.value !== "lost");
  }
  form.elements.status.addEventListener("change", toggleLostReason);

  /* "Đang nói chuyện với khách cũ": hạng, tổng đã ký, link sang hợp đồng. */
  function renderCustomerBanner(customer) {
    const box = $("lead-customer");
    if (!box) return;
    if (!customer) { box.classList.add("hidden"); box.innerHTML = ""; return; }
    const total = fmtKRW(customer.total_value) || "₩ 0";
    box.classList.remove("hidden");
    box.innerHTML = `${icon("handshake", 15)} <span>${esc(t("crm.existingCustomerBanner", {
      grade: customer.grade, total, count: customer.contract_count,
      next: customer.next_end || "—",
    }))}</span> <a href="${customerLink(customer)}" class="crm-link">${esc(t("crm.existingCustomerLink"))}</a>`;
  }

  function renderScore(lead) {
    const box = $("lead-score");
    if (!lead || lead.score === undefined) { box.classList.add("hidden"); return; }
    const parts = (lead.score_breakdown || []).map((part) => `${t("crm.score." + part.key)} +${part.points}`).join(" · ");
    box.classList.remove("hidden");
    box.innerHTML = `<span class="crm-ring crm-ring-${scoreTone(lead.score)}">${lead.score}</span>
      <span class="crm-score-why" title="${esc(parts)}">${esc(t("crm.form.scoreWhy"))}<br><small>${esc(parts || "—")}</small></span>`;
  }

  function renderActivities(list) {
    const ul = $("activity-list");
    if (!list || list.length === 0) {
      ul.innerHTML = `<li class="saved-muted">${esc(t("crm.activity.empty"))}</li>`;
      return;
    }
    ul.innerHTML = list.map((activity) => `<li class="crm-activity" data-activity="${activity.id}">
      <span class="crm-pill crm-pill-act">${esc(label("activity", activity.type))}</span>
      <span class="crm-activity-date">${esc(activity.at)}</span>
      <span class="crm-activity-note">${esc(activity.note || "")}</span>
      <button type="button" class="crm-icon-btn crm-icon-btn-sm" data-delete-activity="${activity.id}" aria-label="delete">${icon("x", 13)}</button>
    </li>`).join("");
  }

  async function openLead(id, overrides, focus) {
    leadError.classList.add("hidden");
    try {
      editing = await api(`/api/leads/${id}`);
    } catch (_) {
      toast(t("crm.error.loadFailed"), "error");
      return;
    }
    $("lead-modal-title").textContent = editing.company_name;
    $("lead-modal-sub").textContent = t("crm.form.titleEdit", { source: label("source", editing.source), date: (editing.updated_at || "").slice(0, 10) });
    renderCustomerBanner(customerOf(editing));
    setForm({ ...editing, ...(overrides || {}) });
    renderScore(editing);
    $("lead-delete").classList.remove("hidden");
    const scanLink = $("lead-scan-link");
    scanLink.classList.toggle("hidden", !editing.company_id);
    if (editing.company_id) scanLink.href = `/?company=${editing.company_id}`;
    const naver = $("lead-naver-link");
    naver.classList.remove("hidden");
    naver.href = `https://search.naver.com/search.naver?query=${encodeURIComponent(editing.company_name)}`;
    $("lead-activities").classList.remove("hidden");
    $("lead-mail-btn").classList.remove("hidden");
    mailPanel.classList.add("hidden");
    $("lead-last-contact").textContent = editing.last_contact ? t("crm.activity.lastContact", { date: editing.last_contact }) : "";
    $("activity-form").elements.at.value = todayIso();
    renderActivities(editing.activities);
    showModal("lead-modal");
    // Hành động nhanh từ bảng: nhảy thẳng tới phần cần dùng.
    if (focus === "log") {
      $("lead-activities").scrollIntoView({ block: "center" });
      $("activity-form").elements.note.focus();
    } else if (focus === "mail") {
      mailPanel.classList.remove("hidden");
      renderMail();
      mailPanel.scrollIntoView({ block: "center" });
    }
  }

  function openNewLead(prefill) {
    editing = null;
    leadError.classList.add("hidden");
    $("lead-modal-title").textContent = t("crm.form.titleAdd");
    $("lead-modal-sub").textContent = t("crm.form.titleAddSub");
    renderCustomerBanner(null);
    setForm({ source: "other", status: "new", ...(prefill || {}) });
    renderScore(null);
    $("lead-delete").classList.add("hidden");
    $("lead-scan-link").classList.add("hidden");
    $("lead-naver-link").classList.add("hidden");
    $("lead-mail-btn").classList.add("hidden");
    mailPanel.classList.add("hidden");
    $("lead-activities").classList.add("hidden");
    showModal("lead-modal");
    form.elements.company_name.focus();
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const save = $("lead-save");
    save.disabled = true;
    save.textContent = t("crm.form.saving");
    leadError.classList.add("hidden");
    try {
      const data = readForm();
      if (!editing) {
        // Thêm tay: cảnh báo nếu đã có lead cùng domain / email / tên công ty.
        const query = new URLSearchParams({ company_name: data.company_name || "", email: data.email || "", website: data.website || "" });
        const found = ((await api(`/api/leads/duplicates?${query}`)).leads || []);
        if (found.length) {
          const listText = found.slice(0, 3).map((d) => `• ${d.company_name} — ${statusLabel(d.status)}${d.contact_name ? " · " + d.contact_name : ""}`).join("\n");
          const proceed = await askConfirm(t("crm.duplicateWarn", { count: found.length, list: listText }), t("crm.duplicateProceed"));
          if (!proceed) { save.disabled = false; save.textContent = t("crm.form.save"); return; }
        }
      }
      const becameWon = data.status === "won" && (!editing || editing.status !== "won");
      let savedLead = null;
      if (editing) {
        savedLead = await api(`/api/leads/${editing.id}`, { ...jsonBody({ lead: data }), method: "PUT" });
      } else {
        savedLead = await api("/api/leads", jsonBody({ lead: data }));
      }
      hideModal("lead-modal");
      await loadLeads();
      if (becameWon && savedLead) offerContract(savedLead.id);
    } catch (error) {
      const known = ["company_required", "email_invalid"].includes(error.code);
      leadError.textContent = known ? t("crm.error." + error.code) : t("crm.error.saveFailed");
      leadError.classList.remove("hidden");
    }
    save.disabled = false;
    save.textContent = t("crm.form.save");
  });

  $("lead-delete").addEventListener("click", async () => {
    if (!editing || !(await askConfirm(t("crm.confirmDeleteOne", { name: editing.company_name }), t("crm.form.delete")))) return;
    try {
      await api(`/api/leads/${editing.id}`, { method: "DELETE" });
      hideModal("lead-modal");
      await loadLeads();
    } catch (_) {
      toast(t("crm.error.saveFailed"), "error");
    }
  });

  $("activity-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!editing) return;
    const elements = event.target.elements;
    try {
      await api(`/api/leads/${editing.id}/activities`, jsonBody({
        activity: { type: elements.type.value, at: elements.at.value, note: elements.note.value.trim() },
      }));
      elements.note.value = "";
      const fresh = await api(`/api/leads/${editing.id}`);
      editing = fresh;
      renderActivities(fresh.activities);
      $("lead-last-contact").textContent = fresh.last_contact ? t("crm.activity.lastContact", { date: fresh.last_contact }) : "";
      loadLeads();
    } catch (_) {
      toast(t("crm.error.saveFailed"), "error");
    }
  });

  $("activity-list").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-delete-activity]");
    if (!button || !editing) return;
    try {
      await api(`/api/activities/${button.dataset.deleteActivity}`, { method: "DELETE" });
      editing = await api(`/api/leads/${editing.id}`);
      renderActivities(editing.activities);
    } catch (_) {
      toast(t("crm.error.saveFailed"), "error");
    }
  });

  // -- Mẫu email ------------------------------------------------------------------
  // Người nhận là người Hàn nên nội dung luôn tiếng Hàn, chỉ nhãn nút đổi theo UI.

  const SIGNATURE_KEY = "company-scanner-mail-signature";
  const mailPanel = $("lead-mail");
  const mailSignature = $("mail-signature");

  function fill(template, values) {
    return Object.entries(values).reduce((text, [key, value]) => text.split(`{${key}}`).join(value), template);
  }

  function mailValues(lead) {
    const rankKo = lead.rank ? t("crm.rank." + lead.rank).replace(/\s*\(.*\)$/, "") : "";
    const contact = lead.contact_name
      ? `${lead.contact_name} ${rankKo || t("crm.mail.defaultRank")}님`
      : t("crm.mail.defaultContact");
    const tech = (lead.tech || []).length ? lead.tech.join(", ") : t("crm.mail.defaultTech");
    const team = lead.team_size ? t("crm.mail.teamSize", { count: lead.team_size }) : "";
    const start = lead.expected_start ? t("crm.mail.expectedStart", { month: lead.expected_start }) : "";
    // "스캐터랩 - ScatterLab" -> "스캐터랩": trong thư chỉ gọi một tên.
    const shortName = (lead.company_name || "").split(/\s+[-|·]\s+/)[0].trim() || lead.company_name;
    return {
      company: shortName, contact, tech, team, start,
      project: lead.project_type ? t("crm.project." + lead.project_type) : t("crm.mail.defaultProject"),
      signature: mailSignature.value.trim() || t("crm.mail.signatureFallback"),
    };
  }

  function renderMail() {
    if (!editing) return;
    const kind = $("mail-template").value;
    const values = mailValues(editing);
    const subject = fill(t(`crm.mail.subject.${kind}`), values);
    const body = fill(t(`crm.mail.body.${kind}`), values).replace(/\n{3,}/g, "\n\n");
    $("mail-subject").value = subject;
    $("mail-body").value = body;
    const to = editing.email ? encodeURIComponent(editing.email) : "";
    $("mail-send").href = `mailto:${to}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
    $("mail-send").classList.toggle("hidden", !editing.email);
  }

  try { mailSignature.value = localStorage.getItem(SIGNATURE_KEY) || ""; } catch (_) { /* không có localStorage */ }
  mailSignature.addEventListener("input", () => {
    try { localStorage.setItem(SIGNATURE_KEY, mailSignature.value); } catch (_) { /* bỏ qua */ }
    renderMail();
  });
  $("mail-template").addEventListener("change", renderMail);
  $("lead-mail-btn").addEventListener("click", () => {
    mailPanel.classList.toggle("hidden");
    if (!mailPanel.classList.contains("hidden")) {
      renderMail();
      mailPanel.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  });
  $("mail-copy").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(`${$("mail-subject").value}\n\n${$("mail-body").value}`);
      $("mail-copied").classList.remove("hidden");
      setTimeout(() => $("mail-copied").classList.add("hidden"), 2000);
    } catch (_) {
      toast(t("crm.error.saveFailed"), "error");
    }
  });

  // -- Sự kiện bảng -------------------------------------------------------------

  rows.addEventListener("click", async (event) => {
    const mail = event.target.closest("[data-quick-mail]");
    if (mail) { openLead(Number(mail.dataset.quickMail), null, "mail"); return; }
    const log = event.target.closest("[data-quick-log]");
    if (log) { openLead(Number(log.dataset.quickLog), null, "log"); return; }
    const kakao = event.target.closest("[data-quick-kakao]");
    if (kakao) {
      try { await navigator.clipboard.writeText(kakao.dataset.quickKakao); toast(t("crm.quick.kakaoCopied", { id: kakao.dataset.quickKakao })); }
      catch (_) { toast(kakao.dataset.quickKakao); }
      return;
    }
    if (event.target.closest("select, input, a, button")) return;
    const row = event.target.closest("tr[data-id]");
    if (row) openLead(Number(row.dataset.id));
  });

  // Ô KPI -> bộ lọc nhanh tương ứng.
  $("crm-kpis").addEventListener("click", (event) => {
    const tile = event.target.closest("[data-kpi-quick]");
    if (!tile) return;
    quick = tile.dataset.kpiQuick;
    $("crm-quick").querySelectorAll(".crm-seg-btn").forEach((item) => item.classList.toggle("crm-seg-active", item.dataset.quick === quick));
    render();
  });

  // Ẩn / hiện cột, nhớ trong trình duyệt.
  const columnsBtn = $("crm-columns-btn");
  const columnsMenu = $("crm-columns-menu");
  columnsBtn.addEventListener("click", (event) => { event.stopPropagation(); renderColumnsMenu(); columnsMenu.classList.toggle("hidden"); });
  columnsMenu.addEventListener("click", (event) => event.stopPropagation());
  columnsMenu.addEventListener("change", (event) => {
    const box = event.target.closest("[data-col-toggle]");
    if (!box) return;
    if (box.checked) hiddenColumns.delete(box.dataset.colToggle); else hiddenColumns.add(box.dataset.colToggle);
    try { localStorage.setItem(COLUMNS_KEY, JSON.stringify([...hiddenColumns])); } catch (_) { /* bỏ qua */ }
    render();
  });
  document.addEventListener("click", (event) => {
    if (!event.target.closest("#crm-columns-menu") && !event.target.closest("#crm-columns-btn")) columnsMenu.classList.add("hidden");
  });

  rows.addEventListener("change", async (event) => {
    const status = event.target.closest("select[data-status-for]");
    if (status) {
      await changeStatus(Number(status.dataset.statusFor), status.value);
      return;
    }
    const check = event.target.closest("input[data-select]");
    if (check) {
      const id = Number(check.dataset.select);
      if (check.checked) selected.add(id); else selected.delete(id);
      check.closest("tr").classList.toggle("crm-row-selected", check.checked);
      renderBulk();
      $("crm-check-all").checked = visibleLeads().every((lead) => selected.has(lead.id));
    }
  });

  $("crm-check-all").addEventListener("change", (event) => {
    const list = visibleLeads();
    list.forEach((lead) => { if (event.target.checked) selected.add(lead.id); else selected.delete(lead.id); });
    renderTable(list);
    renderBulk();
  });

  $("crm-bulk-clear").addEventListener("click", () => { selected.clear(); render(); });

  $("crm-bulk-delete").addEventListener("click", async () => {
    if (selected.size === 0 || !(await askConfirm(t("crm.confirmDelete", { count: selected.size }), t("crm.bulk.delete")))) return;
    try {
      await api("/api/leads/delete", jsonBody({ ids: [...selected] }));
      selected.clear();
      await loadLeads();
    } catch (_) {
      toast(t("crm.error.saveFailed"), "error");
    }
  });

  $("crm-bulk-status").addEventListener("change", async (event) => {
    const status = event.target.value;
    if (!status || selected.size === 0) return;
    try {
      await Promise.all([...selected].map((id) =>
        api(`/api/leads/${id}`, { ...jsonBody({ lead: { status } }), method: "PUT" })));
      selected.clear();
      await loadLeads();
    } catch (_) {
      toast(t("crm.error.saveFailed"), "error");
    }
    event.target.value = "";
  });

  // -- Bộ lọc -------------------------------------------------------------------

  $("crm-quick").addEventListener("click", (event) => {
    const button = event.target.closest("[data-quick]");
    if (!button) return;
    quick = button.dataset.quick;
    $("crm-quick").querySelectorAll(".crm-seg-btn").forEach((item) => item.classList.toggle("crm-seg-active", item === button));
    render();
  });

  $("crm-status-filters").addEventListener("click", (event) => {
    const button = event.target.closest("[data-status-filter]");
    if (!button) return;
    statusFilter = statusFilter === button.dataset.statusFilter ? "" : button.dataset.statusFilter;
    render();
  });

  $("crm-view").addEventListener("click", (event) => {
    const button = event.target.closest("[data-view]");
    if (!button) return;
    view = button.dataset.view;
    $("crm-view").querySelectorAll(".crm-seg-btn").forEach((item) => item.classList.toggle("crm-seg-active", item === button));
    render();
  });

  searchInput.addEventListener("input", render);
  assigneeSelect.addEventListener("change", render);
  $("crm-add-btn").addEventListener("click", () => openNewLead());

  // -- Nhập file ---------------------------------------------------------------

  const importModal = $("import-modal");
  const importInput = $("import-file");
  const importCommit = $("import-commit");
  let importPreview = null;

  function resetImport() {
    importFile = null;
    importPreview = null;
    importInput.value = "";
    $("import-filename").textContent = "";
    $("import-preview").classList.add("hidden");
    $("import-error").classList.add("hidden");
    importCommit.disabled = true;
    importCommit.textContent = t("crm.import.commit", { count: 0 });
  }

  $("crm-import-btn").addEventListener("click", () => { resetImport(); showModal("import-modal"); });

  function readFile(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        const bytes = new Uint8Array(reader.result);
        let binary = "";
        for (let i = 0; i < bytes.length; i += 0x8000) {
          binary += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
        }
        resolve(btoa(binary));
      };
      reader.onerror = reject;
      // Đọc byte thô: CSV từ Excel Hàn thường là CP949, server tự nhận diện.
      reader.readAsArrayBuffer(file);
    });
  }

  async function previewImport(file) {
    $("import-error").classList.add("hidden");
    try {
      importFile = { filename: file.name, content_base64: await readFile(file) };
      $("import-filename").textContent = `${file.name} · ${Math.round(file.size / 1024)} KB`;
      importPreview = await api("/api/leads/import", jsonBody({ ...importFile, commit: false }));
      renderImportPreview(importPreview);
    } catch (error) {
      $("import-error").textContent = error.code === "file_invalid" ? t("crm.error.file_invalid") : t("crm.import.failed");
      $("import-error").classList.remove("hidden");
      importCommit.disabled = true;
    }
  }

  function renderImportPreview(preview) {
    $("import-preview").classList.remove("hidden");
    $("import-stats").innerHTML =
      pill(`${t("crm.import.valid")}: ${preview.valid}`, "emerald") +
      pill(`${t("crm.import.dup")}: ${preview.duplicates}`, "amber") +
      pill(`${t("crm.import.err")}: ${preview.errors.length}`, "rose") +
      `<span class="crm-meta ml-auto">${esc(t("crm.import.total", { count: preview.total }))}</span>`;
    $("import-rows").innerHTML = preview.preview.map((row) => `<tr>
      <td class="crm-strong">${esc(row.company_name)}</td><td>${esc(row.contact_name || "")}</td><td>${esc(label("rank", row.rank))}</td>
      <td>${esc(row.mobile || row.phone || "")}</td><td>${esc(row.email || "")}</td><td>${esc(label("source", row.source))}</td><td>${esc(fmtKRW(row.budget))}</td>
    </tr>`).join("");
    $("import-errors").innerHTML = preview.errors.slice(0, 5).map((error) =>
      `<li>${esc(t("crm.import.rowError", { row: error.row, code: t("crm.error." + error.code) }))}</li>`).join("");
    importCommit.disabled = preview.valid === 0;
    importCommit.textContent = t("crm.import.commit", { count: preview.valid });
  }

  importInput.addEventListener("change", () => { if (importInput.files[0]) previewImport(importInput.files[0]); });
  const drop = $("import-drop");
  drop.addEventListener("dragover", (event) => { event.preventDefault(); drop.classList.add("crm-drop-over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("crm-drop-over"));
  drop.addEventListener("drop", (event) => {
    event.preventDefault();
    drop.classList.remove("crm-drop-over");
    if (event.dataTransfer.files[0]) previewImport(event.dataTransfer.files[0]);
  });

  importCommit.addEventListener("click", async () => {
    if (!importFile) return;
    importCommit.disabled = true;
    try {
      const done = await api("/api/leads/import", jsonBody({ ...importFile, commit: true }));
      hideModal("import-modal");
      await loadLeads();
      toast(t("crm.import.done", { count: done.inserted }));
    } catch (_) {
      $("import-error").textContent = t("crm.import.failed");
      $("import-error").classList.remove("hidden");
      importCommit.disabled = false;
    }
  });

  // -- Xuất file ---------------------------------------------------------------

  const EXPORT_FIELDS = [
    ["company_name", "crm.form.company"], ["biz_number", "crm.form.biz"], ["company_size", "crm.form.size"],
    ["industry", "crm.form.industry"], ["website", "crm.form.website"], ["contact_name", "crm.form.contactName"],
    ["rank", "crm.form.rank"], ["department", "crm.form.department"], ["phone", "crm.form.phone"],
    ["mobile", "crm.form.mobile"], ["email", "crm.form.email"], ["kakao", "crm.form.kakao"],
    ["source", "crm.form.source"], ["project_type", "crm.form.project"], ["tech", "crm.form.tech"],
    ["budget", "crm.form.budget"], ["team_size", "crm.form.teamSize"], ["expected_start", "crm.form.expectedStart"],
    ["bridge_se", "crm.form.bridgeSe"], ["competitor", "crm.form.competitor"], ["score", "crm.col.score"],
    ["status", "crm.form.status"], ["lost_reason", "crm.form.lostReason"], ["assignee", "crm.form.assignee"],
    ["next_action", "crm.form.nextAction"], ["next_date", "crm.form.nextDate"], ["last_contact", "crm.activity.lastContactShort"],
    ["memo", "crm.form.memo"], ["created_at", "crm.col.created"],
  ];
  const EXPORT_LABELS = { company_size: "size", rank: "rank", source: "source", project_type: "project", status: "status", lost_reason: "lost" };

  function exportValue(lead, field) {
    const value = lead[field];
    if (field === "tech") return (value || []).join(" | ");
    if (field === "bridge_se") return value ? "Y" : "";
    if (EXPORT_LABELS[field]) return label(EXPORT_LABELS[field], value);
    return value === null || value === undefined ? "" : String(value);
  }

  function exportCsv() {
    const list = visibleLeads();
    const lines = [EXPORT_FIELDS.map(([, key]) => t(key))];
    list.forEach((lead) => lines.push(EXPORT_FIELDS.map(([field]) => exportValue(lead, field))));
    const csv = lines.map((line) => line.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",")).join("\n");
    download(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" }), `crm_leads_${todayIso()}.csv`);
  }

  function exportJson() {
    download(new Blob([JSON.stringify(visibleLeads(), null, 2)], { type: "application/json" }), `crm_leads_${todayIso()}.json`);
  }

  const exportBtn = $("crm-export-btn");
  const exportMenu = $("crm-export-menu");
  exportBtn.addEventListener("click", (event) => { event.stopPropagation(); exportMenu.classList.toggle("hidden"); });
  $("crm-export-csv").addEventListener("click", () => { exportCsv(); exportMenu.classList.add("hidden"); });
  $("crm-export-json").addEventListener("click", () => { exportJson(); exportMenu.classList.add("hidden"); });
  document.addEventListener("click", (event) => {
    if (!event.target.closest("#crm-export-menu") && !event.target.closest("#crm-export-btn")) exportMenu.classList.add("hidden");
  });

  // -- Khởi động ------------------------------------------------------------------

  window.addEventListener("langchange", () => {
    fillAllSelects();
    render();
    renderFunnel();
    if (!leadModal.classList.contains("hidden") && editing) renderScore(editing);
  });

  fillAllSelects();
  resetImport();
  loadLeads().then(loadCustomers).then(() => { render(); }).then(() => {
    // /crm?lead=<id>: mở ngay lead vừa tạo từ trang quét / công ty đã lưu.
    const requested = new URLSearchParams(window.location.search).get("lead");
    if (requested) {
      openLead(Number(requested));
      window.history.replaceState({}, "", "/crm");
    }
  });
})();
