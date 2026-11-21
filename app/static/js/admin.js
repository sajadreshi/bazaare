// BazaarE' admin: product and category editor helpers. Plain JS, no dependencies.
(function () {
  'use strict';

  // ---------------------------------------------------------------- rich text description
  // A small editor (bold, italic, lists) over the description textarea. The server keeps
  // only those tags, so pasted styling is dropped.
  document.querySelectorAll('textarea[data-bz-rich]').forEach(function (area) {
    var wrap = document.createElement('div');
    wrap.className = 'bz-rich';
    var bar = document.createElement('div');
    bar.className = 'bz-rich__bar';
    [['bold', '<b>B</b>', 'Bold'], ['italic', '<i>I</i>', 'Italic'],
     ['insertUnorderedList', '• List', 'Bulleted list'], ['insertOrderedList', '1. List', 'Numbered list'],
     ['removeFormat', 'Clear', 'Remove formatting']].forEach(function (cmd) {
      var btn = document.createElement('button');
      btn.type = 'button';
      btn.innerHTML = cmd[1];
      btn.title = cmd[2];
      btn.addEventListener('mousedown', function (e) { e.preventDefault(); });
      btn.addEventListener('click', function () { document.execCommand(cmd[0], false, null); sync(); });
      bar.appendChild(btn);
    });
    var editor = document.createElement('div');
    editor.className = 'bz-rich__area form-control';
    editor.contentEditable = 'true';
    var html = area.value.trim();
    editor.innerHTML = html && html.charAt(0) !== '<' ? '<p>' + escapeHtml(html) + '</p>' : html;
    function sync() { area.value = editor.innerHTML; }
    editor.addEventListener('input', sync);
    editor.addEventListener('paste', function (e) {
      e.preventDefault();
      var text = (e.clipboardData || window.clipboardData).getData('text/plain');
      document.execCommand('insertText', false, text);
    });
    area.hidden = true;
    area.parentNode.insertBefore(wrap, area);
    wrap.appendChild(bar);
    wrap.appendChild(editor);
    wrap.appendChild(area);
  });

  function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // ---------------------------------------------------------------- photos manager
  document.querySelectorAll('[data-bz-photos]').forEach(function (box) {
    var name = box.getAttribute('data-name');
    var list = box.querySelector('[data-bz-photos-list]');
    var order = box.querySelector('[data-bz-photos-order]');
    var pick = box.querySelector('[data-bz-photos-pick]');
    var drop = box.querySelector('[data-bz-photos-drop]');
    var holder = box.querySelector('[data-bz-photos-files]');
    var newCount = 0;

    function refresh() {
      var tokens = [];
      list.querySelectorAll('.bz-photo').forEach(function (li, i) {
        tokens.push(li.getAttribute('data-token'));
        li.classList.toggle('is-main', i === 0);
      });
      order.value = JSON.stringify(tokens);
      box.classList.toggle('is-empty', tokens.length === 0);
    }

    function addFiles(files) {
      var images = Array.prototype.filter.call(files, function (f) { return /^image\//.test(f.type); });
      if (!images.length) return;
      // Keep these files in their own named input, so more can be added later.
      var keep = document.createElement('input');
      keep.type = 'file';
      keep.name = name + '_new';
      keep.multiple = true;
      var dt = new DataTransfer();
      images.forEach(function (f) { dt.items.add(f); });
      keep.files = dt.files;
      holder.appendChild(keep);
      images.forEach(function (file) {
        var li = document.createElement('li');
        li.className = 'bz-photo is-new';
        li.draggable = true;
        li.setAttribute('data-token', 'new:' + newCount++);
        var img = document.createElement('img');
        img.src = URL.createObjectURL(file);
        img.alt = '';
        li.appendChild(img);
        li.insertAdjacentHTML('beforeend',
          '<span class="bz-photo__badge">Main</span>' +
          '<span class="bz-photo__new">New</span>' +
          '<button type="button" class="bz-photo__btn" data-act="main" title="Make this the main photo">★</button>' +
          '<button type="button" class="bz-photo__btn" data-act="remove" title="Remove this photo">×</button>');
        list.appendChild(li);
      });
      refresh();
    }

    pick.addEventListener('change', function () { addFiles(pick.files); pick.value = ''; });
    ['dragenter', 'dragover'].forEach(function (type) {
      drop.addEventListener(type, function (e) {
        if (e.dataTransfer && Array.prototype.indexOf.call(e.dataTransfer.types, 'Files') !== -1) {
          e.preventDefault();
          drop.classList.add('is-over');
        }
      });
    });
    ['dragleave', 'drop'].forEach(function (type) {
      drop.addEventListener(type, function () { drop.classList.remove('is-over'); });
    });
    drop.addEventListener('drop', function (e) {
      if (e.dataTransfer && e.dataTransfer.files.length) {
        e.preventDefault();
        addFiles(e.dataTransfer.files);
      }
    });

    list.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-act]');
      if (!btn) return;
      var li = btn.closest('.bz-photo');
      if (btn.getAttribute('data-act') === 'main') list.insertBefore(li, list.firstChild);
      else li.remove();
      refresh();
    });
    sortable(list, '.bz-photo', refresh);
    refresh();
  });

  // ---------------------------------------------------------------- drag to reorder
  function sortable(container, selector, onChange, handle) {
    var dragging = null;
    container.addEventListener('dragstart', function (e) {
      var item = e.target.closest && e.target.closest(selector);
      if (!item || item.parentNode !== container) return;
      dragging = item;
      item.classList.add('is-dragging');
      e.dataTransfer.effectAllowed = 'move';
      e.dataTransfer.setData('text/plain', '');
    });
    container.addEventListener('dragover', function (e) {
      if (!dragging) return;
      e.preventDefault();
      var over = e.target.closest && e.target.closest(selector);
      if (!over || over === dragging || over.parentNode !== container) return;
      var rect = over.getBoundingClientRect();
      var after = container.classList.contains('bz-photos__list')
        ? e.clientX > rect.left + rect.width / 2
        : e.clientY > rect.top + rect.height / 2;
      container.insertBefore(dragging, after ? over.nextSibling : over);
    });
    container.addEventListener('dragend', function () {
      if (!dragging) return;
      dragging.classList.remove('is-dragging');
      dragging = null;
      if (onChange) onChange();
    });
    if (handle) {
      // Rows are only draggable from their grip, so text in their inputs can still be selected.
      container.addEventListener('mousedown', function (e) {
        var row = e.target.closest(selector);
        if (row) row.draggable = !!e.target.closest(handle);
      });
    }
  }

  function renumber(list) {
    Array.prototype.forEach.call(list.children, function (row, i) {
      var pos = row.querySelector('input[name$="-position"]');
      if (pos) pos.value = i;
    });
  }

  document.querySelectorAll('[data-bz-sortable]').forEach(function (list) {
    sortable(list, '.bz-row', function () { renumber(list); }, '.bz-row__grip');
  });

  // ---------------------------------------------------------------- product form
  var form = document.querySelector('[data-bz-editor]');
  if (form) {
    form.addEventListener('submit', function () {
      document.querySelectorAll('[data-bz-sortable]').forEach(renumber);
    });

    var price = form.querySelector('#price');
    var was = form.querySelector('#compare_at_price');
    var hint = form.querySelector('[data-bz-sale-hint]');
    function saleHint() {
      var p = parseFloat(price && price.value);
      var w = parseFloat(was && was.value);
      if (hint && p > 0 && w > p) {
        hint.hidden = false;
        hint.textContent = 'On sale: shoppers see $' + w.toFixed(2) + ' crossed out, ' +
          Math.round((w - p) / w * 100) + '% off.';
      } else if (hint && p > 0 && w > 0 && w <= p) {
        hint.hidden = false;
        hint.textContent = 'The compare-at price is not higher than the price, so no sale is shown.';
      } else if (hint) {
        hint.hidden = true;
      }
    }
    [price, was].forEach(function (input) { if (input) input.addEventListener('input', saleHint); });
    saleHint();

    // Show the SKU that will be created from the name while the SKU box is empty.
    var name = form.querySelector('#name');
    var sku = form.querySelector('#sku');
    if (name && sku) {
      var suggest = function () { sku.placeholder = name.value ? 'Auto: ' + skuFrom(name.value) : ''; };
      name.addEventListener('input', suggest);
      suggest();
    }
  }

  // Same rule as app.adminapp.views.sku_from_name (the server makes it unique).
  function skuFrom(text) {
    var words = text.toUpperCase().replace(/[^A-Z0-9 ]+/g, ' ').split(/\s+/).filter(Boolean);
    return ['BZ'].concat(words.slice(0, 3).map(function (w) { return w.slice(0, 4); })).join('-');
  }

  // ---------------------------------------------------------------- category form
  var catName = document.querySelector('form.admin-form #name');
  var catCode = document.querySelector('form.admin-form #code');
  if (catName && catCode && !form) {
    var address = document.querySelector('[data-bz-address] strong');
    var slug = function (text) { return text.toUpperCase().replace(/[^A-Z0-9]+/g, '-').replace(/^-|-$/g, ''); };
    var codeHint = function () {
      var auto = slug(catName.value);
      catCode.placeholder = auto ? 'Auto: ' + auto : '';
      if (address) address.textContent = slug(catCode.value || catName.value).toLowerCase();
    };
    catName.addEventListener('input', codeHint);
    catCode.addEventListener('input', codeHint);
    codeHint();
  }
})();
