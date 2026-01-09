"""
Resources Handler
Handles educational resources display.
Uses Supabase when configured, SQLite otherwise.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import sys
sys.path.append('../..')
from database.models import (
    get_session, Theme, Book, Resource,
    get_theme, get_book, fetch_theme_resources,
    use_supabase
)
from services.resource_finder import ResourceFinder, EducationalResource


async def handle_resources(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle educational resources display for a theme."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    if not callback_data.startswith('resources_'):
        return
    
    theme_id = int(callback_data.replace('resources_', ''))
    
    # Get theme (uses Supabase or SQLite automatically)
    theme = get_theme(theme_id)
    
    if not theme:
        await query.message.reply_text("❌ Theme not found.")
        return
    
    book = get_book(theme.book_id)
    
    # Get stored resources from database
    db_resources = fetch_theme_resources(theme_id)
    
    # Also get fresh resources from ResourceFinder
    fresh_resources = ResourceFinder.find_resources_for_theme(
        theme_name=theme.name_uz or theme.name_ru or "",
        subject=book.subject if book else "general",
        grade=book.grade if book else 5
    )
    
    # Build response message
    theme_name = theme.name_uz or theme.name_ru or "Theme"
    lines = [f"🔗 **Educational Resources for:**\n_{theme_name}_\n"]
    
    # Group by language
    lang_resources = {'uz': [], 'ru': [], 'en': []}
    
    # Add database resources
    for res in db_resources:
        if res.language in lang_resources:
            lang_resources[res.language].append({
                'title': res.title,
                'url': res.url,
                'type': res.resource_type
            })
    
    # Add fresh resources (avoiding duplicates)
    existing_urls = {res.url for res in db_resources}
    for res in fresh_resources:
        if res.url not in existing_urls and res.language in lang_resources:
            lang_resources[res.language].append({
                'title': res.title,
                'url': res.url,
                'type': res.resource_type
            })
    
    # Format by language
    lang_names = {
        'uz': '🇺🇿 **O\'zbekcha:**',
        'ru': '🇷🇺 **Русский:**',
        'en': '🇬🇧 **English:**'
    }
    
    type_icons = {
        'video': '🎥',
        'course': '📖',
        'article': '📄',
        'research': '🔬'
    }
    
    for lang in ['uz', 'ru', 'en']:
        resources = lang_resources[lang]
        if resources:
            lines.append(f"\n{lang_names[lang]}")
            for res in resources[:4]:  # Limit per language
                icon = type_icons.get(res['type'], '📌')
                lines.append(f"  {icon} [{res['title']}]({res['url']})")
    
    # Add back button
    keyboard = [[
        InlineKeyboardButton("🔙 Back to Theme", callback_data=f"theme_{theme_id}")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(
        '\n'.join(lines),
        reply_markup=reply_markup,
        parse_mode='Markdown',
        disable_web_page_preview=True
    )


async def resources_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /resources command."""
    await update.message.reply_text(
        "🔗 **Educational Resources**\n\n"
        "To get educational resources for a topic:\n\n"
        "1. Search for a theme using `/search`\n"
        "2. Select a theme from results\n"
        "3. Click 'Educational Resources'\n\n"
        "Or just type your search query and I'll find related themes!",
        parse_mode='Markdown'
    )
