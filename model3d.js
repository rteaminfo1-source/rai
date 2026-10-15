/* Rai 3D — показывает 3D-модель прямо в чате и даёт её покрутить. Свой маленький движок на canvas,
   без three.js и любых внешних библиотек (работает офлайн). Сцену собирает Rai (model3d.py):
   {bg, ground, objects:[{geo, args, pos, rot(град), scale, color}]}.
   window.RaiModel.view(container, scene, opts) — показать; .obj(scene) — геометрия в формате .obj для скачивания. */
(function () {
  "use strict";

  const R = (d) => d * Math.PI / 180;

  // ---- тесселяция примитивов в {verts:[[x,y,z]], faces:[[i,j,k(,l)]]} (локальные координаты)
  function box(a) {
    const w = (a.w || 1) / 2, h = (a.h || 1) / 2, d = (a.d || 1) / 2;
    const v = [[-w, -h, -d], [w, -h, -d], [w, h, -d], [-w, h, -d], [-w, -h, d], [w, -h, d], [w, h, d], [-w, h, d]];
    const f = [[0, 1, 2, 3], [5, 4, 7, 6], [4, 0, 3, 7], [1, 5, 6, 2], [3, 2, 6, 7], [4, 5, 1, 0]];
    return {verts: v, faces: f};
  }
  function sphere(a, seg, ring) {
    seg = seg || 22; ring = ring || 16; const r = a.r || 1, v = [], f = [];
    for (let i = 0; i <= ring; i++) {
      const phi = Math.PI * i / ring, y = Math.cos(phi) * r, rr = Math.sin(phi) * r;
      for (let j = 0; j <= seg; j++) { const th = 2 * Math.PI * j / seg; v.push([Math.cos(th) * rr, y, Math.sin(th) * rr]); }
    }
    const row = seg + 1;
    for (let i = 0; i < ring; i++) for (let j = 0; j < seg; j++) {
      const a0 = i * row + j; f.push([a0, a0 + 1, a0 + row + 1, a0 + row]);
    }
    return {verts: v, faces: f};
  }
  function cylinder(a, seg) {
    seg = seg || 28; const r = a.r || 1, h = (a.h || 1) / 2, v = [], f = [];
    for (let j = 0; j < seg; j++) { const th = 2 * Math.PI * j / seg, x = Math.cos(th) * r, z = Math.sin(th) * r; v.push([x, -h, z], [x, h, z]); }
    for (let j = 0; j < seg; j++) { const a0 = j * 2, b0 = ((j + 1) % seg) * 2; f.push([a0, b0, b0 + 1, a0 + 1]); }
    const top = v.push([0, h, 0]) - 1, bot = v.push([0, -h, 0]) - 1;
    for (let j = 0; j < seg; j++) { const a0 = j * 2, b0 = ((j + 1) % seg) * 2; f.push([a0 + 1, b0 + 1, top]); f.push([b0, a0, bot]); }
    return {verts: v, faces: f};
  }
  function cone(a, seg) {
    seg = seg || 28; const r = a.r || 1, h = (a.h || 1) / 2, v = [], f = [];
    for (let j = 0; j < seg; j++) { const th = 2 * Math.PI * j / seg; v.push([Math.cos(th) * r, -h, Math.sin(th) * r]); }
    const tip = v.push([0, h, 0]) - 1, bot = v.push([0, -h, 0]) - 1;
    for (let j = 0; j < seg; j++) { const a0 = j, b0 = (j + 1) % seg; f.push([a0, b0, tip]); f.push([b0, a0, bot]); }
    return {verts: v, faces: f};
  }
  function torus(a, seg, sides) {
    seg = seg || 28; sides = sides || 14; const R0 = a.r || 1, rt = a.tube || 0.3, v = [], f = [];
    for (let i = 0; i < seg; i++) {
      const u = 2 * Math.PI * i / seg, cu = Math.cos(u), su = Math.sin(u);
      for (let j = 0; j < sides; j++) { const vv = 2 * Math.PI * j / sides, cv = Math.cos(vv); v.push([(R0 + rt * cv) * cu, rt * Math.sin(vv), (R0 + rt * cv) * su]); }
    }
    for (let i = 0; i < seg; i++) for (let j = 0; j < sides; j++) {
      const a0 = i * sides + j, b0 = ((i + 1) % seg) * sides + j, c0 = ((i + 1) % seg) * sides + (j + 1) % sides, d0 = i * sides + (j + 1) % sides;
      f.push([a0, b0, c0, d0]);
    }
    return {verts: v, faces: f};
  }
  function primitive(geo, a) {
    if (geo === "box") return box(a);
    if (geo === "sphere") return sphere(a);
    if (geo === "cylinder") return cylinder(a);
    if (geo === "cone") return cone(a);
    if (geo === "torus") return torus(a);
    return box(a || {w: 1, h: 1, d: 1});
  }

  // ---- матрица/вектор
  function rotXYZ(p, rx, ry, rz) {
    let [x, y, z] = p, c, s;
    if (rx) { c = Math.cos(rx); s = Math.sin(rx); [y, z] = [y * c - z * s, y * s + z * c]; }
    if (ry) { c = Math.cos(ry); s = Math.sin(ry); [x, z] = [x * c + z * s, -x * s + z * c]; }
    if (rz) { c = Math.cos(rz); s = Math.sin(rz); [x, y] = [x * c - y * s, x * s + y * c]; }
    return [x, y, z];
  }
  function hexRgb(h) {
    const m = /^#?([0-9a-f]{6})$/i.exec(h || ""); if (!m) return [139, 92, 246];
    const n = parseInt(m[1], 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
  }

  // ---- собрать все грани сцены в мировых координатах: [{p:[[x,y,z]x3-4], rgb}]
  function worldFaces(scene) {
    const faces = [];
    for (const o of (scene.objects || [])) {
      const mesh = primitive(o.geo, o.args || {});
      const s = o.scale || [1, 1, 1], r = o.rot || [0, 0, 0], t = o.pos || [0, 0, 0];
      const rgb = hexRgb(o.color);
      const wv = mesh.verts.map((p) => {
        let q = [p[0] * s[0], p[1] * s[1], p[2] * s[2]];
        q = rotXYZ(q, R(r[0]), R(r[1]), R(r[2]));
        return [q[0] + t[0], q[1] + t[1], q[2] + t[2]];
      });
      for (const fc of mesh.faces) faces.push({idx: fc, rgb: rgb, verts: wv});
    }
    return faces;
  }

  function bounds(scene) {
    let lo = [1e9, 1e9, 1e9], hi = [-1e9, -1e9, -1e9];
    for (const o of (scene.objects || [])) {
      const t = o.pos || [0, 0, 0], a = o.args || {}, s = o.scale || [1, 1, 1];
      const rad = Math.max(a.r || 0, a.tube ? a.r + a.tube : 0, (a.w || 0) / 2, (a.h || 0) / 2, (a.d || 0) / 2, 0.5);
      for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], t[k] - rad * s[k]); hi[k] = Math.max(hi[k], t[k] + rad * s[k]); }
    }
    if (hi[0] < lo[0]) { lo = [-1, -1, -1]; hi = [1, 1, 1]; }
    return {c: [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2],
            r: Math.max(hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]) / 2 || 1, lo: lo, hi: hi};
  }

  /** Показать сцену в контейнере. Возвращает {stop, canvas}. opts: {height, spin}. */
  function view(container, scene, opts) {
    opts = opts || {};
    const cv = document.createElement("canvas");
    cv.style.cssText = "display:block;width:100%;height:" + (opts.height || 320) + "px;border-radius:14px;cursor:grab;touch-action:none;background:" + (scene.bg || "#0e1016");
    container.appendChild(cv);
    const ctx = cv.getContext("2d");
    const faces = worldFaces(scene), bb = bounds(scene), L = (() => { const v = [0.4, 0.8, 0.5]; const n = Math.hypot(...v); return [v[0] / n, v[1] / n, v[2] / n]; })();
    let yaw = R(30), pitch = R(-18), dist = bb.r * 3.2, spin = opts.spin !== false, dpr = Math.min(window.devicePixelRatio || 1, 2);

    function resize() {
      const w = cv.clientWidth || 300, h = opts.height || 320;
      cv.width = w * dpr; cv.height = h * dpr;
    }

    function draw() {
      const W = cv.width, H = cv.height, cx = W / 2, cy = H / 2, f = H * 1.05;
      ctx.clearRect(0, 0, W, H);
      // пол-тень
      if (scene.ground) {
        ctx.fillStyle = scene.ground; ctx.globalAlpha = 1;
      }
      const cyaw = Math.cos(yaw), syaw = Math.sin(yaw), cp = Math.cos(pitch), sp = Math.sin(pitch);
      const tf = (p) => {
        let x = p[0] - bb.c[0], y = p[1] - bb.c[1], z = p[2] - bb.c[2];
        let x1 = x * cyaw + z * syaw, z1 = -x * syaw + z * cyaw;         // yaw (Y)
        let y1 = y * cp - z1 * sp, z2 = y * sp + z1 * cp;                // pitch (X)
        return [x1, y1, z2];
      };
      const drawn = [];
      for (const fa of faces) {
        const pts = fa.idx.map((i) => tf(fa.verts[i]));
        let zc = 0; for (const p of pts) zc += p[2]; zc /= pts.length;
        // нормаль грани
        const u = [pts[1][0] - pts[0][0], pts[1][1] - pts[0][1], pts[1][2] - pts[0][2]];
        const w = [pts[2][0] - pts[0][0], pts[2][1] - pts[0][1], pts[2][2] - pts[0][2]];
        const nx = u[1] * w[2] - u[2] * w[1], ny = u[2] * w[0] - u[0] * w[2], nz = u[0] * w[1] - u[1] * w[0];
        const nl = Math.hypot(nx, ny, nz) || 1;
        if (nz / nl < -0.02) continue;                                   // отбрасываем задние грани
        const lambert = Math.max(0, (nx * L[0] + ny * L[1] + nz * L[2]) / nl);
        const sh = 0.32 + 0.68 * lambert;
        drawn.push({zc: zc, pts: pts, rgb: fa.rgb, sh: sh});
      }
      drawn.sort((a, b) => a.zc - b.zc);                                  // painter's: дальние раньше
      for (const d of drawn) {
        const sx = (p) => cx + p[0] * f / (p[2] + dist), sy = (p) => cy - p[1] * f / (p[2] + dist);
        ctx.beginPath();
        ctx.moveTo(sx(d.pts[0]), sy(d.pts[0]));
        for (let i = 1; i < d.pts.length; i++) ctx.lineTo(sx(d.pts[i]), sy(d.pts[i]));
        ctx.closePath();
        const r = Math.round(d.rgb[0] * d.sh), g = Math.round(d.rgb[1] * d.sh), b = Math.round(d.rgb[2] * d.sh);
        ctx.fillStyle = "rgb(" + r + "," + g + "," + b + ")";
        ctx.strokeStyle = "rgba(0,0,0,0.18)"; ctx.lineWidth = dpr * 0.6;
        ctx.fill(); ctx.stroke();
      }
    }

    let raf = 0, alive = true;
    function loop() { if (!alive) return; if (spin) yaw += 0.006; draw(); raf = requestAnimationFrame(loop); }
    // перетаскивание — крутить
    let drag = null;
    const down = (e) => { drag = {x: e.clientX, y: e.clientY}; spin = false; cv.style.cursor = "grabbing"; };
    const move = (e) => { if (!drag) return; yaw += (e.clientX - drag.x) * 0.01; pitch += (e.clientY - drag.y) * 0.01;
      pitch = Math.max(-1.45, Math.min(1.45, pitch)); drag = {x: e.clientX, y: e.clientY}; };
    const up = () => { drag = null; cv.style.cursor = "grab"; };
    cv.addEventListener("pointerdown", (e) => { cv.setPointerCapture(e.pointerId); down(e); });
    cv.addEventListener("pointermove", move);
    cv.addEventListener("pointerup", up); cv.addEventListener("pointercancel", up);
    cv.addEventListener("wheel", (e) => { e.preventDefault(); dist = Math.max(bb.r * 1.6, Math.min(bb.r * 8, dist * (1 + Math.sign(e.deltaY) * 0.12))); }, {passive: false});
    const ro = typeof ResizeObserver === "function" ? new ResizeObserver(resize) : null;
    if (ro) ro.observe(cv);
    window.addEventListener("resize", resize);
    resize(); loop();
    return {canvas: cv, stop: () => { alive = false; cancelAnimationFrame(raf); if (ro) ro.disconnect(); }, spinOff: () => { spin = false; } };
  }

  /** Геометрия сцены в формате Wavefront .obj (для Blender/любого 3D-редактора). */
  function obj(scene, name) {
    const lines = ["# " + (name || "Модель Rai") + " — экспортировал Rai (rai.rteam.info)", "o " + (name || "RaiModel").replace(/\s+/g, "_")];
    let off = 1;
    for (const o of (scene.objects || [])) {
      const mesh = primitive(o.geo, o.args || {});
      const s = o.scale || [1, 1, 1], r = o.rot || [0, 0, 0], t = o.pos || [0, 0, 0];
      for (const p of mesh.verts) {
        let q = [p[0] * s[0], p[1] * s[1], p[2] * s[2]];
        q = rotXYZ(q, R(r[0]), R(r[1]), R(r[2]));
        lines.push("v " + (q[0] + t[0]).toFixed(4) + " " + (q[1] + t[1]).toFixed(4) + " " + (q[2] + t[2]).toFixed(4));
      }
      for (const fc of mesh.faces) lines.push("f " + fc.map((i) => i + off).join(" "));
      off += mesh.verts.length;
    }
    return lines.join("\n") + "\n";
  }

  window.RaiModel = {view: view, obj: obj, worldFaces: worldFaces, primitive: primitive};
})();
