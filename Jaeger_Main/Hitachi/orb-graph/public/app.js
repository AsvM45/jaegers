import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

// ---- Colors by node type (unknown types get a stable hue from their name) ----
const PALETTE = { service:'#2fd8ff', database:'#ffb02e', person:'#ff4fd0', concept:'#9b7bff', file:'#5cff9d', event:'#ff6b57' };
function colorFor(type) {
  if (PALETTE[type]) return new THREE.Color(PALETTE[type]);
  let h = 0; for (const ch of type) h = (h * 31 + ch.charCodeAt(0)) % 360;
  return new THREE.Color().setHSL(h / 360, 0.95, 0.62);
}


// ---- Data source ----
// true  = built-in fake data generated in the browser (no server data needed)
// false = load data/graph.json through /api/graph
// A ?data=<url> query parameter overrides both, e.g. the control tower's /api/knowledge_graph.
// ?embed=1 hides the hint line; ?bg=0b1437 sets the background color (hex, no #).
const USE_FAKE_DATA = true;
const PARAMS = new URLSearchParams(location.search);
const DATA_URL = PARAMS.get('data');
if (PARAMS.get('embed')) document.body.classList.add('embed');
const BG = /^[0-9a-f]{6}$/i.test(PARAMS.get('bg') || '') ? '#' + PARAMS.get('bg') : '#05060b';

function makeFakeData() {
  let seed = 11; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const pick = (a) => a[Math.floor(rnd() * a.length)];
  const names = {
    service:  ['Gateway','Auth','Billing','Search','Notify','Orders','Catalog','Ingest','Render','Metrics','Payments','Cart'],
    database: ['Postgres','Redis','Elastic','S3 Bucket','Kafka','Warehouse','Mongo'],
    person:   ['Ada','Linus','Grace','Alan','Margaret','Dennis','Ken','Barbara','Tim','Radia'],
    concept:  ['Latency','Caching','Consistency','Queues','Scaling','Privacy','Observability','Retries'],
    file:     ['schema.sql','routes.js','deploy.yml','policy.md','pipeline.py','config.toml'],
    event:    ['Outage','Release','Audit','Migration','Spike'],
  };
  const nodes = [], by = {};
  for (const [type, list] of Object.entries(names)) { by[type] = list; list.forEach((id) => nodes.push({ id, type })); }
  const links = [], seen = new Set();
  const add = (a, b) => { const k = [a, b].sort().join('|'); if (a === b || seen.has(k)) return; seen.add(k); links.push({ source: a, target: b }); };
  by.service.forEach((x) => { add(x, pick(by.database)); add(x, pick(by.service)); add(x, pick(by.concept)); });
  by.person.forEach((x) => { add(x, pick(by.service)); add(x, pick(by.service)); add(x, pick(by.file)); });
  by.file.forEach((x) => add(x, pick(by.service)));
  by.concept.forEach((x) => add(x, pick(by.database)));
  by.event.forEach((x) => { add(x, pick(by.service)); add(x, pick(by.person)); });
  add('Gateway', 'Auth'); add('Gateway', 'Orders'); add('Orders', 'Billing'); add('Orders', 'Payments');
  return { nodes, links };
}

const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches;
const $ = (id) => document.getElementById(id);
const tmp = new THREE.Vector3(), delta = new THREE.Vector3(), desired = new THREE.Vector3(),
  planeN = new THREE.Vector3(0, 0, 1), planeP = new THREE.Vector3(), up = new THREE.Vector3(0, 1, 0);
let mode = '3d';   // '3d' or '2d'

// ---- Renderer, scene, soft bloom ----
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.setSize(innerWidth, innerHeight);
document.body.prepend(renderer.domElement);

