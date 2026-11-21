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
