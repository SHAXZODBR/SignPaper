# SignPaper Bot - Deployment Guide

## Quick Start (Local)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables (create .env file)
TELEGRAM_BOT_TOKEN=your_bot_token
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
ADMIN_CHAT_ID=-123456789  # Your Telegram group ID
GROQ_API_KEY=your_groq_key  # Optional, for AI features

# 3. Run the bot
python -m bot.main
```

---

## Deployment Options

### Option 1: Railway.app (Easiest - Free Tier)

1. Push code to GitHub
2. Go to [railway.app](https://railway.app)
3. Click "New Project" → "Deploy from GitHub"
4. Add environment variables in Railway dashboard
5. Railway auto-detects Python and runs the bot

### Option 2: Render.com (Free Tier)

1. Push code to GitHub
2. Go to [render.com](https://render.com)
3. Create "Background Worker" (not Web Service)
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `python -m bot.main`
6. Add environment variables

### Option 3: Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Login and deploy
fly auth login
fly launch  # Follow prompts
fly secrets set TELEGRAM_BOT_TOKEN=xxx SUPABASE_URL=xxx SUPABASE_KEY=xxx
fly deploy
```

### Option 4: VPS (DigitalOcean, Hetzner, etc.)

```bash
# SSH into server
ssh root@your-server

# Install Python
apt update && apt install python3 python3-pip -y

# Clone your repo
git clone https://github.com/your/repo.git
cd repo

# Install and run with systemd
pip3 install -r requirements.txt

# Create service file
cat > /etc/systemd/system/signpaper.service << EOF
[Unit]
Description=SignPaper Telegram Bot
After=network.target

[Service]
WorkingDirectory=/root/repo
ExecStart=/usr/bin/python3 -m bot.main
Restart=always
EnvironmentFile=/root/repo/.env

[Install]
WantedBy=multi-user.target
EOF

# Start service
systemctl enable signpaper
systemctl start signpaper
systemctl status signpaper
```

---

## Required Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| TELEGRAM_BOT_TOKEN | ✅ | From @BotFather |
| SUPABASE_URL | ✅ | Your Supabase project URL |
| SUPABASE_KEY | ✅ | Supabase anon or service key |
| ADMIN_CHAT_ID | ⭕ | Telegram group ID for support |
| GROQ_API_KEY | ⭕ | For AI summary/quiz features |

---

## Database Setup (Supabase)

Run these SQL commands in Supabase SQL Editor:

```sql
-- Disable RLS on analytics tables (required for bot to write)
ALTER TABLE user_analytics DISABLE ROW LEVEL SECURITY;
ALTER TABLE search_analytics DISABLE ROW LEVEL SECURITY;
ALTER TABLE downloads DISABLE ROW LEVEL SECURITY;
ALTER TABLE feedback DISABLE ROW LEVEL SECURITY;
ALTER TABLE support_messages DISABLE ROW LEVEL SECURITY;
```

---

## Verify Deployment

After deploying, run:
```bash
python production_check.py
```

Should show: **STATUS: PRODUCTION READY!**
