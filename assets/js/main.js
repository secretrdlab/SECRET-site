// SECRET site behaviour: mobile menu, dark mode, BibTeX dialog, publication filter, search.
(function () {
  "use strict";
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  // Mobile menu
  var toggle = $(".nav-toggle"), menu = $("#nav-menu");
  if (toggle && menu) {
    toggle.addEventListener("click", function () {
      var open = menu.classList.toggle("open");
      toggle.setAttribute("aria-expanded", open);
    });
    $$("a", menu).forEach(function (a) { a.addEventListener("click", function () { menu.classList.remove("open"); }); });
  }

  // Cite dialog
  var dlg = $("#cite-dialog");
  if (dlg) {
    var code = $("#cite-code"), dl = $("#cite-download"), copyBtn = $("#cite-copy");
    document.addEventListener("click", function (ev) {
      var btn = ev.target.closest(".cite-btn");
      if (!btn) return;
      var tpl = document.getElementById("bib-" + btn.dataset.key);
      code.textContent = tpl ? (tpl.content ? tpl.content.textContent : tpl.textContent).trim() : "";
      dl.href = btn.dataset.bib;
      dl.setAttribute("download", btn.dataset.key + ".bib");
      copyBtn.querySelector("span").textContent = "Copy";
      if (dlg.showModal) dlg.showModal(); else dlg.setAttribute("open", "");
    });
    $$("[data-close]", dlg).forEach(function (b) { b.addEventListener("click", function () { dlg.close(); }); });
    dlg.addEventListener("click", function (ev) { if (ev.target === dlg) dlg.close(); });
    copyBtn.addEventListener("click", function () {
      var txt = code.textContent, label = copyBtn.querySelector("span");
      var done = function () { label.textContent = "Copied!"; };
      if (navigator.clipboard && window.isSecureContext) {
        navigator.clipboard.writeText(txt).then(done, fallback);
      } else { fallback(); }
      function fallback() {
        var r = document.createRange(); r.selectNodeContents(code);
        var s = getSelection(); s.removeAllRanges(); s.addRange(r);
        try { document.execCommand("copy"); done(); } catch (e) { label.textContent = "Press Ctrl+C"; }
      }
    });
  }

  // Publication filter
  var q = $("#pub-q"), yearSel = $("#pub-year"), typeSel = $("#pub-type");
  if (q) {
    var pubs = $$(".pub-year .pub"), groups = $$(".pub-year"), shown = $("#pub-shown");
    var apply = function () {
      var terms = q.value.toLowerCase().split(/\s+/).filter(Boolean);
      var y = yearSel.value, t = typeSel.value, n = 0;
      pubs.forEach(function (p) {
        var ok = (!y || p.dataset.year === y) && (!t || p.dataset.type === t) &&
          terms.every(function (w) { return p.dataset.search.indexOf(w) !== -1; });
        p.classList.toggle("hidden", !ok);
        if (ok) n++;
      });
      groups.forEach(function (g) { g.classList.toggle("hidden", !g.querySelector(".pub:not(.hidden)")); });
      shown.textContent = n;
    };
    [q, yearSel, typeSel].forEach(function (el) { el.addEventListener("input", apply); });
  }

  // Site search
  var sq = $("#search-q");
  if (sq) {
    var results = $("#search-results"), status = $("#search-status"), index = null;
    var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
    var run = function () {
      if (!index) return;
      var terms = sq.value.toLowerCase().split(/\s+/).filter(Boolean);
      if (!terms.length) { results.innerHTML = ""; status.textContent = ""; return; }
      var hits = index.filter(function (it) {
        var hay = (it.t + " " + it.x + " " + it.k).toLowerCase();
        return terms.every(function (w) { return hay.indexOf(w) !== -1; });
      }).slice(0, 50);
      status.textContent = hits.length + (hits.length === 50 ? "+" : "") + " result(s)";
      results.innerHTML = hits.map(function (h) {
        return '<li><a href="' + esc(h.u) + '">' + esc(h.t) + '</a><span class="meta">' + esc(h.k) + "</span></li>";
      }).join("");
    };
    fetch(sq.dataset.index).then(function (r) { return r.json(); }).then(function (d) { index = d; run(); });
    sq.addEventListener("input", run);
    var params = new URLSearchParams(location.search);
    if (params.get("q")) sq.value = params.get("q");
  }
})();
