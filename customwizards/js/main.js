const PRODUCT_ICONS = {
  candle: '<path d="M18 10 C18 6 30 6 30 10 C30 16 34 20 30 26 L30 38 L18 38 L18 26 C14 20 18 16 18 10 Z" stroke-linejoin="round"/><line x1="14" y1="40" x2="34" y2="40"/>',
  chess: '<rect x="6" y="34" width="36" height="6" rx="1" stroke-linejoin="round"/><path d="M20 34 L20 28 C20 24 24 24 24 20 C24 17 21 16 21 13 C21 10.5 27 10.5 27 13 C27 16 24 17 24 20 C24 24 28 24 28 28 L28 34" stroke-linejoin="round"/>',
  bowl: '<path d="M8 22 C8 30 15 36 24 36 C33 36 40 30 40 22" stroke-linecap="round"/><ellipse cx="24" cy="22" rx="16" ry="6"/><path d="M40 20 L44 16"/>',
  scanner: '<rect x="10" y="14" width="20" height="14" rx="3" stroke-linejoin="round"/><path d="M30 21 L40 21" stroke-linecap="round"/><path d="M14 28 L14 34" stroke-linecap="round"/><path d="M26 28 L26 34" stroke-linecap="round"/>',
  figure: '<circle cx="24" cy="14" r="6"/><path d="M14 38 C14 26 34 26 34 38" stroke-linejoin="round"/><path d="M24 20 L24 26" stroke-linecap="round"/>',
  toy: '<circle cx="12" cy="24" r="4"/><circle cx="20" cy="20" r="4"/><circle cx="28" cy="24" r="4"/><circle cx="36" cy="20" r="4"/><path d="M12 28 L12 32 M36 24 L36 28" stroke-linecap="round"/>',
  cube: '<path d="M24 6 L40 14 L40 32 L24 40 L8 32 L8 14 Z" stroke-linejoin="round"/><path d="M8 14 L24 22 L40 14 M24 22 L24 40" stroke-linejoin="round"/>',
};

function renderProductCard(product) {
  const article = document.createElement("article");
  article.className = "product-card";

  const media = document.createElement("div");
  media.className = "product-media";
  const priceTag = document.createElement("span");
  priceTag.className = "price-tag";
  priceTag.textContent = product.price;
  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("viewBox", "0 0 48 48");
  svg.setAttribute("fill", "none");
  svg.setAttribute("stroke", "#c41e3a");
  svg.setAttribute("stroke-width", "1.6");
  svg.innerHTML = PRODUCT_ICONS[product.icon] || PRODUCT_ICONS.cube;
  media.append(priceTag, svg);

  const body = document.createElement("div");
  body.className = "product-body";

  const cat = document.createElement("span");
  cat.className = "product-cat";
  cat.textContent = product.category;

  const h3 = document.createElement("h3");
  h3.textContent = product.name;

  const desc = document.createElement("p");
  desc.textContent = product.description;

  const link = document.createElement("a");
  link.className = "product-link";
  link.href = product.link;
  link.target = "_blank";
  link.rel = "noopener";
  link.textContent = "Написать →";

  body.append(cat, h3, desc, link);
  article.append(media, body);
  return article;
}

async function loadProducts() {
  const grid = document.getElementById("productsGrid");
  if (!grid) return;
  try {
    const res = await fetch("data/products.json");
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const products = await res.json();
    grid.innerHTML = "";
    products.forEach((product) => grid.appendChild(renderProductCard(product)));
  } catch (err) {
    grid.innerHTML = "<p style=\"color:var(--text-dim);\">Не удалось загрузить товары. Обновите страницу или напишите нам в ВК.</p>";
    console.error("Failed to load products.json", err);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadProducts();

  const menuToggle = document.getElementById("menuToggle");
  const navLinks = document.getElementById("navLinks");
  const navCta = document.getElementById("navCta");

  menuToggle.addEventListener("click", () => {
    navLinks.classList.toggle("open");
    navCta.classList.toggle("open");
  });

  navLinks.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      navLinks.classList.remove("open");
      navCta.classList.remove("open");
    });
  });

  const floatingCta = document.querySelector(".floating-cta");
  const hero = document.querySelector(".hero");
  const toggleFloatingCta = () => {
    const showAfter = hero.offsetTop + hero.offsetHeight;
    floatingCta.classList.toggle("visible", window.scrollY > showAfter);
  };
  toggleFloatingCta();
  window.addEventListener("scroll", toggleFloatingCta, { passive: true });
});
