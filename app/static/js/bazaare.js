// Header: mobile menu panel and search bar toggles.
(function () {
  var menuBtn = document.querySelector('[data-bz-menu-toggle]');
  var nav = document.getElementById('bz-menu');
  if (menuBtn && nav) {
    menuBtn.addEventListener('click', function () {
      var open = nav.classList.toggle('is-open');
      menuBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      document.body.classList.toggle('bz-menu-open', open);
    });
  }
  var searchBtn = document.querySelector('[data-bz-search-toggle]');
  var search = document.querySelector('[data-bz-search]');
  if (searchBtn && search) {
    searchBtn.addEventListener('click', function (event) {
      event.preventDefault();
      search.hidden = !search.hidden;
      if (!search.hidden) search.querySelector('input').focus();
    });
  }
  // Product options: show the chosen option's price (and its photo, if it has one).
  document.querySelectorAll('.bz-options input[name="size"]').forEach(function (radio) {
    radio.addEventListener('change', function () {
      var price = document.querySelector('[data-bz-price]');
      if (price && radio.dataset.price) price.textContent = '$' + radio.dataset.price;
      var main = document.getElementById('productImage');
      if (main && radio.dataset.image) main.src = radio.dataset.image;
    });
  });
  // Bag and checkout: changing an option or delivery method saves it straight away.
  document.querySelectorAll('[data-bz-autosubmit]').forEach(function (input) {
    input.addEventListener('change', function () {
      if (input.form) {
        input.form.classList.add('is-busy');
        input.form.submit();
      }
    });
  });
  // "Added to your bag" panel: slides in after adding; closes on ×, the backdrop, Continue or Escape.
  var drawer = document.querySelector('[data-bz-drawer]');
  if (drawer) {
    var panel = drawer.querySelector('.bz-drawer__panel');
    var opener = document.activeElement;
    // Locking the page scroll hides the scrollbar, which would shift the page sideways;
    // pad the page by the scrollbar's width while the panel is open so nothing moves.
    var lockScroll = function () {
      var gap = window.innerWidth - document.documentElement.clientWidth;
      if (gap > 0) {
        document.body.style.paddingRight = gap + 'px';
        document.querySelectorAll('.bz-header').forEach(function (h) { h.style.paddingRight = gap + 'px'; });
      }
      document.documentElement.classList.add('bz-drawer-open');
    };
    var unlockScroll = function () {
      document.documentElement.classList.remove('bz-drawer-open');
      document.body.style.paddingRight = '';
      document.querySelectorAll('.bz-header').forEach(function (h) { h.style.paddingRight = ''; });
    };
    var close = function () {
      drawer.classList.remove('is-open');
      unlockScroll();
      setTimeout(function () { drawer.hidden = true; }, 250);
      if (opener && opener.focus) opener.focus();
    };
    setTimeout(function () {
      drawer.classList.add('is-open');
      lockScroll();
      panel.focus({ preventScroll: true });
    }, 30);
    drawer.querySelectorAll('[data-bz-drawer-close]').forEach(function (el) { el.addEventListener('click', close); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !drawer.hidden) close(); });
    // The add-to-bag form posted to this page; don't re-post it on refresh.
    if (window.history && history.replaceState) history.replaceState(null, '', location.href);
  }
  // Photos come from the image host (Cloudflare R2). If one fails to load, try once more
  // after a moment, then show a neutral placeholder instead of a broken image.
  function photoFallback(img) {
    if (img.dataset.bzRetried) {
      img.classList.add('is-missing');
      img.src = img.dataset.bzPlaceholder || '/static/images/default.jpg';
      return;
    }
    img.dataset.bzRetried = '1';
    var src = img.currentSrc || img.src;
    setTimeout(function () { img.src = src + (src.indexOf('?') === -1 ? '?' : '&') + 'retry=1'; }, 1500);
  }
  document.querySelectorAll('img').forEach(function (img) {
    if (img.src.indexOf('/static/') !== -1) return;
    if (img.complete && img.naturalWidth === 0 && img.src) photoFallback(img);
    img.addEventListener('error', function () { if (!img.classList.contains('is-missing')) photoFallback(img); });
  });
  // Product gallery: show the full image when a thumbnail is clicked.
  document.querySelectorAll('[data-bz-thumb]').forEach(function (thumb) {
    thumb.addEventListener('click', function () {
      var main = document.getElementById('productImage');
      if (main) main.src = thumb.getAttribute('data-full');
      document.querySelectorAll('[data-bz-thumb]').forEach(function (t) { t.classList.remove('is-active'); });
      thumb.classList.add('is-active');
    });
  });
})();
