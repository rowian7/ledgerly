// Ledgerly frontend: plain JavaScript talking to the FastAPI JSON API.
const $ = (sel) => document.querySelector(sel);
const TOKEN_KEY = "ledgerly_token";

const state = {
  token: localStorage.getItem(TOKEN_KEY),
  mode: "login",        // or "register"
  editingId: null,
  charts: {},
};

const money = new Intl.NumberFormat(undefined, { style: "currency", currency: "GBP" });
const fmt = (v) => money.format(Number(v));

// ---------- API helper ----------
async function api(path, { method = "GET", body } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const res = await fetch(path, { method, headers, body: body && JSON.stringify(body) });
  if (res.status === 401 && state.token) {
    logout();
    throw new Error("Session expired, please log in again");
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(readError(data) || `Request failed (${res.status})`);
  }
  return res.status === 204 ? null : res.json();
}

function readError(data) {
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail.map((e) => `${e.loc.at(-1)}: ${e.msg}`).join("; ");
  }
  return null;
}

// ---------- auth ----------
function setAuthMode(mode) {
  state.mode = mode;
  const login = mode === "login";
  $("#auth-submit").textContent = login ? "Log in" : "Create account";
  $("#auth-switch-text").textContent = login ? "No account?" : "Have an account?";
  $("#auth-switch").textContent = login ? "Create one" : "Log in";
  $("#auth-form [name=password]").autocomplete = login ? "current-password" : "new-password";
  $("#auth-error").textContent = "";
}

$("#auth-switch").addEventListener("click", () => setAuthMode(state.mode === "login" ? "register" : "login"));

$("#auth-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = new FormData(e.target);
  const creds = { username: form.get("username"), password: form.get("password") };
  $("#auth-error").textContent = "";
  try {
    if (state.mode === "register") await api("/api/auth/register", { method: "POST", body: creds });
    const { access_token } = await api("/api/auth/login", { method: "POST", body: creds });
    state.token = access_token;
    localStorage.setItem(TOKEN_KEY, access_token);
    e.target.reset();
    await showApp();
  } catch (err) {
    $("#auth-error").textContent = err.message;
  }
});

function logout() {
  state.token = null;
  localStorage.removeItem(TOKEN_KEY);
  $("#app-view").hidden = true;
  $("#auth-view").hidden = false;
}
$("#logout").addEventListener("click", logout);

// ---------- dashboard ----------
const currentMonth = () => $("#month").value;

async function showApp() {
  const me = await api("/api/auth/me");
  $("#whoami").textContent = me.username;
  $("#auth-view").hidden = true;
  $("#app-view").hidden = false;
  await refresh();
}

async function refresh() {
  const month = currentMonth();
  const [page, summary, trend] = await Promise.all([
    api(`/api/transactions?month=${month}&limit=500`),
    api(`/api/stats/summary?month=${month}`),
    api(`/api/stats/monthly?months=6&until=${month}`),
  ]);
  renderStats(summary);
  renderTable(page.items);
  renderCategoryChart(summary.by_category);
  renderTrendChart(trend);
}

function renderStats(s) {
  $("#stat-income").textContent = fmt(s.income);
  $("#stat-expenses").textContent = fmt(s.expenses);
  const net = $("#stat-net");
  net.textContent = fmt(s.net);
  net.className = Number(s.net) < 0 ? "expense" : "income";
}

function renderTable(items) {
  const body = $("#tx-body");
  body.replaceChildren();
  $("#tx-empty").hidden = items.length > 0;
  for (const t of items) {
    const tr = document.createElement("tr");
    const sign = t.kind === "expense" ? "−" : "+";
    // Build cells with textContent (not innerHTML) so user input can't inject HTML.
    const cells = [
      t.date,
      null,
      t.description,
      `${sign}${fmt(t.amount)}`,
    ];
    cells.forEach((text, i) => {
      const td = document.createElement("td");
      if (i === 1) {
        const pill = document.createElement("span");
        pill.className = "pill";
        pill.textContent = t.category;
        td.append(pill);
      } else {
        td.textContent = text;
      }
      if (i === 3) td.className = `num ${t.kind}`;
      tr.append(td);
    });
    const actions = document.createElement("td");
    actions.className = "actions";
    actions.append(
      iconButton("Edit", "✎", () => startEdit(t)),
      iconButton("Delete", "✕", () => removeTx(t)),
    );
    tr.append(actions);
    body.append(tr);
  }
}

function iconButton(label, glyph, onClick) {
  const b = document.createElement("button");
  b.className = "icon";
  b.title = label;
  b.setAttribute("aria-label", label);
  b.textContent = glyph;
  b.addEventListener("click", onClick);
  return b;
}

