/* 고객 — trang /crm/customers: khách hàng đã ký hợp đồng, giá trị, thời hạn, xếp hạng.
   Dùng icon(), esc(), download() từ app.js và t() từ i18n.js. Mọi số liệu đến
   từ /api/customers (SQLite); không có dữ liệu mẫu. */

(function () {
  const GRADES = ["S", "A", "B", "C"];
  const GRADE_TONE = { S: "violet", A: "emerald", B: "blue", C: "slate" };
  const OPTION_LISTS = {
    project: ["dispatch", "contract", "si", "sm", "odc", "other"],
    cstatus: ["active", "completed", "renewed", "terminated"],
    payment: ["monthly", "milestone", "quarterly", "upfront", "other"],
    rank: ["staff", "assistant", "manager", "deputy", "general", "director", "md", "evp", "svp", "ceo", "cto", "cio", "other"],
    stars: ["5", "4", "3", "2", "1"],
  };
  const LABEL_GROUP = { project: "crm.project", cstatus: "cust.status", payment: "cust.pay", rank: "crm.rank", stars: "cust.stars" };
  const STATUS_TONE = { active: "emerald", completed: "slate", renewed: "blue", terminated: "rose" };

  const $ = (id) => document.getElementById(id);
  const list = $("cust-list");
  const emptyBox = $("cust-empty");
  const searchInput = $("cust-search");

  let customers = [];
  let summary = {};
  let quick = "all";
  let gradeFilter = "";
  let expanded = new Set();
  let editing = null;          // hợp đồng đang sửa, null khi thêm mới

  function toast(message, tone = "ok") {
    let host = $("crm-toast");
    if (!host) { host = document.createElement("div"); host.id = "crm-toast"; document.body.appendChild(host); }
    const item = document.createElement("div");
    item.className = `crm-toast-item crm-toast-${tone}`;
    item.textContent = message;
    host.appendChild(item);
    setTimeout(() => item.classList.add("crm-toast-show"), 10);
    setTimeout(() => { item.classList.remove("crm-toast-show"); setTimeout(() => item.remove(), 300); }, 3500);
  }

  const label = (group, code) => (code ? t(`${LABEL_GROUP[group] || group}.${code}`) : "");

  function fmtKRW(amount) {
    const value = Number(amount);
    if (!Number.isFinite(value) || value <= 0) return "₩ 0";
    if (value >= 100000000) {
      const eok = value / 100000000;
      return `₩ ${eok % 1 === 0 ? eok : eok.toFixed(1)}${t("crm.unit.eok")}`;
    }
    if (value >= 10000) return `₩ ${Math.round(value / 10000).toLocaleString()}${t("crm.unit.man")}`;
    return `₩ ${value.toLocaleString()}`;
  }

  function pill(text, tone = "slate") {
    return `<span class="crm-pill crm-pill-${tone}">${esc(text)}</span>`;
  }

  function gradeBadge(grade) {
    return `<span class="cust-grade cust-grade-${grade}" title="${esc(t("cust.gradeWhy." + grade))}">${esc(grade)}</span>`;
  }

  function fillSelects() {
    document.querySelectorAll("select[data-options]").forEach((select) => {
      const group = select.dataset.options;
      const current = select.value;
      select.innerHTML = (select.dataset.blank === "1" ? `<option value="">—</option>` : "") +
        OPTION_LISTS[group].map((code) => `<option value="${code}">${esc(label(group, code))}</option>`).join("");
      if (current) select.value = current;
    });
  }

  // -- Lọc ------------------------------------------------------------------------

  function visibleCustomers() {
    const query = searchInput.value.trim().toLowerCase();
    return customers.filter((customer) => {
      if (quick === "expiring" && !customer.expiring_count) return false;
      if (quick === "active" && !customer.active_count) return false;
      if (quick === "dormant" && !(customer.dormant_days !== null && customer.dormant_days >= 0)) return false;
      if (gradeFilter && customer.grade !== gradeFilter) return false;
      if (query) {
        const haystack = [customer.company_name, customer.domain, customer.contact_name, customer.email, customer.phone,
          customer.our_pm, customer.biz_number, ...(customer.tech || []),
          ...customer.contracts.map((c) => `${c.title || ""} ${c.contract_no || ""} ${c.memo || ""}`)].join(" ").toLowerCase();
        if (!haystack.includes(query)) return false;
      }
      return true;
    });
  }

  // -- Render --------------------------------------------------------------------

  function renderKpis() {
    const tile = (labelText, value, sub, tone = "") => `<div class="crm-kpi">
      <div class="crm-kpi-label">${esc(labelText)}</div>
      <div class="crm-kpi-value ${tone === "danger" ? "crm-kpi-danger" : ""}">${esc(value)}</div>
      <div class="crm-kpi-sub ${tone === "danger" ? "crm-kpi-danger" : "crm-kpi-ok"}">${esc(sub)}</div>
    </div>`;
    $("cust-kpis").innerHTML =
      tile(t("cust.kpi.total"), fmtKRW(summary.total_value), t("cust.kpi.totalSub", { count: summary.customer_count || 0 })) +
      tile(t("cust.kpi.active"), fmtKRW(summary.active_value), t("cust.kpi.activeSub", { count: summary.active_count || 0 })) +
      tile(t("cust.kpi.year", { year: new Date().getFullYear() }), fmtKRW(summary.year_value), t("cust.kpi.yearSub", { count: summary.year_count || 0 })) +
      tile(t("cust.kpi.expiring"), String(summary.expiring_count || 0),
        summary.expiring_count ? t("cust.kpi.expiringSub", { value: fmtKRW(summary.expiring_value) }) : t("cust.kpi.expiringNone"),
        summary.expiring_count ? "danger" : "");
  }

  function renderGradeFilters() {
    $("cust-grade-filters").innerHTML = GRADES.map((grade) => {
      const count = customers.filter((customer) => customer.grade === grade).length;
      return `<button class="crm-chip crm-chip-${GRADE_TONE[grade]} ${gradeFilter === grade ? "crm-chip-active" : ""}" data-grade="${grade}" title="${esc(t("cust.gradeWhy." + grade))}">
        ${esc(t("cust.grade." + grade))}<span class="crm-chip-count">${count}</span></button>`;
    }).join("");
  }

  function contractRow(contract) {
    const period = [contract.start_date, contract.end_date].filter(Boolean).join(" ~ ") || "—";
    const daysLeft = contract.status === "active" && contract.days_left !== null
      ? (contract.days_left < 0 ? t("cust.daysOver", { days: -contract.days_left }) : t("cust.daysLeft", { days: contract.days_left }))
      : "";
    return `<tr data-contract="${contract.id}" class="${contract.expiring ? "crm-row-overdue" : ""}">
      <td><div class="crm-strong crm-clip" title="${esc(contract.title || "")}">${esc(contract.title || label("project", contract.project_type) || t("cust.untitled"))}</div>
        <div class="crm-meta">${esc([contract.contract_no, label("project", contract.project_type)].filter(Boolean).join(" · "))}</div></td>
      <td class="crm-nowrap">${esc(period)}${daysLeft ? `<div class="crm-meta ${contract.expiring ? "crm-next-overdue" : ""}">${esc(daysLeft)}</div>` : ""}</td>
      <td class="crm-strong crm-nowrap">${fmtKRW(contract.amount)}${contract.monthly_rate ? `<div class="crm-meta">${esc(t("cust.monthlyShort", { rate: fmtKRW(contract.monthly_rate), count: contract.team_size || 1 }))}</div>` : ""}</td>
      <td>${pill(label("cstatus", contract.status), STATUS_TONE[contract.status])}</td>
      <td class="crm-meta">${esc([contract.contact_name, label("rank", contract.rank)].filter(Boolean).join(" · "))}</td>
      <td class="crm-meta">${contract.satisfaction ? "★".repeat(contract.satisfaction) : ""}</td>
      <td><div class="saved-actions"><button class="saved-btn" data-edit="${contract.id}">${esc(t("cust.action.edit"))}</button></div></td>
    </tr>`;
  }

  function customerCard(customer) {
    const open = expanded.has(customer.key);
    const flags = [];
    if (customer.expiring_count) flags.push(pill(t("cust.flag.expiring", { count: customer.expiring_count }), "amber"));
    if (customer.dormant_days !== null && customer.dormant_days >= 0) flags.push(pill(t("cust.flag.dormant", { days: customer.dormant_days }), "rose"));
    if (customer.renewed_count) flags.push(pill(t("cust.flag.renewed", { count: customer.renewed_count }), "emerald"));
    const meta = [
      customer.contact_name ? `${customer.contact_name}${customer.rank ? " · " + label("rank", customer.rank) : ""}` : "",
      customer.email || customer.phone || "",
      customer.our_pm ? t("cust.ourPmShort", { name: customer.our_pm }) : "",
    ].filter(Boolean).join("  ·  ");

    return `<div class="cust-card ${open ? "cust-card-open" : ""}" data-key="${esc(customer.key)}">
      <div class="cust-card-head" data-toggle="${esc(customer.key)}">
        ${gradeBadge(customer.grade)}
        <div class="cust-card-main">
          <div class="cust-card-name">${esc(customer.company_name)}
            ${customer.website ? `<a href="${esc(customer.website)}" target="_blank" rel="noopener noreferrer" class="crm-meta">${esc(customer.domain || "")}</a>` : ""}
          </div>
          <div class="crm-meta crm-clip cust-card-meta">${esc(meta)}</div>
          <div class="crm-pills mt-1">${flags.join("")}${(customer.project_types || []).map((p) => pill(label("project", p), "source")).join("")}</div>
        </div>
        <div class="cust-card-stats">
          <div class="cust-stat"><div class="cust-stat-value">${fmtKRW(customer.total_value)}</div><div class="crm-meta">${esc(t("cust.stat.total", { count: customer.contract_count }))}</div></div>
          <div class="cust-stat"><div class="cust-stat-value">${fmtKRW(customer.active_value)}</div><div class="crm-meta">${esc(t("cust.stat.active", { count: customer.active_count }))}</div></div>
          <div class="cust-stat"><div class="cust-stat-value ${customer.expiring_count ? "crm-kpi-danger" : ""}">${esc(customer.next_end || "—")}</div><div class="crm-meta">${esc(t("cust.stat.nextEnd"))}</div></div>
          <div class="cust-stat"><div class="cust-stat-value">${customer.satisfaction ? customer.satisfaction + " ★" : "—"}</div><div class="crm-meta">${esc(t("cust.stat.satisfaction"))}</div></div>
        </div>
        <div class="cust-card-actions">
          <button class="crm-btn crm-btn-sm" data-add-for="${esc(customer.key)}">${icon("plus", 13)} ${esc(t("cust.action.addContract"))}</button>
          <button class="crm-btn crm-btn-sm crm-btn-primary" data-resell="${esc(customer.key)}" title="${esc(t("cust.action.resellTitle"))}">${icon("userplus", 13)} ${esc(t("cust.action.resell"))}</button>
          <span class="cust-chevron">${icon("chevron", 16)}</span>
        </div>
      </div>
      ${open ? `<div class="cust-card-body"><div class="saved-wrap"><table class="crm-table crm-table-compact"><thead><tr>
          <th data-i18n="cust.col.contract">${esc(t("cust.col.contract"))}</th><th>${esc(t("cust.col.period"))}</th><th>${esc(t("cust.col.amount"))}</th>
          <th>${esc(t("cust.col.status"))}</th><th>${esc(t("cust.col.contact"))}</th><th>${esc(t("cust.col.satisfaction"))}</th><th></th>
        </tr></thead><tbody>${customer.contracts.map(contractRow).join("")}</tbody></table></div></div>` : ""}
    </div>`;
  }

  function render() {
    const shown = visibleCustomers();
    renderKpis();
    renderGradeFilters();
    $("cust-count").textContent = shown.length === customers.length
      ? t("cust.count", { total: customers.length })
      : t("cust.countFiltered", { shown: shown.length, total: customers.length });
    list.innerHTML = shown.map(customerCard).join("");
    emptyBox.classList.toggle("hidden", shown.length > 0);
    if (shown.length === 0) {
      emptyBox.innerHTML = customers.length === 0
        ? `<div class="crm-empty-title">${esc(t("cust.empty"))}</div><div>${esc(t("cust.emptyDesc"))}</div>`
        : esc(t("cust.emptyFiltered"));
    }
    const subCustomers = $("sub-customers-count");
    if (subCustomers) subCustomers.textContent = String(customers.length);
    $("cust-company-list").innerHTML = customers.map((c) => `<option value="${esc(c.company_name)}">`).join("");
  }

  // -- API ------------------------------------------------------------------------

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
  const jsonBody = (body, method = "POST") => ({ method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  async function load() {
    try {
      const payload = await api("/api/customers");
      customers = payload.customers || [];
      summary = payload.summary || {};
      render();
    } catch (_) {
      $("cust-count").textContent = t("cust.error.loadFailed");
    }
  }

  // -- Modal ----------------------------------------------------------------------

  const form = $("contract-form");
  const formError = $("contract-error");

  function showModal() { $("contract-modal").classList.remove("hidden"); document.body.classList.add("crm-lock"); }
  function hideModal() { $("contract-modal").classList.add("hidden"); document.body.classList.remove("crm-lock"); }
  document.querySelectorAll("[data-close]").forEach((button) => button.addEventListener("click", hideModal));
  $("contract-modal").addEventListener("mousedown", (event) => { if (event.target.id === "contract-modal") hideModal(); });
  document.addEventListener("keydown", (event) => { if (event.key === "Escape") hideModal(); });

  function setForm(contract) {
    form.reset();
    for (const element of form.elements) {
      if (!element.name) continue;
      const value = contract[element.name];
      if (element.name === "tech") element.value = (value || []).join(", ");
      else element.value = value === null || value === undefined ? "" : value;
    }
  }

  function readForm() {
    const data = {};
    for (const element of form.elements) {
      if (element.name) data[element.name] = element.value.trim();
    }
    if (editing) {
      if (editing.lead_id) data.lead_id = editing.lead_id;
      if (editing.company_id) data.company_id = editing.company_id;
      if (editing.domain && !data.website) data.domain = editing.domain;
    }
    return data;
  }

  function openContract(contract, prefill = false) {
    editing = prefill ? { ...contract, id: undefined } : contract;
    formError.classList.add("hidden");
    $("contract-modal-title").textContent = prefill || !contract.id ? t("cust.form.titleAdd") : (contract.title || contract.company_name);
    $("contract-modal-sub").textContent = prefill
      ? t("cust.form.fromLead")
      : (contract.id ? t("cust.form.titleEdit", { date: (contract.updated_at || "").slice(0, 10) }) : t("cust.form.titleAddSub"));
    setForm({ status: "active", renewal_notice_days: "", ...contract });
    $("contract-delete").classList.toggle("hidden", !contract.id);
    const leadLink = $("contract-lead-link");
    leadLink.classList.toggle("hidden", !contract.lead_id);
    if (contract.lead_id) leadLink.href = `/crm?lead=${contract.lead_id}`;
    showModal();
    form.elements.company_name.focus();
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const save = $("contract-save");
    save.disabled = true;
    formError.classList.add("hidden");
    try {
      const data = readForm();
      if (editing && editing.id) await api(`/api/contracts/${editing.id}`, jsonBody({ contract: data }, "PUT"));
      else await api("/api/contracts", jsonBody({ contract: data }));
      hideModal();
      await load();
      toast(t("cust.saved"));
    } catch (error) {
      const known = ["company_required", "amount_required", "dates_invalid"].includes(error.code);
      formError.textContent = known ? t("cust.error." + error.code) : t("crm.error.saveFailed");
      formError.classList.remove("hidden");
    }
    save.disabled = false;
  });

  $("contract-delete").addEventListener("click", async () => {
    if (!editing || !editing.id || !(await askConfirm(t("cust.confirmDelete", { name: editing.title || editing.company_name }), t("crm.form.delete")))) return;
    try {
      await api(`/api/contracts/${editing.id}`, { method: "DELETE" });
      hideModal();
      await load();
    } catch (_) {
      toast(t("crm.error.saveFailed"), "error");
    }
  });

  // -- Sự kiện danh sách ---------------------------------------------------------

  list.addEventListener("click", async (event) => {
    const edit = event.target.closest("[data-edit]");
    if (edit) {
      const contract = customers.flatMap((c) => c.contracts).find((c) => c.id === Number(edit.dataset.edit));
      if (contract) openContract(contract);
      return;
    }
    const addFor = event.target.closest("[data-add-for]");
    if (addFor) {
      const customer = customers.find((c) => c.key === addFor.dataset.addFor);
      const latest = customer.contracts[0] || {};
      openContract({
        company_name: customer.company_name, website: customer.website, domain: customer.domain, biz_number: customer.biz_number,
        company_id: customer.company_id, contact_name: customer.contact_name, rank: customer.rank, phone: customer.phone,
        email: customer.email, our_pm: customer.our_pm, project_type: latest.project_type, monthly_rate: latest.monthly_rate,
        team_size: latest.team_size, payment_terms: latest.payment_terms, tech: customer.tech,
      }, true);
      return;
    }
    const resell = event.target.closest("[data-resell]");
    if (resell) {
      resell.disabled = true;
      try {
        const payload = await api(`/api/customers/${encodeURIComponent(resell.dataset.resell)}/lead`, { method: "POST" });
        window.location.href = `/crm?lead=${payload.lead.id}`;
      } catch (_) {
        toast(t("crm.error.saveFailed"), "error");
        resell.disabled = false;
      }
      return;
    }
    const toggle = event.target.closest("[data-toggle]");
    if (toggle && !event.target.closest("a, button")) {
      const key = toggle.dataset.toggle;
      if (expanded.has(key)) expanded.delete(key); else expanded.add(key);
      render();
    }
  });

  $("cust-quick").addEventListener("click", (event) => {
    const button = event.target.closest("[data-quick]");
    if (!button) return;
    quick = button.dataset.quick;
    $("cust-quick").querySelectorAll(".crm-seg-btn").forEach((item) => item.classList.toggle("crm-seg-active", item === button));
    render();
  });
  $("cust-grade-filters").addEventListener("click", (event) => {
    const button = event.target.closest("[data-grade]");
    if (!button) return;
    gradeFilter = gradeFilter === button.dataset.grade ? "" : button.dataset.grade;
    render();
  });
  searchInput.addEventListener("input", render);
  $("cust-add-btn").addEventListener("click", () => openContract({}));

  // -- Xuất ---------------------------------------------------------------------

  const EXPORT_FIELDS = [
    ["company_name", "crm.form.company"], ["title", "cust.form.title"], ["contract_no", "cust.form.contractNo"],
    ["project_type", "crm.form.project"], ["status", "cust.form.status"], ["signed_date", "cust.form.signed"],
    ["start_date", "cust.form.start"], ["end_date", "cust.form.end"], ["amount", "cust.form.amount"],
    ["monthly_rate", "cust.form.monthly"], ["team_size", "crm.form.teamSize"], ["payment_terms", "cust.form.payment"],
    ["contact_name", "crm.form.contactName"], ["rank", "crm.form.rank"], ["phone", "crm.form.phone"],
    ["email", "crm.form.email"], ["our_pm", "cust.form.ourPm"], ["tech", "crm.form.tech"],
    ["satisfaction", "cust.form.satisfaction"], ["memo", "crm.form.memo"],
  ];
  const EXPORT_LABELS = { project_type: "project", status: "cstatus", payment_terms: "payment", rank: "rank" };

  function exportRows() {
    const rows = [];
    visibleCustomers().forEach((customer) => customer.contracts.forEach((contract) => {
      rows.push({ grade: customer.grade, ...contract });
    }));
    return rows;
  }

  function exportCsv() {
    const header = [t("cust.col.grade"), ...EXPORT_FIELDS.map(([, key]) => t(key))];
    const lines = [header];
    exportRows().forEach((row) => lines.push([row.grade, ...EXPORT_FIELDS.map(([field]) => {
      const value = row[field];
      if (field === "tech") return (value || []).join(" | ");
      if (EXPORT_LABELS[field]) return label(EXPORT_LABELS[field], value);
      return value === null || value === undefined ? "" : String(value);
    })]));
    const csv = lines.map((line) => line.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",")).join("\n");
    download(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" }), `contracts_${new Date().toISOString().slice(0, 10)}.csv`);
  }

  function exportJson() {
    download(new Blob([JSON.stringify(visibleCustomers(), null, 2)], { type: "application/json" }), `customers_${new Date().toISOString().slice(0, 10)}.json`);
  }

  const exportBtn = $("cust-export-btn");
  const exportMenu = $("cust-export-menu");
  exportBtn.addEventListener("click", (event) => { event.stopPropagation(); exportMenu.classList.toggle("hidden"); });
  $("cust-export-csv").addEventListener("click", () => { exportCsv(); exportMenu.classList.add("hidden"); });
  $("cust-export-json").addEventListener("click", () => { exportJson(); exportMenu.classList.add("hidden"); });
  document.addEventListener("click", (event) => {
    if (!event.target.closest("#cust-export-menu") && !event.target.closest("#cust-export-btn")) exportMenu.classList.add("hidden");
  });

  // -- Khởi động ------------------------------------------------------------------

  window.addEventListener("langchange", () => { fillSelects(); render(); });
  fillSelects();
  load().then(async () => {
    refreshSubnavCounts({ customers: customers.length });
    // /crm/customers?from_lead=<id>: lead vừa 수주 ở CRM -> form hợp đồng điền sẵn.
    // ?q=<tên>: tới từ nhãn "기존 고객" của một lead -> lọc sẵn khách đó.
    const params = new URLSearchParams(window.location.search);
    if (params.get("q")) {
      searchInput.value = params.get("q");
      render();
      const first = visibleCustomers()[0];
      if (first) { expanded.add(first.key); render(); }
    }
    if (params.get("from_lead")) {
      try {
        const payload = await api(`/api/contracts/from-lead/${encodeURIComponent(params.get("from_lead"))}`);
        openContract(payload.contract, true);
      } catch (_) {
        toast(t("cust.error.loadFailed"), "error");
      }
    }
    if (params.get("from_lead") || params.get("q")) {
      window.history.replaceState({}, "", "/crm/customers");
    }
  });
})();
