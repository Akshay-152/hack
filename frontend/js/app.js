/* Campus Event Bot — frontend logic (vanilla JS). */
const API = location.origin.includes(":5000") || location.port === "5000"
  ? ""  // served by Flask itself
  : "http://localhost:5000";

const INTEREST_OPTIONS = ["coding", "ai", "sports", "music", "arts",
  "entrepreneurship", "volunteering"];

const state = {
  token: localStorage.getItem("token") || null,
  user: JSON.parse(localStorage.getItem("user") || "null"),
};

/* ---------- API helpers ---------- */
async function api(path, opts = {}) {
  const headers = { "Content-Type": "application/json" };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  const res = await fetch(`${API}${path}`, {
    headers, ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

/* ---------- View routing ---------- */
const views = ["landing", "dashboard", "events", "profile", "admin"];
function show(view) {
  views.forEach(v =>
    document.getElementById(`view-${v}`).classList.toggle("hidden", v !== view));
  document.getElementById("nav").classList.toggle("hidden", view === "landing");
  if (view !== "landing" && state.token) refreshView(view);
}

function refreshView(view) {
  if (view === "dashboard") loadDashboard();
  else if (view === "events") loadAllEvents();
  else if (view === "profile") loadProfile();
  else if (view === "admin") loadAdmin();
}

document.getElementById("nav").addEventListener("click", (e) => {
  if (e.target.dataset.view) show(e.target.dataset.view);
});

/* ---------- Auth ---------- */
document.getElementById("login-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const uid = document.getElementById("login-uid").value.trim();
    if (!uid) return;
    const body = {
      uid,
      name: document.getElementById("login-name").value.trim(),
      isAdmin: document.getElementById("login-admin").checked,
    };
    const data = await api("/api/auth/demo-login", { method: "POST", body });
    state.token = data.token;
    state.user = data.user;
    localStorage.setItem("token", state.token);
    localStorage.setItem("user", JSON.stringify(state.user));
    applyAuthChrome();
    show(body.isAdmin ? "" : "dashboard");
    show("dashboard");
  } catch (err) { flash(err.message, "error"); }
});

document.getElementById("btn-logout").onclick = () => {
  state.token = null; state.user = null;
  localStorage.removeItem("token"); localStorage.removeItem("user");
  show("landing");
};

function applyAuthChrome() {
  document.getElementById("nav-admin").classList.toggle("hidden",
    !(state.user && state.user.isAdmin));
}

/* flash messages */
function flash(msg, kind = "ok") {
  let el = document.querySelector(".msg");
  if (!el) {
    el = document.createElement("div");
    document.querySelector(".container:not(.hidden)").prepend(el);
  }
  el.className = `msg ${kind}`;
  el.textContent = msg;
  setTimeout(() => el.remove(), 4000);
}

/* ---------- Event cards ---------- */
function eventCard(e, { score = null, registered = false } = {}) {
  const card = document.createElement("article");
  card.className = "event-card card";
  const when = `${e.date} ${e.startTime || ""}`.trim();
  const seats = `${e.registeredCount || 0}/${e.capacity} registered`;
  card.innerHTML = `
    ${e.category ? `<span class="badge">${e.category}</span>` : ""}
    ${score !== null ? `<span class="score">match score ${score}</span>` : ""}
    <h3></h3>
    <div class="meta">📅 ${when}${e.venue ? ` &nbsp;📍 ${e.venue}` : ""}</div>
    <div class="meta">${e.organizer ? "👤 " + e.organizer + " · " : ""}${seats}</div>
    <p class="small">${e.description || ""}</p>
    <div class="actions"></div>`;
  card.querySelector("h3").textContent = e.title;
  const actions = card.querySelector(".actions");
  if (registered) {
    const b = document.createElement("button");
    b.className = "btn danger small";
    b.textContent = "Cancel registration";
    b.onclick = async () => {
      try {
        await api(`/api/events/${e.eventId}/cancel-registration`, { method: "POST" });
        flash("Registration cancelled");
        refreshView(currentView || "profile");
      } catch (err) { flash(err.message, "error"); }
    };
    actions.appendChild(b);
  } else {
    const b = document.createElement("button");
    b.className = "btn primary small";
    b.textContent = "Register";
    b.onclick = async () => {
      try {
        await api(`/api/events/${e.eventId}/register`, { method: "POST" });
        flash(`Registered for "${e.title}" 🎉`);
        refreshView(currentView);
      } catch (err) { flash(err.message, "error"); }
    };
    actions.appendChild(b);
  }
  return card;
}

/* ---------- Dashboard ---------- */
async function loadDashboard() {
  try {
    const [{ recommendations }, { events }] = await Promise.all([
      api("/api/recommendations"),
      api("/api/events"),
    ]);
    const recList = document.getElementById("recommendation-list");
    recList.innerHTML = "";
    if (!recommendations.length)
      recList.innerHTML = `<p class="muted">No recommendations yet — add interests on the Profile page.</p>`;
    recommendations.forEach(r =>
      recList.appendChild(eventCard(r.event, { score: r.score })));

    const upList = document.getElementById("upcoming-list");
    upList.innerHTML = "";
    events.forEach(e => upList.appendChild(eventCard(e)));
  } catch (err) { flash(err.message, "error"); }
}

/* ---------- All events + filters ---------- */
document.getElementById("filter-bar").addEventListener("submit", (e) => {
  e.preventDefault();
  loadAllEvents();
});

async function loadAllEvents() {
  try {
    const now = new Date().toISOString().slice(0, 10);
    const events = (await api("/api/events")).events;
    const list = document.getElementById("all-events-list");
    list.innerHTML = "";
    if (!events.length) list.innerHTML = `<p class="muted">No events found.</p>`;
    events.forEach(e => list.appendChild(eventCard(e)));
  } catch (err) { flash(err.message, "error"); }
}

/* ---------- Profile ---------- */
async function loadProfile() {
  try {
    const user = (await api("/api/profile")).user;
    state.user = user; localStorage.setItem("user", JSON.stringify(user));
    document.getElementById("p-uid").value = user.uid;
    document.getElementById("p-name").value = user.name || "";
    document.getElementById("p-department").value = user.department || "";
    document.getElementById("p-year").value = user.year || "";
    renderInterests(user.interests || []);
    await loadMyRegistrations();
  } catch (err) { flash(err.message, "error"); }
}

function renderInterests(selected) {
  const box = document.getElementById("interests");
  box.innerHTML = "";
  INTEREST_OPTIONS.forEach(opt => {
    const label = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox"; cb.value = opt;
    cb.checked = selected.some(s => s.toLowerCase() === opt);
    label.append(cb, document.createTextNode(opt));
    box.appendChild(label);
  });
}

document.getElementById("profile-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const interests = [...document.querySelectorAll("#interests input:checked")]
      .map(i => i.value);
    const body = {
      name: document.getElementById("p-name").value.trim(),
      department: document.getElementById("p-department").value.trim(),
      year: document.getElementById("p-year").value.trim(),
      interests,
    };
    const { user } = await api("/api/profile", { method: "PUT", body });
    state.user = user; localStorage.setItem("user", JSON.stringify(user));
    flash("Profile saved ✓");
    loadDashboard();
  } catch (err) { flash(err.message, "error"); }
});

