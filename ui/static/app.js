"use strict";
// MarketingStudio editor. No build step, no libraries. It edits one workflow document and
// asks the local server (a thin wrapper over the studio package) to validate, plan, run and export it.

const $ = (id) => document.getElementById(id);
const NODE_W = 230, ROW_H = 21, HEAD_H = 33;
const REF = /\{\{\s*(inputs|steps)\.([A-Za-z0-9_]+)(?:\.outputs\.([A-Za-z0-9_]+))?[^}]*\}\}/g;
const WHOLE_REF = /^\{\{\s*(inputs|steps)\.([A-Za-z0-9_]+)(?:\.outputs\.([A-Za-z0-9_]+))?\s*(?:\|\s*as\s+[a-z:0-9]+\s*)?\}\}$/;
const TYPES = ["text", "integer", "number", "boolean", "url", "enum", "list", "object", "any", "file:any", "file:image", "file:video", "file:audio", "file:json", "file:mp4", "file:text"];

const S = {
  caps: {}, capList: [], targets: [], root: "",
  doc: blank(), layout: {}, sel: null, file: null, dirty: false,
  check: { errors: [], warnings: [], order: [], approval: {} },
  tab: "problems", drag: null, run: null, exportResult: null, plan: null, yamlDirty: false,
};

function blank() {
  return { spec_version: "0.1", workflow: { id: "new_workflow", name: "New workflow", version: "0.1.0", inputs: {}, steps: [], outputs: {} } };
}
const wf = () => S.doc.workflow;
const steps = () => wf().steps;
const stepById = (id) => steps().find((s) => s.id === id);

function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === false || v == null) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.className = v;
    else if (k === "value") el.value = v;
    else if (v === true) el.setAttribute(k, "");
    else el.setAttribute(k, v);
  }
  for (const kid of kids.flat()) if (kid != null && kid !== false) el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  return el;
}

// like replaceChildren, but arrays are flattened and null/false are skipped (replaceChildren would print them)
function fill(el, ...kids) {
  el.replaceChildren(...kids.flat(Infinity).filter((k) => k != null && k !== false).map((k) => (k.nodeType ? k : document.createTextNode(String(k)))));
}

async function api(path, body) {
  const res = await fetch(path, body === undefined ? {} : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || res.statusText);
  return data;
}
function fail(error) { alert(error.message || String(error)); }

// ---------- document helpers ----------
function refsIn(value) {
  const found = [];
  if (typeof value !== "string") return found;
  for (const m of value.matchAll(REF)) found.push({ kind: m[1], id: m[2], out: m[3] || null });
  return found;
}
function wholeRef(value) {
  const m = typeof value === "string" ? value.match(WHOLE_REF) : null;
  return m ? { kind: m[1], id: m[2], out: m[3] || null } : null;
}
const refText = (r) => (r.kind === "inputs" ? `inputs.${r.id}` : `${r.id}.${r.out}`);
function makeRef(kind, id, out) { return kind === "inputs" ? `{{ inputs.${id} }}` : `{{ steps.${id}.outputs.${out} }}`; }

function changed() {
  S.dirty = true;
  renderAll();
  clearTimeout(changed.t);
  changed.t = setTimeout(validate, 350);
}

function uniqueId(base) {
  base = base.split(".").pop().replace(/[^a-z0-9_]/gi, "_").toLowerCase().replace(/^[^a-z]+/, "") || "step";
  let id = base, n = 2;
  while (stepById(id)) id = `${base}_${n++}`;
  return id;
}

function addStep(capId, x, y) {
  const id = uniqueId(capId);
  steps().push({ id, capability: capId, with: {} });
  S.layout[id] = [Math.max(10, Math.round(x)), Math.max(10, Math.round(y))];
  S.sel = id;
  changed();
}

function renameStep(oldId, newId) {
  if (!/^[a-z][a-z0-9_]*$/.test(newId) || (newId !== oldId && stepById(newId))) { fail(new Error("A step id is lowercase letters, digits and underscores, starts with a letter, and must be unique.")); return false; }
  const swap = (text) => (typeof text === "string" ? text.replace(new RegExp(`(steps\\.)${oldId}(\\.outputs)`, "g"), `$1${newId}$2`) : text);
  for (const s of steps()) {
    if (s.id === oldId) s.id = newId;
    for (const k of Object.keys(s.with || {})) s.with[k] = swap(s.with[k]);
    if (s.needs) s.needs = s.needs.map((n) => (n === oldId ? newId : n));
  }
  for (const k of Object.keys(wf().outputs || {})) wf().outputs[k] = swap(wf().outputs[k]);
  if (S.layout[oldId]) { S.layout[newId] = S.layout[oldId]; delete S.layout[oldId]; }
  if (S.sel === oldId) S.sel = newId;
  return true;
}

