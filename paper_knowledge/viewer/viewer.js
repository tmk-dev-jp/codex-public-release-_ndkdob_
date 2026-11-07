const KIND_ORDER = ["paper", "claim", "method", "dataset", "metric", "task", "term", "note"];
const KIND_COLORS = {
  paper: "#2563eb",
  claim: "#c2410c",
  method: "#059669",
  dataset: "#7c3aed",
  metric: "#d97706",
  task: "#0891b2",
  term: "#4b5563",
  note: "#be185d",
};

const state = {
  graph: normalizeGraph(window.PAPER_KNOWLEDGE_GRAPH || { nodes: [], edges: [] }),
  query: "",
  selectedId: null,
  hoveredId: null,
  edgeType: "all",
  kindEnabled: new Set(KIND_ORDER),
  visible: { nodes: [], edges: [], matches: new Set() },
  positions: new Map(),
  velocities: new Map(),
  zoom: 1,
  pan: { x: 0, y: 0 },
  dragging: null,
  panning: null,
  animation: null,
  viewport: { width: 0, height: 0, ratio: 1 },
};

const canvas = document.getElementById("graphCanvas");
const graphPanel = canvas.parentElement;
const ctx = canvas.getContext("2d");
const searchInput = document.getElementById("searchInput");
const fileInput = document.getElementById("fileInput");
const fitButton = document.getElementById("fitButton");
const resetButton = document.getElementById("resetButton");
const graphSummary = document.getElementById("graphSummary");
const kindFilters = document.getElementById("kindFilters");
const edgeTypeSelect = document.getElementById("edgeTypeSelect");
const resultsList = document.getElementById("resultsList");
const detailsPane = document.getElementById("detailsPane");
const connectionsList = document.getElementById("connectionsList");
const legend = document.getElementById("legend");
let resizeFrame = null;
let resizeObserver = null;

function normalizeGraph(raw) {
  const nodes = Array.isArray(raw.nodes)
    ? raw.nodes
    : Object.entries(raw.nodes || {}).map(([id, value]) => ({ id, ...value }));
  const nodeMap = new Map();
  nodes.forEach((node) => {
    const id = String(node.id || "");
    if (!id) return;
    nodeMap.set(id, {
      id,
      kind: String(node.kind || inferKind(id)),
      title: String(node.title || id),
      aliases: Array.isArray(node.aliases) ? node.aliases.map(String) : [],
      tags: Array.isArray(node.tags) ? node.tags.map(String) : [],
      source: node.source || {},
      metadata: node.metadata || {},
      summary: String(node.summary || ""),
      degree: 0,
    });
  });
  const edges = (raw.edges || [])
    .map((edge, index) => ({
      id: `edge:${index}`,
      source: String(edge.source || ""),
      target: String(edge.target || ""),
      type: String(edge.type || "links_to"),
      evidence: String(edge.evidence || ""),
      confidence: Number(edge.confidence ?? 0.5),
      source_ref: String(edge.source_ref || ""),
    }))
    .filter((edge) => nodeMap.has(edge.source) && nodeMap.has(edge.target));
  edges.forEach((edge) => {
    nodeMap.get(edge.source).degree += 1;
    nodeMap.get(edge.target).degree += 1;
  });
  return { nodes: [...nodeMap.values()], edges, nodeMap };
}

function inferKind(id) {
  const prefix = id.includes(":") ? id.split(":", 1)[0] : "term";
  return KIND_ORDER.includes(prefix) ? prefix : "term";
}

function initialize() {
  buildKindFilters();
  buildEdgeTypes();
  buildLegend();
  bindEvents();
  resizeCanvas(false);
  resetLayout();
  recompute();
  startAnimation();
}

function buildKindFilters() {
  kindFilters.innerHTML = "";
  KIND_ORDER.forEach((kind) => {
    const label = document.createElement("label");
    label.innerHTML = `<input type="checkbox" checked value="${kind}"><span class="swatch" style="background:${KIND_COLORS[kind]}"></span><span>${kind}</span>`;
    label.querySelector("input").addEventListener("change", (event) => {
      if (event.target.checked) state.kindEnabled.add(kind);
      else state.kindEnabled.delete(kind);
      recompute();
    });
    kindFilters.append(label);
  });
}

function buildEdgeTypes() {
  const types = ["all", ...new Set(state.graph.edges.map((edge) => edge.type).sort())];
  edgeTypeSelect.innerHTML = "";
  types.forEach((type) => {
    const option = document.createElement("option");
    option.value = type;
    option.textContent = type;
    edgeTypeSelect.append(option);
  });
}

