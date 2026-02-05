// -----------------------
// Filter + section toggle
// -----------------------
const q = document.getElementById('q');
const cards = Array.from(document.querySelectorAll('.card'));
const sections = Array.from(document.querySelectorAll('.section'));

// Track collapsed state by section id
const collapsed = new Map(); // secId -> bool

function isCardMatch(card, query) {
  const name = card.querySelector('h2').innerText.toLowerCase();
  return (!query || name.includes(query));
}

function applyFilterAndCollapse() {
  if (!q) return;
  const s = q.value.toLowerCase().trim();

  // 1) show/hide cards based on search + collapsed state
  for (const card of cards) {
    const secId = card.getAttribute('data-section');
    const match = isCardMatch(card, s);
    const isCollapsed = collapsed.get(secId) === true;
    const show = match && !isCollapsed;
    card.style.display = show ? '' : 'none';
  }

  // 2) show/hide section headers if they have any matching cards at all
  for (const sec of sections) {
    const secId = sec.getAttribute('data-section');
    const anyMatch = cards.some(c => c.getAttribute('data-section') === secId && isCardMatch(c, s));
    sec.style.display = anyMatch ? '' : 'none';

    const isCollapsed = collapsed.get(secId) === true;
    sec.setAttribute('aria-expanded', isCollapsed ? 'false' : 'true');
  }
}

// click to toggle section
for (const sec of sections) {
  sec.addEventListener('click', () => {
    const secId = sec.getAttribute('data-section');
    collapsed.set(secId, !(collapsed.get(secId) === true)); // toggle
    applyFilterAndCollapse();
  });
}

// ------------
// Tabs (cards)
// ------------
function setActiveTab(btn) {
  const tabs = btn.closest('.tabs');
  const card = btn.closest('.card');
  if (!tabs || !card) return;

  const buttons = Array.from(tabs.querySelectorAll('.tab-btn'));

  for (const b of buttons) {
    const isActive = (b === btn);
    b.classList.toggle('is-active', isActive);
    b.setAttribute('aria-selected', isActive ? 'true' : 'false');
    b.setAttribute('tabindex', isActive ? '0' : '-1');

    const panelId = b.getAttribute('aria-controls');
    if (!panelId) continue;

    const panel = card.querySelector('#' + CSS.escape(panelId));
    if (panel) panel.hidden = !isActive;
  }
}

function initTabsInCard(card) {
  const tabsList = Array.from(card.querySelectorAll('.tabs'));
  for (const tabs of tabsList) {
    const buttons = Array.from(tabs.querySelectorAll('.tab-btn'));
    for (const btn of buttons) {
      btn.addEventListener('click', (ev) => {
        ev.preventDefault();
        ev.stopPropagation(); // don't trigger section toggle
        setActiveTab(btn);
      });
    }
    const active =
      tabs.querySelector('.tab-btn[aria-controls^="panel-overview-"]') ||
      tabs.querySelector('.tab-btn.is-active') ||
      buttons[0];
    if (active) setActiveTab(active);
  }
}

function initCardInteractivity(card) {
  initTabsInCard(card);
}

const cardsAll = Array.from(document.querySelectorAll('.card'));
for (const card of cardsAll) initCardInteractivity(card);

