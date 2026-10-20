// Drifting constellation background: small triangles linked by faint lines.
(() => {
  const canvas = document.getElementById('sky');
  if (!canvas || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const ctx = canvas.getContext('2d');
  const rgb = getComputedStyle(document.documentElement).getPropertyValue('--star').trim() || '168,140,190';
  const LINK = 150;
  let w, h, dpr, stars = [];

  function resize() {
    dpr = Math.min(window.devicePixelRatio || 1, 2);
    w = canvas.clientWidth;
    h = canvas.clientHeight;
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    const count = Math.round((w * h) / 26000);
    stars = Array.from({ length: count }, () => ({
      x: Math.random() * w,
      y: Math.random() * h,
      vx: (Math.random() - 0.5) * 0.12,
      vy: (Math.random() - 0.5) * 0.12,
      r: 2 + Math.random() * 2,
      a: Math.random() * Math.PI * 2
    }));
  }

  function draw() {
    ctx.clearRect(0, 0, w, h);
    for (const s of stars) {
      s.x = (s.x + s.vx + w) % w;
      s.y = (s.y + s.vy + h) % h;
      s.a += 0.002;
    }
    ctx.lineWidth = 0.6;
    for (let i = 0; i < stars.length; i++) {
      for (let j = i + 1; j < stars.length; j++) {
        const dx = stars[i].x - stars[j].x, dy = stars[i].y - stars[j].y;
        const d = Math.hypot(dx, dy);
        if (d < LINK) {
          ctx.strokeStyle = `rgba(${rgb},${0.28 * (1 - d / LINK)})`;
          ctx.beginPath();
          ctx.moveTo(stars[i].x, stars[i].y);
          ctx.lineTo(stars[j].x, stars[j].y);
          ctx.stroke();
        }
      }
    }
    ctx.fillStyle = `rgba(${rgb},0.55)`;
    for (const s of stars) {
      ctx.beginPath();
      for (let k = 0; k < 3; k++) {
        const t = s.a + k * (Math.PI * 2 / 3);
        ctx[k ? 'lineTo' : 'moveTo'](s.x + Math.cos(t) * s.r, s.y + Math.sin(t) * s.r);
      }
      ctx.fill();
    }
    requestAnimationFrame(draw);
  }

  resize();
  window.addEventListener('resize', resize);
  requestAnimationFrame(draw);
})();