function removeStep(id) {
  wf().steps = steps().filter((s) => s.id !== id);
  const gone = (v) => refsIn(v).some((r) => r.kind === "steps" && r.id === id);
  for (const s of steps()) {
    for (const k of Object.keys(s.with || {})) if (gone(s.with[k])) delete s.with[k];
    if (s.needs) s.needs = s.needs.filter((n) => n !== id);
  }
  for (const k of Object.keys(wf().outputs || {})) if (gone(wf().outputs[k])) delete wf().outputs[k];
  delete S.layout[id];
  if (S.sel === id) S.sel = null;
  changed();
}

function connect(from, to) {
  // from: {kind:'inputs'|'steps', id, out}  to: {node:'__outputs'|stepId, name}
  if (to.node === "__outputs") wf().outputs[to.name] = makeRef(from.kind, from.id, from.out);
  else {
    if (from.kind === "steps" && from.id === to.node) return;
    const step = stepById(to.node);
    step.with = step.with || {};
    step.with[to.name] = makeRef(from.kind, from.id, from.out);
  }
  changed();
}
function disconnect(to) {
  if (to.node === "__outputs") delete wf().outputs[to.name];
  else delete stepById(to.node).with[to.name];
  changed();
}

// ---------- layout ----------
const capOf = (step) => S.caps[step.capability];
function stepRows(step) {
  const cap = capOf(step);
  const ins = cap ? Object.entries(cap.inputs) : Object.keys(step.with || {}).map((k) => [k, { type: "?" }]);
  const outs = cap ? Object.entries(cap.outputs) : [];
  return { ins, outs };
}
function nodeHeight(step) { const r = stepRows(step); return HEAD_H + (r.ins.length + r.outs.length) * ROW_H + 10; }

function computeLayout() {
  const depth = {};
  const deps = (s) => {
    const d = new Set();
    for (const v of Object.values(s.with || {})) for (const r of refsIn(v)) if (r.kind === "steps" && r.id !== s.id) d.add(r.id);
    for (const n of s.needs || []) d.add(n);
    return [...d];
  };
  const level = (s, seen = new Set()) => {
    if (depth[s.id] != null) return depth[s.id];
    if (seen.has(s.id)) return 0;
    seen.add(s.id);
    return (depth[s.id] = 1 + Math.max(-1, ...deps(s).map((id) => (stepById(id) ? level(stepById(id), seen) : -1))));
  };
  const columns = {};
  for (const s of steps()) (columns[level(s)] ||= []).push(s);
  S.layout = { __inputs: [30, 40] };
  let last = 0;
  for (const [d, list] of Object.entries(columns)) {
    let y = 40;
    for (const s of list) { S.layout[s.id] = [300 + d * 300, y]; y += nodeHeight(s) + 30; }
    last = Math.max(last, +d);
  }
  S.layout.__outputs = [300 + (last + 1) * 300, 40];
}
function autoLayout() { computeLayout(); renderAll(); }
function ensureLayout() {
  if (steps().every((s) => S.layout[s.id]) && S.layout.__inputs && S.layout.__outputs) return;
  const keep = S.layout;
  computeLayout();
  for (const k of Object.keys(keep)) if (S.layout[k]) S.layout[k] = keep[k];
}

// ---------- rendering: palette ----------
function renderPalette() {
  const q = $("search").value.trim().toLowerCase();
  const box = $("caps");
  fill(box, ...S.capList.filter((c) => !q || (c.id + " " + c.title + " " + c.description).toLowerCase().includes(q)).map((c) => {
    const writes = c.permissions.writes_external_state;
    const el = h("div", { class: "cap", draggable: true, title: c.description + "\n\ndouble-click to add" },
      h("b", {}, c.id),
      h("small", {}, c.title),
      h("div", {}, h("span", { class: "tag" }, c.kind), h("span", { class: "tag" }, c.status || "?"),
        writes ? h("span", { class: "tag warn" }, "writes outside") : null));
    el.addEventListener("dragstart", (e) => e.dataTransfer.setData("text/plain", c.id));
    el.addEventListener("dblclick", () => addStep(c.id, 320 + steps().length * 30, 60 + steps().length * 30));
    return el;
  }));
  if (!S.capList.length) fill(box, h("p", { class: "muted" }, "No capabilities found. Start the editor with --sources DIR."));
}

