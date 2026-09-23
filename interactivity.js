(() => {
  const panel = document.querySelector('.hero-right');
  const canvas = document.getElementById('warp-grid');
  const toggle = document.getElementById('grid-toggle');
  if (panel && canvas && toggle) {
    const ctx = canvas.getContext('2d');
    const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
    let width = 0, height = 0, dpr = 1, visible = true, enabled = true;
    let pointer = { x: -1000, y: -1000, strength: 0 };
    let last = 0;

    const resize = () => {
      const rect = panel.getBoundingClientRect();
      width = rect.width; height = rect.height;
      dpr = Math.min(devicePixelRatio || 1, 2);
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      draw(performance.now());
    };
    new ResizeObserver(resize).observe(panel);
    new IntersectionObserver(entries => { visible = entries[0].isIntersecting; }).observe(panel);
    panel.addEventListener('pointermove', event => {
      const rect = panel.getBoundingClientRect();
      pointer.x = event.clientX - rect.left;
      pointer.y = event.clientY - rect.top;
      pointer.strength = 1;
      if (reducedMotion.matches) draw(performance.now());
    }, { passive: true });
    panel.addEventListener('pointerleave', () => { pointer.strength = 0; });
    toggle.addEventListener('click', () => {
      enabled = !enabled;
      canvas.style.opacity = enabled ? '1' : '0';
      toggle.setAttribute('aria-pressed', String(enabled));
      toggle.querySelector('span').textContent = enabled ? 'on' : 'off';
    });

    function warp(x, y, time) {
      // A broad field bends around the robot; the pointer adds a local ripple.
      const cx = width * .5, cy = height * .52;
      const dx = x - cx, dy = y - cy;
      const ellipse = Math.sqrt((dx / (width * .30)) ** 2 + (dy / (height * .31)) ** 2);
      const modelInfluence = Math.exp(-(Math.max(0, ellipse - .65) ** 2) * 2.6);
      const modelPush = Math.max(0, 1.55 - ellipse) * modelInfluence * 23;
      const length = Math.hypot(dx, dy) || 1;
      let ox = dx / length * modelPush;
      let oy = dy / length * modelPush;
      const px = x - pointer.x, py = y - pointer.y;
      const pd = Math.hypot(px, py) || 1;
      const ripple = Math.exp(-(pd * pd) / 25000) * 34 * pointer.strength;
      ox += px / pd * ripple;
      oy += py / pd * ripple;
      if (!reducedMotion.matches) {
        ox += Math.sin(y * .018 + time * .00038) * 2;
        oy += Math.cos(x * .017 + time * .00032) * 2;
      }
      return [x + ox, y + oy];
    }

    function draw(time) {
      if (!width || !height || !enabled) return;
      ctx.clearRect(0, 0, width, height);
      const step = Math.max(29, Math.min(40, width / 16));
      ctx.lineWidth = 1;
      for (let x = -step; x <= width + step; x += step) {
        ctx.beginPath();
        for (let y = -step; y <= height + step; y += 10) {
          const [wx, wy] = warp(x, y, time);
          if (y === -step) ctx.moveTo(wx, wy); else ctx.lineTo(wx, wy);
        }
        ctx.strokeStyle = 'rgba(115, 160, 255, .26)';
        ctx.stroke();
      }
      for (let y = -step; y <= height + step; y += step) {
        ctx.beginPath();
        for (let x = -step; x <= width + step; x += 10) {
          const [wx, wy] = warp(x, y, time);
          if (x === -step) ctx.moveTo(wx, wy); else ctx.lineTo(wx, wy);
        }
        ctx.strokeStyle = 'rgba(173, 134, 255, .24)';
        ctx.stroke();
      }
    }

    function tick(time) {
      requestAnimationFrame(tick);
      if (!visible || !enabled || reducedMotion.matches || time - last < 32) return;
      last = time;
      draw(time);
    }
    requestAnimationFrame(tick);
  }

  const nav = document.querySelector('nav');
  const links = document.querySelector('.nav-links');
  if (nav && links) {
    const menu = document.createElement('button');
    menu.type = 'button';
    menu.className = 'mobile-menu';
    menu.textContent = 'Menu';
    menu.setAttribute('aria-expanded', 'false');
    menu.setAttribute('aria-label', 'Open section menu');
    nav.insertBefore(menu, links);
    menu.addEventListener('click', () => {
      const open = menu.getAttribute('aria-expanded') !== 'true';
      menu.setAttribute('aria-expanded', String(open));
      menu.setAttribute('aria-label', open ? 'Close section menu' : 'Open section menu');
      links.classList.toggle('open', open);
    });
    links.addEventListener('click', event => {
      if (event.target.closest('a')) { links.classList.remove('open'); menu.setAttribute('aria-expanded', 'false'); }
    });
    const sections = [...document.querySelectorAll('section[id], .section[id]')];
    new IntersectionObserver(entries => {
      const active = entries.filter(e => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
      if (!active) return;
      links.querySelectorAll('a').forEach(a => a.classList.toggle('current', a.getAttribute('href') === '#' + active.target.id));
    }, { rootMargin: '-18% 0px -65% 0px', threshold: [0, .2, .5] }).observe(sections[0] || document.body);
    sections.slice(1).forEach(section => {
      // A separate observer keeps highlight updates cheap across the long page.
      new IntersectionObserver(entries => {
        if (!entries[0].isIntersecting) return;
        links.querySelectorAll('a').forEach(a => a.classList.toggle('current', a.getAttribute('href') === '#' + section.id));
      }, { rootMargin: '-18% 0px -65% 0px' }).observe(section);
    });
  }
})();
