# 🛠️ Environment Variables Guide

To make your bot work, you need 3 main services: **Telegram**, **Supabase**, and optionally **Groq**. Here's exactly where to get your keys:

---

### 1. Telegram Bot Token (`TELEGRAM_BOT_TOKEN`)
- **Where to get it**: Message [@BotFather](https://t.me/BotFather) on Telegram.
- **Steps**:
  1. Send `/newbot`.
  2. Follow instructions to name your bot.
  3. You will receive a token like `12345678:ABCdefGHIjkl...`.
- **In Vercel**: Add as `TELEGRAM_BOT_TOKEN`.

---

### 2. Supabase Keys (`SUPABASE_URL` & `SUPABASE_KEY`)
- **Where to get it**: [supabase.com](https://supabase.com)
- **Steps**:
  1. Go to your Project Dashboard.
  2. Click the **Settings Gear** ⚙️ (bottom left).
  3. Click **API**.
  4. Copy **Project URL** (this is `SUPABASE_URL`).
  5. Copy **anon public Key** (this is `SUPABASE_KEY`).
- **In Vercel**: Add as `SUPABASE_URL` and `SUPABASE_KEY`.

---

### 3. Groq API Key (`GROQ_API_KEY`) - *Optional*
*Used for AI summaries and quizzes.*
- **Where to get it**: [console.groq.com](https://console.groq.com/keys)
- **Steps**:
  1. Create an account.
  2. Go to **API Keys**.
  3. Click **Create API Key**.
- **In Vercel**: Add as `GROQ_API_KEY`.

---

### 4. Admin Chat ID (`ADMIN_CHAT_ID`)
*Used to send support messages to YOU.*
- **Where to get it**: Message [@userinfobot](https://t.me/userinfobot) on Telegram.
- **Steps**:
  1. Start the bot.
  2. It will reply with your **Id**.
- **In Vercel**: Add as `ADMIN_CHAT_ID`.

---

### 🚀 How to add them to Vercel
1. Go to your project on the Vercel Dashboard.
2. Go to **Settings** → **Environment Variables**.
3. Add the names (e.g., `TELEGRAM_BOT_TOKEN`) and their values one by one.
4. **Redeploy** your app for changes to take effect.
