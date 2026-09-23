const photos = JSON.parse(document.getElementById('gallery-data').textContent);
const cards = [...document.querySelectorAll('.photo-card')];
const dialog = document.getElementById('lightbox');
const cameraSelect = document.getElementById('camera-filter');
let category = 'all';
let current = 0;

function visibleCards() { return cards.filter(card => !card.hidden); }
function applyFilters() {
  cards.forEach(card => {
    card.hidden = (category !== 'all' && card.dataset.category !== category) ||
      (cameraSelect.value !== 'all' && card.dataset.camera !== cameraSelect.value);
  });
  document.getElementById('visible-count').textContent = visibleCards().length;
}
document.querySelectorAll('.filter').forEach(button => button.addEventListener('click', () => {
  category = button.dataset.filter;
  document.querySelectorAll('.filter').forEach(other => {
    const selected = other === button;
    other.classList.toggle('active', selected);
    other.setAttribute('aria-pressed', String(selected));
  });
  applyFilters();
}));
cameraSelect.addEventListener('change', applyFilters);

function showPhoto(index) {
  current = index;
  const photo = photos[index];
  document.getElementById('lightbox-image').src = photo.src;
  document.getElementById('lightbox-image').alt = photo.alt;
  document.getElementById('lightbox-title').textContent = photo.title;
  document.getElementById('lightbox-place').textContent = photo.place;
  const shown = visibleCards();
  document.getElementById('lightbox-counter').textContent = `${shown.findIndex(card => Number(card.dataset.index) === index) + 1} / ${shown.length}`;
}
function step(direction) {
  const shown = visibleCards();
  if (!shown.length) return;
  const at = shown.findIndex(card => Number(card.dataset.index) === current);
  const next = shown[(at + direction + shown.length) % shown.length];
  showPhoto(Number(next.dataset.index));
}
cards.forEach(card => card.addEventListener('click', () => {
  showPhoto(Number(card.dataset.index));
  dialog.showModal();
}));
document.getElementById('lightbox-close').addEventListener('click', () => dialog.close());
document.getElementById('lightbox-prev').addEventListener('click', () => step(-1));
document.getElementById('lightbox-next').addEventListener('click', () => step(1));
dialog.addEventListener('click', event => { if (event.target === dialog) dialog.close(); });
document.addEventListener('keydown', event => {
  if (!dialog.open) return;
  if (event.key === 'ArrowRight') step(1);
  if (event.key === 'ArrowLeft') step(-1);
});
let touchStart = null;
dialog.addEventListener('touchstart', event => { touchStart = event.changedTouches[0].screenX; }, {passive:true});
dialog.addEventListener('touchend', event => {
  if (touchStart === null) return;
  const delta = event.changedTouches[0].screenX - touchStart;
  if (Math.abs(delta) > 55) step(delta < 0 ? 1 : -1);
  touchStart = null;
}, {passive:true});
