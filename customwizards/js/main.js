document.addEventListener("DOMContentLoaded", () => {
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
