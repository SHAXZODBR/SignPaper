"""
Support Handler
Handles customer support and feedback for the bot.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import os
from dotenv import load_dotenv

load_dotenv()

# Import database functions
try:
    from database.supabase_client import save_support_message, save_feedback
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# Admin chat ID for receiving support messages (set in .env)
# Get your ID by sending /myid to the bot
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "")

# Conversation states
WAITING_FOR_MESSAGE = 1
WAITING_FOR_REPLY = 2


async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user their Telegram ID - useful for setting ADMIN_CHAT_ID."""
    user = update.effective_user
    chat = update.effective_chat
    
    # Print to console for easy copying
    print(f"📊 /myid command from: User={user.id}, Chat={chat.id}, Type={chat.type}")
    
    if chat.type in ['group', 'supergroup']:
        # In a group
        await update.message.reply_text(
            f"📊 **Group Chat ID**\n\n"
            f"💬 Group ID: `{chat.id}`\n\n"
            f"📝 Add to `.env`:\n"
            f"`ADMIN_CHAT_ID={chat.id}`\n\n"
            f"Support messages will be sent to this group!",
            parse_mode='Markdown'
        )
    else:
        # Private chat
        await update.message.reply_text(
            f"📊 **Your Telegram IDs**\n\n"
            f"👤 Your User ID: `{user.id}`\n"
            f"💬 This Chat ID: `{chat.id}`\n\n"
            f"📝 Add to `.env`:\n"
            f"`ADMIN_CHAT_ID={chat.id}`",
            parse_mode='Markdown'
        )


async def support_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle /support command - start support conversation."""
    keyboard = [
        [InlineKeyboardButton("❌ Bekor qilish / Cancel", callback_data="cancel_support")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📞 **Qo'llab-quvvatlash / Support**\n\n"
        "🇺🇿 Savolingiz yoki muammoingizni yozing. "
        "Biz tez orada javob beramiz!\n\n"
        "🇷🇺 Напишите ваш вопрос или проблему. "
        "Мы ответим вам в ближайшее время!\n\n"
        "✍️ Xabaringizni yozing / Write your message:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    return WAITING_FOR_MESSAGE


async def receive_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Receive and forward support message to admin."""
    user = update.effective_user
    message = update.message.text
    
    # Format support message with reply button
    support_text = (
        f"📩 **Yangi xabar / New Support Message**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👤 User: {user.first_name} (@{user.username or 'no username'})\n"
        f"🆔 ID: `{user.id}`\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"💬 Message:\n{message}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📝 Reply: `/reply {user.id} your message`"
    )
    
    # Send to admin if configured
    sent_to_admin = False
    if ADMIN_CHAT_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=support_text,
                parse_mode='Markdown'
            )
            sent_to_admin = True
            print(f"✅ Support message sent to admin {ADMIN_CHAT_ID}")
        except Exception as e:
            print(f"❌ Error sending to admin: {e}")
    else:
        print("⚠️ ADMIN_CHAT_ID not set in .env - support message not forwarded")
    
    # Save to database
    if DB_AVAILABLE:
        try:
            save_support_message(
                telegram_user_id=user.id,
                message=message,
                telegram_username=user.username,
                first_name=user.first_name,
                is_from_user=True
            )
            print(f"✅ Support message saved to DB")
        except Exception as e:
            print(f"❌ Error saving to DB: {e}")
    
    # Confirm to user
    await update.message.reply_text(
        "✅ **Xabaringiz qabul qilindi!**\n\n"
        "🇺🇿 Tez orada javob beramiz.\n"
        "🇷🇺 Мы скоро ответим вам.\n\n"
        "💬 Javob to'g'ridan-to'g'ri shu chatga keladi!",
        parse_mode='Markdown'
    )
    
    return ConversationHandler.END


async def reply_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to reply to a user. Usage: /reply <user_id> <message>"""
    user = update.effective_user
    chat = update.effective_chat
    
    # Allow reply if from the admin chat (group or personal)
    # Check if this message is from the support group OR from the admin user
    is_in_support_group = str(chat.id) == ADMIN_CHAT_ID
    if not is_in_support_group:
        return  # Silently ignore messages from other chats
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "📝 Usage: `/reply <user_id> <message>`\n"
            "Example: `/reply 123456789 Rahmat, muammo hal qilindi!`",
            parse_mode='Markdown'
        )
        return
    
    try:
        target_user_id = int(context.args[0])
        reply_message = ' '.join(context.args[1:])
        
        # Send reply to user
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"📩 **SignPaper Support**\n\n{reply_message}",
            parse_mode='Markdown'
        )
        
        await update.message.reply_text(f"✅ Message sent to user {target_user_id}")
        
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


async def cancel_support(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel support conversation."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("❌ Bekor qilindi / Cancelled")
    else:
        await update.message.reply_text("❌ Bekor qilindi / Cancelled")
    return ConversationHandler.END


async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /feedback command."""
    keyboard = [
        [
            InlineKeyboardButton("⭐ 5", callback_data="rate_5"),
            InlineKeyboardButton("⭐ 4", callback_data="rate_4"),
            InlineKeyboardButton("⭐ 3", callback_data="rate_3"),
        ],
        [
            InlineKeyboardButton("⭐ 2", callback_data="rate_2"),
            InlineKeyboardButton("⭐ 1", callback_data="rate_1"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⭐ **Botni baholang / Rate the bot**\n\n"
        "🇺🇿 Botimizni baholang!\n"
        "🇷🇺 Оцените нашего бота!",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def handle_rating(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle rating callback."""
    query = update.callback_query
    await query.answer()
    
    rating = int(query.data.replace("rate_", ""))
    user = update.effective_user
    
    # Log rating
    print(f"⭐ Rating: {rating} from {user.first_name} ({user.id})")
    
    # Save to database
    if DB_AVAILABLE:
        try:
            save_feedback(
                telegram_user_id=user.id,
                rating=rating,
                telegram_username=user.username
            )
            print(f"✅ Feedback saved to DB")
        except Exception as e:
            print(f"❌ Error saving feedback to DB: {e}")
    
    # Send to admin
    if ADMIN_CHAT_ID:
        try:
            await context.bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=f"⭐ Rating: {rating}/5\n👤 From: {user.first_name} (@{user.username or 'N/A'})",
            )
        except:
            pass
    
    await query.edit_message_text(
        f"✅ Rahmat! Siz {rating} ⭐ baho berdingiz!\n"
        f"✅ Спасибо! Вы поставили {rating} ⭐!"
    )
