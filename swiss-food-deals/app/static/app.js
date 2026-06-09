const els = {
  search: document.getElementById("search"),
  retailer: document.getElementById("retailer"),
  category: document.getElementById("category"),
  sort: document.getElementById("sort"),
  minDiscount: document.getElementById("min-discount"),
  minDiscountLabel: document.getElementById("min-discount-label"),
  refreshBtn: document.getElementById("refresh-btn"),
  deals: document.getElementById("deals"),
  count: document.getElementById("count"),
  empty: document.getElementById("empty"),
  lastRefresh: document.getElementById("last-refresh"),
  sampleBanner: document.getElementById("sample-banner"),
};

const chf = (v) =>
  new Intl.NumberFormat("fr-CH", { style: "currency", currency: "CHF" }).format(v);

async function loadStats() {
  const res = await fetch("/api/stats");
  const stats = await res.json();

  fillSelect(els.retailer, stats.retailers.map((r) => r.retailer));
  fillSelect(els.category, stats.categories);

  if (stats.last_refresh) {
    const when = new Date(stats.last_refresh.ran_at).toLocaleString("fr-CH");
    els.lastRefresh.textContent = `Dernière mise à jour : ${when} — sources : ${stats.last_refresh.sources}`;
    els.sampleBanner.hidden = stats.last_refresh.sources !== "démo";
  }
}

function fillSelect(select, values) {
  const current = select.value;
  while (select.options.length > 1) select.remove(1);
  for (const value of values) {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = value;
    select.appendChild(opt);
  }
  select.value = current;
}

async function loadDeals() {
  const params = new URLSearchParams();
  if (els.search.value) params.set("search", els.search.value);
  if (els.retailer.value) params.set("retailer", els.retailer.value);
  if (els.category.value) params.set("category", els.category.value);
  if (els.minDiscount.value > 0) params.set("min_discount", els.minDiscount.value);
  params.set("sort", els.sort.value);

  const res = await fetch(`/api/deals?${params}`);
  const { deals } = await res.json();

  els.count.textContent = `${deals.length} offre${deals.length > 1 ? "s" : ""}`;
  els.empty.hidden = deals.length > 0;
  els.deals.innerHTML = deals.map(renderCard).join("");
}

function esc(s) {
  const div = document.createElement("div");
  div.textContent = s ?? "";
  return div.innerHTML;
}

function renderCard(deal) {
  const badge =
    deal.discount_percent != null
      ? `<span class="badge">−${Math.round(deal.discount_percent)}%</span>`
      : "";
  const original = deal.original_price
    ? `<span class="original">${chf(deal.original_price)}</span>`
    : "";
  const unit = deal.unit ? `<span class="unit">/ ${esc(deal.unit)}</span>` : "";
  const link = deal.deal_url
    ? `<a href="${esc(deal.deal_url)}" target="_blank" rel="noopener">Voir l'offre →</a>`
    : "";
  return `
    <article class="deal-card">
      ${badge}
      <span class="retailer">${esc(deal.retailer)}</span>
      <h3>${esc(deal.title)}</h3>
      <span class="category">${esc(deal.category)}</span>
      <div class="prices">
        <span class="price">${chf(deal.price)}</span>
        ${original}
        ${unit}
      </div>
      ${link}
    </article>`;
}

async function forceRefresh() {
  els.refreshBtn.disabled = true;
  els.refreshBtn.textContent = "Agrégation…";
  await fetch("/api/refresh", { method: "POST" });
  // L'agrégation tourne en arrière-plan ; on attend un peu avant de recharger.
  setTimeout(async () => {
    await loadStats();
    await loadDeals();
    els.refreshBtn.disabled = false;
    els.refreshBtn.textContent = "↻ Actualiser";
  }, 4000);
}

let searchTimer;
els.search.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadDeals, 300);
});
for (const el of [els.retailer, els.category, els.sort]) {
  el.addEventListener("change", loadDeals);
}
els.minDiscount.addEventListener("input", () => {
  els.minDiscountLabel.textContent = `${els.minDiscount.value}%`;
  loadDeals();
});
els.refreshBtn.addEventListener("click", forceRefresh);

loadStats().then(loadDeals);
