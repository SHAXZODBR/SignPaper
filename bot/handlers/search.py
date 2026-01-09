"""
Search Handler
Handles search functionality for themes.
Uses Supabase search when configured, local search otherwise.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import sys
sys.path.append('../..')
from bot.translations import get_text
from database.models import (
    get_session, Theme, Book,
    use_supabase
)

# Import Supabase search
try:
    from database.supabase_client import (
        search_themes as sb_search_themes,
        detect_language,
        track_search,
        track_user_action,
        get_user_lang,
        get_theme_by_id,
        get_book_by_id
    )
    SUPABASE_SEARCH = True
except ImportError:
    SUPABASE_SEARCH = False
    def get_user_lang(uid): return 'uz'
    # Fallback to local handles if not in Supabase environment
    from database.models import get_theme as get_theme_by_id, get_book as get_book_by_id

# Initialize local search engine as fallback
from services.search_engine import get_search_engine
search_engine = get_search_engine()


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /search command."""
    lang = get_user_lang(update.effective_user.id)
    if context.args:
        query = ' '.join(context.args)
        await perform_search(update, context, query)
    else:
        await update.message.reply_text(
            get_text('search_usage', lang),
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
    
    user = update.effective_user
    lang = get_user_lang(user.id)
    
    # Track search analytics (only on first page)
    if SUPABASE_SEARCH and offset == 0:
        track_search(
            query=query,
            results_count=len(results),
            telegram_user_id=user.id if user else None,
            language_detected=detect_language(query)
        )
    
    if not display_results:
        text = get_text('no_results', lang, query=query)
        if from_callback:
             await message.edit_text(text, parse_mode='Markdown')
        else:
             await message.reply_text(text, parse_mode='Markdown')
        return
    
    # Create response message
    start_num = offset + 1
    response_lines = [get_text('search_results_header', lang, query=query, start=start_num, end=offset+len(display_results))]
    
    for i, result in enumerate(display_results, start_num):
        # Get theme name based on user language or detection
        theme_name = result.get(f'name_{lang}') or result.get('name_uz') or result.get('name_ru') or 'Theme'
        book_title = result.get(f'book_title_{lang}') or result.get('book_title_uz') or result.get('book_title_ru') or 'Book'
        
        grade = result.get('grade', '')
        start_page = result.get('start_page')
        end_page = result.get('end_page')
        
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
        theme_name = result.get(f'name_{lang}') or result.get('name_uz') or result.get('name_ru') or 'Theme'
        
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
        nav_buttons.append(InlineKeyboardButton(get_text('prev', lang), callback_data=f"search_nav_{offset-limit}"))
    if has_next:
        nav_buttons.append(InlineKeyboardButton(get_text('next', lang), callback_data=f"search_nav_{offset+limit}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if from_callback:
        await message.edit_text(
            '\n'.join(response_lines),
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await message.reply_text(
            '\n'.join(response_lines),
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
async def handle_theme_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle theme selection from search results."""
    query = update.callback_query
    await query.answer()
    
    theme_id = int(query.data.replace('theme_', ''))
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    # Use unified data access (Supabase or SQLite)
    theme = get_theme_by_id(theme_id)
    
    if not theme:
        await query.edit_message_text(get_text('theme_not_found', lang))
        return
    
    book = get_book_by_id(theme['book_id'])
    book_id = book['id'] if book else 0
    grade = book['grade'] if book else '?'
    
    # Track analytics
    track_user_action(
        telegram_user_id=user_id,
        action_type="view_theme",
        telegram_username=update.effective_user.username,
        first_name=update.effective_user.first_name,
        action_data={"theme_id": theme_id, "book_id": theme['book_id'], "language": lang}
    )

    theme_name = theme.get('name_uz') if lang == 'uz' else theme.get('name_ru')
    theme_name = theme_name or theme.get('name_uz') or theme.get('name_ru')
    
    book_title = book.get('title_uz') if lang == 'uz' else book.get('title_ru')
    book_title = book_title or book.get('title_uz') or book.get('title_ru')
    
    # Create theme details message
    start_page = theme.get('start_page') or 0
    end_page = theme.get('end_page') or 0
    
    response = get_text('theme_details_full', lang, 
                        theme_name=theme_name, 
                        book_title=book_title, 
                        grade=grade,
                        subject=book.get('subject') if book else "?",
                        start_page=start_page+1, 
                        end_page=end_page+1)
    
    # Create action buttons
    keyboard = []
    
    # AI buttons
    keyboard.append([
        InlineKeyboardButton(get_text('ai_summary', lang), callback_data=f"ai_sum_{theme_id}"),
        InlineKeyboardButton(get_text('ai_quiz', lang), callback_data=f"ai_quiz_{theme_id}"),
    ])
    
    # Check if PDF URLs are available
    has_uz_pdf = bool(book and book.get('pdf_path_uz'))
    has_ru_pdf = bool(book and book.get('pdf_path_ru'))
    
    # Download buttons
    download_row = []
    if has_uz_pdf:
        download_row.append(InlineKeyboardButton(get_text('download_full_pdf', 'uz'), callback_data=f"dl_book_{book_id}_uz"))
    if has_ru_pdf:
        download_row.append(InlineKeyboardButton(get_text('download_full_pdf', 'ru'), callback_data=f"dl_book_{book_id}_ru"))
    if download_row:
        keyboard.append(download_row)
    
    # Theme PDF (just this chapter)
    if start_page is not None and end_page is not None and end_page > start_page:
        theme_rows = []
        if has_uz_pdf:
            theme_rows.append(InlineKeyboardButton(get_text('download_theme_pdf', 'uz'), callback_data=f"theme_pdf_uz_{theme_id}"))
        if has_ru_pdf:
            theme_rows.append(InlineKeyboardButton(get_text('download_theme_pdf', 'ru'), callback_data=f"theme_pdf_ru_{theme_id}"))
        
        if theme_rows:
            keyboard.append(theme_rows)
    
    # Educational resources
    keyboard.append([
        InlineKeyboardButton(get_text('educational_resources', lang), callback_data=f"resources_{theme_id}")
    ])
    
    # Back button
    keyboard.append([
        InlineKeyboardButton(get_text('back', lang), callback_data="back_to_search")
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        response,
        reply_markup=reply_markup,
        parse_mode='Markdown'
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
    
    lang = get_user_lang(update.effective_user.id)
    
    # Get last search query
    search_query = context.user_data.get('last_search')
    if not search_query:
        await query.edit_message_text(get_text('new_search_prompt', lang))
        return
        
    await perform_search(update, context, search_query, offset=0, from_callback=True)
