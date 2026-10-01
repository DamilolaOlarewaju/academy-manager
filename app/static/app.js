"use strict";
const main = document.querySelector("main"),
  account = document.querySelector("#account");
let state,
  csrf = "",
  tab = "overview",
  demo = false;
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
function notify(message, error = false) {
  const el = document.querySelector("#notice");
  el.textContent = message;
  el.className = error ? "notice error" : "notice";
}
async function api(path, options = {}) {
  const res = await fetch("/api" + path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-CSRF-Token": csrf,
      ...options.headers,
    },
  });
  if (!res.ok) {
    let data = await res.json().catch(() => ({}));
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Check the fields and try again.",
    );
  }
  return res.status === 204 ? null : res.json();
}
function field(label, name, type = "text", value = "", extra = "") {
  return `<label>${label}<input name="${name}" type="${type}" value="${esc(value)}" required ${extra}></label>`;
}
function textField(label, name, value = "") {
  return `<label>${label}<textarea name="${name}" required maxlength="4000">${esc(value)}</textarea></label>`;
}
function loginView() {
  account.innerHTML = "";
  main.innerHTML = `<section class="login"><div><p class="eyebrow">LESS ADMIN. MORE LEARNING.</p><h1>A little structure.<br>A lot of progress.</h1><p class="lede">One shared space for lessons, projects, and the feedback that helps students grow.</p><div class="feature"><b>01</b> Plan the next step</div><div class="feature"><b>02</b> Build something meaningful</div><div class="feature"><b>03</b> Make progress visible</div></div><div class="panel"><span class="pill">Your learning workspace</span><h2>Welcome back</h2><p>Sign in to pick up where you left off.</p><form id="login">${field("Email", "email", "email", "", 'autocomplete="username"')}${field("Password", "password", "password", "", 'autocomplete="current-password"')}<button>Sign in →</button></form>${demo ? '<div class="demo"><b>Explore the fictional demo</b><p>Choose a role to try the complete workflow. Changes are shared with other demo visitors.</p><div class="buttons"><button type="button" data-demo="teacher" class="secondary">Teacher</button><button type="button" data-demo="student" class="secondary">Student</button><button type="button" data-demo="parent" class="secondary">Parent</button></div></div>' : ""}</div></section>`;
}
async function refresh() {
  state = await api("/dashboard");
  csrf = state.user.csrf;
  render();
}
function stats() {
  const graded = state.submissions.filter((s) => s.score !== null);
  return `<div class="stats"><article><span>Learning sessions</span><strong>${state.lessons.length}</strong><small>On your learning timeline</small></article><article><span>Projects submitted</span><strong>${state.submissions.length}</strong><small>Ideas turned into working code</small></article><article><span>Average reviewed score</span><strong>${graded.length ? Math.round(graded.reduce((a, s) => a + s.score, 0) / graded.length) + "%" : "—"}</strong><small>${graded.length} reviewed submission${graded.length === 1 ? "" : "s"}</small></article></div>`;
}
function lessons() {
  return `<div class="section-heading"><h2>Learning timeline</h2><span>${state.lessons.length} sessions</span></div><div class="lesson-list">${state.lessons.map((l, i) => `<article class="lesson"><span class="step">${String(i + 1).padStart(2, "0")}</span><div><h3>${esc(l.title)}</h3><p>${esc(l.summary)}</p></div><time>${esc(l.scheduled.replace("T", " · "))}</time></article>`).join("") || "<p>No lessons yet. Your next chapter starts here.</p>"}</div>`;
}
function projects() {
  return `<div class="section-heading"><h2>Project studio</h2><span>Practice. Submit. Improve.</span></div><div class="projects">${
    state.assignments
      .map((a) => {
        const s = state.submissions.find(
          (x) => x.assignment_id === a.id && x.student_id === state.user.id,
        );
        return `<article class="panel"><div class="project-top"><span class="pill">${s ? (s.score !== null ? "Reviewed" : "Submitted") : "Assignment"}</span><small>Due ${esc(a.due)}</small></div><h3>${esc(a.title)}</h3><p>${esc(a.instructions)}</p>${state.user.role === "student" ? `<form data-submit="${a.id}">${field("Project URL", "url", "url", s?.url || "", 'maxlength="2000" placeholder="https://github.com/you/project"')}<button class="secondary">${s ? "Update submission" : "Submit project"} →</button></form>${s?.score !== null && s?.score !== undefined ? `<div class="feedback"><b>${s.score}/100 · Teacher feedback</b><p>${esc(s.feedback)}</p></div>` : ""}` : ""}</article>`;
      })
      .join("") || "<p>No assignments yet.</p>"
  }</div>`;
}
function reviews() {
  return `<div class="section-heading"><h2>${state.user.role === "teacher" ? "Feedback queue" : "Progress & feedback"}</h2></div>${state.submissions.map((s) => `<article class="panel review"><div><span class="pill">${s.score === null ? "Awaiting feedback" : s.score + "/100"}</span><h3>${esc(state.assignments.find((a) => a.id === s.assignment_id)?.title)}</h3><p>${esc(state.students.find((x) => x.id === s.student_id)?.name)}</p><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">Open project ↗</a></div>${state.user.role === "teacher" ? `<form data-review="${s.id}">${field("Score out of 100", "score", "number", s.score ?? "", 'min="0" max="100" step="1"')}${textField("Constructive feedback", "feedback", s.feedback)}<button>Save feedback</button></form>` : `<div class="feedback"><b>Teacher feedback</b><p>${esc(s.feedback || "Your teacher has not reviewed this submission yet.")}</p></div>`}</article>`).join("") || '<div class="panel"><h3>A fresh start</h3><p>Submitted projects and teacher feedback will appear here.</p></div>'}`;
}
function planning() {
  return `<div class="section-heading"><h2>Plan the next milestone</h2></div><div class="projects"><form class="panel" id="lesson"><h3>New lesson</h3>${field("Title", "title", "text", "", 'maxlength="120"')}${textField("What will students learn?", "summary")}${field("Date and time (academy local time)", "scheduled", "datetime-local")}<button>Create lesson</button></form><form class="panel" id="assignment"><h3>New assignment</h3>${field("Title", "title", "text", "", 'maxlength="120"')}${textField("Instructions", "instructions")}${field("Due date", "due", "date")}<button>Create assignment</button></form></div>`;
}
function render() {
  account.innerHTML = `<span>${esc(state.user.name)} <b class="role">${esc(state.user.role)}</b></span><button id="logout" class="secondary">Sign out</button>`;
  main.innerHTML = `${demo ? '<div class="demo-banner">DEMO WORKSPACE · Fictional people and example projects</div>' : ""}<section class="welcome"><div><p class="eyebrow">YOUR LEARNING, CONNECTED</p><h1>Every step counts.</h1><p class="lede">${state.user.role === "teacher" ? "Turn today’s practice into tomorrow’s confidence." : state.user.role === "parent" ? "A clear view of your child’s learning journey." : "Your next great project starts with one small step."}</p></div><span class="workspace-tag">● Academy workspace</span></section>${stats()}<nav aria-label="Workspace sections">${[["overview", "Overview"], ["projects", "Projects"], ["feedback", "Feedback"], ...(state.user.role === "teacher" ? [["planning", "Plan lessons"]] : [])].map(([id, label]) => `<button class="nav-button ${tab === id ? "active" : ""}" data-tab="${id}" aria-current="${tab === id ? "page" : "false"}">${label}</button>`).join("")}</nav><section id="content">${tab === "overview" ? lessons() : tab === "projects" ? projects() : tab === "feedback" ? reviews() : planning()}</section>`;
}
document.addEventListener("click", async (e) => {
  const button = e.target.closest("button");
  if (!button) return;
  try {
    if (button.dataset.tab) {
      tab = button.dataset.tab;
      render();
      document.querySelector(`[data-tab="${tab}"]`).focus();
    } else if (button.dataset.demo) {
      button.disabled = true;
      await api("/login", {
        method: "POST",
        body: JSON.stringify({
          email: button.dataset.demo + "@demo.test",
          password: "demo-learning-2026",
        }),
      });
      notify("Demo workspace ready.");
      await refresh();
    } else if (button.id === "logout") {
      await api("/logout", { method: "POST" });
      csrf = "";
      notify("Signed out.");
      loginView();
    }
  } catch (error) {
    notify(error.message, true);
    button.disabled = false;
  }
});
document.addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target,
    button = form.querySelector("button");
  button.disabled = true;
  const body = Object.fromEntries(new FormData(form));
  try {
    if (form.id === "login") {
      await api("/login", { method: "POST", body: JSON.stringify(body) });
      await refresh();
      notify("Welcome back.");
      return;
    }
    let path,
      method = "POST";
    if (form.id === "lesson") path = "/lessons";
    else if (form.id === "assignment") path = "/assignments";
    else if (form.dataset.submit) {
      path = `/assignments/${form.dataset.submit}/submission`;
      method = "PUT";
    } else if (form.dataset.review) {
      path = `/submissions/${form.dataset.review}/review`;
      method = "PUT";
      body.score = Number(body.score);
    }
    await api(path, { method, body: JSON.stringify(body) });
    await refresh();
    notify("Saved successfully.");
  } catch (error) {
    notify(error.message, true);
    button.disabled = false;
  }
});
(async () => {
  try {
    demo = (await api("/config")).demo;
    try {
      await refresh();
    } catch {
      loginView();
    }
  } catch (error) {
    main.innerHTML =
      "<h1>Unable to load the workspace</h1><p>Please refresh to try again.</p>";
    notify(error.message, true);
  }
})();