// ---------- rendering: canvas ----------
const portKey = (node, dir, name) => `${node}|${dir}|${name}`;

function nodeEl(id, title, sub, ins, outs, extraClass = "") {
  const pos = S.layout[id] || [40, 40];
  const bad = S.check.errors.some((e) => e.startsWith(`step '${id}'`) || e.includes(`'${id}'`));
  const el = h("div", { class: `node ${extraClass} ${S.sel === id ? "sel" : ""} ${bad ? "bad" : ""}`, style: `left:${pos[0]}px;top:${pos[1]}px`, "data-id": id });
  const head = h("header", {}, h("span", {}, title), h("small", {}, sub));
  head.addEventListener("mousedown", (e) => {
    if (e.button !== 0) return;
    S.sel = id;
    S.drag = { type: "node", id, dx: e.clientX - pos[0], dy: e.clientY - pos[1], moved: false };
    e.preventDefault();
  });
  el.append(head);
  const row = (name, type, dir, opts = {}) => {
    const port = h("span", { class: `port ${dir}`, "data-port": portKey(id, dir, name) });
    port.addEventListener("mousedown", (e) => {
      e.stopPropagation(); e.preventDefault();
      S.drag = { type: "link", from: dir === "out" ? { node: id, name } : null, to: dir === "in" ? { node: id, name } : null, x: e.clientX, y: e.clientY };
    });
    return h("div", { class: `row ${dir} ${opts.required ? "req" : ""}`, title: opts.title || "" }, dir === "in" ? port : null,
      h("span", { class: "n" }, name), h("span", { class: "t" }, type), dir === "out" ? port : null);
  };
  for (const [name, type, o] of ins) el.append(row(name, type, "in", o));
  for (const [name, type, o] of outs) el.append(row(name, type, "out", o));
  return el;
}

function renderCanvas() {
  ensureLayout();
  const world = $("world");
  world.querySelectorAll(".node").forEach((n) => n.remove());
  const inputs = Object.entries(wf().inputs || {});
  world.append(nodeEl("__inputs", "Workflow inputs", "", [], inputs.map(([n, s]) => [n, s.type, { required: s.required }]), "io"));
  for (const s of steps()) {
    const { ins, outs } = stepRows(s);
    const node = nodeEl(s.id, s.id, s.capability + (capOf(s) ? "" : " (unknown)"),
      ins.map(([n, spec]) => [n, spec.type, { required: spec.required && !("default" in spec), title: spec.description }]),
      outs.map(([n, spec]) => [n, spec.type, { title: spec.description }]));
    node.addEventListener("mousedown", () => { if (S.sel !== s.id) { S.sel = s.id; renderInspector(); highlight(); } });
    world.append(node);
  }
  const outputs = Object.keys(wf().outputs || {});
  world.append(nodeEl("__outputs", "Workflow outputs", "", outputs.map((n) => [n, S.check.output_types?.[n] || ""]), [], "io"));
  drawEdges();
}
function highlight() { document.querySelectorAll(".node").forEach((n) => n.classList.toggle("sel", n.dataset.id === S.sel)); }

function portPos(key) {
  const el = document.querySelector(`[data-port="${CSS.escape(key)}"]`);
  if (!el) return null;
  const node = el.closest(".node");
  const x = node.offsetLeft + (el.classList.contains("out") ? node.offsetWidth : 0);
  return [x, node.offsetTop + el.parentElement.offsetTop + el.parentElement.offsetHeight / 2];
}
function curve(a, b) { const d = Math.max(40, Math.abs(b[0] - a[0]) / 2); return `M${a[0]},${a[1]} C${a[0] + d},${a[1]} ${b[0] - d},${b[1]} ${b[0]},${b[1]}`; }

function edgeList() {
  const edges = [];
  const add = (value, to) => {
    for (const r of refsIn(value)) {
      const from = r.kind === "inputs" ? portKey("__inputs", "out", r.id) : portKey(r.id, "out", r.out);
      edges.push({ from, to: portKey(to.node, "in", to.name), target: to });
    }
  };
  for (const s of steps()) for (const [k, v] of Object.entries(s.with || {})) add(v, { node: s.id, name: k });
  for (const [k, v] of Object.entries(wf().outputs || {})) add(v, { node: "__outputs", name: k });
  return edges;
}