function buildLegend() {
  legend.innerHTML = "";
  KIND_ORDER.forEach((kind) => {
    const item = document.createElement("span");
    item.className = "legend-item";
    item.innerHTML = `<span class="swatch" style="background:${KIND_COLORS[kind]}"></span>${kind}`;
    legend.append(item);
  });
}

function bindEvents() {
  searchInput.addEventListener("input", () => {
    state.query = searchInput.value.trim();
    recompute();
  });
  edgeTypeSelect.addEventListener("change", () => {
    state.edgeType = edgeTypeSelect.value;
    recompute();
  });
  fitButton.addEventListener("click", fitVisibleGraph);
  resetButton.addEventListener("click", () => {
    searchInput.value = "";
    state.query = "";
    state.selectedId = null;
    state.edgeType = "all";
    edgeTypeSelect.value = "all";
    state.kindEnabled = new Set(KIND_ORDER);
    kindFilters.querySelectorAll("input").forEach((input) => {
      input.checked = true;
    });
    resetLayout();
    recompute();
  });
  fileInput.addEventListener("change", loadFile);
  window.addEventListener("resize", scheduleCanvasResize);
  if ("ResizeObserver" in window) {
    resizeObserver = new ResizeObserver(() => scheduleCanvasResize());
    resizeObserver.observe(graphPanel);
  }
  canvas.addEventListener("mousedown", onPointerDown);
  canvas.addEventListener("mousemove", onPointerMove);
  window.addEventListener("mouseup", onPointerUp);
  canvas.addEventListener("wheel", onWheel, { passive: false });
  canvas.addEventListener("dblclick", fitVisibleGraph);
}

function loadFile(event) {
  const file = event.target.files && event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = () => {
    try {
      state.graph = normalizeGraph(JSON.parse(String(reader.result || "{}")));
      state.selectedId = null;
      buildEdgeTypes();
      resetLayout();
      recompute();
    } catch (error) {
      detailsPane.innerHTML = `<p class="empty-state">Unable to parse ${escapeHtml(file.name)}.</p>`;
    }
  };
  reader.readAsText(file);
}

function scheduleCanvasResize() {
  if (resizeFrame !== null) {
    cancelAnimationFrame(resizeFrame);
  }
  resizeFrame = requestAnimationFrame(() => {
    resizeFrame = null;
    resizeCanvas(true);
  });
}

function resizeCanvas(preserveCenter = true) {
  const width = Math.max(1, graphPanel.clientWidth);
  const height = Math.max(1, graphPanel.clientHeight);
  const ratio = window.devicePixelRatio || 1;
  const previous = state.viewport;
  const unchanged =
    Math.abs(previous.width - width) < 0.5 &&
    Math.abs(previous.height - height) < 0.5 &&
    previous.ratio === ratio;
  if (unchanged) return false;

  const worldCenter =
    preserveCenter && previous.width > 0 && previous.height > 0
      ? {
          x: (previous.width / 2 - state.pan.x) / state.zoom,
          y: (previous.height / 2 - state.pan.y) / state.zoom,
        }
      : null;
  const backingWidth = Math.max(1, Math.round(width * ratio));
  const backingHeight = Math.max(1, Math.round(height * ratio));
  if (canvas.width !== backingWidth) canvas.width = backingWidth;
  if (canvas.height !== backingHeight) canvas.height = backingHeight;
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  state.viewport = { width, height, ratio };

  if (worldCenter) {
    state.pan.x = width / 2 - worldCenter.x * state.zoom;
    state.pan.y = height / 2 - worldCenter.y * state.zoom;
  }
  return true;
}

function resetLayout() {
  state.positions.clear();
  state.velocities.clear();
  const rect = canvas.getBoundingClientRect();
  const cx = rect.width / 2 || 400;
  const cy = rect.height / 2 || 300;
  const radius = Math.max(80, Math.min(cx, cy) * 0.62);
  state.graph.nodes.forEach((node, index) => {
    const angle = (Math.PI * 2 * index) / Math.max(1, state.graph.nodes.length);
    state.positions.set(node.id, { x: cx + Math.cos(angle) * radius, y: cy + Math.sin(angle) * radius });
    state.velocities.set(node.id, { x: 0, y: 0 });
  });
  state.zoom = 1;
  state.pan = { x: 0, y: 0 };
}

