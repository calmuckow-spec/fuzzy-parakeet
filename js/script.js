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
    sendToTelegram();
  });

  /* ---------- screen 1: yes / runaway no ---------- */
  const answerZone = document.getElementById("answerZone");
  const btnYes = document.getElementById("btnYes");
  const btnNo = document.getElementById("btnNo");

  btnYes.addEventListener("click", () => goToStep(2));

  const SAFE_MARGIN = 14;

  // negative score = candidate overlaps "yes" (worse the more it overlaps),
  // positive score = free gap between candidate and "yes" (bigger is better)
  function clearanceScore(candidate, yesRect) {
    const inflated = {
      left: yesRect.left - SAFE_MARGIN,
      right: yesRect.right + SAFE_MARGIN,
      top: yesRect.top - SAFE_MARGIN,
      bottom: yesRect.bottom + SAFE_MARGIN,
    };

    const dx = Math.max(inflated.left - candidate.right, candidate.left - inflated.right, 0);
    const dy = Math.max(inflated.top - candidate.bottom, candidate.top - inflated.bottom, 0);

    if (dx > 0 || dy > 0) {
      return Math.hypot(dx, dy);
    }

    const xOverlap = Math.min(candidate.right, inflated.right) - Math.max(candidate.left, inflated.left);
    const yOverlap = Math.min(candidate.bottom, inflated.bottom) - Math.max(candidate.top, inflated.top);
    return -(xOverlap * yOverlap);
  }

  function moveNoButton() {
    const zoneRect = answerZone.getBoundingClientRect();
    const btnRect = btnNo.getBoundingClientRect();
    const yesRect = btnYes.getBoundingClientRect();

    const maxLeft = Math.max(zoneRect.width - btnRect.width, 0);
    const maxTop = Math.max(zoneRect.height - btnRect.height, 0);

    // yes-button rect translated into the zone's own coordinate space
    const yesInZone = {
      left: yesRect.left - zoneRect.left,
      right: yesRect.right - zoneRect.left,
      top: yesRect.top - zoneRect.top,
      bottom: yesRect.bottom - zoneRect.top,
    };

    // sample several random spots and keep the one with the best clearance
    // from "yes" — guarantees a non-overlapping spot whenever one exists
    let bestLeft = 0;
    let bestTop = 0;
    let bestScore = -Infinity;

    for (let i = 0; i < 20; i++) {
      const left = Math.random() * maxLeft;
      const top = Math.random() * maxTop;
      const candidate = { left, right: left + btnRect.width, top, bottom: top + btnRect.height };
      const score = clearanceScore(candidate, yesInZone);
      if (score > bestScore) {
        bestScore = score;
        bestLeft = left;
        bestTop = top;
      }
    }

    btnNo.style.position = "absolute";
    btnNo.style.left = `${bestLeft}px`;
    btnNo.style.top = `${bestTop}px`;
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

  function buildSummaryText() {
    const dateText = state.date ? formatDateRu(state.date) : "не выбрана";
    const timeText = state.time || "не выбрано";
    const activitiesText = state.activities.length
      ? state.activities.join(", ")
      : "не выбраны";

    return [
      "Она согласна на свидание! 💌",
      `Дата: ${dateText}`,
      `Время: ${timeText}`,
      `Планы: ${activitiesText}`,
    ].join("\n");
  }

  /* ---------- screen 5: automatic Telegram delivery ----------
     1) Message @BotFather in Telegram, send /newbot, follow the steps —
        you get a token like "123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx".
     2) Open a chat with your new bot and send it any message (e.g. "hi").
     3) Open in a browser: https://api.telegram.org/bot<TOKEN>/getUpdates
        and copy the number after "chat":{"id": — that's your CHAT_ID.
     4) Paste both values below. */
  const TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN";
  const TELEGRAM_CHAT_ID = "YOUR_CHAT_ID";

  const sendStatus = document.getElementById("sendStatus");

  async function sendToTelegram() {
    if (!TELEGRAM_BOT_TOKEN || TELEGRAM_BOT_TOKEN === "YOUR_BOT_TOKEN") {
      sendStatus.innerHTML = "Автоотправка не настроена — скопируй текст вручную";
      sendStatus.className = "send-status error";
      return;
    }

    sendStatus.innerHTML = '<span class="spinner"></span> Отправляю тебе весточку...';
    sendStatus.className = "send-status";

    try {
      const url = `https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: TELEGRAM_CHAT_ID,
          text: buildSummaryText(),
        }),
      });
      if (!res.ok) throw new Error("telegram request failed");

      sendStatus.textContent = "Отправлено ✓";
      sendStatus.className = "send-status ok";
    } catch (err) {
      sendStatus.textContent = "Не отправилось — скопируй текст вручную";
      sendStatus.className = "send-status error";
    }
  }

  /* ---------- screen 5: copy fallback ---------- */
  const copyBtn = document.getElementById("copyBtn");
  const copyFeedback = document.getElementById("copyFeedback");

  let feedbackTimer = null;

  function showCopyFeedback(text) {
    copyFeedback.textContent = text;
    copyFeedback.classList.add("visible");
    clearTimeout(feedbackTimer);
    feedbackTimer = setTimeout(() => copyFeedback.classList.remove("visible"), 2500);
  }

  copyBtn.addEventListener("click", async () => {
    const text = buildSummaryText();
    try {
      await navigator.clipboard.writeText(text);
      showCopyFeedback("Скопировано ✓ — вставь в сообщение мне");
    } catch (err) {
      showCopyFeedback("Не удалось скопировать, выдели текст вручную");
    }
  });

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
