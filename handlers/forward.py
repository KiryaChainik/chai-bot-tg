from telegram import Update
from telegram.ext import ContextTypes

from config import SOURCE_CHAT_ID, TARGET_CHAT_ID, TOPIC_ID_BY_HASHTAG
from utils.logger import debug_log


# ПЕРЕНАПРАВЛЕНИЕ СООБЩЕНИЙ ИЗ ТГК ПО ХЭШТЕГУ
async def forward_by_hashtag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post

    if not message:
        await debug_log(
            context, "[ПЕРЕСЫЛКА ИЗ ТГК] Нет channel_post — это не из канала"
        )
        return

    await debug_log(
        context, "[ПЕРЕСЫЛКА ИЗ ТГК] channel_post от канала ID: {message.chat.id}"
    )
    content = message.text or message.caption
    await debug_log(context, "[ПЕРЕСЫЛКА ИЗ ТГК] Содержимое поста: {content!r}")

    if content and message.chat.id == SOURCE_CHAT_ID:
        await debug_log(
            context,
            "[ПЕРЕСЫЛКА ИЗ ТГК] Канал совпадает с SOURCE_CHAT_ID, начинаем искать теги...",
        )
        for tag, topic_id in TOPIC_ID_BY_HASHTAG.items():
            if tag in content.lower():
                await debug_log(
                    context, "[ПЕРЕСЫЛКА ИЗ ТГК] Нашли тег '{tag}' → тема ID {topic_id}"
                )
                try:
                    await context.bot.forward_message(
                        chat_id=TARGET_CHAT_ID,
                        from_chat_id=message.chat.id,
                        message_id=message.message_id,
                        message_thread_id=topic_id,
                    )
                    await debug_log(context, "[ПЕРЕСЫЛКА ИЗ ТГК] Успешно переслано")
                except Exception:
                    await debug_log(context, "[ОШИБКА при пересылке]: {e}")
                break
        else:
            await debug_log(context, "[ПЕРЕСЫЛКА ИЗ ТГК] Подходящего тега не найдено")
    else:
        await debug_log(
            context,
            "[ПЕРЕСЫЛКА ИЗ ТГК] Либо контент пустой, либо ID канала не совпадает",
        )
