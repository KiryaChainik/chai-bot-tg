from telegram import Update
from telegram.ext import ContextTypes

from utils.logger import debug_log


# ПРАВИЛА ЧАТА - ВЫВЕСТИ
async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules = context.bot_data.get("rules", {})
    user = update.effective_user

    await debug_log(
        context,
        f"[RULES] 📥 /rules вызвал: {user.full_name if user else 'неизвестный'}",
    )

    if not rules:
        await update.message.reply_text("📭 Правила пока не установлены.")
        await debug_log(context, "[RULES] ❌ Правила не заданы в context.bot_data")
        return

    text = rules.get("text", "📃 Правила группы:")
    photo_id = rules.get("photo_file_id")

    if photo_id:
        await debug_log(context, f"[RULES] 🖼 Отправка фото с caption: {text}")
        await update.message.reply_photo(photo=photo_id, caption=text)
    else:
        await debug_log(context, f"[RULES] 📜 Отправка текстовых правил: {text}")
        await update.message.reply_text(text)


# УСТАНОВКА ПРАВИЛ ЧАТА
async def set_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        await debug_log(context, "[SET_RULES] ❌ Нет message в update")
        return

    chat = update.effective_chat
    user = update.effective_user or None
    sender_chat = message.sender_chat or None

    # 💥 Игнорируем альбомы
    if message.media_group_id:
        await debug_log(
            context,
            f"[SET_RULES] ⛔ Пропущено сообщение из альбома (media_group_id={message.media_group_id})",
        )
        return

    # ⚠️ Только для /set_rules (в тексте или подписи)
    text_to_check = message.text or message.caption
    if not text_to_check or not text_to_check.strip().startswith("/set_rules"):
        return

    await debug_log(
        context,
        f"[SET_RULES] 🛡 /set_rules вызвал: {user.full_name if user else 'None'} | "
        f"sender_chat={sender_chat.title if sender_chat else '—'}, chat_id={chat.id}",
    )

    is_authorized = False

    is_anonymous_admin = (
        user
        and user.is_bot
        and user.username == "GroupAnonymousBot"
        and sender_chat
        and sender_chat.id == chat.id
    )

    if is_anonymous_admin:
        await debug_log(
            context, "[SET_RULES] ✅ Анонимный админ подтверждён — разрешено"
        )
        is_authorized = True
    elif user:
        member = await context.bot.get_chat_member(chat.id, user.id)
        is_authorized = member.status in ("administrator", "creator") and getattr(
            member, "can_change_info", False
        )

    if not is_authorized:
        await message.reply_text("🚫 У вас нет прав для изменения правил.")
        await debug_log(
            context,
            f"[SET_RULES] ❌ Отказано — нет прав у {user.full_name if user else '—'}",
        )
        return

    text = message.caption if message.caption else message.text
    photo = message.photo[-1].file_id if message.photo else None

    if not text and not photo:
        await message.reply_text("❗ Отправьте текст, фото или и то, и другое.")
        await debug_log(
            context, "[SET_RULES] ❌ Ничего не передано — ни текста, ни фото"
        )
        return

    if text:
        text = text.replace("/set_rules", "").strip()

    context.bot_data["rules"] = {"text": text, "photo_file_id": photo}

    await debug_log(
        context,
        f"[SET_RULES] ✅ Правила обновлены. Текст: {text[:60]}{'...' if len(text) > 60 else ''}, Фото: {'есть' if photo else 'нет'}",
    )
    await message.delete()
    await context.bot.send_message(chat.id, "✅ Правила обновлены.")
