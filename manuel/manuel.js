// Lot « Le Manuel Pilote, le socle » : le moteur de la page, inliné dans app/manuel/manuel.html.
// Langue et thème (mêmes clés que l'application), une section affichée à la fois (adresse #id),
// sommaire, couverture (escadre et emblème de GET /api/me), zoom des planches et des photos.
// Le zoom est celui de Field Manual (build_field_manual.py du dépôt dcs-mission-plan : ZOOM_JS),
// repris tel quel pour son geste (pincement, molette, déplacement, double toucher) et adapté
// aux planches du manuel (figure.plate) et aux photos scotchées (.taped).
(function () {
  "use strict";

  var LS_LANG = "rr_lang_v1";
  var LS_THEME = "theme_pref_v1";
  var WING_STATIC_EMBLEM = "/static/assets/img/emblem-default.png";

  function lsGet(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function lsSet(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* stockage indisponible : on continue */ } }

  // ---------- langue et thème : lus tout de suite, avant le premier affichage ----------
  var lang = (function () { var v = lsGet(LS_LANG); return (v === "fr" || v === "en") ? v : "fr"; })();
  var pref = (function () { var v = lsGet(LS_THEME); return (v === "dark" || v === "light" || v === "system") ? v : "system"; })();
  var mq = null;
  try { mq = window.matchMedia("(prefers-color-scheme: dark)"); } catch (e) { mq = null; }

  function effectiveTheme() {
    if (pref === "system") { return (mq && mq.matches) ? "dark" : "light"; }
    return pref;
  }

  var TITRES = { fr: "Manuel pilote — Squadron Ready Room", en: "Pilot’s manual — Squadron Ready Room" };

  function applyTheme() {
    document.documentElement.setAttribute("data-theme", effectiveTheme());
    var bs = document.querySelectorAll("[data-theme-pref]");
    for (var i = 0; i < bs.length; i++) {
      var on = bs[i].getAttribute("data-theme-pref") === pref;
      bs[i].classList.toggle("on", on);
      bs[i].setAttribute("aria-pressed", on ? "true" : "false");
    }
  }

  function applyLang() {
    document.documentElement.setAttribute("lang", lang);
    if (document.body) { document.body.setAttribute("lang", lang); }
    document.title = TITRES[lang];
    var retour = document.querySelector(".mb-btn[href]");
    if (retour) { retour.setAttribute("title", "Ready Room"); retour.setAttribute("aria-label", "Ready Room"); }
    var roue = document.querySelector(".mb-gear");
    if (roue) {
      var lib = lang === "en" ? "Settings" : "Réglages";
      roue.setAttribute("title", lib);
      roue.setAttribute("aria-label", lib);
    }
    var fermer = document.querySelector(".toc-x");
    if (fermer) { fermer.setAttribute("aria-label", zt("close")); fermer.setAttribute("title", zt("close")); }
    var bs = document.querySelectorAll("[data-set-lang]");
    for (var i = 0; i < bs.length; i++) {
      var on = bs[i].getAttribute("data-set-lang") === lang;
      bs[i].classList.toggle("on", on);
      bs[i].setAttribute("aria-pressed", on ? "true" : "false");
    }
    zoomRefresh();
  }

  function setLang(l) { lang = l; lsSet(LS_LANG, l); applyLang(); }
  function setPref(p) { pref = p; lsSet(LS_THEME, p); applyTheme(); }

  document.documentElement.setAttribute("data-theme", effectiveTheme());
  document.documentElement.setAttribute("lang", lang);

  // ---------- le palier de la barre : la règle de resolveLayout() d'app.js (addendum 1) ----------
  // compact < 720 ; wide >= 1440 ; large >= 1080 sauf portrait <= 1024 ; intermediate sinon.
  // Il ne gouverne que la barre ; le reste du manuel garde ses @media.
  function resolveLayout() {
    var w = window.innerWidth;
    var portrait = false;
    try { portrait = window.matchMedia("(orientation:portrait)").matches; } catch (e) { portrait = false; }
    if (w < 720) { return "compact"; }
    if (w >= 1440) { return "wide"; }
    if (w >= 1080 && !(portrait && w <= 1024)) { return "large"; }
    return "intermediate";
  }
  function applyLayout() {
    document.documentElement.setAttribute("data-layout", resolveLayout());
    var bar = document.querySelector(".mbar");
    if (bar) { document.documentElement.style.setProperty("--mbar-h", bar.offsetHeight + "px"); }
  }
  applyLayout();
  window.addEventListener("resize", applyLayout);

  if (mq) {
    var onScheme = function () { if (pref === "system") { applyTheme(); } };
    if (mq.addEventListener) { mq.addEventListener("change", onScheme); }
    else if (mq.addListener) { mq.addListener(onScheme); }
  }

  // ---------- les pages : une section à la fois ----------
  var pages = [];
  var cover = null;
  var settled = false;   // le lecteur a pris la main (défilement, toucher, touche, changement d'adresse)

  // Lot « Manuel : le bouton ? » : l'application ouvre `#vue=<id de l'écran>` ; la table `#m-vues` (vues.json, contrôlée par
  // le build) le traduit en ancre. Écran absent ou table illisible : la couverture.
  function ancreDeVue(vue) {
    try {
      var el = document.getElementById("m-vues");
      var table = JSON.parse(el ? el.textContent : "");
      var a = table && Object.prototype.hasOwnProperty.call(table, vue) ? table[vue] : "";
      return typeof a === "string" ? a : "";
    } catch (e) { return ""; }
  }

  function route() {
    var h = "";
    try { h = decodeURIComponent(String(location.hash || "").slice(1)); } catch (e) { h = ""; }
    if (h.indexOf("vue=") === 0) {
      h = ancreDeVue(h.slice(4));
      try { history.replaceState(null, "", h ? "#" + h : location.pathname + location.search); } catch (e) { /* le navigateur refuse : on continue */ }
    }
    var target = h ? document.getElementById(h) : null;
    var page = target && target.closest ? target.closest(".m-page") : null;
    if (!page) { page = cover; target = null; }
    for (var i = 0; i < pages.length; i++) { pages[i].classList.toggle("on", pages[i] === page); }
    closeToc(false);
    if (target && target !== page) {
      target.scrollIntoView();
    } else {
      window.scrollTo(0, 0);
    }
  }

  // ---------- le sommaire ----------
  var toc = null, tocBtn = null;

  function openToc() {
    if (!toc) { return; }
    toc.hidden = false;
    tocBtn.setAttribute("aria-expanded", "true");
    var x = toc.querySelector(".toc-x");
    if (x) { x.focus({ preventScroll: true }); }
  }

  function closeToc(rendreLeFocus) {
    if (!toc || toc.hidden) { return; }
    toc.hidden = true;
    tocBtn.setAttribute("aria-expanded", "false");
    if (rendreLeFocus) { tocBtn.focus({ preventScroll: true }); }
  }

  // ---------- la couverture : l'escadre et son emblème ----------
  function wingFromMe() {
    var el = document.getElementById("cv-wing");
    var emb = document.querySelector(".cv-emb");
    var logo = document.querySelector(".mb-logo");
    if (!el || !emb || typeof fetch !== "function") { return; }
    fetch("/api/me", { credentials: "same-origin", headers: { "Accept": "application/json" } })
      .then(function (r) { if (!r.ok) { throw new Error("me"); } return r.json(); })
      .then(function (me) {
        var w = (me && me.wing) || null;
        // mêmes règles que wingDesignation() et wingEmblemSrc() d'app.js
        el.textContent = (w && w.designation) ? " · " + w.designation : "";
        var src = (w && w.emblem_sha) ? "/api/wing/emblem?v=" + encodeURIComponent(w.emblem_sha) : WING_STATIC_EMBLEM;
        emb.setAttribute("src", src);
        if (logo) { logo.setAttribute("src", src); }
        chip(me);
      })
      .catch(function () { /* repli : « Ready Room » seul et l'emblème générique, déjà posés */ });
  }

  // La pastille du compte : le nom, et l'avatar comme avatarHtml() d'app.js — l'image Discord si le compte en a une,
  // sinon (ou si l'image échoue) les deux premières lettres du nom en capitales.
  function chip(me) {
    var name = me && me.name ? String(me.name) : "";
    var nom = document.querySelector(".mb-name");
    var av = document.querySelector(".mb-av");
    if (nom) { nom.textContent = name; }
    if (!av) { return; }
    var init = (name || "?").slice(0, 2).toUpperCase();
    av.textContent = init;
    if (me && me.id && me.avatar_hash) {
      var img = document.createElement("img");
      img.alt = "";
      img.referrerPolicy = "no-referrer";
      img.addEventListener("error", function () { av.textContent = init; });
      img.addEventListener("load", function () { av.textContent = ""; av.appendChild(img); });
      img.src = "https://cdn.discordapp.com/avatars/" + encodeURIComponent(me.id) + "/" + encodeURIComponent(me.avatar_hash) + ".png?size=64";
    }
  }

  // Le menu des réglages (compact, intermediate, large) : un clic ouvre, un clic à côté ou Échap ferment.
  function initReglages() {
    var g = document.querySelector(".mb-gear"), m = document.querySelector(".mb-menu");
    if (!g || !m) { return; }
    var ferme = function () { m.classList.remove("open"); g.setAttribute("aria-expanded", "false"); };
    g.addEventListener("click", function (e) {
      e.stopPropagation();
      var o = !m.classList.contains("open");
      m.classList.toggle("open", o);
      g.setAttribute("aria-expanded", o ? "true" : "false");
    });
    document.addEventListener("click", function (e) { if (!m.contains(e.target)) { ferme(); } });
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") { ferme(); } });
  }

  // ---------- le zoom (Field Manual, adapté) ----------
  var ZT = {
    fr: { open: "Agrandir", close: "Fermer", "in": "Agrandir", out: "Réduire", fit: "Ajuster" },
    en: { open: "Enlarge", close: "Close", "in": "Zoom in", out: "Zoom out", fit: "Fit" }
  };
  function zt(k) { return ZT[lang][k]; }

  var ZM_MAX = 4;          // zoom maximal, relatif à l'ajustement
  var ZM_STEP = 1.5;       // pas des boutons + et −
  var ZM_REF = 812;        // largeur de référence d'une planche (échelle --zs)
  var ZM_SIDE = 16, ZM_TOP = 60, ZM_BOTTOM = 72;   // marges réservées autour de l'ajustement

  var zm = {
    dlg: null, stage: null, box: null, opener: null, schema: false,
    natW: 1, natH: 1, fitW: 1, s: 1, x: 0, y: 0,
    ptrs: {}, drag: null, pinch: null, moved: false, lastTap: null, ghost: null
  };

  function zoomRefresh() {
    var els = document.querySelectorAll("[data-zoomable]");
    for (var i = 0; i < els.length; i++) {
      els[i].setAttribute("aria-label", zt("open"));
      els[i].setAttribute("title", zt("open"));
    }
    if (!zm.dlg) { return; }
    ["out", "in", "close"].forEach(function (k) {
      var b = zm.dlg.querySelector('[data-zm="' + k + '"]');
      if (b) { b.setAttribute("aria-label", zt(k)); b.setAttribute("title", zt(k)); }
    });
    var fit = zm.dlg.querySelector('[data-zm="fit"]');
    if (fit) { fit.textContent = zt("fit"); fit.setAttribute("aria-label", zt("fit")); fit.setAttribute("title", zt("fit")); }
  }

  function zmView() { return { w: zm.stage.clientWidth, h: zm.stage.clientHeight }; }

  function zmFitRect() {
    var v = zmView();
    return { x: ZM_SIDE, y: ZM_TOP, w: Math.max(80, v.w - 2 * ZM_SIDE), h: Math.max(80, v.h - ZM_TOP - ZM_BOTTOM) };
  }

  function zmSetWidth(w) {
    zm.box.style.width = w + "px";
    if (zm.schema) { zm.box.style.setProperty("--zs", String(w / ZM_REF)); }
  }

  function zmComputeFit() {
    var f = zmFitRect(), aspect;
    if (zm.schema) {
      zmSetWidth(1000);
      aspect = zm.box.offsetHeight / 1000;
    } else {
      aspect = zm.natH / zm.natW;
    }
    zm.fitW = Math.min(f.w, f.h / aspect);
  }

  function zmClamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

  function zmApply() {
    zm.s = zmClamp(zm.s, 1, ZM_MAX);
    var w = zm.fitW * zm.s;
    zmSetWidth(w);
    var h = zm.box.offsetHeight;
    var v = zmView(), f = zmFitRect();
    if (zm.s <= 1.0001) {
      zm.s = 1;
      zm.x = f.x + (f.w - w) / 2;
      zm.y = f.y + (f.h - h) / 2;
    } else {
      // plus grand que l'écran : pas de bord vide ; plus petit : entièrement visible
      zm.x = (w >= v.w) ? zmClamp(zm.x, v.w - w, 0) : zmClamp(zm.x, 0, v.w - w);
      zm.y = (h >= v.h) ? zmClamp(zm.y, v.h - h, 0) : zmClamp(zm.y, 0, v.h - h);
    }
    zm.box.style.transform = "translate3d(" + zm.x + "px," + zm.y + "px,0)";
    zm.dlg.classList.toggle("zoomed", zm.s > 1.0001);
  }

  function zmZoomAt(ns, ax, ay) {
    ns = zmClamp(ns, 1, ZM_MAX);
    if (ns === zm.s) { return; }
    var r = ns / zm.s;
    zm.x = ax - (ax - zm.x) * r;
    zm.y = ay - (ay - zm.y) * r;
    zm.s = ns;
    zmApply();
  }

  function zmZoomCenter(ns) { var v = zmView(); zmZoomAt(ns, v.w / 2, v.h / 2); }
  function zmFit() { zm.s = 1; zmApply(); }

  // Cloner une planche : identifiants uniques (marqueurs) pour que les pointes de flèche s'y affichent
  function zmCloneSchema(el) {
    var c = el.cloneNode(true);
    ["role", "tabindex", "aria-label", "title", "data-zoomable", "id"].forEach(function (a) { c.removeAttribute(a); });
    var ids = [];
    var withId = c.querySelectorAll("[id]");
    for (var k = 0; k < withId.length; k++) { ids.push(withId[k].id); }
    if (ids.length) {
      var all = c.querySelectorAll("*");
      for (var i = 0; i < all.length; i++) {
        var n = all[i];
        if (n.id) { n.id = "zm-" + n.id; }
        var attrs = n.attributes;
        for (var j = 0; j < attrs.length; j++) {
          var v = attrs[j].value;
          if (v.indexOf("url(#") === -1) { continue; }
          ids.forEach(function (id) { v = v.split("url(#" + id + ")").join("url(#zm-" + id + ")"); });
          n.setAttribute(attrs[j].name, v);
        }
      }
    }
    return c;
  }

  function zmInertAround(on) {
    var els = document.querySelectorAll(".mbar, .chemise, .m-toc");
    for (var i = 0; i < els.length; i++) { els[i].inert = on; }
  }

  function zmOpen(el) {
    zm.opener = el;
    zm.schema = el.classList.contains("plate");
    zm.box.innerHTML = "";
    zm.box.style.width = "";
    zm.box.style.removeProperty("--zs");
    var label = "", nat = null, img = null;
    if (zm.schema) {
      var svg = el.querySelector("svg");
      var ti = svg ? svg.querySelector("title") : null;
      label = ti ? ti.textContent : "";
      zm.box.appendChild(zmCloneSchema(el));
    } else {
      // une photo scotchée : l'image visible (celle du thème courant), jamais le scotch
      var imgs = el.querySelectorAll("img:not(.scotch)");
      var src = "";
      for (var i = 0; i < imgs.length; i++) {
        if (imgs[i].offsetParent !== null) { src = imgs[i].currentSrc || imgs[i].src; nat = imgs[i].naturalWidth ? [imgs[i].naturalWidth, imgs[i].naturalHeight] : null; break; }
      }
      label = "";
      img = new Image();
      img.alt = "";
      img.draggable = false;
      zm.box.appendChild(img);
      img.src = src;
    }
    zm.dlg.setAttribute("aria-label", label || zt("open"));
    zm.dlg.hidden = false;
    document.body.classList.add("zm-open");
    zmInertAround(true);
    zm.ptrs = {}; zm.drag = null; zm.pinch = null; zm.lastTap = null;
    zoomRefresh();
    var ready = function () { zmComputeFit(); zm.s = 1; zmApply(); };
    if (zm.schema) {
      ready();
    } else if (nat) {
      zm.natW = nat[0]; zm.natH = nat[1];
      ready();
    } else {
      img.onload = function () {
        zm.natW = img.naturalWidth || 1;
        zm.natH = img.naturalHeight || 1;
        if (!zm.dlg.hidden && zm.box.firstChild === img) { ready(); }
      };
      if (img.complete && img.naturalWidth) { img.onload(); }
    }
    var cb = zm.dlg.querySelector('[data-zm="close"]');
    if (cb) { cb.focus({ preventScroll: true }); }
  }

  function zmClose() {
    if (zm.dlg.hidden) { return; }
    zm.dlg.hidden = true;
    zm.box.innerHTML = "";
    zm.ptrs = {}; zm.drag = null; zm.pinch = null;
    document.body.classList.remove("zm-open");
    zmInertAround(false);
    var o = zm.opener;
    zm.opener = null;
    if (o && o.focus) { o.focus({ preventScroll: true }); }
  }

  function zmDist(a, b) { var dx = a.x - b.x, dy = a.y - b.y; return Math.sqrt(dx * dx + dy * dy); }
  function zmTwo() { var ids = Object.keys(zm.ptrs); return [zm.ptrs[ids[0]], zm.ptrs[ids[1]]]; }

  function zmStartDrag() {
    var ids = Object.keys(zm.ptrs);
    if (ids.length !== 1) { zm.drag = null; return; }
    var p = zm.ptrs[ids[0]];
    zm.drag = { px: p.x, py: p.y, x: zm.x, y: zm.y };
  }

  function zmStartPinch() {
    var pp = zmTwo();
    zm.drag = null;
    zm.pinch = { d: Math.max(1, zmDist(pp[0], pp[1])), mx: (pp[0].x + pp[1].x) / 2, my: (pp[0].y + pp[1].y) / 2, s: zm.s, x: zm.x, y: zm.y };
  }

  function zmTap(x, y, ptype) {
    var now = Date.now(), lt = zm.lastTap;
    var r = zm.box.getBoundingClientRect();
    var inside = x >= r.left && x <= r.right && y >= r.top && y <= r.bottom;
    if (lt && now - lt.t < 400 && Math.abs(x - lt.x) < 30 && Math.abs(y - lt.y) < 30) {
      zm.lastTap = null;
      zmZoomAt(zm.s > 1.0001 ? 1 : 2, x, y);
      return;
    }
    zm.lastTap = { t: now, x: x, y: y };
    if (!inside && zm.s <= 1.0001) {
      if (ptype === "touch") { zm.ghost = { t: now, x: x, y: y }; }
      zmClose();
    }
  }

  function zmOnDown(e) {
    if (e.pointerType === "mouse" && e.button !== 0) { return; }
    try { zm.stage.setPointerCapture(e.pointerId); } catch (err) { /* sans capture : on continue */ }
    zm.ptrs[e.pointerId] = { x: e.clientX, y: e.clientY };
    var n = Object.keys(zm.ptrs).length;
    if (n === 1) { zm.moved = false; zmStartDrag(); }
    else if (n === 2) { zm.moved = true; zmStartPinch(); }
  }

  function zmOnMove(e) {
    var p = zm.ptrs[e.pointerId];
    if (!p) { return; }
    p.x = e.clientX; p.y = e.clientY;
    var n = Object.keys(zm.ptrs).length;
    if (n >= 2 && zm.pinch) {
      var pp = zmTwo();
      var d = zmDist(pp[0], pp[1]);
      var mx = (pp[0].x + pp[1].x) / 2, my = (pp[0].y + pp[1].y) / 2;
      var ns = zmClamp(zm.pinch.s * d / zm.pinch.d, 1, ZM_MAX);
      var r = ns / zm.pinch.s;
      zm.s = ns;
      zm.x = mx - (zm.pinch.mx - zm.pinch.x) * r;
      zm.y = my - (zm.pinch.my - zm.pinch.y) * r;
      zmApply();
    } else if (zm.drag) {
      var dx = p.x - zm.drag.px, dy = p.y - zm.drag.py;
      if (Math.sqrt(dx * dx + dy * dy) > 6) { zm.moved = true; }
      if (zm.moved && zm.s > 1.0001) {
        zm.x = zm.drag.x + dx;
        zm.y = zm.drag.y + dy;
        zmApply();
      }
    }
  }

  function zmOnUp(e) {
    var p = zm.ptrs[e.pointerId];
    if (!p) { return; }
    delete zm.ptrs[e.pointerId];
    var n = Object.keys(zm.ptrs).length;
    if (n === 1) { zm.pinch = null; zmStartDrag(); }
    else if (n === 0) {
      zm.pinch = null; zm.drag = null;
      if (!zm.moved && e.type === "pointerup") { zmTap(e.clientX, e.clientY, e.pointerType); }
    }
  }

  function zmOnWheel(e) {
    e.preventDefault();
    var dy = e.deltaY;
    if (e.deltaMode === 1) { dy *= 16; } else if (e.deltaMode === 2) { dy *= 400; }
    var k = e.ctrlKey ? 0.01 : 0.0015;
    zmZoomAt(zm.s * Math.exp(-dy * k), e.clientX, e.clientY);
  }

  function zmOnKey(e) {
    if (!zm.dlg || zm.dlg.hidden) { return; }
    if (e.key === "Escape") { e.preventDefault(); zmClose(); return; }
    if (e.key === "Tab") {
      var f = [].slice.call(zm.dlg.querySelectorAll("button"));
      if (!f.length) { return; }
      var i = f.indexOf(document.activeElement);
      e.preventDefault();
      f[(i + (e.shiftKey ? f.length - 1 : 1)) % f.length].focus();
      return;
    }
    if (e.key === "+" || e.key === "=") { e.preventDefault(); zmZoomCenter(zm.s * ZM_STEP); }
    else if (e.key === "-") { e.preventDefault(); zmZoomCenter(zm.s / ZM_STEP); }
    else if (e.key === "0") { e.preventDefault(); zmFit(); }
    else if (zm.s > 1.0001 && e.key.indexOf("Arrow") === 0) {
      e.preventDefault();
      var step = 80;
      if (e.key === "ArrowLeft") { zm.x += step; }
      else if (e.key === "ArrowRight") { zm.x -= step; }
      else if (e.key === "ArrowUp") { zm.y += step; }
      else { zm.y -= step; }
      zmApply();
    }
  }

  function initZoom() {
    zm.dlg = document.getElementById("m-zoom");
    if (!zm.dlg) { return; }
    zm.stage = zm.dlg.querySelector(".zm-stage");
    zm.box = zm.dlg.querySelector(".zm-box");

    var cibles = document.querySelectorAll("figure.plate, .taped");
    for (var i = 0; i < cibles.length; i++) {
      (function (el) {
        el.setAttribute("role", "button");
        el.setAttribute("tabindex", "0");
        el.setAttribute("data-zoomable", "1");
        el.addEventListener("click", function (e) {
          // le toucher sur le fond qui ferme la fenêtre ne doit pas rouvrir ce qui se trouve dessous
          var g = zm.ghost;
          if (g && Date.now() - g.t < 400 && Math.abs(e.clientX - g.x) < 14 && Math.abs(e.clientY - g.y) < 14) { zm.ghost = null; return; }
          zmOpen(el);
        });
        el.addEventListener("keydown", function (e) {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); zmOpen(el); }
        });
      })(cibles[i]);
    }

    var bs = zm.dlg.querySelectorAll("[data-zm]");
    for (var j = 0; j < bs.length; j++) {
      (function (b) {
        b.addEventListener("click", function () {
          var a = b.getAttribute("data-zm");
          if (a === "close") { zmClose(); }
          else if (a === "fit") { zmFit(); }
          else if (a === "in") { zmZoomCenter(zm.s * ZM_STEP); }
          else if (a === "out") { zmZoomCenter(zm.s / ZM_STEP); }
        });
      })(bs[j]);
    }

    zm.stage.addEventListener("pointerdown", zmOnDown);
    zm.stage.addEventListener("pointermove", zmOnMove);
    zm.stage.addEventListener("pointerup", zmOnUp);
    zm.stage.addEventListener("pointercancel", zmOnUp);
    zm.stage.addEventListener("wheel", zmOnWheel, { passive: false });
    document.addEventListener("keydown", zmOnKey);
    window.addEventListener("resize", function () {
      if (zm.dlg.hidden) { return; }
      zmComputeFit();
      zmApply();
    });
    zoomRefresh();
  }

  // ---------- le départ ----------
  function init() {
    pages = [].slice.call(document.querySelectorAll(".m-page"));
    cover = document.getElementById("couverture") || pages[0];
    toc = document.getElementById("m-toc");
    tocBtn = document.getElementById("m-toc-btn");

    var bl = document.querySelectorAll("[data-set-lang]");
    for (var i = 0; i < bl.length; i++) {
      (function (b) { b.addEventListener("click", function () { setLang(b.getAttribute("data-set-lang")); }); })(bl[i]);
    }
    var bt = document.querySelectorAll("[data-theme-pref]");
    for (var k = 0; k < bt.length; k++) {
      (function (b) { b.addEventListener("click", function () { setPref(b.getAttribute("data-theme-pref")); }); })(bt[k]);
    }

    if (tocBtn && toc) {
      tocBtn.addEventListener("click", function () { if (toc.hidden) { openToc(); } else { closeToc(true); } });
      var x = toc.querySelector(".toc-x");
      if (x) { x.addEventListener("click", function () { closeToc(true); }); }
      toc.addEventListener("click", function (e) {
        var a = e.target && e.target.closest ? e.target.closest("a") : null;
        if (a) { closeToc(false); }
      });
      document.addEventListener("keydown", function (e) {
        if (e.key === "Escape" && !toc.hidden && zm.dlg && zm.dlg.hidden) { e.preventDefault(); closeToc(true); }
      });
      // un toucher hors du panneau le ferme
      document.addEventListener("pointerdown", function (e) {
        if (toc.hidden) { return; }
        var t = e.target;
        if (toc.contains(t) || tocBtn.contains(t)) { return; }
        closeToc(false);
      });
    }

    applyTheme();
    applyLang();
    applyLayout();
    initReglages();
    initZoom();
    window.addEventListener("hashchange", function () { settled = true; route(); });
    route();
    // Au chargement, le navigateur défile lui-même vers une ancre visible, et les polices qui arrivent déplacent
    // la page : on reprend l'adresse une fois la page et les polices chargées, tant que le lecteur n'a rien touché.
    ["wheel", "touchstart", "keydown", "pointerdown"].forEach(function (ev) {
      window.addEventListener(ev, function () { settled = true; }, { passive: true, once: true });
    });
    var reprendre = function () { if (!settled) { route(); } };
    window.addEventListener("load", reprendre);
    if (document.fonts && document.fonts.ready) { document.fonts.ready.then(reprendre); }
    window.addEventListener("load", applyLayout);
    if (document.fonts && document.fonts.ready) { document.fonts.ready.then(applyLayout); }
    wingFromMe();
  }

  if (document.readyState === "loading") { document.addEventListener("DOMContentLoaded", init); }
  else { init(); }
})();
