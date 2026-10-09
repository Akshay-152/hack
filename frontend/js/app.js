/* Campus Event Management System — frontend logic (vanilla JS).
   Same design as the original demo; auth/admin/suggestions/AI reworked. */
const API = location.port === "5000" || location.pathname.indexOf("/api") === 0
  ? "" : "http://localhost:5000";

const INTEREST_OPTIONS = ["coding", "ai", "sports", "music", "arts",
  "entrepreneurship", "volunteering"];

const state = {
  user: null,
  profile: null,
};

/* ---------- API helpers ---------- */
async function api(path, opts = {}) {
  const init = {
    method: opts.method || "GET",
    headers: {},
    credentials: "same-origin",
  };
  if (opts.body !== undefined) {
    init.body = opts.body instanceof FormData
      ? opts.body
      : (init.headers["Content-Type"] = "application/json", JSON.stringify(opts.body));
  } else if (opts.json !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(opts.json);
  }
  const res = await fetch(`${API}${path}`, init);
  let data = {};
  try { data = await res.json(); } catch { /* empty body ok */ }
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}

/* ---------- View routing ---------- */
const views = ["landing", "dashboard", "events", "profile", "admin"];
function currentActiveView() {
  return views.find(v => !document.getElementById(`view-${v}`).classList.contains("hidden"));
}
function show(view) {
  views.forEach(v =>
    document.getElementById(`view-${v}`).classList.toggle("hidden", v !== view));
  const logged = !!state.user;
  document.getElementById("nav").classList.toggle("hidden", view === "landing");
  if (view === "landing" || !logged) { return; }
  refreshView(view);
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
document.getElementById("login-form")?.addEventListener("submit", (e) => e.preventDefault());

document.getElementById("btn-student-login")?.addEventListener("click", async () => {
  const email = document.getElementById("login-uid").value.trim();
  const password = document.getElementById("login-password").value;
  try {
    const data = await api("/api/auth/login", { method: "POST", json: { email, password } });
    state.user = data.user;
    await afterAuth();
  } catch (err) { flash(err.message, "error"); }
});

document.getElementById("btn-student-signup")?.addEventListener("click", async () => {
  const email = document.getElementById("login-uid").value.trim();
  const password = document.getElementById("login-password").value;
  try {
    await api("/api/auth/register", { method: "POST", json: { email, password } });
    state.user = (await api("/api/me")).user;
    flash("Account created — welcome! Set your profile next.", "ok");
    await afterAuth();
    show("profile");
  } catch (err) { flash(err.message, "error"); }
});

document.getElementById("btn-admin-login")?.addEventListener("click", async () => {
  const email = document.getElementById("login-admin-user").value.trim();
  const password = document.getElementById("login-admin-pass").value;
  try {
    const data = await api("/api/auth/login", { method: "POST", json: { email, password } });
    if (data.user.role !== "admin") return flash("Not an admin account", "error");
    state.user = data.user;
    await afterAuth();
    show("admin");
  } catch (err) { flash(err.message, "error"); }
});

document.getElementById("btn-logout").onclick = async () => {
  await api("/api/auth/logout", { method: "POST" }).catch(() => {});
  state.user = null; state.profile = null;
  document.getElementById("nav-admin").classList.add("hidden");
  show("landing");
};

async function afterAuth() {
  applyAuthChrome();
  if (state.user.role === "student") {
    try { state.profile = (await api("/api/profile")).profile; } catch { state.profile = null; }
  }
  show(state.user.role === "admin" ? "admin" : "dashboard");
}

function applyAuthChrome() {
  document.getElementById("nav-admin").classList.toggle("hidden",
    !(state.user && state.user.role === "admin"));
}

function flash(msg, kind = "ok") {
  const container = document.querySelector(".container:not(.hidden)");
  let el = container?.querySelector(".msg");
  if (!el) {
    el = document.createElement("div");
    el.className = "msg";
    container?.prepend(el);
  }
  el.className = `msg ${kind}`;
  el.textContent = msg;
  clearTimeout(el._t);
  el._t = setTimeout(() => el.remove(), 4000);
}

/* ---------- Event cards ---------- */
function eventCard(e, { score = null, registration = null, showAI = false } = {}) {
  const card = document.createElement("article");
  card.className = "event-card card";
  const when = `${e.event_date || e.date || ""} ${e.start_time || e.startTime || ""}`.trim();
  const seats = `${e.registeredCount || 0}/${e.capacity ?? 0} registered`;
  const statusPill = (e.status === "cancelled")
    ? `<span class="badge danger">Cancelled</span>` : "";
  card.innerHTML = `
    ${e.posterUrl ? `<img class="poster" src="${e.posterUrl}" alt="${e.title} poster" />`
      : ""}
    ${categoryBadge(e)}
    ${score !== null ? `<span class="score">${score}</span>` : ""}
    ${statusPill}
    <h3></h3>
    <div class="meta">📅 ${when}${e.venue ? ` &nbsp;📍 ${e.venue}` : ""}</div>
    <div class="meta">${e.organizer ? "👤 " + e.organizer + " · " : ""}${seats}</div>
    <p class="small desc"></p>
    <div class="regnote small muted"></div>
    <div class="ai-sum small muted"></div>
    <div class="actions"></div>`;
  card.querySelector("h3").textContent = e.title;
  card.querySelector("p.desc").textContent = e.description || "";

  const actions = card.querySelector(".actions");
  const regnote = card.querySelector(".regnote");
  const cancelled = e.status === "cancelled";
  const open = e.registrationOpen !== false && !cancelled;

  if (registration) {
    regnote.textContent = registration.status === "pending_external"
      ? "⏳ External registration pending — complete the form to confirm."
      : "✅ You are registered for this event.";
    const b = document.createElement("button");
    b.className = "btn danger small";
    b.textContent = "Cancel registration";
    b.onclick = async () => {
      try {
        await api(`/api/events/${e.id}/cancel-registration`, { method: "POST" });
        flash("Registration cancelled");
        refreshView(currentActiveView());
      } catch (err) { flash(err.message, "error"); }
    };
    actions.appendChild(b);
  } else if (open && state.user?.role === "student") {
    const b = document.createElement("button");
    b.className = "btn primary small";
    b.textContent = externalOnly(e) ? "Open registration form ↗" : "Register";
    b.onclick = async () => {
      const method = e.registration_type || "internal";
      try {
        const data = await api(`/api/events/${e.id}/register`, { method: "POST" });
        flash(data.registration?.message || "Registered 🎉");
        if (method === "external" || method === "both") {
          // opening external form is user-initiated: actual completion is unverifiable
          if (e.registration_url) window.open(e.registration_url, "_blank", "noopener");
        }
        refreshView(currentActiveView());
      } catch (err) { flash(err.message, "error"); }
    };
    actions.appendChild(b);
  } else if (!cancelled) {
    regnote.textContent = "Registration closed";
  }

  if (e.registration_url && (e.registration_type === "both") && open
      && state.user?.role === "student") {
    const alt = document.createElement("button");
    alt.className = "btn small";
    alt.textContent = "Or use Google Form ↗";
    alt.onclick = () => window.open(e.registration_url, "_blank", "noopener");
    actions.appendChild(alt);
  }

  if (showAI) {
    const btn = document.createElement("button");
    btn.className = "btn small ghost";
    btn.textContent = "✨ AI summary";
    btn.onclick = async () => {
      btn.disabled = true; btn.textContent = "…";
      try {
        const { summary } = await api("/api/ai/event-summary",
          { method: "POST", json: { eventId: e.id } });
        card.querySelector(".ai-sum").textContent = summary;
        btn.remove();
      } catch (err) {
        flash(err.message, "error");
        btn.disabled = false; btn.textContent = "✨ AI summary";
      }
    };
    actions.appendChild(btn);
  }
  return card;
}

function categoryBadge(e) {
  const cat = e.category || "";
  return cat ? `<span class="badge">${cat}</span>` : "";
}
function externalOnly(e) {
  return (e.registration_type || "internal") === "external";
}

/* ---------- Dashboard ---------- */
async function loadDashboard() {
  try {
    const [{ recommendations }, { events }, { aiStatusAvailable }] =
      await Promise.all([
        api("/api/recommendations"),
        api("/api/events"),
        api("/api/ai/status").then(s => s.available).catch(() => false),
      ]);
    const recList = document.getElementById("recommendation-list");
    recList.innerHTML = "";
    if (!recommendations.length)
      recList.innerHTML = `<p class="muted">No recommendations yet — add interests on the Profile page.</p>`;
    recommendations.forEach(e =>
      recList.appendChild(eventCard(e, { showAI: aiStatusAvailable })));

    const upList = document.getElementById("upcoming-list");
    upList.innerHTML = "";
    if (!events.length) upList.innerHTML = `<p class="muted">No upcoming events.</p>`;
    events.forEach(e => upList.appendChild(eventCard(e, { showAI: aiStatusAvailable })));
  } catch (err) { flash(err.message, "error"); }
}

/* ---------- All events + filters ---------- */
document.getElementById("filter-bar")?.addEventListener("submit", (e) => {
  e.preventDefault();
  loadAllEvents();
});

async function loadAllEvents() {
  try {
    const params = new URLSearchParams();
    const q = document.getElementById("f-q")?.value.trim();
    const cat = document.getElementById("f-category")?.value;
    const date = document.getElementById("f-date")?.value;
    if (q) params.set("q", q);
    if (cat) params.set("category", cat);
    if (date) params.set("date", date);
    const qs = params.toString() ? `?${params}` : "";
    const events = (await api(`/api/events${qs}`)).events;
    const list = document.getElementById("all-events-list");
    list.innerHTML = "";
    if (!events.length) list.innerHTML = `<p class="muted">No events found.</p>`;
    events.forEach(e => list.appendChild(eventCard(e)));
  } catch (err) { flash(err.message, "error"); }
}

/* ---------- Profile ---------- */
async function loadProfile() {
  try {
    state.profile = (await api("/api/profile")).profile;
    fillProfileForm();
    await loadMyRegistrations();
    await loadMySuggestions();
  } catch { state.profile = null; fillProfileForm(); }
}

function fillProfileForm() {
  const p = state.profile || {};
  document.getElementById("p-email").value = state.user?.email || "";
  ["full_name", "college_id", "course", "department", "semester"]
    .forEach(f => {
      const el = document.getElementById(`p-${f.replace("_", "-")}`);
      if (el) el.value = p[f] || "";
    });
  renderInterests((p.interests || "").split(",").filter(Boolean),
    "interests");
  renderInterests((p.preferred_categories || "").split(",").filter(Boolean),
    "preferred-categories");
  const photo = p.profile_photo
    ? `<img class="poster" src="/uploads/${p.profile_photo}" alt="profile photo" />`
    : "";
  document.getElementById("p-photo-preview").innerHTML = photo;
}

function renderInterests(selected, boxId) {
  const box = document.getElementById(boxId);
  box.innerHTML = "";
  INTEREST_OPTIONS.forEach(opt => {
    const label = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox"; cb.value = opt;
    cb.checked = selected.some(s => s.trim().toLowerCase() === opt);
    label.append(cb, document.createTextNode(opt));
    box.appendChild(label);
  });
}

document.getElementById("profile-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const interests = [...document.querySelectorAll("#interests input:checked")]
      .map(i => i.value);
    const preferred = [...document.querySelectorAll("#preferred-categories input:checked")]
      .map(i => i.value);
    const body = {
      full_name: document.getElementById("p-full-name").value.trim(),
      college_id: document.getElementById("p-college-id").value.trim(),
      course: document.getElementById("p-course").value.trim(),
      department: document.getElementById("p-department").value.trim(),
      semester: document.getElementById("p-semester").value.trim(),
      interests,
      preferred_categories: preferred,
    };
    const { profile } = await api("/api/profile", { method: "PUT", json: body });
    state.profile = profile;
    flash("Profile saved ✓");
    loadDashboard();
  } catch (err) { flash(err.message, "error"); }
});

