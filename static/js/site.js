(() => {
  "use strict";
  const root = document.documentElement;
  root.classList.remove("no-js");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ---- Mobile navigation
  const toggle = document.querySelector(".nav__toggle");
  const setNav = (open) => {
    document.body.classList.toggle("nav-open", open);
    toggle?.setAttribute("aria-expanded", String(open));
  };
  toggle?.addEventListener("click", () => setNav(!document.body.classList.contains("nav-open")));
  document.querySelectorAll(".nav__links a").forEach((a) => a.addEventListener("click", () => setNav(false)));
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") setNav(false); });
  window.matchMedia("(min-width: 1021px)").addEventListener("change", (e) => { if (e.matches) setNav(false); });

  // ---- Reveal on scroll
  const reveals = document.querySelectorAll(".reveal");
  if (!reduceMotion && "IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          io.unobserve(entry.target);
        }
      });
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    reveals.forEach((el) => {
      el.style.transitionDelay = `${Math.min(Number(el.dataset.delay) || 0, 600)}ms`;
      io.observe(el);
    });
  } else {
    reveals.forEach((el) => el.classList.add("is-visible"));
  }

  // ---- Filterable grids: [data-filterable] wraps buttons [data-filter], an optional
  //      search input [data-filter-search], items [data-item] (data-category, data-search),
  //      a count [data-filter-count] and an empty state [data-filter-empty].
  document.querySelectorAll("[data-filterable]").forEach((scope) => {
    const buttons = scope.querySelectorAll("[data-filter]");
    const search = scope.querySelector("[data-filter-search]");
    const items = scope.querySelectorAll("[data-item]");
    const count = scope.querySelector("[data-filter-count]");
    const empty = scope.querySelector("[data-filter-empty]");
    let category = "all";

    const apply = () => {
      const q = (search?.value || "").trim().toLowerCase();
      let shown = 0;
      items.forEach((item) => {
        const okCat = category === "all" || item.dataset.category === category;
        const okText = !q || (item.dataset.search || item.textContent.toLowerCase()).includes(q);
        const visible = okCat && okText;
        item.hidden = !visible;
        if (visible) { shown++; item.classList.add("is-visible"); }
      });
      if (count) count.textContent = String(shown);
      if (empty) empty.hidden = shown !== 0;
    };

    buttons.forEach((btn) => btn.addEventListener("click", () => {
      category = btn.dataset.filter;
      buttons.forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
      apply();
    }));
    search?.addEventListener("input", apply);
  });

  // ---- Spider-sense: occasional glitch on headings marked [data-autoglitch]
  if (!reduceMotion) {
    const glitchers = document.querySelectorAll("[data-autoglitch]");
    const fire = () => {
      const el = glitchers[Math.floor(Math.random() * glitchers.length)];
      if (el) {
        el.classList.add("is-glitching");
        setTimeout(() => el.classList.remove("is-glitching"), 900);
      }
      setTimeout(fire, 4000 + Math.random() * 5000);
    };
    if (glitchers.length) setTimeout(fire, 1800);
  }
})();

// ---- Outbound click analytics (first-party, no cookies). Elements opt in with data-track.
document.addEventListener("click", (e) => {
  const el = e.target.closest("[data-track]");
  if (!el || !navigator.sendBeacon) return;
  const payload = JSON.stringify({ e: el.dataset.track, l: el.dataset.trackLabel || "", p: location.pathname });
  navigator.sendBeacon("/t", new Blob([payload], { type: "application/json" }));
});
