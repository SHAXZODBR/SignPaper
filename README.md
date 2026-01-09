# 📚 SignPaper - Smart Education Bot

SignPaper is a cloud-native Telegram bot designed to serve educational textbooks and AI-powered learning resources to students and teachers.

## 🚀 Remote Architecture

The system is built to be 100% independent of local hardware, running entirely in the cloud.

- **Frontend**: Telegram Bot API 
- **Compute**: [Railway.app](https://railway.app) (Python 24/7)
- **Database**: [Supabase](https://supabase.com) (PostgreSQL + Full-Text Search)
- **Cloud Storage**: 
  - Supabase Storage (Small PDFs)
  - GitHub Hosting (Oversized textbooks >50MB)
- **AI Engine**: [Groq](https://groq.com) (Llama 3)

## 🛠️ Key Features

- **Omni-Search**: Instant search across 1,263 theme headers (Uzbek & Russian).
- **AI Xulosa**: Generate high-quality summaries of any chapter.
- **AI Test**: Generate 5-question interactive quizzes for student self-testing.
- **Smart PDF**: Extract only the specific pages user needs (Themes) or the full textbook.
- **Persistent UI**: Menus stay visible for seamless multi-action workflows.

## 📖 Deployment Guide

See [DEPLOY.md](DEPLOY.md) and [walkthrough.md](walkthrough.md) for detailed setup and architecture diagrams.

## ⚙️ Environment Variables

- `TELEGRAM_BOT_TOKEN`: Your bot token from @BotFather.
- `SUPABASE_URL`: Your Supabase Project URL.
- `SUPABASE_KEY`: Your Supabase Service Role Key (for full access).
- `GROQ_API_KEY`: API key for AI features.
- `ADMIN_CHAT_ID`: Telegram ID for receiving logs and support messages.

---
*Built with ❤️ for the future of education.*
