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
from database.models import (
    get_session, Book, Theme,
    get_book, get_theme, fetch_books_by_grade, fetch_themes_by_book, count_book_themes,
    use_supabase
)
from services.pdf_processor import PDFProcessor, create_bilingual_theme_pdf
from config import OUTPUT_DIR

# Import analytics tracking
try:
    from database.supabase_client import track_download, track_user_action
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False


async def books_command(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback: bool = False) -> None:
    """Handle /books command - show language selection first."""
    keyboard = [
        [InlineKeyboardButton("🇺🇿 O'zbekcha / Uzbek", callback_data="lang_uz")],
        [InlineKeyboardButton("🇷🇺 Русский / Russian", callback_data="lang_ru")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    message_text = (
        "📚 Kitoblarni ko'rish / Browse Books\n\n"
        "Tilni tanlang / Select language:"
    )
    
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
    if not callback_data.startswith('lang_'):
        return
    
    lang = callback_data.replace('lang_', '')  # 'uz' or 'ru'
    lang_emoji = "🇺🇿" if lang == 'uz' else "🇷🇺"
    lang_name = "O'zbekcha" if lang == 'uz' else "Русский"
    
    keyboard = []
    for grade in range(5, 12):
        keyboard.append([
            InlineKeyboardButton(f"📚 {grade}-sinf / Grade {grade}", callback_data=f"grade_{lang}_{grade}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Ortga / Back", callback_data="back_languages")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"{lang_emoji} {lang_name}\n\n"
        "Sinfni tanlang / Select grade:",
        reply_markup=reply_markup
    )


async def handle_grade_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle grade selection."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    if not callback_data.startswith('grade_'):
        return
    
    # Parse lang and grade from callback: grade_uz_5 or grade_ru_5
    parts = callback_data.split('_')
    if len(parts) == 3:
        lang = parts[1]  # 'uz' or 'ru'
        grade = int(parts[2])
    else:
        # Legacy format: grade_5 (default to uz)
        lang = 'uz'
        grade = int(parts[1])
    
    lang_emoji = "🇺🇿" if lang == 'uz' else "🇷🇺"
    
    # Get books for this grade (uses Supabase or SQLite automatically)
    books = fetch_books_by_grade(grade, language=lang)
    
    # Track analytics
    if ANALYTICS_AVAILABLE:
        user = update.effective_user
        track_user_action(
            telegram_user_id=user.id,
            action_type="browse_grade",
            telegram_username=user.username,
            first_name=user.first_name,
            action_data={"grade": grade, "language": lang}
        )
    
    if not books:
        await query.edit_message_text(
            f"❌ {grade}-sinf uchun kitoblar topilmadi.\n"
            f"❌ No books found for Grade {grade}.\n\n"
            "Books need to be added to the database."
        )
        return
    
    # Create buttons for each book - show title in selected language
    keyboard = []
    for book in books:
        if lang == 'uz':
            title = book.title_uz or book.title_ru or book.subject
        else:
            title = book.title_ru or book.title_uz or book.subject
        title = title[:35] + '...' if len(title) > 35 else title
        keyboard.append([
            InlineKeyboardButton(f"📖 {title}", callback_data=f"book_{lang}_{book.id}")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Ortga / Back", callback_data=f"lang_{lang}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"{lang_emoji} {grade}-sinf / Grade {grade}:\n\n"
        "Kitobni tanlang / Select a book:",
        reply_markup=reply_markup
    )


async def handle_book_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle book selection - show book details."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    if not callback_data.startswith('book_'):
        return
    
    # Parse book_{lang}_{id} format
    parts = callback_data.split('_')
    if len(parts) == 3:
        lang = parts[1]  # 'uz' or 'ru'
        book_id = int(parts[2])
    else:
        # Legacy format: book_{id}
        lang = 'uz'
        book_id = int(parts[1])
    
    lang_emoji = "🇺🇿" if lang == 'uz' else "🇷🇺"
    
    # Get book (uses Supabase or SQLite automatically)
    book = get_book(book_id)
    
    if not book:
        await query.edit_message_text("❌ Kitob topilmadi / Book not found.")
        return
    
    # Get themes count
    themes_count = count_book_themes(book_id)
    
    # Track analytics
    if ANALYTICS_AVAILABLE:
        user = update.effective_user
        track_user_action(
            telegram_user_id=user.id,
            action_type="view_book",
            telegram_username=user.username,
            first_name=user.first_name,
            action_data={"book_id": book_id, "language": lang}
        )
    
    # Show title in selected language first
    if lang == 'uz':
        main_title = book.title_uz or book.title_ru or book.subject
        alt_title = book.title_ru or '-'
        response = (
            f"📖 Kitob ma'lumotlari / Book Details\n\n"
            f"🇺🇿 {main_title}\n"
            f"🇷🇺 {alt_title}\n\n"
            f"📊 Sinf / Grade: {book.grade}\n"
            f"📚 Fan / Subject: {book.subject}\n"
            f"📑 Mavzular / Themes: {themes_count}\n"
        )
    else:
        main_title = book.title_ru or book.title_uz or book.subject
        alt_title = book.title_uz or '-'
        response = (
            f"📖 Информация о книге / Book Details\n\n"
            f"🇷🇺 {main_title}\n"
            f"🇺🇿 {alt_title}\n\n"
            f"📊 Класс / Grade: {book.grade}\n"
            f"📚 Предмет / Subject: {book.subject}\n"
            f"📑 Темы / Themes: {themes_count}\n"
        )
    
    keyboard = [
        [InlineKeyboardButton(f"{lang_emoji} Yuklab olish / Download PDF", callback_data=f"download_{lang}_{book_id}")],
        [InlineKeyboardButton("📑 Mavzular / Themes", callback_data=f"themes_{lang}_{book_id}")],
        [InlineKeyboardButton("🔙 Ortga / Back", callback_data=f"grade_{lang}_{book.grade}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        response,
        reply_markup=reply_markup
    )


async def handle_book_pdf_download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle book PDF download request - supports Supabase Storage URLs and local files."""
    query = update.callback_query
    await query.answer("Preparing PDF... / PDF tayyorlanmoqda...")
    
    callback_data = query.data
    
    # Determine language and book_id
    if callback_data.startswith('download_uz_'):
        book_id = int(callback_data.replace('download_uz_', ''))
        language = 'uz'
    elif callback_data.startswith('download_ru_'):
        book_id = int(callback_data.replace('download_ru_', ''))
        language = 'ru'
    elif callback_data.startswith('book_pdf_'):
        book_id = int(callback_data.replace('book_pdf_', ''))
        language = 'uz'  # Default to Uzbek
    else:
        return
    
    # Get book using unified data access
    book = get_book(book_id)
    
    if not book:
        await query.message.reply_text("❌ Kitob topilmadi / Book not found.")
        return
    
    # Track download analytics
    if ANALYTICS_AVAILABLE:
        user = update.effective_user
        track_download(
            book_id=book_id,
            download_type="book_pdf",
            language=language,
            telegram_user_id=user.id
        )
    
    # Try to get PDF URL from Supabase Storage first
    pdf_url = book.pdf_path_uz if language == 'uz' else book.pdf_path_ru
    actual_lang = language
    
    # Fallback to other language URL if not available
    if not pdf_url:
        alt_url = book.pdf_path_ru if language == 'uz' else book.pdf_path_uz
        if alt_url:
            pdf_url = alt_url
            actual_lang = 'ru' if language == 'uz' else 'uz'
    
    # If we have a Supabase URL, download and send the file directly
    if pdf_url and pdf_url.startswith('http'):
        title = book.title_uz if actual_lang == 'uz' else book.title_ru
        title = title or book.title_ru or book.title_uz or book.subject
        lang_emoji = "🇺🇿" if actual_lang == 'uz' else "🇷🇺"
        
        # Send loading message
        loading_msg = await query.message.reply_text("⏳ PDF yuklanmoqda... / Loading PDF...")
        
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
                            caption=f"{lang_emoji} {title}\n📊 {book.grade}-sinf / Grade {book.grade}\n📁 {book.subject}",
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
                f"{lang_emoji} Brauzerda ochish / Open in browser", 
                url=pdf_url
            )]]
            await query.message.reply_text(
                f"❌ PDF yuklashda xatolik: {str(e)[:50]}...\n\n"
                f"Quyidagi tugmani bosing:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
    
    # Fallback to local file paths
    pdf_path = book.pdf_path_uz if language == 'uz' else book.pdf_path_ru
    actual_lang = language
    
    # Fallback to other language if not available
    if not pdf_path or not Path(pdf_path).exists():
        alt_path = book.pdf_path_ru if language == 'uz' else book.pdf_path_uz
        if alt_path and Path(alt_path).exists():
            pdf_path = alt_path
            actual_lang = 'ru' if language == 'uz' else 'uz'
        else:
            await query.message.reply_text(
                "❌ PDF fayl topilmadi.\n"
                "❌ No PDF available for this book.\n\n"
                "Ma'mur bilan bog'laning / Contact administrator."
            )
            return
    
    # Send the local PDF file
    try:
        title = book.title_uz if actual_lang == 'uz' else book.title_ru
        title = title or book.title_ru or book.title_uz or book.subject
        lang_emoji = "🇺🇿" if actual_lang == 'uz' else "🇷🇺"
        
        await query.message.reply_document(
            document=open(pdf_path, 'rb'),
            filename=f"{title}.pdf",
            caption=f"{lang_emoji} {title} - {book.grade}-sinf / Grade {book.grade}",
            read_timeout=120,
            write_timeout=120
        )
    except Exception as e:
        await query.message.reply_text(f"❌ PDF yuborishda xatolik: {str(e)}")


async def handle_theme_pdf_download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle theme PDF download - creates bilingual PDF."""
    query = update.callback_query
    await query.answer("Generating PDF...")
    
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
    theme = get_theme(theme_id)
    
    if not theme:
        print(f"[PDF DEBUG] Theme not found")
        await query.message.reply_text("❌ Theme not found.")
        return
    
    print(f"[PDF DEBUG] Theme: {theme.name_uz}, Pages: {theme.start_page}-{theme.end_page}")
    
    book = get_book(theme.book_id)
    
    if not book:
        print(f"[PDF DEBUG] Book not found")
        await query.message.reply_text("❌ Book not found.")
        return
    
    print(f"[PDF DEBUG] Book: {book.title_uz}, PDF UZ: {book.pdf_path_uz}")
    
    # Determine which PDF to use
    if req_lang == 'uz':
        pdf_path = book.pdf_path_uz
        lang_name = "O'zbekcha"
        emoji = "🇺🇿"
    else:
        pdf_path = book.pdf_path_ru
        lang_name = "Русский"
        emoji = "🇷🇺"
    
    print(f"[PDF DEBUG] PDF path: {pdf_path}")
    
    # Support for Supabase Storage URLs
    temp_pdf_path = None
    if pdf_path and pdf_path.startswith('http'):
        import aiohttp
        import tempfile
        
        print(f"[PDF DEBUG] Downloading book PDF from URL for extraction: {pdf_path}")
        loading_msg = await query.message.reply_text("⏳ Kitob yuklanmoqda (mavzu ajratish uchun)... / Downloading book (for extraction)...")
        
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
            await query.message.reply_text(f"❌ Kitobni yuklab bo'lmadi: {str(e)}")
            return
            
    if not pdf_path or not Path(pdf_path).exists():
        print(f"[PDF DEBUG] PDF file not found at: {pdf_path}")
        await query.message.reply_text(f"❌ {lang_name} PDF topilmadi (file missing).")
        return
    
    # Generate filename
    theme_name = (theme.name_uz if req_lang == 'uz' else theme.name_ru) or f"theme_{theme_id}"
    safe_name = "".join(c for c in theme_name if c.isalnum() or c in (' ', '-', '_'))[:50]
    output_filename = f"{safe_name}_{req_lang}.pdf"
    
    print(f"[PDF DEBUG] Extracting pages {theme.start_page}-{theme.end_page} to {output_filename}")
    
    try:
        processor = PDFProcessor(pdf_path)
        if processor.open():
            output_path = processor.extract_theme_pdf(
                theme.start_page or 0,
                theme.end_page or 0,
                output_filename
            )
            processor.close()
            
            if output_path and output_path.exists():
                print(f"[PDF DEBUG] Generated: {output_path}")
                
                # Check file size (Telegram limit is 50MB, use 45MB to be safe)
                file_size_mb = output_path.stat().st_size / (1024 * 1024)
                print(f"[PDF DEBUG] File size: {file_size_mb:.2f} MB")
                
                if file_size_mb > 45:
                    await query.message.reply_text(
                        f"❌ PDF juda katta ({file_size_mb:.1f} MB).\n"
                        f"Telegram limiti: 50 MB.\n"
                        f"Iltimos, kitobni bo'laklarda yuklab oling."
                    )
                    return
                
                start_page = (theme.start_page or 0) + 1
                end_page = (theme.end_page or 0) + 1
                await query.message.reply_document(
                    document=open(output_path, 'rb'),
                    filename=output_filename,
                    caption=(
                        f"📄 {emoji} {safe_name}\n"
                        f"Pages: {start_page} - {end_page}\n"
                        f"📚 {book.title_uz or book.title_ru}"
                    ),
                    read_timeout=120,
                    write_timeout=120
                )
                print(f"[PDF DEBUG] Sent successfully!")
                return
            else:
                print(f"[PDF DEBUG] extract_theme_pdf returned: {output_path}")
            
        else:
            print(f"[PDF DEBUG] processor.open() failed")
            
        await query.message.reply_text("❌ Failed to generate PDF.")
    except Exception as e:
        print(f"[PDF DEBUG] Exception: {e}")
        await query.message.reply_text(f"❌ Error: {e}")
            



async def handle_themes_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show list of themes for a book."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    if not callback_data.startswith('themes_'):
        return
    
    # Parse themes_{lang}_{id} format
    parts = callback_data.split('_')
    if len(parts) == 3:
        lang = parts[1]  # 'uz' or 'ru'
        book_id = int(parts[2])
    else:
        # Legacy format: themes_{id}
        lang = 'uz'
        book_id = int(parts[1])
    
    # Get book and themes (uses Supabase or SQLite automatically)
    book = get_book(book_id)
    themes = fetch_themes_by_book(book_id)
    
    if not themes:
        await query.edit_message_text("❌ Mavzular topilmadi / No themes found for this book.")
        return
    
    # Create buttons for first 10 themes - show in selected language
    keyboard = []
    for theme in themes[:10]:
        if lang == 'uz':
            name = theme.name_uz or theme.name_ru or f"Mavzu {theme.id}"
        else:
            name = theme.name_ru or theme.name_uz or f"Тема {theme.id}"
        name = name[:35] + '...' if len(name) > 35 else name
        keyboard.append([
            InlineKeyboardButton(f"📑 {name}", callback_data=f"theme_{theme.id}")
        ])
    
    if len(themes) > 10:
        keyboard.append([
            InlineKeyboardButton(f"... va yana {len(themes) - 10} ta / {len(themes) - 10} more", callback_data=f"themes_more_{lang}_{book_id}_10")
        ])
    
    keyboard.append([InlineKeyboardButton("🔙 Ortga / Back", callback_data=f"book_{lang}_{book_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if lang == 'uz':
        book_title = book.title_uz or book.title_ru or "Kitob" if book else "Kitob"
    else:
        book_title = book.title_ru or book.title_uz or "Книга" if book else "Книга"
    
    await query.edit_message_text(
        f"📑 {book_title} - Mavzular / Themes:",
        reply_markup=reply_markup
    )


async def handle_back_languages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle back to language selection."""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🇺🇿 O'zbekcha / Uzbek", callback_data="lang_uz")],
        [InlineKeyboardButton("🇷🇺 Русский / Russian", callback_data="lang_ru")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📚 Kitoblarni ko'rish / Browse Books\n\n"
        "Tilni tanlang / Select language:",
        reply_markup=reply_markup
    )