document.getElementById("p-photo-file")?.addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  try {
    const fd = new FormData();
    fd.append("photo", file);
    const { photoUrl } = await api("/api/profile/photo",
      { method: "POST", body: fd });
    flash("Photo uploaded ✓");
    document.getElementById("p-photo-preview").innerHTML =
      `<img class="poster" src="${photoUrl}" />`;
  } catch (err) { flash(err.message, "error"); }
});

async function loadMyRegistrations() {
  try {
    const regs = (await api("/api/my-registrations")).registrations;
    const list = document.getElementById("my-registrations");
    list.innerHTML = "";
    if (!regs.length) list.innerHTML = `<p class="muted">No registrations yet.</p>`;
    regs.forEach(({ event, registration }) =>
      list.appendChild(eventCard(event, { registration })));
  } catch (err) { flash(err.message, "error"); }
}

/* ---------- Suggestions ---------- */
document.getElementById("suggestion-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const body = {
      title: document.getElementById("s-title").value.trim(),
      category: document.getElementById("s-category").value,
      description: document.getElementById("s-description").value.trim(),
      preferredDate: document.getElementById("s-date").value,
      reason: document.getElementById("s-reason").value.trim(),
    };
    await api("/api/event-suggestions", { method: "POST", json: body });
    flash("Suggestion submitted — thanks! Admin will review it.", "ok");
    e.target.reset();
    loadMySuggestions();
  } catch (err) { flash(err.message, "error"); }
});