const scene = new THREE.Scene();
scene.background = new THREE.Color(BG);
document.documentElement.style.setProperty('--bg', BG);
const camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.1, 2000);
camera.position.set(0, 70, 250);
scene.add(camera);
camera.add(new THREE.DirectionalLight('#ffffff', 1.8));
scene.add(new THREE.AmbientLight('#aab3d9', 1.0));

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
composer.addPass(new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.5, 0.7, 0.55));
composer.addPass(new OutputPass());

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.07;
controls.minDistance = 40;
controls.maxDistance = 700;
controls.autoRotate = !reduceMotion;
controls.autoRotateSpeed = 0.3;
let idleTimer;
const pauseSpin = () => { controls.autoRotate = false; clearTimeout(idleTimer);
  if (!reduceMotion) idleTimer = setTimeout(() => (controls.autoRotate = mode === '3d'), 6000); };
controls.addEventListener('start', () => { goal = null; touched = true; pauseSpin(); });

// A faint grid sheet at z = 0 that fades in when the graph is flattened
const grid = new THREE.GridHelper(700, 28, '#2a3358', '#1a2040');
Object.assign(grid.material, { transparent: true, opacity: 0, depthWrite: false });
grid.visible = false;
scene.add(grid);

// ---- Helpers ----
function glowTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const g = c.getContext('2d'), grd = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grd.addColorStop(0, 'rgba(255,255,255,.8)'); grd.addColorStop(0.3, 'rgba(255,255,255,.7)'); grd.addColorStop(0.45, 'rgba(255,255,255,.28)'); grd.addColorStop(0.7, 'rgba(255,255,255,.07)'); grd.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grd; g.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
}
const GLOW = glowTexture();
const SPHERE = new THREE.SphereGeometry(1, 16, 12);   // invisible, for mouse picking only
const DISC = new THREE.PlaneGeometry(2, 2);

// Orb look: a camera-facing disc shaded like a sphere (deeper in the middle, lighter toward the edge, soft light from
// the upper left, thin bright ring at the rim). A disc facing the camera is a perfect circle anywhere on screen,
// whereas a real 3D sphere is stretched into an oval toward the edges by perspective.
const orbVert = `varying vec2 vP;
void main(){
  vP = position.xy;
  vec4 mv = modelViewMatrix * vec4(0.0, 0.0, 0.0, 1.0);
  float s = length(modelViewMatrix[0].xyz);
  vec4 front = projectionMatrix * (mv + vec4(0.0, 0.0, s, 0.0));   // depth of the sphere's near surface
  mv.xy += position.xy * s;
  gl_Position = projectionMatrix * mv;
  gl_Position.z = front.z / front.w * gl_Position.w;
}`;
const orbFrag = `uniform vec3 uColor; uniform float uK; varying vec2 vP;
void main(){
  float r = length(vP);
  float aa = max(fwidth(r), 0.001);
  float a = 1.0 - smoothstep(1.0 - aa * 1.5, 1.0, r);
  if (a <= 0.0) discard;
  vec3 n = vec3(vP, sqrt(max(0.0, 1.0 - r * r)));
  float l = clamp(dot(n, normalize(vec3(-0.35, 0.45, 0.82))), 0.0, 1.0);
  vec3 inner = uColor * 0.5;
  vec3 outer = mix(uColor, vec3(1.0), 0.3);
  vec3 c = mix(inner, outer, pow(r, 1.8)) * (0.82 + 0.3 * l);
  float ring = smoothstep(0.92, 0.975, r);
  c = mix(c, mix(uColor, vec3(1.0), 0.75), ring * 0.9);
  gl_FragColor = vec4(c * uK, a);
}`;

