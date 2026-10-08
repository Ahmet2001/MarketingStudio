"use strict";
// MarketingStudio viewer. Read-only: lists workflows and capabilities, and shows what each export looks like.
const $ = (id) => document.getElementById(id);
const S = { view: "workflows", workflows: [], capabilities: [], targets: [], selected: null, detail: null, target: null, exported: null, file: null };

function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === false || v == null) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.className = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat(Infinity)) if (kid != null && kid !== false) el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  return el;
}
function fill(el, ...kids) {
  el.replaceChildren(...kids.flat(Infinity).filter((k) => k != null && k !== false).map((k) => (k.nodeType ? k : document.createTextNode(String(k)))));
}
async function api(path, body) {
  const res = await fetch(path, body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}
const tag = (text, kind = "") => h("span", { class: `tag ${kind}` }, text);
const kb = (n) => (n < 1024 ? `${n} B` : `${(n / 1024).toFixed(1)} KB`);

// ---------- list ----------
function renderList() {
  const q = $("search").value.trim().toLowerCase();
  const items = S.view === "workflows" ? S.workflows : S.capabilities;
  const match = (x) => !q || JSON.stringify([x.id, x.name, x.title, x.path, x.description]).toLowerCase().includes(q);
  if (S.view === "workflows") {
    fill($("items"), S.workflows.filter(match).map((w) => h("div", { class: `item ${S.selected === w.path ? "on" : ""}`, onclick: () => openWorkflow(w.path) },
      h("b", {}, w.name || w.id), h("small", {}, w.path),
      tag(`${w.steps} step${w.steps === 1 ? "" : "s"}`), tag(`${w.inputs} input${w.inputs === 1 ? "" : "s"}`),
      w.valid ? tag("valid", "ok") : tag(`${w.errors} problem${w.errors === 1 ? "" : "s"}`, "bad"),
      w.gated ? tag("needs approval", "warn") : null)),
      !S.workflows.length ? h("p", { class: "muted" }, "No workflow files found under the root.") : null);
  } else {
    fill($("items"), S.capabilities.filter(match).map((c) => h("div", { class: `item ${S.selected === c.id ? "on" : ""}`, onclick: () => { S.selected = c.id; renderList(); renderDetail(); } },
      h("b", {}, c.id), h("small", {}, c.title), tag(c.kind), tag(c.status || "?"), c.permissions.writes_external_state ? tag("writes outside", "warn") : null)));
  }
}

// ---------- workflow detail ----------
async function openWorkflow(path) {
  S.selected = path; S.detail = null; S.exported = null; S.target = null; S.file = null;
  renderList(); fill($("detail"), h("p", { class: "muted" }, "Loading…"));
  try { S.detail = await api("/api/workflow?path=" + encodeURIComponent(path)); } catch (e) { return fill($("detail"), h("p", { class: "bad" }, e.message)); }
  renderDetail();
}

function renderWorkflow() {
  const d = S.detail, wf = d.doc.workflow;
  const inputs = Object.entries(wf.inputs || {}), outputs = Object.entries(wf.outputs || {});
  const steps = d.order.length ? d.order : (wf.steps || []).map((s) => s.id);
  const stepOf = (id) => (wf.steps || []).find((s) => s.id === id) || {};
  const root = h("div", {},
    h("h1", {}, wf.name || wf.id),
    h("div", { class: "muted" }, h("code", {}, d.path), "  ", wf.version ? `v${wf.version}` : "", wf.description ? ` · ${wf.description}` : ""),
    d.errors.length ? h("div", {}, h("h2", {}, "Problems"), h("ul", { class: "plain bad" }, d.errors.map((e) => h("li", {}, e)))) : null,
    d.warnings.length ? h("ul", { class: "plain warn" }, d.warnings.map((e) => h("li", {}, e))) : null,
    h("h2", {}, "Inputs"),
    inputs.length ? h("table", {}, h("tr", {}, ["name", "type", "required", "default"].map((x) => h("th", {}, x))),
      inputs.map(([n, s]) => h("tr", {}, h("td", {}, h("code", {}, n)), h("td", {}, s.type), h("td", {}, s.required ? "yes" : ""), h("td", { class: "muted" }, "default" in s ? JSON.stringify(s.default) : "")))) : h("p", { class: "muted" }, "none"),
    h("h2", {}, "Steps, in the order they run"),
    h("table", {}, h("tr", {}, ["#", "step", "capability", "kind", "after", "approval"].map((x) => h("th", {}, x))),
      steps.map((id, i) => {
        const s = stepOf(id), cap = d.capabilities[s.capability];
        return h("tr", {}, h("td", {}, i + 1), h("td", {}, h("code", {}, id)), h("td", {}, s.capability, cap ? h("div", { class: "muted" }, cap.title) : h("div", { class: "bad" }, "not in the registry")),
          h("td", {}, cap?.kind || ""), h("td", { class: "muted" }, (d.plan?.steps.find((p) => p.id === id)?.needs || []).join(", ")),
          h("td", {}, d.approval[id] ? tag("required", "warn") : ""));
      })),
    h("h2", {}, "Outputs"),
    outputs.length ? h("table", {}, outputs.map(([n, v]) => h("tr", {}, h("td", {}, h("code", {}, n)), h("td", { class: "muted" }, h("code", {}, String(v)))))) : h("p", { class: "muted" }, "none"),
    d.plan ? h("div", {}, h("h2", {}, "On this machine"),
      h("p", { class: d.plan.missing.length ? "bad" : "ok" }, d.plan.missing.length ? "Not ready: " + d.plan.missing.join("; ") : "Ready: nothing is missing."),
      h("p", { class: "muted" }, `Estimated cost: $${d.plan.total_cost_usd}` + (d.plan.unknown_cost_steps.length ? `, unknown for ${d.plan.unknown_cost_steps.join(", ")}` : ""))) : null,
    h("h2", {}, "Export"),
    h("p", { class: "about" }, "Pick a format to see exactly which files it produces and what is in them. Nothing is installed or sent anywhere."),
    h("div", { class: "chips" }, S.targets.map((t) => h("button", { class: S.target === t.id ? "on" : "", disabled: !!d.errors.length, onclick: () => doExport(t.id) }, t.id))),
    h("div", { id: "export" }),
    h("details", {}, h("summary", {}, "Source file"), h("pre", { class: "muted" }, d.yaml)));
  return root;
}

async function doExport(target) {
  S.target = target; S.file = null; S.exported = null;
  renderDetail(true);
  try { S.exported = await api("/api/export", { path: S.selected, target }); } catch (e) { S.exported = { errors: [e.message] }; }
  S.file = S.exported.files?.[0]?.name || null;
  renderExport();
}

function renderExport() {
  const box = $("export"), x = S.exported;
  if (!box) return;
  document.querySelectorAll(".chips button").forEach((b) => b.classList.toggle("on", b.textContent === S.target));
  if (!x) return fill(box, h("p", { class: "muted" }, "Building…"));
  if (x.errors) return fill(box, h("ul", { class: "plain bad" }, x.errors.map((e) => h("li", {}, e))));
  const about = S.targets.find((t) => t.id === S.target)?.about;
  const file = x.files.find((f) => f.name === S.file) || x.files[0];
  fill(box,
    h("p", { class: "about" }, about),
    h("p", {}, h("button", { class: "primary", onclick: () => download(x) }, "Download " + x.name), `  ${x.files.length} file${x.files.length === 1 ? "" : "s"}`),
    x.notes.length ? h("div", {}, h("b", {}, "Notes"), h("ul", { class: "plain warn" }, x.notes.map((n) => h("li", {}, n)))) : null,
    h("div", { class: "files" },
      h("ul", {}, x.files.map((f) => h("li", { class: f.name === file.name ? "on" : "", onclick: () => { S.file = f.name; renderExport(); } }, f.name, h("small", {}, kb(f.size))))),
      h("div", { class: "viewer" },
        h("div", { class: "bar" }, h("code", {}, file.name), h("button", { onclick: (e) => { navigator.clipboard?.writeText(file.text); e.target.textContent = "Copied"; setTimeout(() => (e.target.textContent = "Copy"), 1200); } }, "Copy")),
        h("pre", {}, file.text, file.cut ? "\n\n… shortened here; the download has the whole file." : ""))));
}

function download(x) {
  const bytes = Uint8Array.from(atob(x.zip), (c) => c.charCodeAt(0));
  const a = h("a", { href: URL.createObjectURL(new Blob([bytes], { type: "application/zip" })), download: x.name });
  document.body.append(a); a.click(); a.remove();
}

// ---------- capability detail ----------
function renderCapability(c) {
  const rows = (obj) => Object.entries(obj).map(([n, s]) => h("tr", {}, h("td", {}, h("code", {}, n)), h("td", {}, s.type), h("td", {}, s.required && !("default" in s) ? "yes" : ""), h("td", { class: "muted" }, s.description || (("default" in s) ? `default ${JSON.stringify(s.default)}` : ""))));
  const head = ["name", "type", "required", "about"].map((x) => h("th", {}, x));
  const req = c.requires, needs = [...(req.env || []).map((e) => `env ${e}`), ...(req.binaries || []).map((b) => `program ${b}`), ...(req.hardware || []).map((x) => `hardware ${x}`), ...(req.packages || []).map((p) => `python ${p}`)];
  return h("div", {}, h("h1", {}, c.id), h("div", { class: "muted" }, c.title, " · from ", h("code", {}, c.origin)),
    h("p", {}, c.description), h("div", {}, tag(c.kind), tag(c.status || "?"), c.permissions.network ? tag("network") : null, c.permissions.writes_external_state ? tag("writes outside · approval required", "warn") : null),
    h("h2", {}, "Inputs"), Object.keys(c.inputs).length ? h("table", {}, h("tr", {}, head), rows(c.inputs)) : h("p", { class: "muted" }, "none"),
    h("h2", {}, "Outputs"), Object.keys(c.outputs).length ? h("table", {}, h("tr", {}, head), rows(c.outputs)) : h("p", { class: "muted" }, "none"),
    h("h2", {}, "Needs"), needs.length ? h("ul", { class: "plain" }, needs.map((n) => h("li", {}, n))) : h("p", { class: "muted" }, "nothing beyond Python"),
    h("p", { class: "muted" }, c.cost == null ? "Cost: not measured." : `Estimated cost: $${c.cost}`));
}

function renderDetail(keepScroll) {
  const pane = $("detail"), top = pane.scrollTop;
  if (S.view === "workflows") {
    if (!S.detail) return fill(pane, h("p", { class: "muted" }, "Choose a workflow on the left."));
    fill(pane, renderWorkflow());
    renderExport();
  } else {
    const c = S.capabilities.find((x) => x.id === S.selected);
    fill(pane, c ? renderCapability(c) : h("p", { class: "muted" }, "Choose a capability on the left."));
  }
  if (keepScroll) pane.scrollTop = top;
}

// ---------- wiring ----------
async function load() {
  try {
    const [w, c] = await Promise.all([api("/api/workflows"), api("/api/capabilities")]);
    Object.assign(S, { workflows: w.workflows, capabilities: c.capabilities, targets: c.targets });
    $("root").textContent = c.root;
    if (c.error) alert("Capabilities could not be loaded:\n" + c.error);
  } catch (e) { alert(e.message); }
  renderList(); renderDetail();
}
document.querySelectorAll("#views button").forEach((b) => b.addEventListener("click", () => {
  S.view = b.dataset.view; S.selected = null; S.detail = null; S.exported = null;
  document.querySelectorAll("#views button").forEach((x) => x.classList.toggle("on", x === b));
  $("search").value = ""; renderList(); renderDetail();
}));
$("search").addEventListener("input", renderList);
$("reload").addEventListener("click", async () => { const keep = S.selected; await load(); if (S.view === "workflows" && keep) openWorkflow(keep); });
load();
