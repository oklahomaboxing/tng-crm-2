function isSmallScreen() {
  return window.innerWidth <= 768;
}

function isStandalone() {
  return window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;
}

function shouldShowDock() {
  return isSmallScreen() || isStandalone();
}

function isVisible(el) {
  if (!el) return false;
  const style = window.getComputedStyle(el);
  if (style.display === 'none' || style.visibility === 'hidden' || style.pointerEvents === 'none') return false;
  const rect = el.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0;
}

function textOf(el) {
  return (el?.innerText || el?.textContent || el?.getAttribute?.('aria-label') || '').trim().toLowerCase();
}

function firstVisible(list) {
  return list.find(isVisible) || null;
}

function findMenuTarget() {
  const selectors = [
    '[aria-label*="menu" i]',
    '[title*="menu" i]',
    '.menu-button',
    '.hamburger',
    '.nav-toggle',
    '.drawer-toggle',
    '.navbar-toggler',
    '.mobile-menu-button',
    'button'
  ];

  let candidates = [];
  selectors.forEach(sel => {
    document.querySelectorAll(sel).forEach(el => candidates.push(el));
  });

  const preferred = candidates.filter(el => {
    const t = textOf(el);
    const cls = (el.className || '').toString().toLowerCase();
    return t.includes('menu') || cls.includes('menu') || cls.includes('hamburger') || cls.includes('drawer') || cls.includes('toggle');
  });

  return firstVisible(preferred) || firstVisible(candidates);
}

function findLogoutTarget() {
  let candidates = [];

  [
    'a[href*="logout" i]',
    'button',
    'a',
    '[role="button"]'
  ].forEach(sel => {
    document.querySelectorAll(sel).forEach(el => candidates.push(el));
  });

  const preferred = candidates.filter(el => {
    const t = textOf(el);
    const href = (el.getAttribute?.('href') || '').toLowerCase();
    return t.includes('logout') || t.includes('log out') || t.includes('sign out') || href.includes('logout');
  });

  return firstVisible(preferred);
}

function goHome() {
  const homeCandidates = [
    ...document.querySelectorAll('a[href="/"]'),
    ...document.querySelectorAll('a[href="/dashboard"]'),
    ...document.querySelectorAll('a[href="/home"]')
  ].filter(isVisible);

  if (homeCandidates.length) {
    homeCandidates[0].click();
    return;
  }

  if (window.location.pathname !== '/') {
    window.location.href = '/';
  } else {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}

function clickTarget(target) {
  if (!target) return false;
  try {
    target.click();
    return true;
  } catch (e) {
    return false;
  }
}

function removeExistingDock() {
  document.querySelectorAll('.tng-ios-bottom-dock').forEach(el => el.remove());
}

function buildDock() {
  removeExistingDock();

  if (!shouldShowDock()) {
    document.body.classList.remove('tng-bottom-dock-enabled');
    return;
  }

  document.body.classList.add('tng-bottom-dock-enabled');

  const dock = document.createElement('div');
  dock.className = 'tng-ios-bottom-dock';

  dock.innerHTML = `
    <div class="tng-ios-bottom-dock-inner">
      <button type="button" class="secondary" data-action="home">Home</button>
      <button type="button" data-action="menu">Menu</button>
      <button type="button" class="ghost" data-action="logout">Logout</button>
    </div>
  `;

  dock.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-action]');
    if (!btn) return;

    const action = btn.getAttribute('data-action');

    if (action === 'home') {
      goHome();
      return;
    }

    if (action === 'menu') {
      const target = findMenuTarget();
      if (!clickTarget(target)) {
        alert('Menu button not found on this screen yet.');
      }
      return;
    }

    if (action === 'logout') {
      const target = findLogoutTarget();
      if (!clickTarget(target)) {
        alert('Logout button not found on this screen yet.');
      }
    }
  });

  document.body.appendChild(dock);
}

function startDock() {
  buildDock();

  let rebuildTimer = null;
  const queueBuild = () => {
    clearTimeout(rebuildTimer);
    rebuildTimer = setTimeout(buildDock, 150);
  };

  window.addEventListener('resize', queueBuild);
  window.addEventListener('orientationchange', queueBuild);
  window.addEventListener('pageshow', queueBuild);
  window.addEventListener('focus', queueBuild);
  window.addEventListener('hashchange', queueBuild);
  window.addEventListener('popstate', queueBuild);

  const observer = new MutationObserver(queueBuild);
  observer.observe(document.body, { childList: true, subtree: true });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', startDock);
} else {
  startDock();
}
