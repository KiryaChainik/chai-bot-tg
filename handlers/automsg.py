from telegram import Update
from telegram.ext import ContextTypes

from utils.logger import debug_log


async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    old = update.chat_member.old_chat_member
    new = update.chat_member.new_chat_member
    chat = update.effective_chat
    user = new.user

    await debug_log(
        context,
        f"[AUTOMSG] Изменение прав у {user.full_name} ({user.id}): {old.status} → {new.status}",
    )

    # ✅ Разбан
    if old.status == "kicked" and new.status == "member":
        await context.bot.send_message(
            chat.id, f"✅ {user.mention_html()} был разбанен.", parse_mode="HTML"
        )
        await debug_log(
            context, f"[AUTOMSG] Подтверждён разбан: {user.full_name} ({user.id})"
        )

    # ✅ Размут
    if old.can_send_messages is False and new.can_send_messages is True:
        await context.bot.send_message(
            chat.id, f"🔊 {user.mention_html()} был размучен.", parse_mode="HTML"
        )
        await debug_log(
            context, f"[AUTOMSG] Подтверждён размут: {user.full_name} ({user.id})"
        )
