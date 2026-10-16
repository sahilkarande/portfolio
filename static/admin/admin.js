(() => {
  "use strict";
  const csrf = document.querySelector('meta[name="csrf-token"]')?.content;

  // Mobile sidebar
  const sidebar = document.querySelector(".sidebar");
  document.querySelectorAll("[data-menu-toggle]").forEach((btn) =>
    btn.addEventListener("click", () => sidebar?.classList.toggle("open"))
  );

  // Confirm destructive actions
  document.querySelectorAll("form[data-confirm]").forEach((form) =>
    form.addEventListener("submit", (e) => {
      if (!confirm(form.dataset.confirm)) e.preventDefault();
    })
  );

  // Flash messages: dismiss button + auto-hide success
  document.querySelectorAll(".flash").forEach((el) => {
    el.querySelector("button")?.addEventListener("click", () => el.remove());
    if (el.classList.contains("flash--success")) {
      setTimeout(() => { el.style.opacity = "0"; setTimeout(() => el.remove(), 300); }, 5000);
    }
  });

  // Live table filter
  const search = document.querySelector("[data-table-search]");
  if (search) {
    const rows = document.querySelectorAll("[data-row]");
    search.addEventListener("input", () => {
      const q = search.value.trim().toLowerCase();
      rows.forEach((row) => { row.hidden = q && !row.textContent.toLowerCase().includes(q); });
    });
  }

  // Publish toggle without page reload
  document.querySelectorAll("form[data-toggle]").forEach((form) =>
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const btn = form.querySelector("button");
      btn.disabled = true;
      try {
        const res = await fetch(form.action, {
          method: "POST", headers: { "X-CSRFToken": csrf, Accept: "application/json" },
        });
        if (!res.ok) throw new Error(res.status);
        const { published } = await res.json();
        btn.classList.toggle("on", published);
        btn.textContent = published ? "Visible" : "Hidden";
        form.closest("tr")?.classList.toggle("is-hidden", !published);
      } catch {
        form.submit();
      } finally {
        btn.disabled = false;
      }
    })
  );

  // Drag-and-drop reordering
  const tbody = document.querySelector("[data-sortable]");
  if (tbody && window.Sortable) {
    const status = document.querySelector("[data-sort-status]");
    Sortable.create(tbody, {
      handle: ".cell-handle",
      animation: 150,
      ghostClass: "sortable-ghost",
      onEnd: async () => {
        const ids = [...tbody.querySelectorAll("[data-row]")].map((r) => Number(r.dataset.id));
        if (status) status.textContent = "Saving order…";
        const res = await fetch(tbody.dataset.sortable, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
          body: JSON.stringify({ ids }),
        });
        if (status) status.textContent = res.ok ? "Order saved ✓" : "Couldn't save order — reload and retry";
      },
    });
  }

  // Preview chosen image before upload
  document.querySelectorAll(".upload input[type=file]").forEach((input) =>
    input.addEventListener("change", () => {
      const file = input.files[0];
      if (!file || !file.type.startsWith("image/")) return;
      let img = input.closest(".upload").querySelector("img.upload__preview");
      if (!img) {
        img = document.createElement("img");
        img.className = "upload__preview";
        img.alt = "Preview";
        input.closest(".upload").prepend(img);
      }
      img.src = URL.createObjectURL(file);
    })
  );
})();

// Analytics column chart tooltip (values via textContent; never innerHTML with data)
document.querySelectorAll("[data-chart]").forEach((chart) => {
  const tip = chart.querySelector(".chart__tip");
  const row = (keyClass, value, label) => {
    const div = document.createElement("div");
    div.className = "tip-row";
    const key = document.createElement("span");
    key.className = `tip-key ${keyClass}`;
    const b = document.createElement("b");
    b.textContent = value;
    const span = document.createElement("span");
    span.textContent = label;
    div.append(key, b, span);
    return div;
  };
  const show = (hit) => {
    const date = document.createElement("div");
    date.className = "tip-date";
    date.textContent = hit.dataset.date;
    tip.replaceChildren(date, row("", hit.dataset.views, "page views"), row("tip-key--none", hit.dataset.visitors, "visitors"));
    const box = chart.getBoundingClientRect();
    const r = hit.getBoundingClientRect();
    const x = Math.min(Math.max(r.left + r.width / 2 - box.left, 80), box.width - 80);
    tip.style.left = `${x}px`;
    tip.style.top = `${r.top - box.top + 12}px`;
    tip.hidden = false;
  };
  chart.querySelectorAll(".chart__hit").forEach((hit) => {
    hit.addEventListener("mouseenter", () => show(hit));
    hit.addEventListener("focus", () => show(hit));
  });
  chart.addEventListener("mouseleave", () => { tip.hidden = true; });
  chart.addEventListener("focusout", () => { tip.hidden = true; });
});