function drawEdges() {
  const svg = $("edges");
  fill(svg, );
  document.querySelectorAll(".port").forEach((p) => p.classList.remove("on"));
  for (const e of edgeList()) {
    const a = portPos(e.from), b = portPos(e.to);
    if (!a || !b) continue;
    for (const k of [e.from, e.to]) document.querySelector(`[data-port="${CSS.escape(k)}"]`)?.classList.add("on");
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", curve(a, b));
    const title = document.createElementNS("http://www.w3.org/2000/svg", "title");
    title.textContent = "double-click to remove";
    path.append(title);
    path.addEventListener("dblclick", () => disconnect(e.target));
    svg.append(path);
  }
  if (S.drag?.type === "link" && S.drag.cursor) {
    const fixed = portPos(S.drag.from ? portKey(S.drag.from.node, "out", S.drag.from.name) : portKey(S.drag.to.node, "in", S.drag.to.name));
    if (fixed) {
      const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
      path.setAttribute("class", "temp");
      path.setAttribute("d", S.drag.from ? curve(fixed, S.drag.cursor) : curve(S.drag.cursor, fixed));
      svg.append(path);
    }
  }
}

// ---------- mouse handling on the canvas ----------
const worldPoint = (e) => { const r = $("world").getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };

document.addEventListener("mousemove", (e) => {
  const d = S.drag;
  if (!d) return;
  if (d.type === "node") {
    S.layout[d.id] = [Math.max(0, e.clientX - d.dx), Math.max(0, e.clientY - d.dy)];
    d.moved = true;
    const el = document.querySelector(`.node[data-id="${CSS.escape(d.id)}"]`);
    if (el) { el.style.left = S.layout[d.id][0] + "px"; el.style.top = S.layout[d.id][1] + "px"; }
    drawEdges();
  } else if (d.type === "link") {
    d.cursor = worldPoint(e);
    drawEdges();
  }
});
document.addEventListener("mouseup", (e) => {
  const d = S.drag;
  if (!d) return;
  S.drag = null;
  if (d.type === "node") { if (d.moved) S.dirty = true; renderInspector(); highlight(); renderTopbar(); return; }
  const over = document.elementFromPoint(e.clientX, e.clientY)?.closest?.(".port");
  if (over) {
    const [node, dir, name] = over.dataset.port.split("|");
    if (d.from && dir === "in") {
      const src = d.from.node === "__inputs" ? { kind: "inputs", id: d.from.name } : { kind: "steps", id: d.from.node, out: d.from.name };
      return connect(src, { node, name });
    }
    if (d.to && dir === "out") {
      const src = node === "__inputs" ? { kind: "inputs", id: name } : { kind: "steps", id: node, out: name };
      return connect(src, d.to);
    }
  }
  drawEdges();
});
$("canvas").addEventListener("dragover", (e) => e.preventDefault());
$("canvas").addEventListener("drop", (e) => {
  e.preventDefault();
  const id = e.dataTransfer.getData("text/plain");
  if (!S.caps[id]) return;
  const [x, y] = worldPoint(e);
  addStep(id, x - NODE_W / 2, y - 16);
});
$("canvas").addEventListener("mousedown", (e) => { if (e.target.id === "world" || e.target.id === "canvas") { S.sel = null; highlight(); renderInspector(); } });
document.addEventListener("keydown", (e) => {
  if ((e.key === "Delete" || e.key === "Backspace") && S.sel && S.sel[0] !== "_" && !/INPUT|TEXTAREA|SELECT/.test(document.activeElement.tagName)) removeStep(S.sel);
});

// ---------- rendering: inspector ----------
function field(label, control, hint) { return h("div", { class: "field" }, h("label", {}, label), control, hint ? h("span", { class: "hint" }, hint) : null); }

function typedValue(spec, text) {
  if (text === "") return undefined;
  if (spec?.type === "integer" || spec?.type === "number") { const n = Number(text); return Number.isNaN(n) ? text : n; }
  if (spec?.type === "boolean") return text === "true";
  return text;
}

function valueControl(spec, value, onSet) {
  const type = spec?.type;
  if (type === "boolean") {
    const sel = h("select", { onchange: () => onSet(sel.value === "" ? undefined : sel.value === "true") },
      h("option", { value: "" }, spec && "default" in spec ? `default (${spec.default})` : "—"), h("option", { value: "true" }, "true"), h("option", { value: "false" }, "false"));
    sel.value = value === true ? "true" : value === false ? "false" : "";
    return sel;
  }
  if (type === "enum" && spec.values) {
    const sel = h("select", { onchange: () => onSet(sel.value || undefined) }, h("option", { value: "" }, "default" in spec ? `default (${spec.default})` : "—"), spec.values.map((v) => h("option", { value: v }, v)));
    sel.value = value ?? "";
    return sel;
  }
  const input = h("input", { value: value ?? "", placeholder: spec && "default" in spec ? `default: ${JSON.stringify(spec.default)}` : "", type: type === "integer" || type === "number" ? "number" : "text",
    onchange: () => onSet(typedValue(spec, input.value)) });
  return input;
}