// ---- Selection ring and click pulse: flat camera-facing quads, so both stay perfectly circular ----
const flatVert = `varying vec2 vP;
void main(){
  vP = position.xy;
  vec4 mv = modelViewMatrix * vec4(0.0, 0.0, 0.0, 1.0);
  mv.xy += position.xy * length(modelViewMatrix[0].xyz);
  gl_Position = projectionMatrix * mv;
}`;
const ringFrag = `uniform vec3 uColor; uniform float uA; uniform float uT; varying vec2 vP;
void main(){
  float r = length(vP);
  float aa = max(fwidth(r), 0.002);
  float line = 1.0 - smoothstep(0.025 - aa, 0.025 + aa, abs(r - 0.7));
  float f = fract(atan(vP.y, vP.x) / 6.2831853 * 14.0 + uT * 0.12);          // 14 dashes, slowly turning
  float dash = smoothstep(0.22, 0.28, abs(f - 0.5));
  gl_FragColor = vec4(uColor, line * (0.3 + 0.7 * dash) * uA);
}`;
const pulseFrag = `uniform vec3 uColor; uniform float uP; varying vec2 vP;
void main(){
  float r = length(vP);
  float rad = mix(0.36, 0.98, 1.0 - pow(1.0 - uP, 3.0));                    // ripple expands, easing out
  float aa = max(fwidth(r), 0.002), w = mix(0.03, 0.012, uP);
  float line = 1.0 - smoothstep(w - aa, w + aa, abs(r - rad));
  gl_FragColor = vec4(uColor, line * pow(1.0 - uP, 1.4) * 0.9);
}`;
const WHITE = new THREE.Color('#ffffff');
const flatMat = (frag, uniforms) => new THREE.ShaderMaterial({ uniforms, vertexShader: flatVert, fragmentShader: frag,
  transparent: true, depthTest: false, depthWrite: false, side: THREE.DoubleSide });
const selRing = new THREE.Mesh(DISC, flatMat(ringFrag, { uColor: { value: new THREE.Color() }, uA: { value: 0 }, uT: { value: 0 } }));
selRing.visible = false; selRing.renderOrder = 5; selRing.frustumCulled = false; scene.add(selRing);
const pulses = Array.from({ length: 6 }, () => {
  const mesh = new THREE.Mesh(DISC, flatMat(pulseFrag, { uColor: { value: new THREE.Color() }, uP: { value: 0 } }));
  mesh.visible = false; mesh.renderOrder = 6; mesh.frustumCulled = false; scene.add(mesh);
  return { mesh, node: null, t0: 0 };
});
let selAt = 0;
function firePulse(n) {   // two ripples, the second a beat behind the first
  if (reduceMotion) return;
  const now = performance.now();
  [0, 160].forEach((delay) => {
    const p = pulses.find((q) => !q.node); if (!p) return;
    p.node = n; p.t0 = now + delay; p.mesh.material.uniforms.uColor.value.copy(n.color).lerp(WHITE, 0.5);
  });
}