function recompute() {
  const tokens = tokenize(state.query);
  const matchScores = new Map();
  const baseNodes = state.graph.nodes.filter((node) => state.kindEnabled.has(node.kind));
  baseNodes.forEach((node) => {
    const score = scoreNode(node, tokens);
    if (!tokens.length || score > 0) matchScores.set(node.id, score);
  });
  let visibleIds;
  if (!tokens.length) {
    visibleIds = new Set(baseNodes.map((node) => node.id));
  } else {
    visibleIds = new Set(matchScores.keys());
    state.graph.edges.forEach((edge) => {
      if (matchScores.has(edge.source) && state.kindEnabled.has(state.graph.nodeMap.get(edge.target).kind)) visibleIds.add(edge.target);
      if (matchScores.has(edge.target) && state.kindEnabled.has(state.graph.nodeMap.get(edge.source).kind)) visibleIds.add(edge.source);
    });
  }
  const edges = state.graph.edges.filter((edge) => {
    if (!visibleIds.has(edge.source) || !visibleIds.has(edge.target)) return false;
    return state.edgeType === "all" || edge.type === state.edgeType;
  });
  const connectedIds = new Set();
  edges.forEach((edge) => {
    connectedIds.add(edge.source);
    connectedIds.add(edge.target);
  });
  const nodes = state.graph.nodes.filter((node) => visibleIds.has(node.id) && (!tokens.length || connectedIds.has(node.id) || matchScores.has(node.id)));
  state.visible = { nodes, edges, matches: new Set(matchScores.keys()), scores: matchScores };
  graphSummary.textContent = `${nodes.length}/${state.graph.nodes.length} nodes · ${edges.length}/${state.graph.edges.length} edges`;
  renderResults();
  renderDetails();
}

function tokenize(value) {
  return value.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
}

function scoreNode(node, tokens) {
  if (!tokens.length) return 1;
  const fields = [
    [node.id, 3],
    [node.title, 5],
    [node.kind, 2],
    [node.tags.join(" "), 4],
    [node.aliases.join(" "), 2],
    [node.summary, 1],
    [Object.values(node.metadata || {}).join(" "), 1],
  ];
  return tokens.reduce((sum, token) => {
    return sum + fields.reduce((fieldSum, [text, weight]) => fieldSum + (String(text).toLowerCase().includes(token) ? weight : 0), 0);
  }, 0);
}

function renderResults() {
  const nodes = [...state.visible.nodes]
    .map((node) => ({ node, score: state.visible.scores.get(node.id) || 0 }))
    .sort((left, right) => right.score - left.score || right.node.degree - left.node.degree || left.node.id.localeCompare(right.node.id))
    .slice(0, 80);
  resultsList.innerHTML = "";
  if (!nodes.length) {
    resultsList.innerHTML = '<p class="empty-state">No matching nodes.</p>';
    return;
  }
  nodes.forEach(({ node }) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `result-item${node.id === state.selectedId ? " active" : ""}`;
    button.innerHTML = `<span class="item-title">${escapeHtml(node.title)}</span><span class="item-meta">${escapeHtml(node.kind)} · ${escapeHtml(node.id)}</span>`;
    button.addEventListener("click", () => {
      state.selectedId = node.id;
      centerNode(node.id);
      renderResults();
      renderDetails();
    });
    resultsList.append(button);
  });
}

function renderDetails() {
  const selected = state.graph.nodeMap.get(state.selectedId) || state.visible.nodes[0];
  if (!selected) {
    detailsPane.innerHTML = '<p class="empty-state">No node selected.</p>';
    connectionsList.innerHTML = '<p class="empty-state">No connections.</p>';
    return;
  }
  if (!state.selectedId) state.selectedId = selected.id;
  const tags = selected.tags.map((tag) => `<span class="chip">#${escapeHtml(tag)}</span>`).join("");
  const metaRows = Object.entries(selected.metadata || {})
    .filter(([, value]) => value !== "" && value !== null && value !== undefined && !(Array.isArray(value) && value.length === 0))
    .map(([key, value]) => `<div><dt>${escapeHtml(key)}</dt><dd>${escapeHtml(formatValue(value))}</dd></div>`)
    .join("");
  detailsPane.innerHTML = `
    <h3 class="details-title">${escapeHtml(selected.title)}</h3>
    <div class="details-meta">
      <span class="chip"><span class="swatch" style="background:${KIND_COLORS[selected.kind] || KIND_COLORS.term}"></span>${escapeHtml(selected.kind)}</span>
      <span class="chip">${escapeHtml(selected.id)}</span>
      ${tags}
    </div>
    <p class="summary">${escapeHtml(selected.summary || "No summary.")}</p>
    <dl class="kv-list">${metaRows}</dl>
  `;
  renderConnections(selected.id);
}

