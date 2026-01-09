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
    ContextTypes,
)
import sys
sys.path.append('..')
from config import TELEGRAM_BOT_TOKEN
from database.models import init_db
from bot.handlers.search import (
    search_command,
    handle_theme_selection,
    text_search_handler,
    handle_search_pagination,
    handle_back_to_search,
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
    ADMIN_CHAT_ID,
)

# Import analytics and settings
try:
    from database.supabase_client import (
        track_user_action, track_download,
        get_user_lang, set_user_lang,
        get_stats
    )
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False
    # Fallback if Supabase client not fully updated
    def get_user_lang(uid): return 'uz'
    def set_user_lang(uid, lang): return False
    def get_stats(): return {}

from bot.translations import get_text

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# PROFESSIONAL WELCOME MESSAGE
# ═══════════════════════════════════════════════════════════════════════════

async def start_command(update: Update, context, from_callback: bool = False) -> None:
    """Handle /start command with custom grid menu."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    user = update.effective_user
    
    # Track user visit
    if ANALYTICS_AVAILABLE:
        try:
            track_user_action(
                telegram_user_id=user.id,
                action_type="start",
                telegram_username=user.username,
                first_name=user.first_name,
                action_data={"source": "start_command"}
            )
        except:
            pass
    
    # Get user language preference
    lang = get_user_lang(user.id)
    
    # Use bilingual welcome message
    welcome_message = get_text('welcome_bilingual', lang, name=user.first_name)
    
    # Grid layout matching screenshot
    keyboard = [
        [
            InlineKeyboardButton(get_text('subject_sonlar', lang), callback_data="search_sonlar"),
            InlineKeyboardButton(get_text('subject_matematika', lang), callback_data="search_matematika")
        ],
        [
            InlineKeyboardButton(get_text('subject_kimyo', lang), callback_data="search_kimyo"),
            InlineKeyboardButton(get_text('subject_fizika', lang), callback_data="search_fizika")
        ],
        [
            InlineKeyboardButton(get_text('subject_biologiya', lang), callback_data="search_biologiya"),
            InlineKeyboardButton(get_text('subject_tarix', lang), callback_data="search_tarix")
        ],
        [
            InlineKeyboardButton(get_text('kitoblar_books', lang), callback_data="browse_books")
        ],
        [
            InlineKeyboardButton(get_text('yordam_support', lang), callback_data="show_support"),
            InlineKeyboardButton(get_text('baholash', lang), callback_data="show_feedback")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if from_callback and update.callback_query:
        await update.callback_query.message.edit_text(
            welcome_message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    elif update.message:
        await update.message.reply_text(
            welcome_message, 
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    else:
        # Fallback
        await update.effective_message.reply_text(
            welcome_message,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )


async def lang_command(update: Update, context) -> None:
    """Handle /lang command for language selection."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [
            InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="set_lang_uz"),
            InlineKeyboardButton("🇷🇺 Русский", callback_data="set_lang_ru")
        ],
        [InlineKeyboardButton(get_text('back', get_user_lang(update.effective_user.id)), callback_data="back_to_start")]
    ]
    
    await update.message.reply_text(
        get_text('select_language', get_user_lang(update.effective_user.id)),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

 
 


async def set_language_handler(update: Update, context) -> None:
    """Handle language selection callback."""
    query = update.callback_query
    await query.answer()
    
    lang = query.data.replace("set_lang_", "")
    user = update.effective_user
    
    # Save setting
    set_user_lang(user.id, lang)
    
    # Confirm and show welcome again with new language
    await query.message.edit_text(
        get_text('lang_changed', lang),
        parse_mode='Markdown'
    )
    
    # Trigger start command logic after a short delay or just show menu
    await start_command(update, context, from_callback=True)


async def help_command(update: Update, context) -> None:
    """Handle /help command."""
    lang = get_user_lang(update.effective_user.id)
    await update.message.reply_text(get_text('help', lang), parse_mode='Markdown')


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /stats command with localization."""
    lang = get_user_lang(update.effective_user.id)
    # Check if user is admin
    if str(update.effective_user.id) != str(ADMIN_CHAT_ID):
        await update.message.reply_text(get_text('admin_only', lang))
        return
        
    try:
        stats = get_stats()
        
        response = get_text('stats_report', lang, 
                            users=stats.get('total_users', 0),
                            searches=stats.get('total_searches', 0),
                            downloads=stats.get('total_downloads', 0))
        
        await update.message.reply_text(response, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"Error fetching stats: {e}")


async def set_bot_commands(application: Application) -> None:
    """Set bot commands for the menu."""
    commands = [
        BotCommand("start", "🏠 Start / Boshlash"),
        BotCommand("search", "🔍 Search / Qidirish"),
        BotCommand("books", "📚 Books / Kitoblar"),
        BotCommand("lang", "🌐 Language / Til"),
        BotCommand("support", "📞 Support / Yordam"),
        BotCommand("help", "❓ Help / Yordam"),
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
    application.add_handler(CommandHandler("lang", lang_command))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CommandHandler("books", books_command))
    application.add_handler(CommandHandler("resources", resources_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("feedback", feedback_command))
    application.add_handler(CommandHandler("myid", myid_command))
    application.add_handler(CommandHandler("reply", reply_command))
    
    # Support conversation handler
    support_conv = ConversationHandler(
        entry_points=[
            CommandHandler("support", support_command),
            CallbackQueryHandler(support_command, pattern="^show_support$")
        ],
        states={
            WAITING_FOR_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_support_message)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_support, pattern="^cancel_support$"),
            CommandHandler("cancel", cancel_support),
            CallbackQueryHandler(back_to_start, pattern="^back_to_start$"),
        ],
        allow_reentry=True
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
    application.add_handler(CallbackQueryHandler(handle_theme_pdf_download, pattern=r"^theme_pdf_(?:(?:uz|ru)_)?\d+$"))
    application.add_handler(CallbackQueryHandler(handle_themes_list, pattern=r"^themes_(uz|ru)_\d+$"))
    
    # Search Pagination
    application.add_handler(CallbackQueryHandler(handle_search_pagination, pattern=r"^search_nav_"))
    application.add_handler(CallbackQueryHandler(handle_back_to_search, pattern=r"^back_to_search$"))
    application.add_handler(CallbackQueryHandler(handle_resources, pattern=r"^resources_\d+$"))
    application.add_handler(CallbackQueryHandler(handle_back_languages, pattern=r"^back_languages$"))
    
    # AI handlers
    application.add_handler(CallbackQueryHandler(handle_summary_request, pattern=r"^summary_\d+$"))
    application.add_handler(CallbackQueryHandler(handle_quiz_request, pattern=r"^quiz_\d+$"))
    
    # Rating handler
    application.add_handler(CallbackQueryHandler(handle_rating, pattern=r"^rate_\d$"))
    
    # Language setter handler
    application.add_handler(CallbackQueryHandler(set_language_handler, pattern=r"^set_lang_"))
    
    # Back to start
    async def back_to_start(update: Update, context):
        await start_command(update, context)
    application.add_handler(CallbackQueryHandler(back_to_start, pattern=r"^back_to_start$"))
    
    application.add_handler(CallbackQueryHandler(feedback_command, pattern=r"^show_feedback$"))
    
    # Quick search from start menu
    async def handle_quick_search(update: Update, context):
        query = update.callback_query
        await query.answer()
        search_term = query.data.replace("search_", "")
        from bot.handlers.search import perform_search
        await perform_search(update, context, search_term, from_callback=True)
    
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
    print("=" * 50)
    print("SignPaper Bot - Starting...")
    print("=" * 50)
    print("Bot is running!")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
