"""
Books Handler
Handles book browsing and PDF downloads.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from pathlib import Path
import sys
sys.path.append('../..')
from database.models import get_session, Book, Theme
from services.pdf_processor import PDFProcessor, create_bilingual_theme_pdf
from config import OUTPUT_DIR


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
    
    # Get books for this grade
    session = get_session()
    books = session.query(Book).filter(Book.grade == grade).all()
    
    if not books:
        await query.edit_message_text(
            f"❌ {grade}-sinf uchun kitoblar topilmadi.\n"
            f"❌ No books found for Grade {grade}.\n\n"
            "Books need to be processed first. Run:\n"
            "python -m services.book_processor"
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
    
    session = get_session()
    book = session.query(Book).filter(Book.id == book_id).first()
    
    if not book:
        await query.edit_message_text("❌ Kitob topilmadi / Book not found.")
        return
    
    # Get themes count
    themes_count = session.query(Theme).filter(Theme.book_id == book_id).count()
    
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
    """Handle book PDF download request."""
    query = update.callback_query
    await query.answer("Preparing PDF...")
    
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
    
    session = get_session()
    book = session.query(Book).filter(Book.id == book_id).first()
    
    if not book:
        await query.message.reply_text("❌ Book not found.")
        return
    
    # Get PDF path - fallback to other language if requested not available
    pdf_path = book.pdf_path_uz if language == 'uz' else book.pdf_path_ru
    actual_lang = language
    
    # Fallback to other language if not available
    if not pdf_path or not Path(pdf_path).exists():
        # Try the other language
        alt_path = book.pdf_path_ru if language == 'uz' else book.pdf_path_uz
        if alt_path and Path(alt_path).exists():
            pdf_path = alt_path
            actual_lang = 'ru' if language == 'uz' else 'uz'
        else:
            await query.message.reply_text("❌ No PDF available for this book.")
            return
    
    # Send the PDF
    try:
        title = book.title_uz if actual_lang == 'uz' else book.title_ru
        title = title or book.title_ru or book.title_uz or book.subject
        lang_emoji = "🇺🇿" if actual_lang == 'uz' else "🇷🇺"
        
        await query.message.reply_document(
            document=open(pdf_path, 'rb'),
            filename=f"{title}.pdf",
            caption=f"{lang_emoji} {title} - Grade {book.grade}",
            read_timeout=120,
            write_timeout=120
        )
    except Exception as e:
        await query.message.reply_text(f"❌ Error sending PDF: {str(e)}")


async def handle_theme_pdf_download(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle theme PDF download - creates bilingual PDF."""
    query = update.callback_query
    await query.answer("Generating bilingual PDF...")
    
    callback_data = query.data
    if not callback_data.startswith('theme_pdf_'):
        return
    
    theme_id = int(callback_data.replace('theme_pdf_', ''))
    
    session = get_session()
    theme = session.query(Theme).filter(Theme.id == theme_id).first()
    
    if not theme:
        await query.message.reply_text("❌ Theme not found.")
        return
    
    book = session.query(Book).filter(Book.id == theme.book_id).first()
    
    # Check if we have both PDFs
    uz_path = book.pdf_path_uz
    ru_path = book.pdf_path_ru
    
    if not uz_path and not ru_path:
        await query.message.reply_text("❌ No PDF files available for this book.")
        return
    
    # Generate filename
    theme_name = theme.name_uz or theme.name_ru or f"theme_{theme_id}"
    safe_name = "".join(c for c in theme_name if c.isalnum() or c in (' ', '-', '_'))[:50]
    output_filename = f"{safe_name}_bilingual.pdf"
    
    try:
        # If both languages available, create bilingual PDF
        if uz_path and ru_path and Path(uz_path).exists() and Path(ru_path).exists():
            output_path = create_bilingual_theme_pdf(
                uz_pdf_path=uz_path,
                ru_pdf_path=ru_path,
                uz_start=theme.start_page or 0,
                uz_end=theme.end_page or 0,
                ru_start=theme.start_page or 0,
                ru_end=theme.end_page or 0,
                output_filename=output_filename
            )
        else:
            # Use whichever is available
            available_path = uz_path if uz_path and Path(uz_path).exists() else ru_path
            processor = PDFProcessor(available_path)
            if processor.open():
                output_path = processor.extract_theme_pdf(
                    theme.start_page or 0,
                    theme.end_page or 0,
                    output_filename
                )
                processor.close()
            else:
                output_path = None
        
        if output_path and output_path.exists():
            start_page = (theme.start_page or 0) + 1
            end_page = (theme.end_page or 0) + 1
            await query.message.reply_document(
                document=open(output_path, 'rb'),
                filename=output_filename,
                caption=(
                    f"📄 {theme.name_uz or theme.name_ru}\n"
                    f"Pages: {start_page} - {end_page}\n"
                    f"📚 {book.title_uz or book.title_ru}"
                ),
                read_timeout=120,
                write_timeout=120
            )
        else:
            await query.message.reply_text("❌ Failed to generate PDF.")
            
    except Exception as e:
        await query.message.reply_text(f"❌ Error generating PDF: {str(e)}")


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
    
    session = get_session()
    book = session.query(Book).filter(Book.id == book_id).first()
    themes = session.query(Theme).filter(Theme.book_id == book_id).all()
    
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
        book_title = book.title_uz or book.title_ru or "Kitob"
    else:
        book_title = book.title_ru or book.title_uz or "Книга"
    
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