async function loadMyRegistrations() {
  try {
    const regs = (await api("/api/my-registrations")).registrations;
    const list = document.getElementById("my-registrations");
    list.innerHTML = "";
    if (!regs.length) list.innerHTML = `<p class="muted">No registrations yet.</p>`;
    regs.forEach(({ event }) =>
      list.appendChild(eventCard(event, { registered: true })));
  } catch (err) { flash(err.message, "error"); }
}

/* ---------- Admin ---------- */
document.getElementById("admin-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const split = id => document.getElementById(id).value.split(",")
      .map(s => s.trim()).filter(Boolean);
    const body = {
      title: document.getElementById("a-title").value.trim(),
      description: document.getElementById("a-description").value.trim(),
      category: document.getElementById("a-category").value,
      tags: split("a-tags"),
      targetAudience: split("a-audience"),
      date: document.getElementById("a-date").value,
      startTime: document.getElementById("a-start").value,
      endTime: document.getElementById("a-end").value,
      venue: document.getElementById("a-venue").value.trim(),
      organizer: document.getElementById("a-organizer").value.trim(),
      registrationDeadline: document.getElementById("a-deadline").value,
      capacity: parseInt(document.getElementById("a-capacity").value, 10),
      status: document.getElementById("a-status").value,
    };
    await api("/api/admin/events", { method: "POST", body });
    flash("Event created ✓");
    e.target.reset();
    loadAdmin();
  } catch (err) { flash(err.message, "error"); }
});

async function loadAdmin() {
  if (!(state.user && state.user.isAdmin)) { show("dashboard"); return; }
  try {
    const now = new Date().toISOString().slice(0, 10);
    const events = (await api("/api/admin/events")).events;
    const list = document.getElementById("admin-events");
    list.innerHTML = "";
    if (!events.length) list.innerHTML = `<p class="muted">No events yet — create one above.</p>`;
    events.forEach(e => {
      const card = eventCard(e);
      const actions = card.querySelector(".actions");
      if (e.status !== "published") {
        const pub = document.createElement("button");
        pub.className = "btn small"; pub.textContent = "Publish";
        pub.onclick = async () => {
          await api(`/api/admin/events/${e.eventId}`,
            { method: "PUT", body: { status: "published" } });
          flash("Event published ✓"); loadAdmin();
        };
        actions.appendChild(pub);
      }
      if (e.status !== "cancelled") {
        const cancel = document.createElement("button");
        cancel.className = "btn danger small"; cancel.textContent = "Cancel";
        cancel.onclick = async () => {
          try {
            await api(`/api/admin/events/${e.eventId}/cancel`, { method: "POST" });
            flash("Event cancelled"); loadAdmin();
          } catch (err) { flash(err.message, "error"); }
        };
        actions.appendChild(cancel);
      }
      list.appendChild(card);
    });
  } catch (err) { flash(err.message, "error"); }
}

/* ---------- Boot ---------- */
let currentView = "landing";
show(state.token && state.user ? "dashboard" : "landing");
const observer = new MutationObserver(() => {
  const visible = views.find(v =>
    !document.getElementById(`view-${v}`).classList.contains("hidden"));
  if (visible) currentView = visible;
});
observer.observe(document.body, { subtree: true, attributes: true, attributeFilter: ["class"] });
