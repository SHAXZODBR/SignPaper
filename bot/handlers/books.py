"""
Books Handler
Handles book browsing and PDF downloads.
Uses Supabase when configured, SQLite otherwise.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from pathlib import Path
import sys
sys.path.append('../..')
from bot.translations import get_text
try:
    from database.supabase_client import (
        get_all_books, get_books_by_grade, get_book_by_id,
        track_user_action, track_download, get_user_lang
    )
    # Import theme functions
    from database.supabase_client import get_themes_by_book, get_theme_by_id
except ImportError:
    # Fallback to local
    from database.models import get_all_books, get_books_by_grade, get_book_by_id
    from database.models import get_themes_by_book, get_theme_by_id
    def track_user_action(*args, **kwargs): pass
    def track_download(*args, **kwargs): pass
    def get_user_lang(uid): return 'uz' # Default to Uzbek if Supabase client not available

from services.pdf_processor import PDFProcessor, create_bilingual_theme_pdf
from config import OUTPUT_DIR


async def books_command(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback: bool = False) -> None:
    """Handle /books command - show language selection first."""
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)

    keyboard = [
        [InlineKeyboardButton(get_text("lang_uz_button", lang), callback_data="set_lang_uz")],
        [InlineKeyboardButton(get_text("lang_ru_button", lang), callback_data="set_lang_ru")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = get_text("select_language_prompt", lang)
    
    if from_callback:
        # Called from inline button - edit the existing message
        await update.callback_query.edit_message_text(
            message_text,
            reply_markup=reply_markup
        )
    else:
        # Called from /books command - send new message
        await update.message.reply_text(
            message_text,
            reply_markup=reply_markup
        )


async def handle_language_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle language selection - show grades for that language."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    if not callback_data.startswith('set_lang_'):
        return
    
    lang = callback_data.replace('set_lang_', '')  # 'uz' or 'ru'
    user_id = update.effective_user.id
    
    # Update user's language preference (assuming this is handled by supabase_client or similar)
    # For now, we'll just use it for the current session
    context.user_data['lang'] = lang

    # Track analytics
    track_user_action(
        telegram_user_id=user_id,
        action_type="set_language",
        telegram_username=update.effective_user.username,
        first_name=update.effective_user.first_name,
        action_data={"language": lang}
    )
    
    await browse_books(update, context)


async def handle_grade_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle grade selection."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    if not callback_data.startswith('grade_'):
        return
    
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    grade_range_str = callback_data.replace('grade_', '')
    
    # Parse grade range (e.g., "1-4", "5-9", "10-11")
    if '-' in grade_range_str:
        start_grade, end_grade = map(int, grade_range_str.split('-'))
        grade_range = list(range(start_grade, end_grade + 1))
    else:
        grade_range = [int(grade_range_str)] # Should not happen with current buttons

    # Get books for this grade range
    books = get_books_by_grade(grade_range)
    
    # Track analytics
    track_user_action(
        telegram_user_id=user_id,
        action_type="browse_grade",
        telegram_username=update.effective_user.username,
        first_name=update.effective_user.first_name,
        action_data={"grade_range": grade_range_str, "language": lang}
    )
    
    if not books:
        await query.message.edit_text(
            get_text('no_books_found', lang),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(get_text('back', lang), callback_data="browse_books")]])
        )
        return

    keyboard = []
    for book in books:
        title = book.get('title_uz') if lang == 'uz' else book.get('title_ru')
        title = title or book.get('title_uz') or book.get('title_ru')
        title = title[:35] + '...' if len(title) > 35 else title
        keyboard.append([InlineKeyboardButton(f"📖 {title}", callback_data=f"book_{book.get('id')}")])
    
    keyboard.append([InlineKeyboardButton(get_text('back', lang), callback_data="browse_books")])
    
    await query.message.edit_text(
        get_text('select_book', lang, grade=grade_range_str),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_book_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle book selection - show book details."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    if not callback_data.startswith('book_'):
        return
    
    book_id = int(callback_data.replace('book_', ''))
    
    user_id = update.effective_user.id
    lang = get_user_lang(user_id)
    
    book = get_book_by_id(book_id)
    
    if not book:
        await query.message.edit_text(get_text('error_occurred', lang))
        return

    themes = get_themes_by_book(book_id)
    
    # Track analytics
    track_user_action(
        telegram_user_id=user_id,
        action_type="view_book",
        telegram_username=update.effective_user.username,
        first_name=update.effective_user.first_name,
        action_data={"book_id": book_id, "language": lang}
    )
    
    # Book details text
    title = book.get('title_uz') if lang == 'uz' else book.get('title_ru')
    title = title or book.get('title_uz') or book.get('title_ru')
    
    text = get_text('book_details', lang, title=title, grade=book.get('grade'), subject=book.get('subject'), themes_count=len(themes))
    
    keyboard = []
    # Themes list (first 15 for brevity, can implement pagination later)
    for theme in themes[:15]:
        name = theme.get('name_uz') if lang == 'uz' else theme.get('name_ru')
        name = name or theme.get('name_uz') or theme.get('name_ru')
        name = name[:35] + '...' if len(name) > 35 else name
        keyboard.append([InlineKeyboardButton(f"📑 {name}", callback_data=f"theme_{theme['id']}")])
    
    # PDF download buttons - check if available for current language
    has_pdf = (lang == 'uz' and book.get('pdf_path_uz')) or (lang == 'ru' and book.get('pdf_path_ru'))
    if has_pdf:
        keyboard.append([InlineKeyboardButton(get_text('download_full_pdf', lang, lang_upper=lang.upper()), callback_data=f"dl_book_{book['id']}_{lang}")])
    
    # Add alternative language PDF if available
    alt_lang = 'ru' if lang == 'uz' else 'uz'
    has_alt_pdf = (alt_lang == 'uz' and book.get('pdf_path_uz')) or (alt_lang == 'ru' and book.get('pdf_path_ru'))
    if has_alt_pdf:
        keyboard.append([InlineKeyboardButton(get_text('download_full_pdf', alt_lang, lang_upper=alt_lang.upper()), callback_data=f"dl_book_{book['id']}_{alt_lang}")])

    keyboard.append([InlineKeyboardButton(get_text('back', lang), callback_data=f"grade_{book.get('grade')}-{book.get('grade')}")]) # Go back to specific grade range
    
    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def handle_book_pdf_download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle book PDF download request - supports Supabase Storage URLs and local files."""
    query = update.callback_query
    user_id = update.effective_user.id
    user_lang = get_user_lang(user_id)
    await query.answer(get_text("preparing_pdf", user_lang))
    
    callback_data = query.data
    
    # Determine language and book_id
    if callback_data.startswith('dl_book_'):
        parts = callback_data.split('_')
        book_id = int(parts[2])
        language = parts[3]
    else:
        # Fallback for legacy or unexpected format
        await query.message.reply_text(get_text("error_occurred", user_lang))
        return
    
    # Get book using unified data access
    book = get_book_by_id(book_id)
    
    if not book:
        await query.message.reply_text(get_text("book_not_found", user_lang))
        return
    
    # Track download analytics
    track_download(
        book_id=book_id,
        download_type="book_pdf",
        language=language,
        telegram_user_id=user_id
    )
    
    # Try to get PDF URL from Supabase Storage first
    pdf_url = book.get('pdf_path_uz') if language == 'uz' else book.get('pdf_path_ru')
    actual_lang = language
    
    # Fallback to other language URL if not available
    if not pdf_url:
        alt_url = book.get('pdf_path_ru') if language == 'uz' else book.get('pdf_path_uz')
        if alt_url:
            pdf_url = alt_url
            actual_lang = 'ru' if language == 'uz' else 'uz'
    
    # If we have a Supabase URL, download and send the file directly
    if pdf_url and pdf_url.startswith('http'):
        title = book.get('title_uz') if actual_lang == 'uz' else book.get('title_ru')
        title = title or book.get('title_ru') or book.get('title_uz') or book.get('subject')
        lang_emoji = "🇺🇿" if actual_lang == 'uz' else "🇷🇺"
        
        # Send loading message
        loading_msg = await query.message.reply_text(get_text("loading_pdf", user_lang))
        
        try:
            import aiohttp
            import io
            
            # Download PDF from Supabase Storage
            async with aiohttp.ClientSession() as session:
                async with session.get(pdf_url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                    if resp.status == 200:
                        pdf_data = await resp.read()
                        pdf_file = io.BytesIO(pdf_data)
                        pdf_file.name = f"{title}.pdf"
                        
                        # Delete loading message
                        try:
                            await loading_msg.delete()
                        except:
                            pass
                        
                        # Send the PDF document directly
                        await query.message.reply_document(
                            document=pdf_file,
                            filename=f"{title}.pdf",
                            caption=get_text("book_pdf_caption", user_lang, lang_emoji=lang_emoji, title=title, grade=book.get('grade'), subject=book.get('subject')),
                            read_timeout=120,
                            write_timeout=120
                        )
                        return
                    else:
                        raise Exception(f"Download failed: {resp.status}")
        except Exception as e:
            # Delete loading message
            try:
                await loading_msg.delete()
            except:
                pass
            
            # Show error with direct link as fallback
            keyboard = [[InlineKeyboardButton(
                get_text("open_in_browser", user_lang, lang_emoji=lang_emoji), 
                url=pdf_url
            )]]
            await query.message.reply_text(
                get_text("pdf_download_error_with_link", user_lang, error_message=str(e)[:50]),
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
    
    # Fallback to local file paths
    pdf_path = book.get('pdf_path_uz') if language == 'uz' else book.get('pdf_path_ru')
    actual_lang = language
    
    # Fallback to other language if not available
    if not pdf_path or not (isinstance(pdf_path, str) and Path(pdf_path).exists()):
        alt_path = book.get('pdf_path_ru') if language == 'uz' else book.get('pdf_path_uz')
        if alt_path and isinstance(alt_path, str) and Path(alt_path).exists():
            pdf_path = alt_path
            actual_lang = 'ru' if language == 'uz' else 'uz'
        else:
            await query.message.reply_text(get_text("pdf_file_not_found", user_lang))
            return
    
    # Send the local PDF file
    try:
        title = book.title_uz if actual_lang == 'uz' else book.title_ru
        title = title or book.title_ru or book.title_uz or book.subject
        lang_emoji = "🇺🇿" if actual_lang == 'uz' else "🇷🇺"
        
        await query.message.reply_document(
            document=open(pdf_path, 'rb'),
            filename=f"{title}.pdf",
            caption=get_text("book_pdf_caption", user_lang, lang_emoji=lang_emoji, title=title, grade=book.get('grade'), subject=book.get('subject')),
            read_timeout=120,
            write_timeout=120
        )
    except Exception as e:
        await query.message.reply_text(get_text("pdf_sending_error", user_lang, error_message=str(e)))


async def handle_theme_pdf_download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle theme PDF download - creates bilingual PDF."""
    query = update.callback_query
    user_id = update.effective_user.id
    user_lang = get_user_lang(user_id)
    await query.answer(get_text("generating_pdf", user_lang))
    
    callback_data = query.data
    print(f"[PDF DEBUG] Callback: {callback_data}")
    
    if not callback_data.startswith('theme_pdf_'):
        print(f"[PDF DEBUG] Invalid callback format")
        return
    
    # Parse callback: theme_pdf_uz_123 or theme_pdf_ru_123
    data_part = callback_data.replace('theme_pdf_', '')
    if data_part.startswith('uz_'):
        req_lang = 'uz'
        theme_id = int(data_part.replace('uz_', ''))
    elif data_part.startswith('ru_'):
        req_lang = 'ru'
        theme_id = int(data_part.replace('ru_', ''))
    else:
        # Legacy
        req_lang = 'uz'
        theme_id = int(data_part)
    
    print(f"[PDF DEBUG] Theme ID: {theme_id}, Lang: {req_lang}")
    
    # Use unified data access
    theme = get_theme_by_id(theme_id)
    
    if not theme:
        print(f"[PDF DEBUG] Theme not found")
        await query.message.reply_text(get_text("theme_not_found", user_lang))
        return
    
    print(f"[PDF DEBUG] Theme: {theme.get('name_uz')}, Pages: {theme.get('start_page')}-{theme.get('end_page')}")
    
    book = get_book_by_id(theme.get('book_id'))
    
    if not book:
        print(f"[PDF DEBUG] Book not found")
        await query.message.reply_text(get_text("book_not_found", user_lang))
        return
    
    print(f"[PDF DEBUG] Book: {book.get('title_uz')}, PDF UZ: {book.get('pdf_path_uz')}")
    
    # Determine which PDF to use
    if req_lang == 'uz':
        pdf_path = book.get('pdf_path_uz')
        lang_name = get_text("uzbek_language", user_lang)
        emoji = "🇺🇿"
    else:
        pdf_path = book.get('pdf_path_ru')
        lang_name = get_text("russian_language", user_lang)
        emoji = "🇷🇺"
    
    print(f"[PDF DEBUG] PDF path: {pdf_path}")
    
    # Support for Supabase Storage URLs
    temp_pdf_path = None
    if pdf_path and pdf_path.startswith('http'):
        import aiohttp
        import tempfile
        
        print(f"[PDF DEBUG] Downloading book PDF from URL for extraction: {pdf_path}")
        loading_msg = await query.message.reply_text(get_text("downloading_book_for_extraction", user_lang))
        
        try:
            temp_dir = Path("data/temp_books")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Use filename as unique identifier for caching
            filename = pdf_path.split('/')[-1]
            temp_pdf_path = temp_dir / filename
            
            if not temp_pdf_path.exists():
                async with aiohttp.ClientSession() as session:
                    async with session.get(pdf_path, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                        if resp.status == 200:
                            content = await resp.read()
                            with open(temp_pdf_path, 'wb') as f:
                                f.write(content)
                        else:
                            raise Exception(f"Failed to download book: {resp.status}")
            
            pdf_path = str(temp_pdf_path)
            await loading_msg.delete()
        except Exception as e:
            if 'loading_msg' in locals(): await loading_msg.delete()
            await query.message.reply_text(get_text("book_download_failed", user_lang, error_message=str(e)))
            return
            
    if not pdf_path or not Path(pdf_path).exists():
        print(f"[PDF DEBUG] PDF file not found at: {pdf_path}")
        await query.message.reply_text(get_text("pdf_file_missing", user_lang, lang_name=lang_name))
        return
    
    # Generate filename
    theme_name = (theme.get('name_uz') if req_lang == 'uz' else theme.get('name_ru')) or f"theme_{theme_id}"
    safe_name = "".join(c for c in theme_name if c.isalnum() or c in (' ', '-', '_'))[:50]
    output_filename = f"{safe_name}_{req_lang}.pdf"
    
    print(f"[PDF DEBUG] Extracting pages {theme.get('start_page')}-{theme.get('end_page')} to {output_filename}")
    
    try:
        processor = PDFProcessor(pdf_path)
        if processor.open():
            output_path = processor.extract_theme_pdf(
                theme.get('start_page') or 0,
                theme.get('end_page') or 0,
                output_filename
            )
            processor.close()
            
            if output_path and output_path.exists():
                print(f"[PDF DEBUG] Generated: {output_path}")
                
                # Check file size (Telegram limit is 50MB, use 45MB to be safe)
                file_size_mb = output_path.stat().st_size / (1024 * 1024)
                print(f"[PDF DEBUG] File size: {file_size_mb:.2f} MB")
                
                if file_size_mb > 45:
                    await query.message.reply_text(get_text("pdf_too_large", user_lang, file_size=f"{file_size_mb:.1f}"))
                    return
                
                start_page = (theme.get('start_page') or 0) + 1
                end_page = (theme.get('end_page') or 0) + 1
                await query.message.reply_document(
                    document=open(output_path, 'rb'),
                    filename=output_filename,
                    caption=get_text("theme_pdf_caption", user_lang, emoji=emoji, theme_name=safe_name, start_page=start_page, end_page=end_page, book_title=(book.get('title_uz') if user_lang == 'uz' else book.get('title_ru'))),
                    read_timeout=120,
                    write_timeout=120
                )
                print(f"[PDF DEBUG] Sent successfully!")
                return
            else:
                print(f"[PDF DEBUG] extract_theme_pdf returned: {output_path}")
            
        else:
            print(f"[PDF DEBUG] processor.open() failed")
            
        await query.message.reply_text(get_text("failed_to_generate_pdf", user_lang))
    except Exception as e:
        print(f"[PDF DEBUG] Exception: {e}")
        await query.message.reply_text(get_text("error_message", user_lang, error_message=str(e)))
            


async def handle_themes_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show list of themes for a book."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    if not callback_data.startswith('theme_'): # This callback is for a single theme, not themes list
        return
    
    theme_id = int(callback_data.replace('theme_', ''))

    user_id = update.effective_user.id
    lang = get_user_lang(user_id)

    theme = get_theme_by_id(theme_id)
    if not theme:
        await query.message.edit_text(get_text('theme_not_found', lang))
        return
    
    book = get_book_by_id(theme.get('book_id'))
    if not book:
        await query.message.edit_text(get_text('book_not_found', lang))
        return

    theme_name = theme.get('name_uz') if lang == 'uz' else theme.get('name_ru')
    theme_name = theme_name or theme.get('name_uz') or theme.get('name_ru')

    book_title = book.get('title_uz') if lang == 'uz' else book.get('title_ru')
    book_title = book_title or book.get('title_uz') or book.get('title_ru')

    text = get_text('theme_details', lang, theme_name=theme_name, book_title=book_title, start_page=(theme.get('start_page') or 0) + 1, end_page=(theme.get('end_page') or 0) + 1)

    keyboard = [
        [InlineKeyboardButton(get_text('download_theme_pdf', lang), callback_data=f"theme_pdf_{lang}_{theme_id}")],
        [InlineKeyboardButton(get_text('back', lang), callback_data=f"book_{book.get('id')}")]
    ]

    await query.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def browse_books(update: Update, context) -> None:
    """Show grade selection menu."""
    query = update.callback_query
    if query:
        await query.answer()
        user_id = update.effective_user.id
    else:
        user_id = update.effective_user.id

    lang = get_user_lang(user_id)
    
    keyboard = [
        [
            InlineKeyboardButton("1-4", callback_data="grade_1-4"),
            InlineKeyboardButton("5-9", callback_data="grade_5-9"),
            InlineKeyboardButton("10-11", callback_data="grade_10-11")
        ],
        [InlineKeyboardButton(get_text('back', lang), callback_data="back_to_start")]
    ]
    
    markup = InlineKeyboardMarkup(keyboard)
    text = get_text('select_grade', lang)
    
    if query:
        await query.message.edit_text(text, reply_markup=markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode='Markdown')


async def handle_back_languages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle back button to language selection."""
    query = update.callback_query
    await query.answer()
    await books_command(update, context, from_callback=True)