function renderConnections(nodeId) {
  const edges = state.graph.edges
    .filter((edge) => edge.source === nodeId || edge.target === nodeId)
    .sort((left, right) => left.type.localeCompare(right.type));
  connectionsList.innerHTML = "";
  if (!edges.length) {
    connectionsList.innerHTML = '<p class="empty-state">No connections.</p>';
    return;
  }
  edges.forEach((edge) => {
    const otherId = edge.source === nodeId ? edge.target : edge.source;
    const other = state.graph.nodeMap.get(otherId);
    const div = document.createElement("div");
    div.className = "connection-item";
    div.innerHTML = `<span class="item-title">${escapeHtml(edge.type)} · ${escapeHtml(other ? other.title : otherId)}</span><span class="item-meta">${escapeHtml(edge.source)} → ${escapeHtml(edge.target)}</span>`;
    connectionsList.append(div);
  });
}

function startAnimation() {
  const frame = () => {
    simulateStep();
    draw();
    state.animation = requestAnimationFrame(frame);
  };
  state.animation = requestAnimationFrame(frame);
}

function simulateStep() {
  const nodes = state.visible.nodes;
  const edges = state.visible.edges;
  const width = canvas.clientWidth || 800;
  const height = canvas.clientHeight || 600;
  const center = { x: width / 2, y: height / 2 };
  nodes.forEach((node) => {
    const pos = state.positions.get(node.id);
    const vel = state.velocities.get(node.id);
    if (!pos || !vel || state.dragging === node.id) return;
    vel.x += (center.x - pos.x) * 0.0008;
    vel.y += (center.y - pos.y) * 0.0008;
  });
  for (let i = 0; i < nodes.length; i += 1) {
    for (let j = i + 1; j < nodes.length; j += 1) {
      const a = state.positions.get(nodes[i].id);
      const b = state.positions.get(nodes[j].id);
      const va = state.velocities.get(nodes[i].id);
      const vb = state.velocities.get(nodes[j].id);
      if (!a || !b || !va || !vb) continue;
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const distSq = Math.max(64, dx * dx + dy * dy);
      const force = Math.min(2.4, 1100 / distSq);
      const dist = Math.sqrt(distSq);
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      va.x -= fx;
      va.y -= fy;
      vb.x += fx;
      vb.y += fy;
    }
  }
  edges.forEach((edge) => {
    const a = state.positions.get(edge.source);
    const b = state.positions.get(edge.target);
    const va = state.velocities.get(edge.source);
    const vb = state.velocities.get(edge.target);
    if (!a || !b || !va || !vb) return;
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const dist = Math.max(1, Math.sqrt(dx * dx + dy * dy));
    const target = 120;
    const force = (dist - target) * 0.004;
    const fx = (dx / dist) * force;
    const fy = (dy / dist) * force;
    va.x += fx;
    va.y += fy;
    vb.x -= fx;
    vb.y -= fy;
  });
  nodes.forEach((node) => {
    const pos = state.positions.get(node.id);
    const vel = state.velocities.get(node.id);
    if (!pos || !vel || state.dragging === node.id) return;
    vel.x *= 0.82;
    vel.y *= 0.82;
    pos.x += vel.x;
    pos.y += vel.y;
  });
}

function draw() {
  ctx.save();
  ctx.clearRect(0, 0, canvas.clientWidth, canvas.clientHeight);
  ctx.translate(state.pan.x, state.pan.y);
  ctx.scale(state.zoom, state.zoom);
  drawEdges();
  drawNodes();
  ctx.restore();
}

function drawEdges() {
  ctx.lineCap = "round";
  state.visible.edges.forEach((edge) => {
    const source = state.positions.get(edge.source);
    const target = state.positions.get(edge.target);
    if (!source || !target) return;
    const selected = state.selectedId && (edge.source === state.selectedId || edge.target === state.selectedId);
    ctx.strokeStyle = selected ? "rgba(37, 99, 235, 0.75)" : "rgba(100, 112, 132, 0.28)";
    ctx.lineWidth = selected ? 2.4 / state.zoom : 1.2 / state.zoom;
    ctx.beginPath();
    ctx.moveTo(source.x, source.y);
    ctx.lineTo(target.x, target.y);
    ctx.stroke();
  });
}