function inspectStep(step) {
  const cap = capOf(step);
  const box = h("div", {});
  const idInput = h("input", { value: step.id, onchange: () => { if (renameStep(step.id, idInput.value.trim())) changed(); else idInput.value = step.id; } });
  box.append(h("h3", {}, "Step"), field("id", idInput), field("capability", h("code", {}, step.capability), cap?.description));
  if (!cap) box.append(h("p", { class: "bad" }, "Not in the registry. Reload capabilities, or tick “allow unknown capabilities”."));
  const forced = cap?.permissions.writes_external_state || !cap;
  const approval = h("select", { disabled: forced, onchange: () => { if (approval.value) step.approval = approval.value; else delete step.approval; changed(); } },
    h("option", { value: "" }, "automatic"), h("option", { value: "required" }, "required"));
  approval.value = forced ? "required" : step.approval || "";
  box.append(field("approval", approval, forced ? "This step changes something outside the machine, so approval is always required." : "Ask before this step runs."));
  box.append(h("h3", {}, "Inputs"));
  const { ins } = stepRows(step);
  step.with = step.with || {};
  for (const [name, spec] of ins) {
    const value = step.with[name];
    const ref = wholeRef(value);
    let control;
    if (ref) control = h("span", { class: "chip" }, "← " + refText(ref), h("button", { title: "disconnect", onclick: () => disconnect({ node: step.id, name }) }, "×"));
    else if (refsIn(value).length) control = h("input", { value, onchange: (e) => setWith(step, name, e.target.value || undefined) });
    else control = valueControl(spec, value, (v) => setWith(step, name, v));
    box.append(field(`${name}${spec.required && !("default" in spec) ? " *" : ""}  (${spec.type})`, control, spec.description));
  }
  box.append(h("div", { class: "inline" }, h("button", { class: "danger", onclick: () => removeStep(step.id) }, "Delete step")));
  return box;
}
function setWith(step, name, v) { if (v === undefined) delete step.with[name]; else step.with[name] = v; changed(); }

function inspectInputs() {
  const box = h("div", {}, h("h3", {}, "Workflow inputs"), h("p", { class: "muted" }, "What a person (or an agent) gives this workflow. Drag from a dot on the node to a step input to use it."));
  const list = h("datalist", { id: "types" }, TYPES.map((t) => h("option", { value: t })));
  box.append(list);
  for (const [name, spec] of Object.entries(wf().inputs || {})) {
    const nameInput = h("input", { value: name, onchange: () => {
      const n = nameInput.value.trim();
      if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(n) || (n !== name && wf().inputs[n])) { nameInput.value = name; return; }
      const next = {}; for (const [k, v] of Object.entries(wf().inputs)) next[k === name ? n : k] = v;
      wf().inputs = next;
      const swap = (t) => (typeof t === "string" ? t.replace(new RegExp(`(inputs\\.)${name}\\b`, "g"), `$1${n}`) : t);
      for (const s of steps()) for (const k of Object.keys(s.with || {})) s.with[k] = swap(s.with[k]);
      changed();
    } });
    const type = h("input", { value: spec.type, list: "types", onchange: () => { spec.type = type.value.trim(); changed(); } });
    const required = h("input", { type: "checkbox", onchange: () => { if (required.checked) spec.required = true; else delete spec.required; changed(); } });
    required.checked = !!spec.required;
    const def = h("input", { value: "default" in spec ? spec.default : "", placeholder: "default", onchange: () => { const v = typedValue(spec, def.value); if (v === undefined) delete spec.default; else spec.default = v; changed(); } });
    box.append(h("div", { class: "box" },
      h("div", { class: "inline" }, nameInput, h("button", { class: "danger", onclick: () => { delete wf().inputs[name]; changed(); } }, "×")),
      field("type", type), h("label", { class: "inline" }, required, "required"), field("default", def)));
  }
  box.append(h("button", { onclick: () => { let n = 1; while (wf().inputs["input_" + n]) n++; wf().inputs["input_" + n] = { type: "text", required: true }; changed(); } }, "+ Add input"));
  return box;
}