document.getElementById("s-ai-help")?.addEventListener("click", async () => {
  try {
    const { suggestion } = await api("/api/ai/polish-suggestion", {
      method: "POST",
      json: {
        title: document.getElementById("s-title").value,
        category: document.getElementById("s-category").value,
        description: document.getElementById("s-description").value,
        reason: document.getElementById("s-reason").value,
      },
    });
    document.getElementById("s-title").value = suggestion.title || "";
    document.getElementById("s-category").value = suggestion.category || "coding";
    document.getElementById("s-description").value = suggestion.description || "";
    document.getElementById("s-reason").value = suggestion.reason || "";
    flash("AI polished your suggestion ✓");
  } catch (err) { flash(err.message, "error"); }
});

async function loadMySuggestions() {
  try {
    const suggestions = (await api("/api/event-suggestions")).suggestions;
    const list = document.getElementById("my-suggestions");
    list.innerHTML = "";
    if (!suggestions.length) list.innerHTML = `<p class="muted">No suggestions yet.</p>`;
    suggestions.forEach(s => {
      const div = document.createElement("div");
      div.className = "card suggestion-row";
      div.innerHTML = `<strong></strong> <span class="badge"></span>
        <span class="badge status"></span>
        <p class="small"></p>`;
      div.querySelector("strong").textContent = s.title;
      div.querySelector(".badge").textContent = s.category;
      div.querySelector(".badge.status").textContent = s.status;
      div.querySelector("p").textContent = s.description || "";
      list.appendChild(div);
    });
  } catch (err) { flash(err.message, "error"); }
}

