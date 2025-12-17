"""
Uzbek School Books Telegram Bot
SignPaper - Professional Educational Bot
Main entry point for the bot.
"""
import logging
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
)
import sys
sys.path.append('..')
from config import TELEGRAM_BOT_TOKEN
from database.models import init_db
from bot.handlers.search import (
    search_command,
    handle_theme_selection,
    text_search_handler,
)
from bot.handlers.books import (
    books_command,
    handle_language_selection,
    handle_grade_selection,
    handle_book_selection,
    handle_book_pdf_download,
    handle_theme_pdf_download,
    handle_themes_list,
    handle_back_languages,
)
from bot.handlers.resources import (
    handle_resources,
    resources_command,
)
from bot.handlers.ai_handler import (
    handle_summary_request,
    handle_quiz_request,
)
from bot.handlers.support import (
    support_command,
    receive_support_message,
    cancel_support,
    feedback_command,
    handle_rating,
    myid_command,
    reply_command,
    WAITING_FOR_MESSAGE,
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# PROFESSIONAL WELCOME MESSAGE
# ═══════════════════════════════════════════════════════════════════════════

async def start_command(update: Update, context) -> None:
    """Handle /start command with professional welcome."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    user = update.effective_user
    
    welcome_message = (
        f"👋 Assalomu alaykum, **{user.first_name}**!\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📚 **SignPaper** - O'zbekiston maktab darsliklari\n"
        "📚 **SignPaper** - Школьные учебники Узбекистана\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "✨ **Imkoniyatlar / Features:**\n"
        "• 🔍 Mavzularni qidirish\n"
        "• 📥 Darsliklarni yuklab olish\n"
        "• 🤖 AI bilan test va xulosa\n"
        "• 📚 72+ ta darslik\n\n"
        "⬇️ **Tez qidirish / Quick Search:**"
    )
    
    keyboard = [
        [
            InlineKeyboardButton("🔢 Natural sonlar", callback_data="search_Natural sonlar"),
            InlineKeyboardButton("📐 Pifagor", callback_data="search_Pifagor")
        ],
        [
            InlineKeyboardButton("🧬 Hujayra", callback_data="search_Hujayra"),
            InlineKeyboardButton("⚗️ Atom", callback_data="search_Atom")
        ],
        [
            InlineKeyboardButton("🧪 Химия", callback_data="search_Химия"),
            InlineKeyboardButton("📊 Физика", callback_data="search_Физика")
        ],
        [
            InlineKeyboardButton("📚 Kitoblar / Books", callback_data="browse_books")
        ],
        [
            InlineKeyboardButton("📞 Yordam / Support", callback_data="show_support"),
            InlineKeyboardButton("⭐ Baholash", callback_data="show_feedback")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message, 
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def help_command(update: Update, context) -> None:
    """Handle /help command."""
    help_text = (
        "📖 **SignPaper Bot - Yordam**\n\n"
        "**Buyruqlar / Commands:**\n"
        "`/start` - Boshlash\n"
        "`/search` - Mavzularni qidirish\n"
        "`/books` - Kitoblarni ko'rish\n"
        "`/support` - Qo'llab-quvvatlash\n"
        "`/feedback` - Bot haqida fikr\n"
        "`/stats` - Statistika\n\n"
        "**Tips:**\n"
        "• Istalgan matnni yozing - avtomatik qidiradi\n"
        "• O'zbek va rus tilida ishlaydi\n"
        "• PDF yuklab olish bepul!\n\n"
        "📧 Aloqa: @SignPaperSupport"
    )
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def stats_command(update: Update, context) -> None:
    """Handle /stats command."""
    from database.models import get_session, Book, Theme, Resource
    
    session = get_session()
    books_count = session.query(Book).count()
    themes_count = session.query(Theme).count()
    resources_count = session.query(Resource).count()
    
    stats_text = (
        "📊 **SignPaper Statistika**\n\n"
        f"📚 Kitoblar: {books_count}\n"
        f"📑 Mavzular: {themes_count}\n"
        f"🔗 Resurslar: {resources_count}\n"
    )
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')


async def set_bot_commands(application: Application) -> None:
    """Set bot commands for the menu."""
    commands = [
        BotCommand("start", "🏠 Boshlash / Start"),
        BotCommand("search", "🔍 Qidirish / Search"),
        BotCommand("books", "📚 Kitoblar / Books"),
        BotCommand("support", "📞 Yordam / Support"),
        BotCommand("feedback", "⭐ Baholash / Rate"),
        BotCommand("help", "❓ Yordam / Help"),
    ]
    await application.bot.set_my_commands(commands)


# ═══════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    """Start the bot."""
    # Initialize database
    init_db()
    
    # Check for bot token
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_bot_token_here":
        print("❌ Error: TELEGRAM_BOT_TOKEN not set!")
        return

    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # ═══════════════════════════════════════════════════════════════════
    # COMMAND HANDLERS
    # ═══════════════════════════════════════════════════════════════════
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("books", books_command))
    application.add_handler(CommandHandler("resources", resources_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("feedback", feedback_command))
    application.add_handler(CommandHandler("myid", myid_command))
    application.add_handler(CommandHandler("reply", reply_command))
    
    # Support conversation handler
    support_conv = ConversationHandler(
        entry_points=[CommandHandler("support", support_command)],
        states={
            WAITING_FOR_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_support_message)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_support, pattern="^cancel_support$"),
            CommandHandler("cancel", cancel_support),
        ],
    )
    application.add_handler(support_conv)
    
    # ═══════════════════════════════════════════════════════════════════
    # CALLBACK HANDLERS
    # ═══════════════════════════════════════════════════════════════════
    application.add_handler(CallbackQueryHandler(handle_theme_selection, pattern=r"^theme_\d+$"))
    application.add_handler(CallbackQueryHandler(handle_language_selection, pattern=r"^lang_(uz|ru)$"))
    application.add_handler(CallbackQueryHandler(handle_grade_selection, pattern=r"^grade_(uz|ru)_\d+$"))
    application.add_handler(CallbackQueryHandler(handle_book_selection, pattern=r"^book_(uz|ru)_\d+$"))
    application.add_handler(CallbackQueryHandler(handle_book_pdf_download, pattern=r"^download_(uz|ru)_\d+$"))
    application.add_handler(CallbackQueryHandler(handle_theme_pdf_download, pattern=r"^theme_pdf_\d+$"))
    application.add_handler(CallbackQueryHandler(handle_themes_list, pattern=r"^themes_(uz|ru)_\d+$"))
    application.add_handler(CallbackQueryHandler(handle_resources, pattern=r"^resources_\d+$"))
    application.add_handler(CallbackQueryHandler(handle_back_languages, pattern=r"^back_languages$"))
    
    # AI handlers
    application.add_handler(CallbackQueryHandler(handle_summary_request, pattern=r"^summary_\d+$"))
    application.add_handler(CallbackQueryHandler(handle_quiz_request, pattern=r"^quiz_\d+$"))
    
    # Rating handler
    application.add_handler(CallbackQueryHandler(handle_rating, pattern=r"^rate_\d$"))
    
    # Support/Feedback from start menu
    async def show_support_menu(update: Update, context):
        query = update.callback_query
        await query.answer()
        await query.message.reply_text(
            "📞 **Qo'llab-quvvatlash**\n\n"
            "Savolingiz bo'lsa /support buyrug'ini yuboring.\n\n"
            "📧 Email: support@sign.uz\n"
            "💬 Telegram: @shakhzodbr",
            parse_mode='Markdown'
        )
    
    async def show_feedback_menu(update: Update, context):
        query = update.callback_query
        await query.answer()
        await feedback_command.__wrapped__(update, context) if hasattr(feedback_command, '__wrapped__') else None
        # Send feedback prompt
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [
                InlineKeyboardButton("⭐ 5", callback_data="rate_5"),
                InlineKeyboardButton("⭐ 4", callback_data="rate_4"),
                InlineKeyboardButton("⭐ 3", callback_data="rate_3"),
            ],
            [
                InlineKeyboardButton("⭐ 2", callback_data="rate_2"),
                InlineKeyboardButton("⭐ 1", callback_data="rate_1"),
            ]
        ]
        await query.message.reply_text(
            "⭐ **Botni baholang!**\n\n"
            "Sizning fikringiz biz uchun muhim.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    application.add_handler(CallbackQueryHandler(show_support_menu, pattern=r"^show_support$"))
    application.add_handler(CallbackQueryHandler(show_feedback_menu, pattern=r"^show_feedback$"))
    
    # Quick search from start menu
    async def handle_quick_search(update: Update, context):
        query = update.callback_query
        await query.answer()
        search_term = query.data.replace("search_", "")
        from bot.handlers.search import perform_search
        await perform_search(update, search_term, from_callback=True)
    
    async def handle_browse_books(update: Update, context):
        query = update.callback_query
        await query.answer()
        await books_command(update, context, from_callback=True)
    
    application.add_handler(CallbackQueryHandler(handle_quick_search, pattern=r"^search_.+"))
    application.add_handler(CallbackQueryHandler(handle_browse_books, pattern=r"^browse_books$"))
    
    # Text message handler (search)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_search_handler))
    
    # Set bot commands
    application.post_init = set_bot_commands
    
    # Start bot
    print("═" * 50)
    print("📚 SignPaper Bot - Starting...")
    print("═" * 50)
    print("🤖 Bot is running!")
    print("📞 Press Ctrl+C to stop")
    print("═" * 50)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