function inspectOutputs() {
  const box = h("div", {}, h("h3", {}, "Workflow outputs"), h("p", { class: "muted" }, "Each output is exactly one step output. Drag a step's right dot onto a dot here."));
  for (const [name, value] of Object.entries(wf().outputs || {})) {
    const ref = wholeRef(value);
    box.append(h("div", { class: "box" }, h("div", { class: "inline" }, h("b", {}, name), h("button", { class: "danger", onclick: () => disconnect({ node: "__outputs", name }) }, "×")),
      ref ? h("span", { class: "chip" }, "← " + refText(ref)) : h("input", { value, onchange: (e) => { wf().outputs[name] = e.target.value; changed(); } })));
  }
  const name = h("input", { placeholder: "new output name" });
  box.append(h("div", { class: "inline" }, name, h("button", { onclick: () => { const n = name.value.trim(); if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(n)) { wf().outputs[n] = wf().outputs[n] || ""; changed(); } } }, "+ Add")));
  return box;
}

function inspectWorkflow() {
  const w = wf();
  const bind = (key) => h("input", { value: w[key] ?? "", onchange: (e) => { if (e.target.value) w[key] = e.target.value; else delete w[key]; changed(); } });
  return h("div", {}, h("h3", {}, "Workflow"), field("id", bind("id"), "lowercase letters, digits, underscores"), field("name", bind("name")), field("version", bind("version")), field("description", bind("description")),
    h("p", { class: "muted" }, "Click a node to edit it. Click “Workflow inputs” or “Workflow outputs” to edit those."));
}

function renderInspector() {
  const pane = $("inspector");
  const focus = document.activeElement?.closest?.("#inspector");
  if (focus && document.activeElement.tagName === "INPUT" && document.activeElement.dataset.keep) return;
  let content;
  if (S.sel === "__inputs") content = inspectInputs();
  else if (S.sel === "__outputs") content = inspectOutputs();
  else if (S.sel && stepById(S.sel)) content = inspectStep(stepById(S.sel));
  else content = inspectWorkflow();
  fill(pane, content);
}

// ---------- rendering: top bar ----------
function renderTopbar() {
  $("where").textContent = (S.file || "unsaved") + (S.dirty ? " •" : "");
  document.title = (S.dirty ? "• " : "") + "MarketingStudio Editor";
}

// ---------- bottom panel ----------
const TABS = [["problems", () => `Problems${S.check.errors.length ? ` (${S.check.errors.length})` : ""}`], ["plan", () => "Plan"], ["run", () => "Run"], ["export", () => "Export"], ["yaml", () => "YAML"]];
function renderTabs() {
  fill($("tabs"), ...TABS.map(([id, label]) => h("button", { class: S.tab === id ? "on" : "", onclick: () => { S.tab = id; if (id === "plan") loadPlan(); renderTabs(); renderPanel(); } }, label())));
}

function renderPanel() {
  const p = $("panel");
  if (S.tab === "problems") {
    const c = S.check;
    fill(p, 
      c.errors.length ? h("ul", { class: "plain bad" }, c.errors.map((e) => h("li", {}, e))) : h("p", { class: "ok" }, steps().length ? "Valid." : "Add a step to begin."),
      c.warnings.length ? h("ul", { class: "plain warn" }, c.warnings.map((e) => h("li", {}, e))) : null,
      c.order.length ? h("p", { class: "muted" }, "Runs in this order: " + c.order.join(" → ")) : null);
  } else if (S.tab === "plan") renderPlan(p);
  else if (S.tab === "run") renderRun(p);
  else if (S.tab === "export") renderExport(p);
  else renderYaml(p);
}

async function loadPlan() {
  try { S.plan = await api("/api/plan", { doc: S.doc, allow_unknown: $("unknown").checked }); } catch (e) { S.plan = { errors: [e.message], steps: [], missing: [] }; }
  if (S.tab === "plan") renderPanel();
}
function renderPlan(p) {
  const plan = S.plan;
  if (!plan) { fill(p, h("p", { class: "muted" }, "Loading…")); return loadPlan(); }
  if (plan.errors?.length) return fill(p, h("p", { class: "bad" }, "Not valid yet:"), h("ul", { class: "plain bad" }, plan.errors.map((e) => h("li", {}, e))));
  fill(p, 
    h("table", {}, h("tr", {}, ["#", "step", "capability", "where", "approval", "missing here"].map((x) => h("th", {}, x))),
      plan.steps.map((s, i) => h("tr", {}, h("td", {}, i + 1), h("td", {}, s.id), h("td", {}, s.capability), h("td", { class: "muted" }, s.where || ""), h("td", {}, s.approval ? "required" : "—"),
        h("td", { class: s.missing?.length ? "bad" : "ok" }, s.missing?.length ? s.missing.join(", ") : "ready")))),
    h("p", {}, `Cost: $${plan.total_cost_usd}` + (plan.unknown_cost_steps?.length ? ` + unknown for ${plan.unknown_cost_steps.join(", ")}` : "")),
    h("p", { class: plan.missing.length ? "bad" : "ok" }, plan.missing.length ? "Not ready on this machine: " + plan.missing.join("; ") : "Ready on this machine."),
    h("button", { onclick: loadPlan }, "Refresh"));
}