if (q) {
  q.addEventListener('input', applyFilterAndCollapse);
  applyFilterAndCollapse();
}

  // -----------------------
  
  // Variant selector (param sets)
  // -----------------------
  function parseVariants(card) {
    const script = card.querySelector('script.variants-json');
    const raw = script ? script.textContent : '[]';
    try {
      return JSON.parse(raw) || [];
    } catch (e) {
      return [];
    }
  }

  function updateVariant(card, variantId, opts) {
    const focusInfo = !!(opts && opts.focusInfo);
    const variants = parseVariants(card);
    if (!variants.length) return;

    const v = variants.find(x => x.id === variantId) || variants[0];

    const preview = card.querySelector('.variant-preview');
    if (preview && v.preview_html) preview.innerHTML = v.preview_html;

    const info = card.querySelector('.variant-info');
    if (info && v.tabs_html) info.innerHTML = v.tabs_html;

    initCardInteractivity(card);
    if (focusInfo) {
      const infoTab = card.querySelector('.tab-btn[aria-controls^="panel-info-"]');
      if (infoTab) setActiveTab(infoTab);
    }

    const gdsBtn = card.querySelector('.variant-gds');
    if (gdsBtn) {
      if (v.gds_href) {
        gdsBtn.classList.remove('btn-disabled');
        gdsBtn.setAttribute('href', v.gds_href);
        gdsBtn.setAttribute('download', '');
        gdsBtn.textContent = 'Download GDS';
      } else {
        gdsBtn.classList.add('btn-disabled');
        gdsBtn.removeAttribute('href');
        gdsBtn.textContent = 'GDS unavailable';
      }
    }

    const statusPill = card.querySelector('.status-pill');
    if (statusPill) {
      const status = (v.status || 'ok').toLowerCase();
      statusPill.classList.remove('ok', 'fail');
      statusPill.classList.add(status === 'ok' ? 'ok' : 'fail');
      statusPill.textContent = 'RENDER ' + status.toUpperCase();
    }
  }

  const cardsWithVariants = Array.from(document.querySelectorAll('.card'));
  for (const card of cardsWithVariants) {
    const select = card.querySelector('.variant-select');
    const variants = parseVariants(card);
    if (!variants.length) continue;

    const initialId = select ? select.value : variants[0].id;
    updateVariant(card, initialId, { focusInfo: false });

    if (select) {
      select.addEventListener('change', () => updateVariant(card, select.value, { focusInfo: true }));
    }
  }

// -----------------------
// SHA lock overlay (gate)
// -----------------------
// Read build-time config from <body data-*>.
const body = document.body;
const LOCK_ENABLED = (body.dataset.lockEnabled || 'false') === 'true';
const LOCK_SHA256_HEX = body.dataset.lockSha256Hex || '';
const LOCK_STORAGE_KEY = body.dataset.lockStorageKey || 'my_pdk_cells_unlock_v1';

function hexFromBuf(buf) {
  const bytes = new Uint8Array(buf);
  let hex = '';
  for (let i = 0; i < bytes.length; i++) {
    hex += bytes[i].toString(16).padStart(2, '0');
  }
  return hex;
}

async function sha256Hex(text) {
  const enc = new TextEncoder();
  const data = enc.encode(text);
  const digest = await crypto.subtle.digest('SHA-256', data);
  return hexFromBuf(digest);
}

function setLocked(on) {
  document.body.classList.toggle('locked', !!on);
  const ov = document.getElementById('lockOverlay');
  if (ov) ov.setAttribute('aria-hidden', on ? 'false' : 'true');
}

function rememberUnlock(token) {
  try {
    localStorage.setItem(LOCK_STORAGE_KEY, token);
  } catch (e) {}
}

function hasUnlockToken() {
  try {
    const t = localStorage.getItem(LOCK_STORAGE_KEY) || '';
    return (t && t === LOCK_SHA256_HEX);
  } catch (e) {
    return false;
  }
}

async function tryUnlock(pass) {
  const err = document.getElementById('lockErr');
  if (err) err.textContent = '';

  if (!pass || pass.trim().length === 0) {
    if (err) err.textContent = 'Enter a key.';
    return false;
  }
  if (!crypto || !crypto.subtle) {
    if (err) err.textContent = 'Browser crypto unavailable.';
    return false;
  }
  const h = await sha256Hex(pass.trim());
  if (h === LOCK_SHA256_HEX) {
    rememberUnlock(LOCK_SHA256_HEX);
    setLocked(false);
    return true;
  }
  if (err) err.textContent = 'Incorrect key.';
  return false;
}