function drawNodes() {
  state.visible.nodes.forEach((node) => {
    const pos = state.positions.get(node.id);
    if (!pos) return;
    const radius = nodeRadius(node);
    const isMatch = state.visible.matches.has(node.id);
    const isSelected = node.id === state.selectedId;
    ctx.beginPath();
    ctx.fillStyle = KIND_COLORS[node.kind] || KIND_COLORS.term;
    ctx.arc(pos.x, pos.y, radius, 0, Math.PI * 2);
    ctx.fill();
    if (isMatch || isSelected) {
      ctx.lineWidth = isSelected ? 4 / state.zoom : 2.5 / state.zoom;
      ctx.strokeStyle = isSelected ? "#111827" : "#f59e0b";
      ctx.stroke();
    }
    if (state.zoom > 0.52 || isSelected) {
      ctx.font = `${Math.max(10, 12 / state.zoom)}px sans-serif`;
      ctx.fillStyle = "#111827";
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      ctx.fillText(shortTitle(node.title), pos.x, pos.y + radius + 4 / state.zoom);
    }
  });
}

function nodeRadius(node) {
  return 7 + Math.min(10, Math.sqrt(node.degree) * 3);
}

function onPointerDown(event) {
  const point = screenToWorld(event);
  const node = hitNode(point);
  if (node) {
    state.dragging = node.id;
    state.selectedId = node.id;
    renderResults();
    renderDetails();
    return;
  }
  state.panning = { x: event.clientX, y: event.clientY, pan: { ...state.pan } };
}

function onPointerMove(event) {
  const point = screenToWorld(event);
  if (state.dragging) {
    const pos = state.positions.get(state.dragging);
    if (pos) {
      pos.x = point.x;
      pos.y = point.y;
    }
    return;
  }
  if (state.panning) {
    state.pan.x = state.panning.pan.x + event.clientX - state.panning.x;
    state.pan.y = state.panning.pan.y + event.clientY - state.panning.y;
    return;
  }
  const node = hitNode(point);
  canvas.style.cursor = node ? "pointer" : "grab";
}

function onPointerUp() {
  state.dragging = null;
  state.panning = null;
}

function onWheel(event) {
  event.preventDefault();
  const rect = canvas.getBoundingClientRect();
  const before = screenToWorld(event);
  const delta = event.deltaY < 0 ? 1.12 : 0.88;
  state.zoom = clamp(state.zoom * delta, 0.2, 3.5);
  const afterX = before.x * state.zoom + state.pan.x;
  const afterY = before.y * state.zoom + state.pan.y;
  state.pan.x += event.clientX - rect.left - afterX;
  state.pan.y += event.clientY - rect.top - afterY;
}

function screenToWorld(event) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: (event.clientX - rect.left - state.pan.x) / state.zoom,
    y: (event.clientY - rect.top - state.pan.y) / state.zoom,
  };
}

function hitNode(point) {
  for (let index = state.visible.nodes.length - 1; index >= 0; index -= 1) {
    const node = state.visible.nodes[index];
    const pos = state.positions.get(node.id);
    if (!pos) continue;
    const radius = nodeRadius(node) + 5 / state.zoom;
    const dx = point.x - pos.x;
    const dy = point.y - pos.y;
    if (dx * dx + dy * dy <= radius * radius) return node;
  }
  return null;
}

function fitVisibleGraph() {
  const nodes = state.visible.nodes;
  if (!nodes.length) return;
  const rect = canvas.getBoundingClientRect();
  const positions = nodes.map((node) => state.positions.get(node.id)).filter(Boolean);
  const minX = Math.min(...positions.map((pos) => pos.x));
  const maxX = Math.max(...positions.map((pos) => pos.x));
  const minY = Math.min(...positions.map((pos) => pos.y));
  const maxY = Math.max(...positions.map((pos) => pos.y));
  const width = Math.max(1, maxX - minX);
  const height = Math.max(1, maxY - minY);
  state.zoom = clamp(Math.min((rect.width - 80) / width, (rect.height - 80) / height), 0.25, 2.2);
  state.pan.x = rect.width / 2 - ((minX + maxX) / 2) * state.zoom;
  state.pan.y = rect.height / 2 - ((minY + maxY) / 2) * state.zoom;
}

function centerNode(id) {
  const pos = state.positions.get(id);
  if (!pos) return;
  const rect = canvas.getBoundingClientRect();
  state.pan.x = rect.width / 2 - pos.x * state.zoom;
  state.pan.y = rect.height / 2 - pos.y * state.zoom;
}

function shortTitle(title) {
  return title.length > 24 ? `${title.slice(0, 23)}...` : title;
}

function formatValue(value) {
  if (Array.isArray(value)) return value.join("; ");
  if (value && typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

initialize();

