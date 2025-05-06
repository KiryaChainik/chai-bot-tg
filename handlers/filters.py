import re

from telegram import Update
from telegram.ext import ContextTypes

from utils.logger import debug_log

# ❗️❗️❗️ АВТОФИЛЬТРЫ БОТА ---------------------------------------------------------

# ПРОВЕРКА НИКА НА АРАБСКИЕ СИМВОЛЫ ПРИ ВХОДЕ
ARABIC_REGEX = re.compile(
    r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]"
)


async def check_arabic_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if not user:
        await debug_log(
            context,
            "[ARABIC] ⚠️ Нет пользователя в update — возможно, это системное сообщение",
        )
        return

    full_name = f"{user.first_name or ''} {user.last_name or ''}"
    await debug_log(
        context,
        f"[ARABIC] 🔍 Проверка ника на арабский: user_id={user.id}, full_name='{full_name}'",
    )

    if ARABIC_REGEX.search(full_name):
        await debug_log(
            context, f"[ARABIC] ❌ Найдены арабские символы в имени: user_id={user.id}"
        )

        try:
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=user.id,
                permissions=telegram.ChatPermissions(can_send_messages=False),
            )
            await debug_log(
                context,
                f"[ARABIC] 🔇 Пользователь замучен за арабский ник: user_id={user.id}",
            )

            keyboard = telegram.InlineKeyboardMarkup(
                [
                    [
                        telegram.InlineKeyboardButton(
                            "🔁 Проверить ник", callback_data=f"check_nick:{user.id}"
                        )
                    ]
                ]
            )

            await update.message.reply_text(
                "❌ Ваше имя (никнейм) содержит арабские символы. Вы были замучены навсегда.\n"
                "Поменяйте имя (никнейм) и нажмите кнопку ниже для повторной проверки.",
                reply_markup=keyboard,
            )

        except Exception as e:
            await debug_log(context, f"[ARABIC] ❗ Ошибка при муте: {e}")


# КНОПКА ПРОВЕРКИ НИКА НА АРАБСКИЕ СИМВОЛЫ
async def handle_check_nick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    chat = query.message.chat

    full_name = f"{user.first_name or ''} {user.last_name or ''}"
    await debug_log(
        context,
        f"[ARABIC_BTN] 🔍 Кнопка проверки ника: user_id={user.id}, full_name='{full_name}'",
    )

    if ARABIC_REGEX.search(full_name):
        await debug_log(
            context,
            f"[ARABIC_BTN] ❌ Арабские символы всё ещё в имени: user_id={user.id}",
        )

        keyboard = telegram.InlineKeyboardMarkup(
            [
                [
                    telegram.InlineKeyboardButton(
                        "🔁 Проверить снова", callback_data=f"check_nick:{user.id}"
                    )
                ]
            ]
        )

        await query.edit_message_text(
            "❌ Имя (никнейм) всё ещё содержит арабские символы. Поменяйте и попробуйте снова.",
            reply_markup=keyboard,
        )
    else:
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=user.id,
                permissions=telegram.ChatPermissions(can_send_messages=True),
            )
            await query.edit_message_text("✅ Имя (никнейм) изменёно. Мут снят.")
            await debug_log(
                context,
                f"[ARABIC_BTN] ✅ Арабские символы удалены — мут снят: user_id={user.id}",
            )
        except Exception as e:
            await debug_log(context, f"[ARABIC_BTN] ❗ Ошибка при размуте: {e}")


# ПРОВЕРКА НИКА НА ПУСТОЙ
INVALID_NAME_REGEX = re.compile(r"^[\s.]+$")


async def check_empty_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user = update.effective_user
    chat = update.effective_chat

    if not message or not user:
        return

    name = f"{user.first_name or ''}{user.last_name or ''}".strip()
    await debug_log(
        context, f"[EMPTY_NAME] 🔍 Проверка имени: user_id={user.id}, name='{name}'"
    )

    if not name or INVALID_NAME_REGEX.match(name):
        await debug_log(
            context, f"[EMPTY_NAME] ❌ Имя невалидно: user_id={user.id}, name='{name}'"
        )
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=user.id,
                permissions=telegram.ChatPermissions(can_send_messages=False),
            )
            await debug_log(
                context,
                f"[EMPTY_NAME] 🔇 Замучен за пустое/некорректное имя: user_id={user.id}",
            )

            keyboard = telegram.InlineKeyboardMarkup(
                [
                    [
                        telegram.InlineKeyboardButton(
                            "🔁 Проверить имя (никнейм)",
                            callback_data=f"check_name:{user.id}",
                        )
                    ]
                ]
            )

            await message.reply_text(
                "❌ Ваше имя (никнейм) отсутствует или состоит только из пробелов/точек. Вы были замучены навсегда.\n"
                "Пожалуйста, установите нормальное имя (никнейм) в профиле и нажмите кнопку ниже для повторной проверки.",
                reply_markup=keyboard,
            )
        except Exception as e:
            await debug_log(context, f"[EMPTY_NAME] ❗ Ошибка при муте: {e}")


