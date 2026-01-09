"""
Search Handler
Handles search functionality for themes.
Uses Supabase search when configured, local search otherwise.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import sys
sys.path.append('../..')
from database.models import (
    get_session, Theme, Book,
    get_theme, get_book, use_supabase
)
from services.search_engine import SearchEngine

# Import Supabase search
try:
    from database.supabase_client import (
        search_themes as sb_search_themes,
        detect_language,
        track_search,
        track_user_action
    )
    SUPABASE_SEARCH = True
except ImportError:
    SUPABASE_SEARCH = False

# Initialize local search engine as fallback
search_engine = SearchEngine()


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /search command."""
    if context.args:
        query = ' '.join(context.args)
        await perform_search(update, context, query)
    else:
        await update.message.reply_text(
            "🔍 **Search for Topics**\n\n"
            "Usage: `/search <query>`\n"
            "Example: `/search Pifagor teoremasi`\n\n"
            "Or just type any text to search!",
            parse_mode='Markdown'
        )


async def perform_search(
    update: Update, 
    context: ContextTypes.DEFAULT_TYPE, 
    query: str, 
    offset: int = 0, 
    from_callback: bool = False
) -> None:
    """Perform search and display results."""
    
    # Store query for pagination
    if context and context.user_data is not None:
        context.user_data['last_search'] = query
        
    # Use Supabase search if available, otherwise use local engine
    limit = 5
    if SUPABASE_SEARCH and use_supabase():
        # Fetch limit + 1 to check for next page
        results = sb_search_themes(query, limit=limit + 1, offset=offset)
        
        # Convert to consistent format
        formatted_results = []
        for r in results:
            formatted_results.append({
                'theme_id': r.get('theme_id'),
                'book_id': r.get('book_id'),
                'name_uz': r.get('name_uz'),
                'name_ru': r.get('name_ru'),
                'subject': r.get('subject'),
                'grade': r.get('grade'),
                'book_title_uz': r.get('book_title_uz'),
                'book_title_ru': r.get('book_title_ru'),
                'score': r.get('relevance_score', 0),
                'query_lang': detect_language(query),
                'snippet': r.get('snippet', '')
            })
        results = formatted_results
    else:
        results = search_engine.search(query, limit=limit) # Local doesn't support offset yet easily
    
    # Check pagination
    has_next = len(results) > limit
    display_results = results[:limit]
    
    # Get the right message object
    if from_callback and update.callback_query:
        message = update.callback_query.message
    else:
        message = update.message
    
    # Get user for analytics
    user = update.effective_user
    
    # Track search analytics (only on first page)
    if SUPABASE_SEARCH and offset == 0:
        track_search(
            query=query,
            results_count=len(results),
            telegram_user_id=user.id if user else None,
            language_detected=detect_language(query)
        )
    
    if not display_results:
        text = (
            f"❌ No results found for: {query}\n\n"
            "Try:\n"
            "• Using different keywords\n"
            "• Searching in another language\n"
            "• Checking spelling"
        )
        if from_callback:
             await message.edit_text(text)
        else:
             await message.reply_text(text)
        return
    
    # Create response message
    start_num = offset + 1
    response_lines = [f"🔍 Natijalar / Results: {query} ({start_num}-{offset+len(display_results)})\n"]
    
    query_lang = display_results[0].get('query_lang', 'uz')
    
    for i, result in enumerate(display_results, start_num):
        theme_id = result.get('theme_id')
        
        # Get book title
        if query_lang == 'ru':
            book_title = result.get('book_title_ru') or result.get('book_title_uz') or 'Unknown'
        else:
            book_title = result.get('book_title_uz') or result.get('book_title_ru') or 'Unknown'
        
        grade = result.get('grade', '')
        start_page = result.get('start_page')
        end_page = result.get('end_page')
        
        # Get theme name
        theme_name_uz = result.get('name_uz')
        theme_name_ru = result.get('name_ru')
        
        if query_lang == 'ru':
            theme_name = theme_name_ru or theme_name_uz or 'Theme'
        else:
            theme_name = theme_name_uz or theme_name_ru or 'Mavzu'
            
        # Display: Theme name and book info (no snippet)
        display_text = f"📄 {theme_name}"
        
        # Only show page info if valid
        if start_page is not None and end_page is not None and end_page > 0:
            page_info = f"p.{start_page+1}-{end_page+1}"
        else:
            page_info = ""
            
        response_lines.append(
            f"{i}. {display_text}\n"
            f"   📚 {book_title} | {grade}-sinf" + (f" | {page_info}" if page_info else "")
        )
    
    # Add keyboard with select buttons
    keyboard = []
    for i, result in enumerate(display_results, start_num):
        theme_id = result.get('theme_id')
        theme_name = result.get('name_uz') or result.get('name_ru') or ''
        
        # Show theme name in button (cleaner)
        btn_text = f"{i}. {theme_name[:30]}"
        keyboard.append([
            InlineKeyboardButton(
                btn_text,
                callback_data=f"theme_{theme_id}"
            )
        ])
        
    # Navigation Buttons
    nav_buttons = []
    if offset > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Oldingi", callback_data=f"search_nav_{offset-limit}"))
    if has_next:
        nav_buttons.append(InlineKeyboardButton("Keyingi ➡️", callback_data=f"search_nav_{offset+limit}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if from_callback:
        await message.edit_text(
            '\n'.join(response_lines),
            reply_markup=reply_markup
        )
    else:
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
    
    # Use unified data access (Supabase or SQLite)
    theme = get_theme(theme_id)
    
    if not theme:
        await query.edit_message_text("❌ Mavzu topilmadi / Theme not found.")
        return
    
    book = get_book(theme.book_id)
    book_id = book.id if book else 0
    grade = book.grade if book else '?'
    subject = book.subject if book else '?'
    
    # Check what content is available
    has_uz = bool(theme.name_uz)
    has_ru = bool(theme.name_ru)
    
    # Check if PDF URLs are available (Supabase) or local paths
    has_uz_pdf = bool(book and book.pdf_path_uz) if book else False
    has_ru_pdf = bool(book and book.pdf_path_ru) if book else False
    
    # Determine display language based on what's available
    if has_uz:
        show_lang = 'uz'
        name = theme.name_uz
        book_title = book.title_uz or book.title_ru or subject if book else subject
    elif has_ru:
        show_lang = 'ru'
        name = theme.name_ru
        book_title = book.title_ru or book.title_uz or subject if book else subject
    else:
        show_lang = 'uz'
        name = f"Mavzu #{theme_id}"
        book_title = subject
    
    # Create theme details message - bilingual
    start_page = theme.start_page or 0
    end_page = theme.end_page or 0
    
    response = (
        f"📖 **Mavzu / Тема**\n\n"
        f"🇺🇿 {theme.name_uz or '-'}\n"
        f"🇷🇺 {theme.name_ru or '-'}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📚 {book_title}\n"
        f"📊 Sinf / Класс: {grade}\n"
        f"📁 Fan / Предмет: {subject}\n"
        f"📄 Sahifalar / Страницы: {start_page} - {end_page}\n"
    )
    
    # Create action buttons
    keyboard = []
    
    # AI buttons
    keyboard.append([
        InlineKeyboardButton("🤖 AI Xulosa", callback_data=f"summary_{theme_id}"),
        InlineKeyboardButton("📝 AI Test", callback_data=f"quiz_{theme_id}"),
    ])
    
    # Download buttons - show both languages if available
    download_row = []
    if has_uz_pdf:
        download_row.append(InlineKeyboardButton("📥 🇺🇿 PDF", callback_data=f"download_uz_{book_id}"))
    if has_ru_pdf:
        download_row.append(InlineKeyboardButton("📥 🇷🇺 PDF", callback_data=f"download_ru_{book_id}"))
    if download_row:
        keyboard.append(download_row)
    
    # Theme PDF (just this chapter) - show if we have valid page range
    # Note: start_page can be 0, so check for None explicitly
    if start_page is not None and end_page is not None and end_page > start_page:
        theme_rows = []
        if has_uz_pdf:
            theme_rows.append(InlineKeyboardButton("📄 Mavzu UZ", callback_data=f"theme_pdf_uz_{theme_id}"))
        if has_ru_pdf:
            theme_rows.append(InlineKeyboardButton("📄 Тема RU", callback_data=f"theme_pdf_ru_{theme_id}"))
        
        if theme_rows:
            keyboard.append(theme_rows)
    
    # Educational resources
    keyboard.append([
        InlineKeyboardButton("🔗 Ta'lim resurslari / Ресурсы", callback_data=f"resources_{theme_id}")
    ])
    
    # Back button - go back to search (not random book)
    keyboard.append([
        InlineKeyboardButton("🔙 Ortga / Back", callback_data="back_to_search")
    ])
    
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
    
    await perform_search(update, context, query)


async def handle_search_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle pagination (Next/Prev) for search."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith('search_nav_'):
        return

    # Parse offset
    try:
        offset = int(data.replace('search_nav_', ''))
    except ValueError:
        return
        
    # Get last query
    search_query = context.user_data.get('last_search')
    if not search_query:
        await query.message.reply_text("❌ Search session expired. Please search again.")
        return
        
    await perform_search(update, context, search_query, offset=offset, from_callback=True)


async def handle_back_to_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle back button from theme view - returns to last search."""
    query = update.callback_query
    await query.answer()
    
    # Get last search query
    search_query = context.user_data.get('last_search')
    if not search_query:
        await query.edit_message_text(
            "🔍 Yangi qidiruv uchun matn yozing.\n"
            "Type any text to search."
        )
        return
        
    await perform_search(update, context, search_query, offset=0, from_callback=True)
