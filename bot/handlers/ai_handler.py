"""
AI Handler
Handles AI-powered features like summaries and quizzes.
Uses Supabase when configured, SQLite otherwise.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import sys
sys.path.append('../..')

try:
    from database.supabase_client import (
        get_book_by_id as get_book,
        get_theme_by_id as get_theme,
        get_theme_with_book as get_theme_and_book,
        track_user_action, get_user_lang
    )
    ANALYTICS_AVAILABLE = True
except ImportError:
    from database.models import get_book, get_theme, get_theme_and_book
    ANALYTICS_AVAILABLE = False
    def track_user_action(*args, **kwargs): pass
    def get_user_lang(uid): return 'uz'

from services.ai_summary import generate_summary, generate_quiz
from bot.translations import get_text


async def handle_summary_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle AI Summary button click."""
    query = update.callback_query
    user_id = update.effective_user.id
    lang = get_user_lang(user_id) or 'uz'
    
    await query.answer(get_text('generating_summary', lang))
    
    callback_data = query.data
    # Supporting both formats (some handlers might use ai_sum_ or summary_)
    if callback_data.startswith('ai_sum_'):
        theme_id = int(callback_data.replace('ai_sum_', ''))
    elif callback_data.startswith('summary_'):
        theme_id = int(callback_data.replace('summary_', ''))
    else:
        return
    
    # Get theme with book (uses Supabase or SQLite automatically)
    theme = get_theme_and_book(theme_id)
    
    if not theme:
        await query.message.reply_text(get_text('theme_not_found', lang))
        return
    
    book = theme.get('books') if isinstance(theme, dict) else getattr(theme, '_book', None)
    
    # Track analytics
    if ANALYTICS_AVAILABLE:
        user = update.effective_user
        track_user_action(
            telegram_user_id=user.id,
            action_type="summary",
            telegram_username=user.username,
            first_name=user.first_name,
            action_data={"theme_id": theme_id}
        )
    
    # Determine content and AI output language
    # Strategy: Use content of current preferred language if available, else fallback
    content = theme.get('content_uz') if lang == 'uz' else theme.get('content_ru')
    ai_lang = lang
    
    if not content:
        content = theme.get('content_ru') if lang == 'uz' else theme.get('content_uz')
        ai_lang = 'ru' if lang == 'uz' else 'uz'
        
    name = theme.get('name_uz') if lang == 'uz' else theme.get('name_ru')
    name = name or theme.get('name_uz') or theme.get('name_ru')
    
    if not content or len(content) < 100:
        await query.message.reply_text(get_text('not_enough_content', lang))
        return
    
    # Generate summary
    try:
        summary = generate_summary(content, name, ai_lang)
        
        if summary:
            book_title = book.get('title_uz') if (book and isinstance(book, dict)) else (book.title_uz if book else None)
            if not book_title and book and isinstance(book, dict):
                book_title = book.get('title_ru')
            elif not book_title and book:
                book_title = book.title_ru
            
            book_title = book_title or 'Book'
            
            response = get_text('ai_summary_header', lang, theme_name=name, book_title=book_title, summary=summary)
            
            # Add buttons: Refresh and Back
            keyboard = [
                [InlineKeyboardButton(get_text('refresh_summary', lang), callback_data=f"ai_sum_{theme_id}")],
                [InlineKeyboardButton(get_text('back_to_theme', lang), callback_data=f"theme_{theme_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                response,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await query.message.reply_text(get_text('ai_generation_failed', lang))
    except Exception as e:
        await query.message.reply_text(get_text('error_message', lang, error_message=str(e)))


async def handle_quiz_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle AI Quiz button click."""
    query = update.callback_query
    user_id = update.effective_user.id
    lang = get_user_lang(user_id) or 'uz'
    
    await query.answer(get_text('generating_quiz', lang))
    
    callback_data = query.data
    # Supporting both formats
    if callback_data.startswith('ai_quiz_'):
        theme_id = int(callback_data.replace('ai_quiz_', ''))
    elif callback_data.startswith('quiz_'):
        theme_id = int(callback_data.replace('quiz_', ''))
    else:
        return
    
    # Get theme with book (uses Supabase or SQLite automatically)
    theme = get_theme_and_book(theme_id)
    
    if not theme:
        await query.message.reply_text(get_text('theme_not_found', lang))
        return
    
    book = theme.get('books') if isinstance(theme, dict) else getattr(theme, '_book', None)
    
    # Track analytics
    if ANALYTICS_AVAILABLE:
        user = update.effective_user
        track_user_action(
            telegram_user_id=user.id,
            action_type="quiz",
            telegram_username=user.username,
            first_name=user.first_name,
            action_data={"theme_id": theme_id, "language": lang}
        )
    
    # Determine content and AI output language
    content = theme.get('content_uz') if lang == 'uz' else theme.get('content_ru')
    ai_lang = lang
    
    if not content:
        content = theme.get('content_ru') if lang == 'uz' else theme.get('content_uz')
        ai_lang = 'ru' if lang == 'uz' else 'uz'
        
    name = theme.get('name_uz') if lang == 'uz' else theme.get('name_ru')
    name = name or theme.get('name_uz') or theme.get('name_ru')
    
    if not content or len(content) < 100:
        await query.message.reply_text(get_text('not_enough_content', lang))
        return
    
    # Generate quiz with 5 questions (shorter to fit Telegram limit)
    try:
        # Send loading message immediately
        loading_msg = await query.message.reply_text(get_text('generating_questions', lang))
        
        quiz = generate_quiz(content, name, num_questions=5, language=ai_lang)
        
        # Delete loading message
        try:
            await loading_msg.delete()
        except:
            pass
        
        # Check for rate limit
        if quiz == "RATE_LIMITED":
            await query.message.reply_text(get_text('ai_busy', lang))
            return
        
        if quiz:
            # Escape HTML special characters (except our spoiler tags)
            import html
            def escape_html_keep_spoilers(text):
                # First escape all HTML
                escaped = html.escape(text)
                # Then restore our spoiler tags
                escaped = escaped.replace('&lt;tg-spoiler&gt;', '<tg-spoiler>')
                escaped = escaped.replace('&lt;/tg-spoiler&gt;', '</tg-spoiler>')
                return escaped
            
            book_title = book.get('title_uz') if (book and isinstance(book, dict)) else (book.title_uz if book else None)
            if not book_title and book and isinstance(book, dict):
                book_title = book.get('title_ru')
            elif not book_title and book:
                book_title = book.title_ru
            
            book_title = book_title or 'Book'
            
            safe_name = html.escape(name)
            safe_book_title = html.escape(book_title)
            safe_quiz = escape_html_keep_spoilers(quiz)
            
            response = get_text('ai_quiz_header', lang, 
                                theme_name=safe_name, 
                                book_title=safe_book_title, 
                                quiz=safe_quiz)
            
            # Telegram limit is 4096, split if needed
            if len(response) > 4000:
                response = response[:3900] + "\n..."
            
            # Add buttons: Refresh and Back
            keyboard = [
                [InlineKeyboardButton(get_text('refresh_quiz', lang), callback_data=f"ai_quiz_{theme_id}")],
                [InlineKeyboardButton(get_text('back_to_theme', lang), callback_data=f"theme_{theme_id}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                response,
                reply_markup=reply_markup,
                parse_mode='HTML'
            )
        else:
            await query.message.reply_text(get_text('ai_generation_failed', lang))
    except Exception as e:
        print(f"Quiz error: {e}")
        await query.message.reply_text(get_text('error_message', lang, error_message=str(e)))
