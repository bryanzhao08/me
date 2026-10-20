// Subtle low-poly background: a jittered triangle mesh whose vertices bob
// slowly in z, shaded in near-black greys by each facet's angle to a light.
// Moving the pointer crinkles the mesh like paper; it springs back flat.
(() => {
  const canvas = document.getElementById('sky');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const still = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const CELL = 95;
  const RADIUS = 230;
  const light = normalize([-0.4, -0.6, 0.7]);
  let w, h, cols, rows, pts = [];
  let pointer = null;

  function normalize(v) {
    const l = Math.hypot(v[0], v[1], v[2]);
    return [v[0] / l, v[1] / l, v[2] / l];
  }

  function resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = canvas.clientWidth;
    h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    cols = Math.ceil(w / CELL) + 2;
    rows = Math.ceil(h / CELL) + 2;
    pts = [];
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        pts.push({
          hx: (c - 1) * CELL + (Math.random() - 0.5) * CELL * 0.7,
          hy: (r - 1) * CELL + (Math.random() - 0.5) * CELL * 0.7,
          phase: Math.random() * Math.PI * 2,
          speed: 0.15 + Math.random() * 0.2,
          amp: 30 + Math.random() * 40,
          // Each vertex folds up or down, which is what makes it look crinkled.
          fold: Math.random() < 0.5 ? -1 : 1,
          ox: 0, oy: 0, vx: 0, vy: 0, dz: 0, vz: 0,
          x: 0, y: 0, z: 0
        });
      }
    }
  }

  window.addEventListener('pointermove', e => {
    const prev = pointer;
    pointer = { x: e.clientX, y: e.clientY };
    if (!prev || still) return;
    const mx = pointer.x - prev.x, my = pointer.y - prev.y;
    const moved = Math.min(Math.hypot(mx, my), 60);
    if (!moved) return;
    for (const p of pts) {
      const dx = p.hx + p.ox - pointer.x, dy = p.hy + p.oy - pointer.y;
      const d = Math.hypot(dx, dy);
      if (d > RADIUS) continue;
      const f = (1 - d / RADIUS) ** 2;
      // Drag the surface along with the pointer and fold it.
      p.vx += mx * f * 0.12 + (dx / (d || 1)) * f * moved * 0.06;
      p.vy += my * f * 0.12 + (dy / (d || 1)) * f * moved * 0.06;
      p.vz += p.fold * f * moved * 0.9;
    }
  }, { passive: true });
  document.addEventListener('pointerleave', () => { pointer = null; });

  function facet(a, b, c) {
    const u = [b.x - a.x, b.y - a.y, b.z - a.z];
    const v = [c.x - a.x, c.y - a.y, c.z - a.z];
    let n = normalize([u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]);
    if (n[2] < 0) n = [-n[0], -n[1], -n[2]];
    const shade = Math.max(0, n[0] * light[0] + n[1] * light[1] + n[2] * light[2]);
    // Creased facets catch more light so the crinkles read.
    const crease = Math.min(1, (Math.abs(a.dz) + Math.abs(b.dz) + Math.abs(c.dz)) / 240);
    const g = Math.round(15 + shade * (10 + crease * 16));
    ctx.fillStyle = ctx.strokeStyle = `rgb(${g},${g},${g})`;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.lineTo(c.x, c.y);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();
  }

  function step(s) {
    for (const p of pts) {
      // Damped springs pull every crease back to rest.
      p.vx = (p.vx - p.ox * 0.04) * 0.88;
      p.vy = (p.vy - p.oy * 0.04) * 0.88;
      p.vz = (p.vz - p.dz * 0.015) * 0.92;
      p.ox += p.vx;
      p.oy += p.vy;
      p.dz = Math.max(-160, Math.min(160, p.dz + p.vz));
      p.x = p.hx + p.ox;
      p.y = p.hy + p.oy;
      p.z = Math.sin(s * p.speed + p.phase) * p.amp + p.dz;
    }
  }

  function draw(t) {
    step(t / 1000);
    ctx.lineWidth = 1;
    for (let r = 0; r < rows - 1; r++) {
      for (let c = 0; c < cols - 1; c++) {
        const a = pts[r * cols + c], b = pts[r * cols + c + 1];
        const d = pts[(r + 1) * cols + c], e = pts[(r + 1) * cols + c + 1];
        // Alternate the diagonal so the mesh doesn't read as a grid.
        if ((r + c) % 2) { facet(a, b, e); facet(a, e, d); }
        else { facet(a, b, d); facet(b, e, d); }
      }
    }
    // Faint white edges over the facets.
    ctx.strokeStyle = 'rgba(255,255,255,0.025)';
    ctx.beginPath();
    for (let r = 0; r < rows - 1; r++) {
      for (let c = 0; c < cols - 1; c++) {
        const a = pts[r * cols + c], b = pts[r * cols + c + 1], d = pts[(r + 1) * cols + c];
        const e = pts[(r + 1) * cols + c + 1];
        ctx.moveTo(d.x, d.y); ctx.lineTo(a.x, a.y); ctx.lineTo(b.x, b.y);
        if ((r + c) % 2) { ctx.moveTo(a.x, a.y); ctx.lineTo(e.x, e.y); }
        else { ctx.moveTo(b.x, b.y); ctx.lineTo(d.x, d.y); }
      }
    }
    ctx.stroke();
    if (!still) requestAnimationFrame(draw);
  }

  resize();
  window.addEventListener('resize', () => { resize(); if (still) draw(0); });
  requestAnimationFrame(draw);
})();