function initLock() {
  if (!LOCK_ENABLED) {
    setLocked(false);
    return;
  }

  // If already unlocked on this browser, skip prompt.
  if (hasUnlockToken()) {
    setLocked(false);
    return;
  }

  setLocked(true);

  const input = document.getElementById('lockInput');
  const btn = document.getElementById('lockBtn');

  async function go() {
    const pass = input ? input.value : '';
    await tryUnlock(pass);
    if (input) input.value = '';
    if (input) input.focus();
  }

  if (btn) btn.addEventListener('click', (e) => {
    e.preventDefault();
    go();
  });

  if (input) {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        go();
      }
    });
    input.focus();
  }
}

// -----------------------
// Spy sidebar (hover + scroll reveal)
// -----------------------
function initSpy() {
  const sectionsLocal = Array.from(document.querySelectorAll('.section'));
  const cardsLocal = Array.from(document.querySelectorAll('.card'));
  if (!sectionsLocal.length || !cardsLocal.length) return;

  // 1) ensure sidebar container (spyNav)
  let bar = document.getElementById('spyNav');
  if (!bar) {
    bar = document.createElement('nav');
    bar.id = 'spyNav';
    bar.setAttribute('aria-label', 'Section navigator');
    bar.innerHTML = `
      <div class="spy-inner">
        <div class="spy-handle" role="button" aria-label="Toggle sections"></div>
        <div class="spy-list">
          <div class="spy-head mono">Sections</div>
          <div id="spyList"></div>
        </div>
      </div>
    `;
    document.body.appendChild(bar);
  }

  const listEl = bar.querySelector('#spyList');
  const handle = bar.querySelector('.spy-handle');
  if (!listEl || !handle) return;

  // Build items: use section buttons' data-section + title text
  const items = [];
  listEl.innerHTML = '';
  for (const sec of sectionsLocal) {
    const secId = sec.getAttribute('data-section') || '';
    const titleEl = sec.querySelector('.section-title');
    const title = (titleEl ? titleEl.textContent : sec.textContent).trim();

    const link = document.createElement('a');
    link.className = 'spy-item';
    link.href = '#' + secId;
    link.textContent = title || secId || 'Section';
    link.dataset.section = secId;

    link.addEventListener('click', (e) => {
      e.preventDefault();

      if (sec.getAttribute('aria-expanded') === 'false') {
        sec.click();
      }

      sec.scrollIntoView({ behavior: 'smooth', block: 'start' });
      showSpyPeek();
    });

    listEl.appendChild(link);
    items.push(link);
  }

  function setActiveSection(secId) {
    for (const it of items) {
      it.classList.toggle('active', it.dataset.section === secId);
    }
  }

  // 2) reveal behavior: stay open by default, only toggle on handle click
  let isPinned = true;

  function showSpy() {
    if (document.body.classList.contains('locked')) return;
    document.body.classList.add('spy-open');
  }

  function hideSpy() {
    document.body.classList.remove('spy-open');
  }

  handle.addEventListener('click', (e) => {
    e.preventDefault();
    isPinned = !isPinned;
    if (isPinned) {
      showSpy();
    } else {
      hideSpy();
    }
  });

  // 3) IntersectionObserver: highlight current section
  const obs = new IntersectionObserver((entries) => {
    const visible = entries
      .filter(e => e.isIntersecting)
      .sort((a,b) => Math.abs(a.boundingClientRect.top) - Math.abs(b.boundingClientRect.top));

    if (visible.length) {
      const sec = visible[0].target;
      const secId = sec.getAttribute('data-section') || '';
      setActiveSection(secId);
    }
  }, {
    root: null,
    threshold: 0.15,
    rootMargin: '-20% 0px -70% 0px'
  });

  for (const sec of sectionsLocal) obs.observe(sec);

  // default: open
  showSpy();
}

initLock();
initSpy();