// Labels keep a fixed size on screen (LABEL_PX tall text) at any zoom; a dataset can scale it with
// { layout: { label: 1.2 } }. In a big graph only well-connected orbs show a name until you focus
// one, so names do not pile on top of each other.
const LABEL_PX = 13.5, LABEL_GAP = 4;
function labelSprite(text) {
  // Drawn at 2x and outlined in near-black, so labels stay sharp and readable over glowing orbs and links.
  const c = document.createElement('canvas'), g = c.getContext('2d');
  const font = '700 48px "Avenir Next","Segoe UI",system-ui,sans-serif';
  g.font = font; const w = Math.ceil(g.measureText(text).width) + 36; c.width = w; c.height = 76;
  g.font = font; g.textAlign = 'center'; g.textBaseline = 'middle'; g.lineJoin = 'round';
  g.lineWidth = 10; g.strokeStyle = 'rgba(4,6,18,.92)'; g.strokeText(text, w / 2, 40);
  g.fillStyle = '#f2f5ff'; g.fillText(text, w / 2, 40);
  const tex = new THREE.CanvasTexture(c);
  tex.anisotropy = 4; tex.minFilter = THREE.LinearFilter;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false,
    depthTest: false, sizeAttenuation: false }));
  s.userData.aspect = w / 76;
  s.center.set(0.5, -0.25);   // sits just above its orb on screen
  sizeLabel(s); s.renderOrder = 10; return s;
}
// Place labels so no two overlap on screen: the focused orb and its neighbours first, then
// labels already showing (so they keep their place while things move), then the best-connected
// orbs. Labels are re-placed when the view comes to rest (a quarter second after dragging, zooming
// or orbiting stops), at most every 1.5 s while it keeps moving, and at once when the focus changes.
// They fade in and out instead of blinking.
const _proj = new THREE.Vector3(), _lastCam = new THREE.Vector3();
let _declutterAt = -1e9, _lastFocus = null, _movedAt = 0, _settledDone = false;
function declutterLabels(f, now) {
  const camMoved = _lastCam.distanceToSquared(camera.position) > 1e-4;
  _lastCam.copy(camera.position);
  if (camMoved || dragging || alpha > 0.02) { _movedAt = now; _settledDone = false; }
  const settled = now - _movedAt > 250;
  const due = f !== _lastFocus || (settled && !_settledDone) || now - _declutterAt > 1500;
  if (!due) return;
  if (settled) _settledDone = true;
  _declutterAt = now; _lastFocus = f;
  const W = renderer.domElement.clientWidth, H = renderer.domElement.clientHeight;
  const placed = [];
  const rank = (n) => (f && n === f ? 1e6 : 0) + (f && f.nbrs.has(n) ? 1e5 : 0) + (n.lblOn ? 1e4 : 0) + n.deg * 10;
  const order = nodes.filter((n) => !hidden.has(n.type)).sort((a, b) => rank(b) - rank(a));
  for (const n of order) {
    _proj.copy(n.label.position).project(camera);
    if (_proj.z > 1 || Math.abs(_proj.x) > 1.2 || Math.abs(_proj.y) > 1.2) { n.lblOn = false; continue; }
    const x = (_proj.x + 1) / 2 * W, y = (1 - _proj.y) / 2 * H;
    const h = (LABEL_PX / 0.63) * (LAYOUT.label || 1) * 0.72, w = h * n.label.userData.aspect * 0.9;
    // A label already showing tolerates a little overlap before giving way; a hidden one needs
    // clear space plus a margin before it appears. That gap stops labels flickering.
    const pad = n.lblOn ? -2 : LABEL_GAP + 4;
    const r = { l: x - w / 2 - pad, r: x + w / 2 + pad, t: y - h * 1.35 - pad, b: y - h * 0.15 + pad };
    const clash = placed.some((q) => r.l < q.r && r.r > q.l && r.t < q.b && r.b > q.t);
    n.lblOn = !clash;
    if (!clash) placed.push(r);
  }
}
// Screen-space size: with sizeAttenuation off, a sprite's height in pixels is
// scale.y * P[1][1] / 2 * viewport height. The text is about 63% of the canvas height.
function sizeLabel(s) {
  const px = (LABEL_PX / 0.63) * (LAYOUT.label || 1);
  const h = (2 * px) / (camera.projectionMatrix.elements[5] * Math.max(renderer.domElement.clientHeight, 1));
  s.scale.set(h * s.userData.aspect, h, 1);
}

// ---- Layout strength, as multiples of the defaults. A dataset may set { layout: {...} } ----
// charge: how hard orbs push apart; distance: link rest length; gravity: pull toward the middle.
const LAYOUT = { charge: 1, distance: 1, gravity: 1, label: 1 };

// ---- State (declared before build, which uses it) ----
let nodes = [], links = [], byId = new Map(), hidden = new Set();
let selected = null, hovered = null, alpha = 1, followUntil = 0, goal = null, touched = false;
let linkLines, linkPos, linkCol;
const orbMeshes = [];

try {
  let data;
  if (DATA_URL) {
    const res = await fetch(DATA_URL, { cache: 'no-store' });
    if (!res.ok) throw new Error(DATA_URL + ' returned ' + res.status);
    data = await res.json();
  } else data = USE_FAKE_DATA ? makeFakeData() : await (await fetch('/api/graph')).json();
  if (data.colors) Object.assign(PALETTE, data.colors);
  if (data.title) document.querySelector('#title h1').textContent = data.title;
  if (data.layout) Object.assign(LAYOUT, data.layout);
  build(data);
} catch (e) {
  $('err').style.display = 'grid';
  $('err').textContent = 'Could not start the graph: ' + e.message + ' (see the browser console, F12, for details)';
  throw e;
}

