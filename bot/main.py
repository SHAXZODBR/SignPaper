"""
Uzbek School Books Telegram Bot
Main entry point for the bot.
"""
import logging
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
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
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start_command(update: Update, context) -> None:
    """Handle /start command with default search suggestions."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    user = update.effective_user
    welcome_message = (
        f"👋 Salom, {user.first_name}!\n\n"
        "📚 **O'zbekiston maktab darsliklari** boti\n"
        "📚 **Uzbek School Books** bot\n\n"
        "🔍 **Qidirish / Search:**\n"
        "Mavzu nomini yozing / Type any topic\n\n"
        "⬇️ **Tez qidirish / Quick Search:**"
    )
    
    # Default search suggestions as buttons
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
            InlineKeyboardButton("🦠 Инфузории", callback_data="search_Инфузории"),
            InlineKeyboardButton("🔬 Споровики", callback_data="search_Споровики")
        ],
        [
            InlineKeyboardButton("🧪 Химия", callback_data="search_Химия"),
            InlineKeyboardButton("📊 Физика", callback_data="search_Физика")
        ],
        [
            InlineKeyboardButton("📚 Ko'rish / Browse", callback_data="browse_books")
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
        "📖 **Bot Commands:**\n\n"
        "`/start` - Welcome message\n"
        "`/search <query>` - Search for themes\n"
        "`/books` - Browse books by grade\n"
        "`/resources` - Educational resources info\n"
        "`/help` - Show this help\n"
        "`/stats` - Show database statistics\n\n"
        "**Tips:**\n"
        "• Just type any text to search\n"
        "• Search works in UZ, RU, and EN\n"
        "• Click theme to get PDF and resources"
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
        "📊 **Database Statistics:**\n\n"
        f"📚 Books: {books_count}\n"
        f"📑 Themes: {themes_count}\n"
        f"🔗 Resources: {resources_count}\n"
    )
    
    if books_count == 0:
        stats_text += (
            "\n⚠️ **No books found!**\n\n"
            "Please run the book processor:\n"
            "`python -m services.book_processor`"
        )
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')


async def set_bot_commands(application: Application) -> None:
    """Set bot commands for the menu."""
    commands = [
        BotCommand("start", "Start the bot / Botni ishga tushirish"),
        BotCommand("search", "Search themes / Mavzularni qidirish"),
        BotCommand("books", "Browse books / Kitoblarni ko'rish"),
        BotCommand("resources", "Educational resources / Ta'lim manbalari"),
        BotCommand("stats", "Database statistics / Statistika"),
        BotCommand("help", "Help / Yordam"),
    ]
    await application.bot.set_my_commands(commands)


def main() -> None:
    """Start the bot."""
    # Initialize local SQLite database
    from database.models import init_db
    init_db()
    
    # Check for bot token
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "your_bot_token_here":
        print("❌ Error: TELEGRAM_BOT_TOKEN not set!")
        return

    
    # Create application
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("books", books_command))
    application.add_handler(CommandHandler("resources", resources_command))
    application.add_handler(CommandHandler("stats", stats_command))
    
    # Add callback query handlers (for inline buttons)
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
    
    # Quick search handlers from start menu
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
    
    # Add text message handler (for plain text search)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_search_handler))
    
    # Set bot commands
    application.post_init = set_bot_commands
    
    # Start bot
    print("🤖 Bot is starting...")
    print("📚 Uzbek School Books Bot")
    print("Press Ctrl+C to stop")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
