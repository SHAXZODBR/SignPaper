"""
Search Handler
Handles search functionality for themes.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import sys
sys.path.append('../..')
from database.models import get_session, Theme, Book
from services.search_engine import SearchEngine


# Initialize search engine
search_engine = SearchEngine()


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /search command."""
    if context.args:
        query = ' '.join(context.args)
        await perform_search(update, query)
    else:
        await update.message.reply_text(
            "🔍 **Search for Topics**\n\n"
            "Usage: `/search <query>`\n"
            "Example: `/search Pifagor teoremasi`\n\n"
            "Or just type any text to search!",
            parse_mode='Markdown'
        )


async def perform_search(update: Update, query: str, from_callback: bool = False) -> None:
    """Perform search and display results."""
    results = search_engine.search(query, limit=10)
    
    # Get the right message object
    if from_callback and update.callback_query:
        message = update.callback_query.message
    else:
        message = update.message
    
    if not results:
        await message.reply_text(
            f"❌ No results found for: {query}\n\n"
            "Try:\n"
            "• Using different keywords\n"
            "• Searching in another language\n"
            "• Checking spelling"
        )
        return
    
    # Create response message
    response_lines = [f"🔍 Results for: {query}\n"]
    
    session = get_session()
    
    for i, result in enumerate(results[:5], 1):
        theme_id = result.get('theme_id')
        theme = session.query(Theme).filter(Theme.id == theme_id).first()
        if theme:
            book = session.query(Book).filter(Book.id == theme.book_id).first()
            name = theme.name_uz or theme.name_ru or 'Unknown'
            book_title = book.title_uz or book.title_ru or 'Unknown' if book else 'Unknown'
            grade = book.grade if book else ''
            
            response_lines.append(
                f"{i}. {name}\n"
                f"   📚 {book_title} | Grade {grade}"
            )
    
    # Add keyboard with select buttons
    keyboard = []
    for i, result in enumerate(results[:5], 1):
        theme_id = result.get('theme_id')
        theme = session.query(Theme).filter(Theme.id == theme_id).first()
        if theme:
            name = theme.name_uz or theme.name_ru or 'Theme'
            name = name[:30] + '...' if len(name) > 30 else name
            keyboard.append([
                InlineKeyboardButton(
                    f"{i}. {name}",
                    callback_data=f"theme_{theme_id}"
                )
            ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await message.reply_text(
        '\n'.join(response_lines),
        reply_markup=reply_markup
    )


async def handle_theme_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle theme selection from search results."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    if not callback_data.startswith('theme_'):
        return
    
    theme_id = int(callback_data.replace('theme_', ''))
    
    session = get_session()
    theme = session.query(Theme).filter(Theme.id == theme_id).first()
    
    if not theme:
        await query.edit_message_text("❌ Theme not found.")
        return
    
    book = session.query(Book).filter(Book.id == theme.book_id).first()
    
    # Create theme details message
    name_uz = theme.name_uz or "-"
    name_ru = theme.name_ru or "-"
    book_title = book.title_uz or book.title_ru or "Unknown Book" if book else "Unknown Book"
    grade = book.grade if book else '?'
    book_id = book.id if book else 0
    
    response = (
        f"📖 Theme Details\n\n"
        f"🇺🇿 O'zbekcha: {name_uz}\n"
        f"🇷🇺 Русский: {name_ru}\n\n"
        f"📚 Book: {book_title}\n"
        f"📊 Grade: {grade}\n"
        f"📄 Pages: {theme.start_page or 0} - {theme.end_page or 0}\n"
    )
    
    # Create action buttons
    keyboard = [
        [
            InlineKeyboardButton("📝 AI Summary", callback_data=f"summary_{theme_id}"),
            InlineKeyboardButton("📋 AI Quiz", callback_data=f"quiz_{theme_id}"),
        ],
        [
            InlineKeyboardButton("🇺🇿 PDF (UZ)", callback_data=f"download_uz_{book_id}"),
            InlineKeyboardButton("🇷🇺 PDF (RU)", callback_data=f"download_ru_{book_id}"),
        ],
        [
            InlineKeyboardButton("📄 Theme PDF (UZ+RU)", callback_data=f"theme_pdf_{theme_id}"),
        ],
        [
            InlineKeyboardButton("🔗 Educational Resources", callback_data=f"resources_{theme_id}"),
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        response,
        reply_markup=reply_markup
    )


async def text_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text messages as search queries."""
    query = update.message.text.strip()
    
    # Ignore very short queries
    if len(query) < 2:
        return
    
    # Ignore if it looks like a command
    if query.startswith('/'):
        return
    
    await perform_search(update, query)