function build({ nodes: ns, links: ls }) {
  nodes = ns.map((n) => ({ ...n, name: String(n.label ?? n.id), deg: 0, nbrs: new Set(), k: 1,
    pos: new THREE.Vector3().randomDirection().multiplyScalar(90 + Math.random() * 40),
    vel: new THREE.Vector3(), fixed: false }));
  nodes.forEach((n) => byId.set(n.id, n));
  links = ls.map((l) => ({ s: byId.get(l.source), t: byId.get(l.target) })).filter((l) => l.s && l.t);
  links.forEach((l) => { l.s.deg++; l.t.deg++; l.s.nbrs.add(l.t); l.t.nbrs.add(l.s); });

  if (!nodes.length) $('hint').textContent = 'No records to show for this view.';
  for (const n of nodes) {
    n.color = colorFor(n.type);
    n.r = 3.4 + Math.sqrt(n.deg) * 1.6;
    n.disc = new THREE.Mesh(DISC, new THREE.ShaderMaterial({
      uniforms: { uColor: { value: n.color }, uK: { value: 1 } }, vertexShader: orbVert, fragmentShader: orbFrag,
      transparent: true, side: THREE.DoubleSide }));
    n.core = new THREE.Mesh(SPHERE, new THREE.MeshBasicMaterial({ visible: false }));   // pick target
    n.core.scale.setScalar(1.1); n.core.userData.node = n;
    n.halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: GLOW, color: n.color, transparent: true,
      opacity: 0.45, depthWrite: false, blending: THREE.AdditiveBlending }));
    n.halo.scale.setScalar(6);
    n.group = new THREE.Group(); n.group.add(n.disc, n.core, n.halo);
    n.label = labelSprite(n.name);
    scene.add(n.group, n.label); orbMeshes.push(n.core);
  }

  linkPos = new Float32Array(links.length * 6); linkCol = new Float32Array(links.length * 6);
  const lg = new THREE.BufferGeometry();
  lg.setAttribute('position', new THREE.BufferAttribute(linkPos, 3));
  lg.setAttribute('color', new THREE.BufferAttribute(linkCol, 3));
  linkLines = new THREE.LineSegments(lg, new THREE.LineBasicMaterial({
    vertexColors: true, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
  linkLines.frustumCulled = false; scene.add(linkLines);

  for (let i = 0; i < 250; i++) simulate();   // pre-settle the layout
  alpha = 0.5;
  buildLegend();
  $('stats').textContent = `${nodes.length} nodes, ${links.length} links`;
}

// ---- Force layout. In 2D mode a flattening force pulls every node onto z = 0 ----
function simulate() {
  for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
    const a = nodes[i], b = nodes[j];
    tmp.subVectors(a.pos, b.pos);
    const d2 = Math.max(tmp.lengthSq(), 25), d = Math.sqrt(d2);
    tmp.multiplyScalar((2600 * LAYOUT.charge / d2 / d) * alpha);
    a.vel.add(tmp); b.vel.sub(tmp);
  }
  for (const l of links) {
    tmp.subVectors(l.t.pos, l.s.pos);
    const d = Math.max(tmp.length(), 0.01);
    tmp.multiplyScalar(((d - 58 * LAYOUT.distance) / d) * 0.07 * alpha);
    l.s.vel.add(tmp); l.t.vel.sub(tmp);
  }
  for (const n of nodes) {
    n.vel.addScaledVector(n.pos, -0.03 * LAYOUT.gravity * alpha).multiplyScalar(0.82);
    if (mode === '2d') n.vel.addScaledVector(planeN, -n.vel.dot(planeN));
    if (!n.fixed) n.pos.add(n.vel); else n.vel.set(0, 0, 0);
  }
  alpha *= 0.992;
}

// ---- 2D / 3D switch ----
function setMode(m) {
  if (m === mode) return;
  mode = m;
  document.querySelectorAll('#mode button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.mode === m)));
  if (m === '2d') {
    // Flatten onto a plane square to the camera right now, so you see the face of the sheet, not its edge.
    planeN.subVectors(camera.position, controls.target).normalize();
    planeP.set(0, 0, 0); nodes.forEach((n) => planeP.add(n.pos)); planeP.divideScalar(Math.max(nodes.length, 1));
    grid.quaternion.setFromUnitVectors(up, planeN); grid.position.copy(planeP);
    controls.autoRotate = false;   // spinning would turn the sheet edge-on
  } else {
    nodes.forEach((n) => n.pos.addScaledVector(planeN, (Math.random() - 0.5) * 24));
    controls.autoRotate = !reduceMotion;
  }
  alpha = Math.max(alpha, m === '3d' ? 0.5 : 0.25);
}
document.querySelectorAll('#mode button').forEach((b) => (b.onclick = () => setMode(b.dataset.mode)));

// ---- Legend ----
function buildLegend() {
  const counts = {}; nodes.forEach((n) => (counts[n.type] = (counts[n.type] || 0) + 1));
  const box = $('legend');
  for (const type of Object.keys(counts)) {
    const b = document.createElement('button');
    b.setAttribute('aria-pressed', 'true');
    b.style.setProperty('--c', '#' + colorFor(type).getHexString());
    b.innerHTML = `<span class="dot"></span><span>${type}</span><span class="n">${counts[type]}</span>`;
    b.onclick = () => {
      const off = !hidden.has(type);
      off ? hidden.add(type) : hidden.delete(type);
      b.setAttribute('aria-pressed', String(!off));
      if (selected && hidden.has(selected.type)) select(null);
    };
    box.appendChild(b);
  }
}

// ---- Selection / info panel ----
const CHIP_CAP = 24;
function select(n) {
  const changed = n !== selected;
  selected = n;
  const p = $('info');
  if (!n) { p.style.display = 'none'; return; }
  goal = null; followUntil = performance.now() + 1300;   // pan to the chosen orb
  if (changed) selAt = performance.now();
  selRing.material.uniforms.uColor.value.copy(n.color).lerp(WHITE, 0.65);
  firePulse(n);
  p.style.display = 'block';
  p.style.setProperty('--c', '#' + n.color.getHexString());
  p.innerHTML = `<h2></h2><div class="type"><span class="dot"></span><span></span></div><p class="detail"></p><div class="chips"></div>`;
  p.querySelector('h2').textContent = n.name;
  const det = p.querySelector('.detail');
  if (n.detail) det.textContent = n.detail; else det.remove();
  p.querySelector('.type span:last-child').textContent = `${n.type}, ${n.deg} connection${n.deg === 1 ? '' : 's'}`;
  const chips = p.querySelector('.chips');
  // Hubs can have dozens of links; show the first CHIP_CAP and count the rest.
  const nbrs = [...n.nbrs].sort((a, b) => a.type.localeCompare(b.type) || a.name.localeCompare(b.name));
  nbrs.slice(0, CHIP_CAP).forEach((m) => {
    const c = document.createElement('button'); c.textContent = m.name;
    c.style.setProperty('--c', '#' + m.color.getHexString());
    c.onclick = () => select(m); chips.appendChild(c);
  });
  if (nbrs.length > CHIP_CAP) {
    const more = document.createElement('span'); more.className = 'more';
    more.textContent = `+${nbrs.length - CHIP_CAP} more`; chips.appendChild(more);
  }
}

// ---- Pointer interaction: hover, click, drag-a-node ----
const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(), plane = new THREE.Plane(), hit = new THREE.Vector3();
let dragging = null, downAt = null, moved = false;
function setNdc(e) { ndc.set((e.clientX / innerWidth) * 2 - 1, -(e.clientY / innerHeight) * 2 + 1); ray.setFromCamera(ndc, camera); }
function pick() {
  const hits = ray.intersectObjects(orbMeshes.filter((m) => !hidden.has(m.userData.node.type)), false);
  return hits.length ? hits[0].object.userData.node : null;
}
const el = renderer.domElement;
el.addEventListener('pointerdown', (e) => {
  setNdc(e); downAt = { x: e.clientX, y: e.clientY }; moved = false;
  const n = pick();
  if (n) {
    dragging = n; n.fixed = true; controls.enabled = false; pauseSpin();
    if (mode === '2d') plane.setFromNormalAndCoplanarPoint(planeN, planeP); else plane.setFromNormalAndCoplanarPoint(camera.getWorldDirection(tmp.clone()), n.pos);
    el.setPointerCapture(e.pointerId);
  }
});
el.addEventListener('pointermove', (e) => {
  setNdc(e);
  if (downAt && Math.hypot(e.clientX - downAt.x, e.clientY - downAt.y) > 4) moved = true;
  if (dragging && moved && ray.ray.intersectPlane(plane, hit)) {
    dragging.pos.copy(hit); alpha = Math.max(alpha, 0.35);
  } else if (!dragging) {
    hovered = pick(); el.style.cursor = hovered ? 'pointer' : 'default';
  }
});
el.addEventListener('pointerup', (e) => {
  setNdc(e);
  if (dragging) { dragging.fixed = false; controls.enabled = true; }
  if (!moved) select(pick());
  dragging = null; downAt = null;
});
addEventListener('keydown', (e) => { if (e.key === 'Escape') select(null); });

// ---- Zoom buttons ----
const clampDist = (d) => THREE.MathUtils.clamp(d, controls.minDistance, controls.maxDistance);
function zoomBy(f) {
  const d = goal ? goal.dist : camera.position.distanceTo(controls.target);
  goal = { target: goal ? goal.target : null, dist: clampDist(d * f) }; followUntil = 0;
}
function fitGoal() {   // frame every visible node, measured as it actually projects on screen
  const vis = nodes.filter((n) => !hidden.has(n.type));
  if (!vis.length) return null;
  camera.updateMatrixWorld();
  const fwd = camera.getWorldDirection(new THREE.Vector3());
  const right = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 0);
  const upv = new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld, 1);
  const lo = new THREE.Vector3(Infinity, Infinity, Infinity), hi = new THREE.Vector3(-Infinity, -Infinity, -Infinity);
  vis.forEach((n) => { lo.min(n.pos); hi.max(n.pos); });
  const c = lo.add(hi).multiplyScalar(0.5);                         // centre of the bounding box
  const tv = Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) * 0.9, th = tv * camera.aspect;   // keep a 10% margin
  let d = 0;
  for (const n of vis) {
    tmp.subVectors(n.pos, c);
    const depth = tmp.dot(fwd), pad = n.r * 1.4;
    d = Math.max(d, (Math.abs(tmp.dot(right)) + pad) / th - depth, (Math.abs(tmp.dot(upv)) + pad + 4) / tv - depth);
  }
  return { target: c, dist: clampDist(d) };
}
$('zoom-in').onclick = () => zoomBy(0.7);
$('zoom-out').onclick = () => zoomBy(1 / 0.7);
$('zoom-fit').onclick = () => { const g = fitGoal(); if (g) { goal = g; followUntil = 0; } };