/* ---------- AI Assistant (dashboard) ---------- */
document.getElementById("assistant-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  const q = document.getElementById("assistant-q").value.trim();
  if (!q) return;
  const out = document.getElementById("assistant-out");
  out.textContent = "Thinking…";
  try {
    const { answer } = await api("/api/ai/assistant",
      { method: "POST", json: { question: q } });
    out.textContent = answer;
  } catch (err) {
    out.textContent = "AI is unavailable right now — you can still browse all events below.";
  }
});

/* ---------- Admin ---------- */
document.getElementById("admin-form")?.addEventListener("submit", async (e) => {
  e.preventDefault();
  try {
    const split = id => document.getElementById(id).value.split(",")
      .map(s => s.trim()).filter(Boolean);
    const fd = new FormData();
    fd.append("title", document.getElementById("a-title").value.trim());
    fd.append("description", document.getElementById("a-description").value.trim());
    fd.append("category", document.getElementById("a-category").value);
    fd.append("tags", split("a-tags").join(","));
    fd.append("event_date", document.getElementById("a-date").value);
    fd.append("start_time", document.getElementById("a-start").value);
    fd.append("end_time", document.getElementById("a-end").value);
    fd.append("venue", document.getElementById("a-venue").value.trim());
    fd.append("organizer", document.getElementById("a-organizer").value.trim());
    fd.append("registration_deadline", document.getElementById("a-deadline").value);
    fd.append("capacity", parseInt(document.getElementById("a-capacity").value || "0", 10));
    fd.append("registration_type", document.getElementById("a-regtype").value);
    fd.append("registration_url", document.getElementById("a-regurl").value.trim());
    fd.append("registration_instructions",
              document.getElementById("a-reginstr").value.trim());
    fd.append("status", document.getElementById("a-status").value);
    const poster = document.getElementById("a-poster").files[0];
    if (poster) fd.append("poster", poster);

    await api("/api/admin/events", { method: "POST", body: fd });
    flash("Event created ✓");
    e.target.reset();
    document.getElementById("a-editing").value = "";
    document.getElementById("admin-submit").textContent = "Create event";
    loadAdmin();
  } catch (err) { flash(err.message, "error"); }
});

