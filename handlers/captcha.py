import random

import telegram
from sqlalchemy import update as sql_update
from telegram import Update
from telegram.ext import ContextTypes

from database import async_session
from models.users import User
from utils.logger import debug_log
from utils.user_events import log_event

# КАПЧА ПРИ ВХОДЕ - ВЫВОД
CAPTCHA_EMOJIS = ["🫖", "☕️", "🧋", "🍵", "🍺", "🧃", "🥤", "🥃"]


async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for user in update.message.new_chat_members:
        if user.is_bot:
            continue
        chat_id = update.effective_chat.id
        async with async_session() as session:
            # Очистка left_at, если пользователь уже есть
            async with async_session() as session:
                await session.execute(
                    sql_update(User).where(User.user_id == user.id).values(left_at=None)
                )
                await session.commit()
        await log_event(user, "join", "Новый участник")
        await debug_log(
            context,
            f"[CAPTCHA_JOIN] 🆕 Новый участник: {user.full_name} (ID: {user.id})",
        )

        # Мутим при входе
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user.id,
                permissions=telegram.ChatPermissions(can_send_messages=False),
            )
            await debug_log(
                context,
                f"[CAPTCHA_JOIN] 🔇 Пользователь {user.id} замучен до прохождения капчи",
            )
        except Exception as e:
            await debug_log(
                context, f"[CAPTCHA_JOIN] ❗ Ошибка при муте нового пользователя: {e}"
            )

        # Формируем капчу
        correct = random.choice(CAPTCHA_EMOJIS)
        fake = random.sample([e for e in CAPTCHA_EMOJIS if e != correct], 3)
        options = fake + [correct]
        random.shuffle(options)

        keyboard = telegram.InlineKeyboardMarkup(
            [
                [
                    telegram.InlineKeyboardButton(
                        e, callback_data=f"captcha:{user.id}:{e}:{correct}"
                    )
                ]
                for e in options
            ]
        )

        try:
            msg = await context.bot.send_message(
                chat_id=chat_id,
                text=f"👋 Привет, {user.full_name}!\nДавай убедимся, что ты не бот!\nНажми на эмодзи: {correct}",
                reply_markup=keyboard,
            )
            await debug_log(
                context,
                f"[CAPTCHA_JOIN] 📩 Капча выдана пользователю {user.id}, сообщение: {msg.message_id}",
            )
            context.chat_data[user.id] = {"captcha_msg_id": msg.message_id}
        except Exception as e:
            await debug_log(
                context, f"[CAPTCHA_JOIN] ❗ Ошибка при отправке капчи: {e}"
            )

        try:
            context.job_queue.run_once(
                kick_if_no_captcha,
                when=300,
                data={"chat_id": chat_id, "user_id": user.id},
                name=str(user.id),
            )
            await debug_log(
                context,
                f"[CAPTCHA_JOIN] ⏱ Таймер кика установлен для user_id={user.id}",
            )
        except Exception as e:
            await debug_log(
                context, f"[CAPTCHA_JOIN] ❗ Ошибка при установке таймера кика: {e}"
            )


# ОБРАБОТКА НАЖАТИЯ КАПЧИ
async def handle_captcha_press(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    chat_id = query.message.chat.id
    parts = query.data.split(":")
    uid, pressed, correct = int(parts[1]), parts[2], parts[3]

    await debug_log(
        context,
        f"[CAPTCHA_PRESS] 🔘 Нажата кнопка капчи: user_id={user.id}, нажал={pressed}, правильный={correct}",
    )

    if user.id != uid:
        await query.answer("Это не ваша капча", show_alert=True)
        await debug_log(
            context,
            f"[CAPTCHA_PRESS] ⛔ Попытка нажать чужую капчу: {user.id} != {uid}",
        )
        return

    # Удаляем отложенный кик
    for j in context.job_queue.get_jobs_by_name(str(user.id)):
        j.schedule_removal()
    await debug_log(context, f"[CAPTCHA_PRESS] ⏹ Таймер кика снят: user_id={user.id}")

    # Удаляем сообщение с капчей
    try:
        msg_id = context.chat_data.get(user.id, {}).get("captcha_msg_id")
        if msg_id:
            await context.bot.delete_message(chat_id, msg_id)
            await debug_log(
                context, f"[CAPTCHA_PRESS] 🗑 Удалено сообщение капчи: msg_id={msg_id}"
            )
    except Exception as e:
        await debug_log(context, f"[CAPTCHA_PRESS] ❗ Ошибка при удалении капчи: {e}")

    if pressed == correct:
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user.id,
                permissions=telegram.ChatPermissions(can_send_messages=True),
            )
            await context.bot.send_message(
                chat_id, f"✅ {user.full_name}, добро пожаловать!"
            )
            await debug_log(
                context, f"[CAPTCHA_PRESS] 🔓 Размут пользователя: {user.id}"
            )
        except Exception as e:
            await debug_log(context, f"[CAPTCHA_PRESS] ❗ Ошибка при размуте: {e}")
    else:
        try:
            await context.bot.send_message(
                chat_id, "❌ Неверный выбор. Вы были удалены."
            )
            await context.bot.ban_chat_member(chat_id, user.id)
            await debug_log(
                context,
                f"[CAPTCHA_PRESS] 🚫 Пользователь {user.id} кикнут за неверную капчу",
            )
        except Exception as e:
            await debug_log(context, f"[CAPTCHA_PRESS] ❗ Ошибка при кике: {e}")


# КАПЧА - АВТОКИК ПО ТАЙМЕРУ
async def kick_if_no_captcha(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    chat_id = data["chat_id"]
    user_id = data["user_id"]

    await debug_log(
        context, f"[CAPTCHA_TIMEOUT] ⏰ Таймер истёк — кик: user_id={user_id}"
    )
    try:
        await context.bot.ban_chat_member(chat_id, user_id)
        await context.bot.unban_chat_member(chat_id, user_id)
        await debug_log(
            context,
            f"[CAPTCHA_TIMEOUT] 👢 Пользователь {user_id} был кикнут по таймеру капчи",
        )
    except Exception as e:
        await debug_log(
            context, f"[CAPTCHA_TIMEOUT] ❗ Ошибка при автокике user_id={user_id}: {e}"
        )