const PALETTE = ["#2f6fed", "#c2410c", "#12805c", "#9333ea", "#ca8a04", "#0891b2", "#db2777", "#64748b"];

function renderCategoryChart(byCat) {
  $("#cat-empty").hidden = byCat.length > 0;
  $("#cat-chart").parentElement.hidden = byCat.length === 0;
  state.charts.cat?.destroy();
  if (!byCat.length || !window.Chart) return;
  state.charts.cat = new Chart($("#cat-chart"), {
    type: "doughnut",
    data: {
      labels: byCat.map((c) => c.category),
      datasets: [{ data: byCat.map((c) => Number(c.amount)), backgroundColor: PALETTE, borderWidth: 0 }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "right", labels: { color: textColor() } },
        tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${fmt(ctx.raw)}` } },
      },
    },
  });
}

function renderTrendChart(trend) {
  state.charts.trend?.destroy();
  if (!window.Chart) return;
  const label = (m) => new Date(`${m}-01T00:00`).toLocaleString(undefined, { month: "short" });
  state.charts.trend = new Chart($("#trend-chart"), {
    type: "bar",
    data: {
      labels: trend.map((t) => label(t.month)),
      datasets: [
        { label: "Income", data: trend.map((t) => Number(t.income)), backgroundColor: cssVar("--income") },
        { label: "Expenses", data: trend.map((t) => Number(t.expenses)), backgroundColor: cssVar("--expense") },
      ],
    },
    options: {
      maintainAspectRatio: false,
      scales: {
        x: { ticks: { color: textColor() }, grid: { display: false } },
        y: { ticks: { color: textColor(), callback: (v) => fmt(v) }, grid: { color: cssVar("--border") } },
      },
      plugins: { legend: { labels: { color: textColor() } } },
    },
  });
}

const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const textColor = () => cssVar("--muted");

// ---------- add / edit / delete ----------
$("#tx-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const f = new FormData(e.target);
  const body = {
    kind: f.get("kind"),
    amount: f.get("amount"),
    category: f.get("category"),
    description: f.get("description"),
    date: f.get("date"),
  };
  $("#tx-error").textContent = "";
  try {
    if (state.editingId) {
      await api(`/api/transactions/${state.editingId}`, { method: "PUT", body });
    } else {
      await api("/api/transactions", { method: "POST", body });
    }
    resetForm();
    await refresh();
  } catch (err) {
    $("#tx-error").textContent = err.message;
  }
});

function startEdit(t) {
  state.editingId = t.id;
  const form = $("#tx-form");
  for (const key of ["kind", "amount", "category", "description", "date"]) form[key].value = t[key];
  $("#form-title").textContent = "Edit transaction";
  $("#tx-submit").textContent = "Save";
  $("#tx-cancel").hidden = false;
  form.scrollIntoView({ behavior: "smooth", block: "center" });
}

function resetForm() {
  state.editingId = null;
  const form = $("#tx-form");
  form.reset();
  form.date.value = defaultDate();
  $("#form-title").textContent = "Add transaction";
  $("#tx-submit").textContent = "Add";
  $("#tx-cancel").hidden = true;
}
$("#tx-cancel").addEventListener("click", resetForm);

async function removeTx(t) {
  if (!confirm(`Delete ${t.category} ${fmt(t.amount)} on ${t.date}?`)) return;
  await api(`/api/transactions/${t.id}`, { method: "DELETE" });
  await refresh();
}

// CSV export needs the auth header, so fetch it and hand the browser a blob.
$("#export").addEventListener("click", async (e) => {
  e.preventDefault();
  const res = await fetch(`/api/transactions/export.csv?month=${currentMonth()}`, {
    headers: { Authorization: `Bearer ${state.token}` },
  });
  const url = URL.createObjectURL(await res.blob());
  const a = Object.assign(document.createElement("a"), { href: url, download: `ledgerly-${currentMonth()}.csv` });
  a.click();
  URL.revokeObjectURL(url);
});

// ---------- startup ----------
function todayISO() {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}
// New entries default to today if viewing this month, else the 1st of the viewed month.
function defaultDate() {
  const today = todayISO();
  return today.startsWith(currentMonth()) ? today : `${currentMonth()}-01`;
}

$("#month").value = todayISO().slice(0, 7);
$("#month").addEventListener("change", () => { resetForm(); refresh(); });
$("#tx-form").date.value = defaultDate();
setAuthMode("login");

if (state.token) {
  showApp().catch(logout);
} else {
  logout();
}
