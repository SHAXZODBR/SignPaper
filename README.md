# 📚 Uzbek School Books Bot - Setup Guide

## Quick Setup (5 minutes)

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment
Edit `.env` file with your keys:
```env
# Required
TELEGRAM_BOT_TOKEN="your-bot-token"

# Optional - AI Summary
GEMINI_API_KEY="your-gemini-key"

# Optional - Cloud Database
SUPABASE_URL="your-supabase-url"
SUPABASE_KEY="your-supabase-key"
```

### Step 3: Add Your Books
Place PDF files in folders:
```
books/
├── uzbek/
│   ├── Matematika/
│   │   └── matematika_5.pdf
│   ├── Biologiya/
│   │   └── biologiya_9.pdf
│   └── Fizika/
│       └── fizika_8.pdf
└── russian/
    └── История/
        └── история_6.pdf
```

### Step 4: Process Books
```bash
python -m services.book_processor
```

### Step 5: Run Bot
```bash
python -m bot.main
```

---

## 🔑 Getting API Keys

### Telegram Bot Token
1. Open Telegram, search `@BotFather`
2. Send `/newbot`
3. Copy the token

### Gemini API Key (Free)
1. Go to https://makersuite.google.com/app/apikey
2. Create API key
3. Copy to `.env`

### Supabase (Optional)
1. Go to https://supabase.com
2. Create project
3. Settings → API → Copy URL and `service_role` key

---

## 🤖 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/search <query>` | Search themes |
| `/books` | Browse by grade |
| `/stats` | Database info |
| `/help` | Help |

---

## ✨ Features

- **🔍 Search** - Type any topic to search
- **📖 Browse** - Browse books by grade
- **📥 PDF Download** - Download full books or specific chapters
- **📝 AI Summary** - Get AI-generated summaries (requires Gemini key)
- **📋 AI Quiz** - Generate quiz questions from chapters
- **🔗 Resources** - Educational links for each topic

---

## 📁 Project Structure

```
BB/
├── bot/
│   ├── main.py           # Bot entry point
│   └── handlers/
│       ├── search.py     # Search functionality
│       ├── books.py      # Book browsing
│       ├── resources.py  # Educational resources
│       └── ai_handler.py # AI Summary & Quiz
├── services/
│   ├── book_processor.py # PDF processing
│   ├── search_engine.py  # Search functionality
│   ├── ai_summary.py     # Gemini AI integration
│   └── pdf_processor.py  # PDF extraction
├── database/
│   ├── models.py         # SQLite models
│   ├── supabase_client.py # Supabase integration
│   └── supabase_schema.sql # SQL schema
├── books/                # Your PDF books
├── data/                 # Generated data
├── .env                  # Configuration
└── requirements.txt      # Dependencies
```

---

## 🚀 Quick Commands

```bash
# Process new books
python -m services.book_processor

# Run bot
python -m bot.main

# Test AI summary
python -m services.ai_summary
```
