// Black-and-white spinning viewer for the 95071X worlds robot.
(() => {
  const canvas = document.getElementById('robot');
  const status = document.getElementById('robot-status');
  if (!canvas || typeof THREE === 'undefined') return;

  const MODEL_URL = 'assets/models/worlds-compact.glb';

  // Models are split into parts to stay under the host's file size limit.
  async function loadChunkedGLB(loader, url, onLoad, onProgress, onError) {
    try {
      const manifest = await (await fetch(url + '.parts.json')).json();
      const base = url.slice(0, url.lastIndexOf('/') + 1);
      let loaded = 0;
      const chunks = await Promise.all(manifest.parts.map(async name => {
        const response = await fetch(base + name);
        if (!response.ok) throw new Error('Model part unavailable: ' + name);
        const bytes = new Uint8Array(await response.arrayBuffer());
        loaded += bytes.byteLength;
        onProgress(loaded / manifest.size);
        return bytes;
      }));
      const joined = new Uint8Array(manifest.size);
      let offset = 0;
      for (const bytes of chunks) {
        joined.set(bytes, offset);
        offset += bytes.byteLength;
      }
      loader.parse(joined.buffer, base, onLoad, onError);
    } catch (error) { onError(error); }
  }

  // Include EXT_mesh_gpu_instancing transforms when framing optimized CAD.
  function accurateBounds(root) {
    root.updateMatrixWorld(true);
    const result = new THREE.Box3().makeEmpty();
    const instanceMatrix = new THREE.Matrix4();
    const worldMatrix = new THREE.Matrix4();
    const part = new THREE.Box3();
    root.traverse(object => {
      if (!object.isMesh || !object.geometry) return;
      if (!object.geometry.boundingBox) object.geometry.computeBoundingBox();
      if (object.isInstancedMesh) {
        for (let i = 0; i < object.count; i++) {
          object.getMatrixAt(i, instanceMatrix);
          worldMatrix.multiplyMatrices(object.matrixWorld, instanceMatrix);
          part.copy(object.geometry.boundingBox).applyMatrix4(worldMatrix);
          result.union(part);
        }
      } else {
        part.copy(object.geometry.boundingBox).applyMatrix4(object.matrixWorld);
        result.union(part);
      }
    });
    return result;
  }

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.5));
  renderer.outputEncoding = THREE.sRGBEncoding;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(40, 1, 0.1, 100);
  camera.position.set(0, 1.1, 5.6);
  camera.lookAt(0, 0, 0);

  scene.add(new THREE.AmbientLight(0xffffff, 0.35));
  const key = new THREE.DirectionalLight(0xffffff, 0.9);
  key.position.set(5, 8, 6);
  scene.add(key);
  const rim = new THREE.DirectionalLight(0xffffff, 0.3);
  rim.position.set(-5, 2, -6);
  scene.add(rim);

  const pivot = new THREE.Group();
  scene.add(pivot);

  let rotY = 0.6, rotX = -0.25, dragging = false, last = null, visible = false, requested = false;

  function resize() {
    const w = canvas.clientWidth, h = canvas.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }

  function frame() {
    if (!visible) return;
    if (!dragging) rotY += 0.003;
    pivot.rotation.set(rotX, rotY, 0);
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }

  canvas.addEventListener('pointerdown', e => { dragging = true; last = { x: e.clientX, y: e.clientY }; });
  window.addEventListener('pointermove', e => {
    if (!dragging) return;
    rotY += (e.clientX - last.x) * 0.008;
    rotX = Math.max(-1.2, Math.min(1.2, rotX + (e.clientY - last.y) * 0.006));
    last = { x: e.clientX, y: e.clientY };
  });
  window.addEventListener('pointerup', () => { dragging = false; });
  window.addEventListener('resize', resize);

  function load() {
    const loader = new THREE.GLTFLoader();
    const draco = new THREE.DRACOLoader();
    draco.setDecoderPath('vendor/draco/');
    loader.setDRACOLoader(draco);
    if (typeof MeshoptDecoder !== 'undefined') loader.setMeshoptDecoder(MeshoptDecoder);

    loadChunkedGLB(loader, MODEL_URL, gltf => {
      const root = gltf.scene;
      // Onshape exports Z-up; Three.js is Y-up.
      root.rotation.x = -Math.PI / 2;
      // Black and white: flatten every material to its luminance.
      root.traverse(obj => {
        if (!obj.isMesh) return;
        for (const m of [].concat(obj.material)) {
          if (!m || !m.color) continue;
          const c = m.color;
          const l = 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b;
          c.setRGB(l, l, l);
          if (m.emissive) m.emissive.setRGB(0, 0, 0);
        }
      });
      const size = accurateBounds(root).getSize(new THREE.Vector3());
      root.scale.setScalar(3.8 / Math.max(size.x, size.y, size.z));
      root.position.sub(accurateBounds(root).getCenter(new THREE.Vector3()));
      pivot.add(root);
      status.style.opacity = '0';
    }, fraction => {
      status.textContent = `loading… ${Math.round(fraction * 100)}%`;
    }, error => {
      console.error('robot viewer:', error);
      status.textContent = 'model unavailable';
    });
  }

  resize();
  new IntersectionObserver(([entry]) => {
    const wasVisible = visible;
    visible = entry.isIntersecting;
    if (visible && !requested) { requested = true; load(); }
    if (visible && !wasVisible) requestAnimationFrame(frame);
  }, { rootMargin: '200px' }).observe(canvas);
})();