document.getElementById("a-ai-draft")?.addEventListener("click", async () => {
  try {
    const { description } = await api("/api/ai/admin-draft", {
      method: "POST",
      json: {
        title: document.getElementById("a-title").value,
        category: document.getElementById("a-category").value,
        venue: document.getElementById("a-venue").value,
        organizer: document.getElementById("a-organizer").value,
        details: document.getElementById("a-description").value,
      },
    });
    document.getElementById("a-description").value = description;
    flash("AI draft ready ✓");
  } catch (err) { flash(err.message, "error"); }
});

async function loadAdmin() {
  if (state.user?.role !== "admin") { show("dashboard"); return; }
  try {
    const { events } = await api("/api/admin/events");
    const list = document.getElementById("admin-events");
    list.innerHTML = "";
    if (!events.length) list.innerHTML = `<p class="muted">No events yet — create one above.</p>`;
    events.forEach(e => {
      const card = eventCard(e);
      card.insertAdjacentHTML("afterbegin",
        `<span class="badge ${e.status}">${e.status}</span>`);
      const actions = card.querySelector(".actions");
      if (e.status !== "published") {
        const pub = document.createElement("button");
        pub.className = "btn small"; pub.textContent = "Publish";
        pub.onclick = async () => {
          await api(`/api/admin/events/${e.id}`,
            { method: "PUT", json: { status: "published" } });
          flash("Event published ✓"); loadAdmin();
        };
        actions.appendChild(pub);
      }
      if (e.status === "published" && !cancelled(e)) {
        const unp = document.createElement("button");
        unp.className = "btn small"; unp.textContent = "Unpublish";
        unp.onclick = async () => {
          await api(`/api/admin/events/${e.id}`,
            { method: "PUT", json: { status: "draft" } });
          flash("Event unpublished"); loadAdmin();
        };
        actions.appendChild(unp);
      }
      const edit = document.createElement("button");
      edit.className = "btn small"; edit.textContent = "Edit";
      edit.onclick = () => {
        fillAdminForm(e);
        document.getElementById("a-editing").value = e.id;
        document.getElementById("admin-submit").textContent = "Update event";
        window.scrollTo({ top: 0, behavior: "smooth" });
      };
      actions.appendChild(edit);

      const del = document.createElement("button");
      del.className = "btn danger small"; del.textContent = "Delete";
      del.onclick = async () => {
        const n = e.registeredCount || 0;
        if (!confirm(`Delete "${e.title}"${n ? ` and its ${n} registration(s)` : ""}? This cannot be undone.`)) return;
        try {
          await api(`/api/admin/events/${e.id}`, { method: "DELETE" });
          flash("Event deleted");
          loadAdmin();
        } catch (err) { flash(err.message, "error"); }
      };
      actions.appendChild(del);
      list.appendChild(card);
    });

    // pending suggestions
    const { suggestions } = await api("/api/admin/suggestions");
    const suggList = document.getElementById("admin-suggestions");
    suggList.innerHTML = "";
    if (!suggestions.length)
      suggList.innerHTML = `<p class="muted">No student suggestions yet.</p>`;
    suggestions.forEach(s => {
      const row = document.createElement("div");
      row.className = "card suggestion-row";
      row.innerHTML = `<strong></strong>
        <span class="badge">${s.category}</span>
        <span class="badge ${s.status}">${s.status}</span>
        <span class="muted small">by ${s.student_email}</span>
        <p class="small"></p>
        ${s.preferred_date ? `<p class="small">Preferred: ${s.preferred_date}</p>` : ""}
        <div class="actions"></div>`;
      row.querySelector("strong").textContent = s.title;
      row.querySelector("p").textContent = s.description || "";
      const actions = row.querySelector(".actions");
      if (s.status === "pending") {
        const ap = document.createElement("button");
        ap.className = "btn primary small"; ap.textContent = "Approve";
        ap.onclick = async () => {
          await api(`/api/admin/suggestions/${s.id}/approve`, { method: "POST" });
          flash("Suggestion approved"); loadAdmin();
        };
        const rj = document.createElement("button");
        rj.className = "btn danger small"; rj.textContent = "Reject";
        rj.onclick = async () => {
          await api(`/api/admin/suggestions/${s.id}/reject`, { method: "POST" });
          flash("Suggestion rejected"); loadAdmin();
        };
        actions.append(ap, rj);
      } else if (s.status === "approved") {
        const mk = document.createElement("button");
        mk.className = "btn primary small";
        mk.textContent = "Create event from this";
        mk.onclick = () => {
          fillAdminForm({
            title: s.title, category: s.category, description: s.description,
            event_date: s.preferred_date, organizer: s.student_email,
          });
          document.getElementById("admin-submit").textContent = "Create event";
          show("admin-form-target") || window.scrollTo({ top: 0 });
        };
        actions.appendChild(mk);
      } else {
        actions.remove();
      }
      suggList.appendChild(row);
    });
  } catch (err) { flash(err.message, "error"); }
}

