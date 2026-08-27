(() => {
  "use strict";

  /* ---------- state ---------- */
  const state = {
    date: "",
    time: "",
    activities: [],
  };

  /* ---------- screen navigation ---------- */
  const screens = Array.from(document.querySelectorAll(".screen"));
  const dots = Array.from(document.querySelectorAll(".progress .dot"));

  function goToStep(step) {
    screens.forEach((s) => s.classList.remove("active"));
    document.getElementById(`screen-${step}`).classList.add("active");

    dots.forEach((dot) => {
      const dotStep = Number(dot.dataset.step);
      dot.classList.toggle("done", dotStep < step);
      dot.classList.toggle("current", dotStep === step);
    });
  }

  goToStep(1);

  document.getElementById("toStep3").addEventListener("click", () => goToStep(3));
  document.getElementById("toStep4").addEventListener("click", () => goToStep(4));
  document.getElementById("toStep5").addEventListener("click", () => {
    fillSummary();
    goToStep(5);
  });

  /* ---------- screen 1: yes / runaway no ---------- */
  const answerZone = document.getElementById("answerZone");
  const btnYes = document.getElementById("btnYes");
  const btnNo = document.getElementById("btnNo");

  btnYes.addEventListener("click", () => goToStep(2));

  function moveNoButton() {
    const zoneRect = answerZone.getBoundingClientRect();
    const btnRect = btnNo.getBoundingClientRect();

    const maxLeft = Math.max(zoneRect.width - btnRect.width, 0);
    const maxTop = Math.max(zoneRect.height - btnRect.height, 0);

    const left = Math.random() * maxLeft;
    const top = Math.random() * maxTop;

    btnNo.style.position = "absolute";
    btnNo.style.left = `${left}px`;
    btnNo.style.top = `${top}px`;
  }

  // place it inside the zone from the start so it can safely dodge
  window.addEventListener("load", moveNoButton);

  const DODGE_DISTANCE = 90;

  answerZone.addEventListener("mousemove", (e) => {
    const btnRect = btnNo.getBoundingClientRect();
    const cx = btnRect.left + btnRect.width / 2;
    const cy = btnRect.top + btnRect.height / 2;
    const dist = Math.hypot(e.clientX - cx, e.clientY - cy);
    if (dist < DODGE_DISTANCE) {
      moveNoButton();
    }
  });

  function dodgeAndBlock(e) {
    e.preventDefault();
    moveNoButton();
  }

  btnNo.addEventListener("touchstart", dodgeAndBlock, { passive: false });
  btnNo.addEventListener("pointerdown", dodgeAndBlock);
  btnNo.addEventListener("click", (e) => e.preventDefault());

  window.addEventListener("resize", moveNoButton);

  /* ---------- screen 3: date & time ---------- */
  const dateInput = document.getElementById("dateInput");
  const timeInput = document.getElementById("timeInput");
  const toStep4Btn = document.getElementById("toStep4");

  const today = new Date();
  dateInput.min = today.toISOString().split("T")[0];

  function validateStep3() {
    state.date = dateInput.value;
    state.time = timeInput.value;
    toStep4Btn.disabled = !(state.date && state.time);
  }

  dateInput.addEventListener("change", validateStep3);
  timeInput.addEventListener("change", validateStep3);

  /* ---------- screen 4: activities ---------- */
  const optionCards = Array.from(document.querySelectorAll(".option-card"));
  const toStep5Btn = document.getElementById("toStep5");

  optionCards.forEach((card) => {
    card.addEventListener("click", () => {
      card.classList.toggle("selected");
      const value = card.dataset.value;
      if (card.classList.contains("selected")) {
        state.activities.push(value);
      } else {
        state.activities = state.activities.filter((v) => v !== value);
      }
      toStep5Btn.disabled = state.activities.length === 0;
    });
  });

  /* ---------- screen 5: summary ---------- */
  const MONTHS_RU = [
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
  ];

  function formatDateRu(isoDate) {
    const [y, m, d] = isoDate.split("-").map(Number);
    return `${d} ${MONTHS_RU[m - 1]} ${y}`;
  }

  function fillSummary() {
    const summaryEl = document.getElementById("summary");
    const dateText = state.date ? formatDateRu(state.date) : "—";
    const timeText = state.time || "—";
    const activitiesText = state.activities.length
      ? state.activities.join(", ")
      : "—";

    summaryEl.innerHTML = `
      <div>📅 <strong>${dateText}</strong>, в <strong>${timeText}</strong></div>
      <div>💫 Планы: <strong>${activitiesText}</strong></div>
    `;
  }

  /* ---------- floating hearts background ---------- */
  const heartsBg = document.getElementById("heartsBg");
  const HEART_COUNT = 7;

  function spawnHeart() {
    const heart = document.createElement("span");
    heart.className = "floating-heart";
    heart.textContent = "♥";

    const left = Math.random() * 100;
    const duration = 9 + Math.random() * 7;
    const delay = Math.random() * 4;
    const size = 14 + Math.random() * 14;
    const drift = (Math.random() - 0.5) * 80;

    heart.style.left = `${left}%`;
    heart.style.fontSize = `${size}px`;
    heart.style.animationDuration = `${duration}s`;
    heart.style.animationDelay = `${delay}s`;
    heart.style.setProperty("--drift", `${drift}px`);

    heartsBg.appendChild(heart);
  }

  for (let i = 0; i < HEART_COUNT; i++) {
    spawnHeart();
  }
})();