# КНОПКА ПРОВЕРКИ НИКА НА СПЕЦ СИМВОЛЫ И ПУСТОТУ
async def handle_check_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    chat = query.message.chat
    name = f"{user.first_name or ''}{user.last_name or ''}".strip()

    await debug_log(
        context,
        f"[NAME_BTN] 🔍 Проверка кнопкой имени: user_id={user.id}, name='{name}'",
    )

    if not name or INVALID_NAME_REGEX.match(name):
        await debug_log(
            context, f"[NAME_BTN] ❌ Имя всё ещё невалидно: user_id={user.id}"
        )
        keyboard = telegram.InlineKeyboardMarkup(
            [
                [
                    telegram.InlineKeyboardButton(
                        "🔁 Проверить снова", callback_data=f"check_name:{user.id}"
                    )
                ]
            ]
        )
        await query.edit_message_text(
            "❌ Имя (никнейм) всё ещё отсутствует или слишком подозрительное. Установите нормальное имя.",
            reply_markup=keyboard,
        )
    else:
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=user.id,
                permissions=telegram.ChatPermissions(can_send_messages=True),
            )
            await query.edit_message_text("✅ Имя (никнейм) принято. Мут снят.")
            await debug_log(
                context, f"[NAME_BTN] ✅ Мут снят: user_id={user.id}, name='{name}'"
            )
        except Exception as e:
            await debug_log(context, f"[NAME_BTN] ❗ Ошибка при размуте: {e}")


# ПРОВЕРКА НА ПУСТОЙ ЮЗЕРНЕЙМ
async def check_empty_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user = update.effective_user
    chat = update.effective_chat

    if not message or not user:
        return

    await debug_log(
        context,
        f"[USERNAME_EMPTY] 🔍 Проверка username: user_id={user.id}, username={user.username}",
    )

    if not user.username:
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=user.id,
                permissions=telegram.ChatPermissions(can_send_messages=False),
            )
            await debug_log(
                context,
                f"[USERNAME_EMPTY] 🔇 Мут за отсутствие username: user_id={user.id}",
            )

            keyboard = telegram.InlineKeyboardMarkup(
                [
                    [
                        telegram.InlineKeyboardButton(
                            "🔁 Проверить username",
                            callback_data=f"check_username:{user.id}",
                        )
                    ]
                ]
            )

            await message.reply_text(
                "❌ У вас не установлен username (имя пользователя). Вы были замучены навсегда.\n"
                "Пожалуйста, укажите его в профиле и нажмите кнопку ниже для повторной проверки.",
                reply_markup=keyboard,
            )
        except Exception as e:
            await debug_log(context, f"[USERNAME_EMPTY] ❗ Ошибка при муте: {e}")


# КНОПКА ПРОВЕРКИ НА ПУСТОЙ ЮЗЕРНЕЙМ
async def handle_check_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    chat = query.message.chat

    await debug_log(
        context,
        f"[USERNAME_BTN] 🔍 Кнопка проверки username: user_id={user.id}, username={user.username}",
    )

    if not user.username:
        keyboard = telegram.InlineKeyboardMarkup(
            [
                [
                    telegram.InlineKeyboardButton(
                        "🔁 Проверить снова", callback_data=f"check_username:{user.id}"
                    )
                ]
            ]
        )
        await query.edit_message_text(
            "❌ Username (имя пользователя) всё ещё не установлено. Пожалуйста, обновите профиль и попробуйте снова.",
            reply_markup=keyboard,
        )
        await debug_log(
            context,
            f"[USERNAME_BTN] ❌ Username по-прежнему отсутствует: user_id={user.id}",
        )
    else:
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=user.id,
                permissions=telegram.ChatPermissions(can_send_messages=True),
            )
            await query.edit_message_text(
                "✅ Username (имя пользователя) найдено. Мут снят."
            )
            await debug_log(
                context,
                f"[USERNAME_BTN] ✅ Username установлен, мут снят: user_id={user.id}",
            )
        except Exception as e:
            await debug_log(context, f"[USERNAME_BTN] ❗ Ошибка при размуте: {e}")


# АНТИСПАМ
async def check_spam(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user = update.effective_user
    chat = update.effective_chat

    if not message or not user or not message.text:
        return

    # Игнорируем команды
    if message.text.strip().startswith("/"):
        await debug_log(
            context,
            f"[SPAM_CHECK] ⏭️ Пропущена команда от {user.id}: {message.text!r}",
        )
        return

    await debug_log(
        context, f"[SPAM_CHECK] 📨 Сообщение от {user.id}: {message.text!r}"
    )

    # Хранилище спам-трекинга
    user_data = context.chat_data.setdefault("spam_tracker", {})
    entry = user_data.get(user.id, {"text": "", "count": 0})

    if message.text == entry["text"]:
        entry["count"] += 1
        await debug_log(
            context,
            f"[SPAM_CHECK] 🔁 Повтор #{entry['count']} от {user.id}",
        )
    else:
        entry["text"] = message.text
        entry["count"] = 1
        await debug_log(
            context,
            f"[SPAM_CHECK] ✏️ Новый текст от {user.id}, счётчик сброшен",
        )

    user_data[user.id] = entry

    if entry["count"] >= 3:
        try:
            until_date = update.message.date + timedelta(hours=1)
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=user.id,
                permissions=telegram.ChatPermissions(can_send_messages=False),
                until_date=until_date,
            )
            await message.reply_text(
                f"🚫 Пользователь {user.full_name} замучен на 1 час за спам одинаковыми сообщениями."
            )
            entry["count"] = 0
            await debug_log(
                context,
                f"[SPAM_CHECK] 🔇 {user.full_name} ({user.id}) замучен на 1 час за спам",
            )
        except Exception as e:
            await debug_log(context, f"[SPAM_CHECK] ❗ Ошибка при муте за спам: {e}")