// ---- Frame loop ----
const c1 = new THREE.Color(), c2 = new THREE.Color();
function frame() {
  requestAnimationFrame(frame);
  const f = dragging || hovered || selected, now = performance.now();
  if (alpha > 0.002) simulate();
  if (mode === '2d') for (const n of nodes) if (!n.fixed) { tmp.subVectors(n.pos, planeP); n.pos.addScaledVector(planeN, -tmp.dot(planeN) * 0.12); }   // glide onto the sheet
  grid.material.opacity += ((mode === '2d' ? 0.22 : 0) - grid.material.opacity) * 0.1;
  grid.visible = grid.material.opacity > 0.01;

  for (const n of nodes) {
    const vis = !hidden.has(n.type);
    n.group.visible = n.label.visible = vis;
    if (!vis) continue;
    const active = !f || n === f || f.nbrs.has(n);
    n.k += ((active ? 1 : 0.2) - n.k) * 0.12;
    n.group.position.copy(n.pos);
    n.group.scale.setScalar(n.r * (n === f ? 1.12 : 1));
    n.disc.material.uniforms.uK.value = 0.25 + 0.75 * n.k;
    n.halo.material.opacity = 0.45 * n.k;
    n.label.position.set(n.pos.x, n.pos.y + n.r * 1.05, n.pos.z);

  }

  declutterLabels(f, now);
  for (const n of nodes) {   // fade toward shown or hidden; three.js hides an object only on === false
    if (hidden.has(n.type)) continue;
    n.lblA = (n.lblA ?? 0) + ((n.lblOn ? 1 : 0) - (n.lblA ?? 0)) * 0.18;
    n.label.visible = n.lblA > 0.03;
    n.label.material.opacity = (0.25 + 0.75 * n.k) * n.lblA;
  }

  links.forEach((l, i) => {
    const vis = !hidden.has(l.s.type) && !hidden.has(l.t.type);
    const on = !f || l.s === f || l.t === f;
    const k = vis ? (on ? (f ? 0.85 : 0.3) : 0.04) : 0;
    l.s.pos.toArray(linkPos, i * 6); l.t.pos.toArray(linkPos, i * 6 + 3);
    c1.copy(l.s.color).multiplyScalar(k).toArray(linkCol, i * 6);
    c2.copy(l.t.color).multiplyScalar(k).toArray(linkCol, i * 6 + 3);
  });
  if (linkLines) { linkLines.geometry.attributes.position.needsUpdate = true; linkLines.geometry.attributes.color.needsUpdate = true; }

  const ringOn = selected && !hidden.has(selected.type);
  selRing.visible = !!ringOn;
  if (ringOn) {   // the ring grows in from slightly larger, then holds and slowly turns
    const u = reduceMotion ? 1 : Math.min(1, (now - selAt) / 320), e = 1 - Math.pow(1 - u, 3);
    selRing.position.copy(selected.pos);
    selRing.scale.setScalar(selected.r * 1.9 * (1 + (1 - e) * 0.45));
    selRing.material.uniforms.uA.value = e;
    selRing.material.uniforms.uT.value = reduceMotion ? 0 : now / 1000;
  }
  for (const p of pulses) {
    if (!p.node) continue;
    const u = (now - p.t0) / 800;
    if (u >= 1) { p.node = null; p.mesh.visible = false; continue; }
    p.mesh.visible = u >= 0;
    if (u < 0) continue;
    p.mesh.position.copy(p.node.pos); p.mesh.scale.setScalar(p.node.r * 3.4);
    p.mesh.material.uniforms.uP.value = u;
  }

  // pan toward the selected orb (or the middle) for a moment after a click or mode switch
  if (now < followUntil) {
    tmp.copy(controls.target);
    controls.target.lerp(selected && !hidden.has(selected.type) ? selected.pos : desired.set(0, 0, 0), 0.08);
    camera.position.add(delta.subVectors(controls.target, tmp));
  }
  if (goal) {   // ease toward the zoom / fit goal, keeping the viewing direction
    tmp.subVectors(camera.position, controls.target).normalize();
    const d = camera.position.distanceTo(controls.target);
    if (goal.target) controls.target.lerp(goal.target, 0.14);
    const nd = d + (goal.dist - d) * 0.14;
    camera.position.copy(controls.target).addScaledVector(tmp, nd);
    if (Math.abs(goal.dist - nd) < 0.3 && (!goal.target || controls.target.distanceTo(goal.target) < 0.3)) goal = null;
  }
  controls.update();
  composer.render();
}
{ // start framed on the whole graph
  const g = fitGoal();
  if (g) { tmp.subVectors(camera.position, controls.target).normalize(); controls.target.copy(g.target); camera.position.copy(g.target).addScaledVector(tmp, g.dist); }
}
frame();
setTimeout(() => { if (!touched) goal = fitGoal(); }, 2500);

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight); composer.setSize(innerWidth, innerHeight);
  nodes.forEach((n) => sizeLabel(n.label));
});
