(() => {
  "use strict";

  /* Change this before sharing the site with anyone — it's the only thing
     keeping a random visitor who finds this page from editing your settings.
     It is NOT real security (anyone could read it from this file's source),
     just a simple deterrent for a private, low-stakes personal project. */
  const ADMIN_PIN = "0000";

  const pinScreen = document.getElementById("pinScreen");
  const pinInput = document.getElementById("pinInput");
  const pinSubmit = document.getElementById("pinSubmit");
  const pinError = document.getElementById("pinError");
  const settingsScreen = document.getElementById("settingsScreen");

  function unlock() {
    pinScreen.style.display = "none";
    settingsScreen.classList.add("visible");
    initSettings();
  }

  pinSubmit.addEventListener("click", () => {
    if (pinInput.value === ADMIN_PIN) {
      unlock();
    } else {
      pinError.textContent = "Неверный код";
    }
  });

  pinInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter") pinSubmit.click();
  });

  /* ---------- settings form (loaded only after PIN is correct) ---------- */
  let settingsInitialized = false;

  function makeActivityRow(emoji, label) {
    const row = document.createElement("div");
    row.className = "activity-row";
    row.innerHTML = `
      <input type="text" class="emoji-input" value="${emoji}" maxlength="4">
      <input type="text" class="label-input" value="${label}" placeholder="Название">
      <button type="button" class="remove-btn" aria-label="Удалить">×</button>
    `;
    row.querySelector(".remove-btn").addEventListener("click", () => row.remove());
    return row;
  }

  async function initSettings() {
    if (settingsInitialized) return;
    settingsInitialized = true;

    document.getElementById("notConfiguredNote").style.display = window.SiteConfig.canSave()
      ? "none"
      : "block";

    const activityList = document.getElementById("activityList");
    const addActivityBtn = document.getElementById("addActivityBtn");
    const botTokenInput = document.getElementById("botTokenInput");
    const chatIdInput = document.getElementById("chatIdInput");
    const saveBtn = document.getElementById("saveBtn");
    const status = document.getElementById("adminStatus");

    const cfg = await window.SiteConfig.loadConfig();

    cfg.activities.forEach(({ emoji, label }) => {
      activityList.appendChild(makeActivityRow(emoji, label));
    });
    botTokenInput.value = cfg.telegram.botToken || "";
    chatIdInput.value = cfg.telegram.chatId || "";

    addActivityBtn.addEventListener("click", () => {
      activityList.appendChild(makeActivityRow("✨", ""));
    });

    saveBtn.addEventListener("click", async () => {
      const activities = Array.from(activityList.querySelectorAll(".activity-row"))
        .map((row) => ({
          emoji: row.querySelector(".emoji-input").value.trim(),
          label: row.querySelector(".label-input").value.trim(),
        }))
        .filter((a) => a.label);

      if (!activities.length) {
        status.textContent = "Добавь хотя бы один вариант";
        status.className = "admin-status error";
        return;
      }

      const newConfig = {
        activities,
        telegram: {
          botToken: botTokenInput.value.trim(),
          chatId: chatIdInput.value.trim(),
        },
      };

      status.textContent = "Сохраняю...";
      status.className = "admin-status";

      try {
        await window.SiteConfig.saveConfig(newConfig);
        status.textContent = "Сохранено ✓";
        status.className = "admin-status ok";
      } catch (err) {
        status.textContent = "Не удалось сохранить — проверь настройку jsonbin.io в js/config.js";
        status.className = "admin-status error";
      }
    });
  }
})();
