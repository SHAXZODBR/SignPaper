# SignPaper Bot - Deployment Guide

## 🚀 Quick Deployment Options

### Option 1: VPS (Recommended - $4-5/month)

**Best for:** Production, 24/7 uptime

1. **Get a VPS** from:
   - [DigitalOcean](https://digitalocean.com) - $4/mo
   - [Hetzner](https://hetzner.com) - €3/mo
   - [Vultr](https://vultr.com) - $2.50/mo

2. **Setup the server:**
```bash
# Connect to your VPS
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y

# Install Python
apt install python3 python3-pip python3-venv git -y

# Clone your bot
git clone https://github.com/your-username/SignPaper.git
cd SignPaper

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
nano .env
```

3. **Configure .env:**
```env
TELEGRAM_BOT_TOKEN=your_bot_token
GROQ_API_KEY=your_groq_key
ADMIN_CHAT_ID=your_telegram_id
```

4. **Create systemd service:**
```bash
sudo nano /etc/systemd/system/signpaper.service
```

```ini
[Unit]
Description=SignPaper Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/SignPaper
Environment=PATH=/root/SignPaper/venv/bin
ExecStart=/root/SignPaper/venv/bin/python -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

5. **Start the bot:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable signpaper
sudo systemctl start signpaper

# Check status
sudo systemctl status signpaper

# View logs
journalctl -u signpaper -f
```

---

### Option 2: Railway (Free tier available)

1. Go to [railway.app](https://railway.app)
2. Connect GitHub
3. Import your repository
4. Add environment variables
5. Deploy!

---

### Option 3: Local (Development)

```bash
# Activate virtual environment
source venv/bin/activate

# Run the bot
python -m bot.main
```

---

## 📋 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | ✅ | Bot token from @BotFather |
| `GROQ_API_KEY` | ✅ | API key from console.groq.com |
| `ADMIN_CHAT_ID` | ❌ | Your Telegram ID for support messages |

---

## 🔧 Maintenance Commands

```bash
# Restart bot
sudo systemctl restart signpaper

# Stop bot
sudo systemctl stop signpaper

# View logs
journalctl -u signpaper -f --lines=100

# Update bot
cd /root/SignPaper
git pull
sudo systemctl restart signpaper
```

---

## 📊 Monitoring

Check bot health:
```bash
# Service status
sudo systemctl status signpaper

# Memory usage
ps aux | grep python

# Disk usage
df -h
```
