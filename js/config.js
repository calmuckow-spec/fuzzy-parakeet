/* ---------- shared site config (read by index.html, written by admin.html) ----------

   One-time setup so the admin page can actually save changes for everyone:
   1) Sign up for free at https://jsonbin.io
   2) Open "API Keys" in the left menu and copy your Master Key.
   3) Click "Create Bin" — UNCHECK "Private" so anyone with the link can read
      it — and paste this as the starting content:

      {
        "activities": [
          { "emoji": "🚶‍♀️", "label": "Погулять" },
          { "emoji": "🍕", "label": "Пицца" },
          { "emoji": "🍣", "label": "Роллы" },
          { "emoji": "🥟", "label": "Хинкали" }
        ],
        "telegram": {
          "botToken": "paste-your-bot-token-here",
          "chatId": "paste-your-chat-id-here"
        }
      }

      (grab your current bot token / chat id from js/script.js further down —
      they're already set up there, this just lets you change them from the
      admin page without editing code)

   4) Create it, then copy the Bin ID (shown on the bin's page) and paste
      both values below.
*/
window.SiteConfig = (() => {
  "use strict";

  const BIN_ID = "YOUR_BIN_ID";
  const MASTER_KEY = "YOUR_MASTER_KEY";

  const READ_URL = `https://api.jsonbin.io/v3/b/${BIN_ID}/latest`;
  const WRITE_URL = `https://api.jsonbin.io/v3/b/${BIN_ID}`;

  const DEFAULT_CONFIG = {
    activities: [
      { emoji: "🚶‍♀️", label: "Погулять" },
      { emoji: "🍕", label: "Пицца" },
      { emoji: "🍣", label: "Роллы" },
      { emoji: "🥟", label: "Хинкали" },
    ],
    // left empty on purpose — script.js falls back to its own hardcoded
    // bot token/chat id (see the comment above TELEGRAM_BOT_TOKEN there)
    // whenever this is empty, so the site keeps working either way
    telegram: {
      botToken: "",
      chatId: "",
    },
  };

  function isConfigured() {
    return Boolean(BIN_ID) && BIN_ID !== "YOUR_BIN_ID";
  }

  function canSave() {
    return isConfigured() && Boolean(MASTER_KEY) && MASTER_KEY !== "YOUR_MASTER_KEY";
  }

  function normalize(record) {
    const activities =
      Array.isArray(record.activities) && record.activities.length
        ? record.activities
        : DEFAULT_CONFIG.activities;

    const telegram =
      record.telegram && record.telegram.chatId
        ? record.telegram
        : DEFAULT_CONFIG.telegram;

    return { activities, telegram };
  }

  async function loadConfig() {
    if (!isConfigured()) return DEFAULT_CONFIG;
    try {
      const res = await fetch(READ_URL, { cache: "no-store" });
      if (!res.ok) throw new Error("bad response");
      const data = await res.json();
      return normalize(data.record || {});
    } catch (err) {
      return DEFAULT_CONFIG;
    }
  }

  async function saveConfig(config) {
    if (!canSave()) throw new Error("saving is not configured");
    const res = await fetch(WRITE_URL, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "X-Master-Key": MASTER_KEY,
      },
      body: JSON.stringify(config),
    });
    if (!res.ok) throw new Error("save failed");
    return res.json();
  }

  return { loadConfig, saveConfig, isConfigured, canSave, DEFAULT_CONFIG };
})();
