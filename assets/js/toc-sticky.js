// Quarto (under theme: none) renders the page title block, TOC, and
// article content as flat siblings of <main id="main">, with no wrapper
// to hang layout on:
//
//   <main id="main">
//     <header class="quarto-title-block"><h1 class="title">...</h1></header>
//     <nav id="TOC">...</nav>
//     <h2>...</h2><p>...</p>...
//   </main>
//
// This does two structural things about that, on every inner page:
//
// 1. Gives the title block Bootstrap's own `.container` class — the
//    same class the custom template's other sections already use for
//    left/right padding and a centered max-width — instead of leaving
//    every .qmd file to remember `::: {.container}` by hand (some did,
//    some didn't, which is what caused the title to sit flush left
//    while the body below it was indented, or vice versa).
//
// 2. Regroups <nav id="TOC"> plus everything after it into a single
//    flex row, and gives THAT row the same `.container` class, so the
//    TOC+content row lines up with the title above at exactly the same
//    left edge and max-width — one shared class, one source of truth,
//    instead of per-page padding that has to be kept in sync by hand.
//    (The inner content div itself stays unpadded; the row it's part
//    of already supplies the container's padding.)
//
//    <div class="quarto-toc-row container">
//      <nav id="TOC">...</nav>
//      <div class="quarto-inner-content">...</div>
//    </div>
//
//    A floated TOC and the content beneath it disagree about column
//    height once you scroll past the float's own (short) height, so
//    content ends up running underneath a sticky TOC — a real flex
//    row avoids that.
//
// 3. Builds "page-intro" cards and inserts them into <nav id="TOC">,
//    above the "On this page" heading. Two sources, both optional,
//    both can be present at once:
//
//    a) content/sidebar_nav.yml — a category's "blurb" and/or "image"
//       field applies automatically to every page reached through that
//       category (see scripts/build_sidebar_nav.py, which embeds a
//       page-href -> ordered [{label, blurb, image}, ...] map as JSON
//       right after the nav include, id="category-intros"). A page
//       nested under several blurb/image-bearing categories gets all
//       of them, outermost category first. This is the normal way to
//       give a whole section of the site (e.g. everything under
//       "Science") some standing context — and optionally a small
//       image — when there's no dedicated landing page for it yet —
//       set once in the YAML, not per page. "image" is independent of
//       "blurb": a category can set either, both, or neither.
//
//    b) a hand-authored ::: {.page-intro} div as the first block of a
//       specific page's body, for one-off context beyond (or instead
//       of) its category's blurb — including its own image, just an
//       ordinary markdown image given the .page-intro-img class so it
//       gets the same small/rounded treatment as one from the YAML:
//
//         ::: {.page-intro}
//         ![](path/to/small-image.jpg){.page-intro-img}
//
//         **One-off note**
//
//         Something true of this page specifically.
//         :::
//
//       (Use bold text for the label, not a heading — a real heading
//       there would also get picked up by Quarto's own TOC-from-
//       headings scan and show up as a confusing entry pointing at
//       itself.) If both (a) and (b) apply, (a)'s cards come first
//       and (b)'s comes last, right above "On this page".
//
// See quarto-overrides.css for the accompanying layout rules.
(function () {
  function buildCard(label, blurb, image) {
    var div = document.createElement("div");
    div.className = "page-intro";
    if (image) {
      var img = document.createElement("img");
      img.className = "page-intro-img";
      img.src = image;
      img.alt = "";
      div.appendChild(img);
    }
    if (label) {
      var strong = document.createElement("strong");
      strong.textContent = label;
      div.appendChild(strong);
    }
    if (blurb) {
      var p = document.createElement("p");
      p.textContent = blurb;
      div.appendChild(p);
    }
    return div;
  }

  function lookupIntroEntries(map) {
    var path = window.location.pathname;

    // Exact match: how this resolves when the site is actually served
    // from its domain root (GitHub Pages, `quarto preview`, ...) —
    // pathname is genuinely "/science/nonlin_causality.html".
    if (Object.prototype.hasOwnProperty.call(map, path)) {
      return map[path];
    }

    // Fallback: opening the rendered file directly (file://.../_site/
    // science/nonlin_causality.html) makes pathname the full local
    // filesystem path, which will never equal a map key — but it does
    // always END with one, since the map key is just the page's path
    // relative to the site root. Match on that instead. (Quarto itself
    // rewrites the asset/script <link>/<script> tags in this same
    // include to page-relative paths at build time, which is why
    // everything else on the page still looks right under file:// —
    // this map can't get the same treatment, since matching it happens
    // at runtime in the browser, against a URL Quarto never sees.)
    for (var key in map) {
      if (
        Object.prototype.hasOwnProperty.call(map, key) &&
        path.length >= key.length &&
        path.slice(path.length - key.length) === key
      ) {
        return map[key];
      }
    }

    return null;
  }

  function categoryIntroCards() {
    var script = document.getElementById("category-intros");
    if (!script) return [];
    var map;
    try {
      map = JSON.parse(script.textContent || "{}");
    } catch (e) {
      return [];
    }
    var entries = lookupIntroEntries(map);
    if (!entries || !entries.length) return [];
    return entries.map(function (entry) {
      return buildCard(entry.label, entry.blurb, entry.image);
    });
  }

  function restructure() {
    var main = document.getElementById("main");
    if (!main) return;

    main.querySelectorAll(":scope > header.quarto-title-block").forEach(
      function (title) {
        title.classList.add("container");
      }
    );

    var toc = main.querySelector(":scope > nav#TOC");
    if (!toc) return; // page has no TOC (toc: false) — nothing more to do

    var content = document.createElement("div");
    content.className = "quarto-inner-content";

    var node = toc.nextSibling;
    while (node) {
      var next = node.nextSibling;
      content.appendChild(node);
      node = next;
    }

    var introNodes = categoryIntroCards();

    var manualIntro = content.querySelector(":scope > .page-intro");
    if (manualIntro) {
      content.removeChild(manualIntro);
      introNodes.push(manualIntro);
    }

    if (introNodes.length) {
      var fragment = document.createDocumentFragment();
      introNodes.forEach(function (introNode) {
        fragment.appendChild(introNode);
      });
      toc.insertBefore(fragment, toc.firstChild);
    }

    var row = document.createElement("div");
    row.className = "quarto-toc-row container";

    main.removeChild(toc);
    row.appendChild(toc);
    row.appendChild(content);
    main.appendChild(row);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", restructure);
  } else {
    restructure();
  }
})();