function renderRun(p) {
  const specs = wf().inputs || {};
  const values = (S.runInputs ||= {});
  const rows = Object.entries(specs).map(([name, spec]) => {
    const input = spec.type === "boolean"
      ? h("input", { type: "checkbox", onchange: (e) => (values[name] = e.target.checked) })
      : h("input", { value: values[name] ?? "", placeholder: spec.type.startsWith("file:") ? "path of a file on this machine" : "default" in spec ? String(spec.default) : "", style: "width:340px", onchange: (e) => (values[name] = e.target.value) });
    return h("tr", {}, h("td", {}, name + (spec.required ? " *" : "")), h("td", { class: "muted" }, spec.type), h("td", {}, input));
  });
  const gated = Object.entries(S.check.approval || {}).filter(([, v]) => v).map(([id]) => id);
  const approved = (S.approved ||= new Set());
  const box = h("div", {}, rows.length ? h("table", {}, rows) : h("p", { class: "muted" }, "This workflow takes no inputs."));
  if (gated.length) box.append(h("p", {}, "These steps change something outside this machine. Tick the ones you allow:"), gated.map((id) => {
    const c = h("input", { type: "checkbox", onchange: () => (c.checked ? approved.add(id) : approved.delete(id)) });
    c.checked = approved.has(id);
    return h("label", { class: "inline" }, c, id + " (" + (stepById(id)?.capability || "") + ")");
  }));
  box.append(h("p", {}, h("button", { class: "primary", disabled: S.run?.status === "running" || S.check.errors.length > 0, onclick: startRun }, "Run on this machine"),
    S.check.errors.length ? h("span", { class: "bad" }, "  fix the problems first") : null));
  if (S.run) {
    box.append(h("p", { class: S.run.status === "failed" ? "bad" : S.run.status === "done" ? "ok" : "muted" }, `Status: ${S.run.status}` + (S.run.folder ? `  ·  files in ${S.run.folder}` : "")));
    if (S.run.error) box.append(h("pre", { class: "bad" }, S.run.error));
    if (S.run.outputs) box.append(h("table", {}, Object.entries(S.run.outputs).map(([k, v]) => h("tr", {}, h("td", {}, k), h("td", {}, typeof v === "string" ? v : JSON.stringify(v))))));
    box.append(h("pre", { class: "muted" }, S.run.log.join("\n")));
  }
  fill(p, box);
}
async function startRun() {
  try {
    const inputs = {};
    for (const [k, v] of Object.entries(S.runInputs || {})) if (v !== "" && v != null) inputs[k] = v;
    const { id } = await api("/api/run", { doc: S.doc, inputs, approve: [...(S.approved || [])] });
    S.run = { status: "running", log: [], id };
    renderPanel();
    const poll = async () => {
      S.run = { ...(await api("/api/run?id=" + id)), id };
      if (S.tab === "run") renderPanel();
      if (S.run.status === "running") setTimeout(poll, 700);
    };
    poll();
  } catch (e) { fail(e); }
}

function renderExport(p) {
  const target = (S.target ||= "mcp");
  const select = h("select", { onchange: () => (S.target = select.value) }, S.targets.map((t) => h("option", { value: t }, t)));
  select.value = target;
  const result = S.exportResult;
  fill(p, 
    h("p", { class: "muted" }, "Writes the files a consumer reads. Nothing is installed or sent anywhere."),
    h("div", { class: "inline" }, select, h("button", { class: "primary", onclick: doExport }, "Export")),
    result?.errors ? h("ul", { class: "plain bad" }, result.errors.map((e) => h("li", {}, e))) : null,
    result?.files ? h("div", {}, h("p", {}, h("button", { onclick: () => download(result) }, "Download " + result.name), `  ${result.files.length} files: ${result.files.join(", ")}`),
      result.notes.length ? h("ul", { class: "plain warn" }, result.notes.map((n) => h("li", {}, n))) : null) : null);
}
async function doExport() {
  try { S.exportResult = await api("/api/export", { doc: S.doc, target: S.target || "mcp" }); renderPanel(); } catch (e) { fail(e); }
}
function download(result) {
  const bytes = Uint8Array.from(atob(result.zip), (c) => c.charCodeAt(0));
  const a = h("a", { href: URL.createObjectURL(new Blob([bytes], { type: "application/zip" })), download: result.name });
  document.body.append(a); a.click(); a.remove();
}