function cancelled(e) { return e.status === "cancelled"; }

function fillAdminForm(e) {
  const set = (id, v) => { const el = document.getElementById(id); if (el) el.value = v ?? ""; };
  set("a-title", e.title);
  set("a-description", e.description);
  set("a-category", e.category || "coding");
  set("a-tags", Array.isArray(e.tags) ? e.tags.join(",") : (e.tags || ""));
  set("a-date", e.event_date);
  set("a-start", e.start_time);
  set("a-end", e.end_time);
  set("a-venue", e.venue);
  set("a-organizer", e.organizer);
  set("a-deadline", e.registration_deadline);
  set("a-capacity", e.capacity);
  set("a-regtype", e.registration_type || "internal");
  set("a-regurl", e.registration_url);
  set("a-reginstr", e.registration_instructions);
  set("a-status", e.status || "draft");
}

/* ---------- Boot ---------- */
(async function boot() {
  try { state.user = (await api("/api/me")).user; } catch { state.user = null; }
  if (state.user) await afterAuth();
  else show("landing");
})();

const observer = new MutationObserver(() => {
  const visible = currentActiveView();
  if (visible && visible !== "landing") refreshOnce(visible);
});
function refreshOnce(view) {
  if (refreshOnce._last === view) return;
  refreshOnce._last = view;
  refreshView(view);
}
observer.observe(document.body, { subtree: true, attributes: true,
  attributeFilter: ["class"] });