async function renderYaml(p) {
  const area = h("textarea", { class: "yaml", spellcheck: false, oninput: () => (S.yamlDirty = true) });
  try { area.value = (await api("/api/yaml", { doc: S.doc })).text; } catch (e) { area.value = String(e.message); }
  fill(p, area, h("p", {}, h("button", { onclick: async () => {
    try { S.doc = (await api("/api/parse", { text: area.value })).doc; S.yamlDirty = false; S.sel = null; S.layout = {}; wf().inputs ||= {}; wf().steps ||= []; wf().outputs ||= {}; changed(); } catch (e) { fail(e); }
  } }, "Apply YAML"), h("span", { class: "muted" }, "  Editing here replaces the document; the canvas layout is recomputed.")));
}

// ---------- validation, files ----------
async function validate() {
  try { S.check = await api("/api/validate", { doc: S.doc, allow_unknown: $("unknown").checked }); } catch (e) { S.check = { errors: [e.message], warnings: [], order: [], approval: {} }; }
  S.plan = null;
  renderTabs();
  renderPanel();
  document.querySelectorAll(".node").forEach((n) => { const id = n.dataset.id; n.classList.toggle("bad", S.check.errors.some((e) => e.startsWith(`step '${id}'`))); });
}

async function loadList(select) {
  const { workflows } = await api("/api/workflows");
  fill($("open"), h("option", { value: "" }, "Open workflow…"), workflows.map((w) => h("option", { value: w }, w)));
  $("open").value = select || "";
}

async function openFile(path) {
  if (S.dirty && !confirm("Discard unsaved changes?")) { $("open").value = S.file || ""; return; }
  try {
    const { doc, layout } = await api("/api/workflow?path=" + encodeURIComponent(path));
    if (!doc?.workflow) throw new Error("This file has no 'workflow' section.");
    doc.workflow.inputs ||= {}; doc.workflow.steps ||= []; doc.workflow.outputs ||= {};
    Object.assign(S, { doc, layout: layout || {}, file: path, sel: null, dirty: false, run: null, plan: null, exportResult: null, runInputs: {}, approved: new Set() });
    changed(); S.dirty = false; renderTopbar();
  } catch (e) { fail(e); }
}

async function save() {
  let path = S.file || prompt("Save as (a .yaml path inside " + S.root + "):", `workflows/${wf().id}.yaml`);
  if (!path) return;
  try {
    ensureLayout();
    await api("/api/save", { path, doc: S.doc, layout: S.layout });
    S.file = path; S.dirty = false;
    await loadList(path);
    renderTopbar();
  } catch (e) { fail(e); }
}

async function loadCapabilities() {
  const data = await api("/api/capabilities");
  S.capList = data.capabilities; S.targets = data.targets; S.root = data.root;
  S.caps = Object.fromEntries(data.capabilities.map((c) => [c.id, c]));
  if (data.error) alert("Capabilities could not be loaded:\n" + data.error);
  renderPalette();
}

function renderAll() { renderTopbar(); renderCanvas(); renderInspector(); renderTabs(); }

$("search").addEventListener("input", renderPalette);
$("open").addEventListener("change", (e) => e.target.value && openFile(e.target.value));
$("save").addEventListener("click", save);
$("layout").addEventListener("click", () => { autoLayout(); S.dirty = true; renderTopbar(); });
$("new").addEventListener("click", () => { if (S.dirty && !confirm("Discard unsaved changes?")) return; Object.assign(S, { doc: blank(), layout: {}, file: null, sel: null, dirty: false, run: null, plan: null, runInputs: {}, approved: new Set() }); $("open").value = ""; changed(); S.dirty = false; renderTopbar(); });
$("reload").addEventListener("click", async () => { await loadCapabilities(); renderAll(); validate(); });
$("unknown").addEventListener("change", validate);
window.addEventListener("beforeunload", (e) => { if (S.dirty) e.preventDefault(); });
window.addEventListener("resize", drawEdges);

(async function init() {
  try { await loadCapabilities(); await loadList(); } catch (e) { fail(e); }
  renderAll();
  validate();
})();
