# ❗️❗️❗️ ИМПОРТ БИБЛИОТЕК ТГ ДЛЯ БОТА ---------------------------------------------------------

import re
import os
from dotenv import load_dotenv
import random
from telegram.constants import ChatType
from telegram import (
    Update,
    ChatPermissions,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    BotCommand,
    BotCommandScopeChatAdministrators,
    BotCommandScopeChat,
    BotCommandScopeDefault,
    MenuButtonCommands,
)
from datetime import timedelta, datetime
from telegram.ext import ChatMemberHandler, CallbackQueryHandler, ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

# ЛОГ ДЕБАГА ОТДЕЛЬНЫЙ ЧАТ
DEBUG_CHAT_ID = int(os.getenv("DEBUG_CHAT_ID"))

def debug_log_sync(text: str):
    print(f"[DEBUG] {text}")

async def debug_log(context, text: str):
    print(f"{text}")
    try:
        await context.bot.send_message(
            chat_id=DEBUG_CHAT_ID,
            text=f"{text}",
            disable_notification=True
        )
    except Exception as e:
        print(f"[DEBUG] Ошибка при логировании: {e}")

# ❗️❗️❗️ ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ БОТА ---------------------------------------------------------

TOKEN = os.getenv("BOT_TOKEN")


SOURCE_CHAT_ID = -1001887222284  # ID исходной группы
TARGET_CHAT_ID = -1002443521655  # ID целевой группы
TOPIC_ID_BY_HASHTAG = { # хэштеги и номера тем
    '#барахолка': 2,
    '#оцените_сетап': 6,
    '#почувствуй_боль': 7,
    '#кккомбо': 9,
    '#тесты_магниток': 11,
    '#коллекция': 12,
    '#новости': 17,
    '#тесты_мышек': 20
}

# ПЕРЕНАПРАВЛЕНИЕ СООБЩЕНИЙ ИЗ ТГК ПО ХЭШТЕГУ
async def forward_by_hashtag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.channel_post

    if not message:
        await debug_log(context, "[ПЕРЕСЫЛКА ИЗ ТГК] Нет channel_post — это не из канала")
        return

    await debug_log(context, "[ПЕРЕСЫЛКА ИЗ ТГК] channel_post от канала ID: {message.chat.id}")
    content = message.text or message.caption
    await debug_log(context, "[ПЕРЕСЫЛКА ИЗ ТГК] Содержимое поста: {content!r}")

    if content and message.chat.id == SOURCE_CHAT_ID:
        await debug_log(context, "[ПЕРЕСЫЛКА ИЗ ТГК] Канал совпадает с SOURCE_CHAT_ID, начинаем искать теги...")
        for tag, topic_id in TOPIC_ID_BY_HASHTAG.items():
            if tag in content.lower():
                await debug_log(context, "[ПЕРЕСЫЛКА ИЗ ТГК] Нашли тег '{tag}' → тема ID {topic_id}")
                try:
                    await context.bot.forward_message(
                        chat_id=TARGET_CHAT_ID,
                        from_chat_id=message.chat.id,
                        message_id=message.message_id,
                        message_thread_id=topic_id
                    )
                    await debug_log(context, "[ПЕРЕСЫЛКА ИЗ ТГК] Успешно переслано")
                except Exception as e:
                    await debug_log(context, "[ОШИБКА при пересылке]: {e}")
                break
        else:
            await debug_log(context, "[ПЕРЕСЫЛКА ИЗ ТГК] Подходящего тега не найдено")
    else:
        await debug_log(context, "[ПЕРЕСЫЛКА ИЗ ТГК] Либо контент пустой, либо ID канала не совпадает")



# ❗️❗️❗️ КОМАНДЫ БОТУ В ЧАТЕ ---------------------------------------------------------

# ПОДСКАЗКИ ПО КОМАНДАМ
async def set_bot_commands(application):
    group_ids = [-1002443521655]  # ← сюда добавляй все нужные chat_id

    # Установка глобального меню кнопок
    await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
    debug_log_sync("[CMD] ✅ Установлено глобальное меню команд")

    for chat_id in group_ids:
        debug_log_sync(f"[CMD] ⚙️ Настройка команд для группы {chat_id}")

        # Команды для всех пользователей в группе
        await application.bot.set_my_commands(
            commands=[
                BotCommand("menu", "Показать все доступные команды бота"),
                BotCommand("rules", "Показать правила группы"),
            ],
            scope=BotCommandScopeChat(chat_id=chat_id)
        )

        # Команды только для админов
        await application.bot.set_my_commands(
            commands=[
                BotCommand("menu", "Показать все доступные команды бота"),
                BotCommand("rules", "Показать правила группы"),
                BotCommand("set_rules", "Установить правила"),
                BotCommand("ban", "Забанить пользователя"),
                BotCommand("unban", "Разбанить пользователя"),
                BotCommand("kick", "Исключить пользователя"),
                BotCommand("mute", "Обеззвучить пользователя"),
                BotCommand("unmute", "Снять мут"),
            ],
            scope=BotCommandScopeChatAdministrators(chat_id=chat_id)
        )

    # Резерв: глобальные команды по умолчанию
    await application.bot.set_my_commands(
        commands=[
            BotCommand("rules", "Показать правила группы"),
        ],
        scope=BotCommandScopeDefault()
    )

    debug_log_sync("[CMD] ✅ Команды установлены во всех указанных группах")

# ОБРАБОТЧИК НАЖАТИЙ КНОПОК МЕНЮ ВСЕХ КОМАНД
async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data

    await query.answer()

    if data == "menu_rules":
        await query.message.reply_text("📜 Вот правила группы: ...")
        await debug_log(context, f"[MENU] 📥 {user.full_name} ({user.id}) нажал кнопку 'Правила'")
    elif data == "menu_rights":
        await query.message.reply_text("🔐 У вас есть базовые права. Если вы админ — используйте /ban, /mute и другие.")
        await debug_log(context, f"[MENU] 📥 {user.full_name} ({user.id}) нажал кнопку 'Мои права'")

# ПОЛУЧЕНИЕ ID ЧАТА ПО КОМАНДЕ
async def show_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    await update.message.reply_text(f"chat_id: {chat.id}")
    await debug_log(context, f"[CHAT_ID] ℹ️ {user.full_name} ({user.id}) запросил chat_id: {chat.id}")

# ПОЛУЧЕНИЕ ID ТРЕДА ПО КОМАНДЕ
async def thread_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.channel_post
    if not message:
        await debug_log(context, "[THREAD_ID] ⚠️ Нет message — ни обычного, ни channel_post")
        return

    chat = message.chat
    user = message.from_user or message.sender_chat

    if not chat.is_forum:
        await message.reply_text("❌ Это не форум. Команда работает только в темах.")
        await debug_log(context, f"[THREAD_ID] ℹ️ Команда вызвана вне форума пользователем: {user.full_name if hasattr(user, 'full_name') else user.title}")
        return

    if not message.message_thread_id:
        await message.reply_text("⚠️ Это не сообщение внутри темы форума.")
        await debug_log(context, f"[THREAD_ID] ⚠️ Команда вызвана вне темы. Чат: {chat.id}")
        return

    await message.reply_text(f"📌 ID этой темы (message_thread_id): {message.message_thread_id}")
    await debug_log(context, f"[THREAD_ID] 📌 Запрос от {user.full_name if hasattr(user, 'full_name') else user.title}: {message.message_thread_id}")

# БАН ПОЛЬЗОВАТЕЛЯ
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat = update.effective_chat
    user = update.effective_user
    sender_chat = message.sender_chat

    await debug_log(context, f"[BAN] 🛡 Команда /ban вызвана: {user.full_name if user else '—'}, sender_chat={sender_chat.title if sender_chat else '—'}")

    is_anonymous_admin = (
        user and user.is_bot and user.username == "GroupAnonymousBot"
        and sender_chat and sender_chat.id == chat.id
    )

    is_authorized = False
    if is_anonymous_admin:
        await debug_log(context, "[BAN] ✅ Анонимный админ подтверждён — разрешено")
        is_authorized = True
    elif user:
        member = await context.bot.get_chat_member(chat.id, user.id)
        is_authorized = (
            member.status in ("administrator", "creator")
            and getattr(member, "can_restrict_members", False)
        )

    if not is_authorized:
        await message.reply_text("🚫 У вас нет прав на бан.")
        await debug_log(context, "[BAN] ❌ Нет прав на бан у вызывающего")
        return

    parts = message.text.strip().split()
    command = parts[0].lower()
    raw_args = parts[1:]
    target = None

    if message.reply_to_message:
        target = message.reply_to_message.from_user

    elif raw_args:
        arg = raw_args[0]
        if arg.isdigit():
            try:
                member = await context.bot.get_chat_member(chat.id, int(arg))
                target = member.user
            except Exception as e:
                await message.reply_text(f"⚠️ Не удалось найти пользователя по ID: {e}")
                await debug_log(context, f"[BAN] ❌ Ошибка поиска по ID: {repr(e)}")
                return
        elif arg.startswith("@"):
            try:
                username = arg[1:]  # удаляем "@"
                user_info = await context.bot.get_chat(username)
                member = await context.bot.get_chat_member(chat.id, user_info.id)
                target = member.user
            except Exception as e:
                await message.reply_text(f"⚠️ Произошла ошибка при поиске: {e}")
                await debug_log(context, f"[BAN] ❌ Полный текст ошибки при username: {repr(e)}")
                return
        else:
            await message.reply_text("⚠️ Укажите корректного пользователя (реплай, ID или @username).")
            return
    else:
        await message.reply_text("⚠️ Укажите пользователя (реплай, ID или @username).")
        return

    if not target:
        await message.reply_text("⚠️ Не удалось определить пользователя.")
        await debug_log(context, "[BAN] ❌ Цель бана не определена")
        return

    target_member = await context.bot.get_chat_member(chat.id, target.id)
    if target_member.status in ("administrator", "creator"):
        await message.reply_text("🚫 Нельзя забанить администратора.")
        await debug_log(context, f"[BAN] 🚫 Попытка бана администратора: {target.full_name}")
        return

    try:
        await context.bot.ban_chat_member(chat.id, target.id)
        await debug_log(context, f"[BAN] ✅ Забанен: {target.full_name} (ID: {target.id})")
        mention = target.mention_html()
        await message.reply_html(f"🚫 {mention} был забанен.")
    except Exception as e:
        await message.reply_text(f"❌ Не удалось забанить: {e}")
        await debug_log(context, f"[BAN] ❌ Ошибка при бане {target.full_name}: {repr(e)}")

    if command.startswith("!ban"):
        try:
            await message.delete()
            await debug_log(context, "[BAN] 🗑 Команда !ban удалена из чата")
        except:
            pass

# РАЗБАН ПОЛЬЗОВАТЕЛЯ
async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat = update.effective_chat
    user = update.effective_user
    sender_chat = message.sender_chat

    await debug_log(context, f"[UNBAN] 📥 Команда /unban вызвана: {user.full_name if user else sender_chat.title}")

    is_authorized = False
    if user and user.username == "GroupAnonymousBot" and sender_chat and sender_chat.id == chat.id:
        is_authorized = True
        await debug_log(context, "[UNBAN] ✅ Подтверждён анонимный админ")
    elif user:
        try:
            member = await context.bot.get_chat_member(chat.id, user.id)
            is_authorized = (
                member.status in ("administrator", "creator")
                and getattr(member, "can_restrict_members", False)
            )
        except Exception as e:
            await debug_log(context, f"[UNBAN] ⚠️ Ошибка проверки прав: {e}")

    if not is_authorized:
        await message.reply_text("🚫 У вас нет прав на разбан.")
        await debug_log(context, "[UNBAN] ❌ Недостаточно прав")
        return

    parts = message.text.strip().split()
    raw_args = parts[1:] if len(parts) > 1 else []
    target_id = None
    target_name = None

    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
        target_id = target.id
        target_name = target.full_name
    elif raw_args:
        arg = raw_args[0]
        try:
            if arg.isdigit():
                target_id = int(arg)
                target = await context.bot.get_chat(target_id)
                target_name = target.full_name
            elif arg.startswith("@"):
                user_info = await context.bot.get_chat(arg)
                target_id = user_info.id
                target_name = user_info.full_name
            else:
                await message.reply_text("⚠️ Укажите корректного пользователя.")
                return
        except Exception as e:
            await message.reply_text("⚠️ Не удалось определить пользователя.")
            await debug_log(context, f"[UNBAN] ❌ Ошибка определения цели: {e}")
            return
    else:
        await message.reply_text("⚠️ Укажите пользователя для разбана.")
        return

    if not target_id:
        await message.reply_text("⚠️ Не удалось определить ID пользователя.")
        await debug_log(context, "[UNBAN] ❌ Цель не определена")
        return

    try:
        result = await context.bot.unban_chat_member(chat.id, target_id, only_if_banned=True)
        mention = f"<a href='tg://user?id={target_id}'>{target_name or target_id}</a>"
        if result:
            await message.reply_html(f"✅ {mention} был разбанен.")
            await debug_log(context, f"[UNBAN] ✅ Разбанен: {target_name or target_id}")
        else:
            await message.reply_text("⚠️ Пользователь не был в бане.")
            await debug_log(context, f"[UNBAN] ℹ️ Пользователь {target_id} не находился в бане")
    except Exception as e:
        await message.reply_text(f"❌ Не удалось разбанить: {e}")
        await debug_log(context, f"[UNBAN] ❌ Ошибка при разблокировке {target_id}: {e}")

# КИК ПОЛЬЗОВАТЕЛЯ
async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat = update.effective_chat
    user = update.effective_user
    sender_chat = message.sender_chat

    await debug_log(context, f"[KICK] 🛡 /kick вызван: {user.full_name if user else 'None'}, sender_chat={sender_chat.title if sender_chat else '—'}")

    is_anonymous_admin = (
        user and user.is_bot and user.username == "GroupAnonymousBot"
        and sender_chat and sender_chat.id == chat.id
    )

    is_authorized = False
    if is_anonymous_admin:
        await debug_log(context, "[KICK] ✅ Анонимный админ подтверждён — разрешено")
        is_authorized = True
    elif user:
        member = await context.bot.get_chat_member(chat.id, user.id)
        is_authorized = (
            member.status in ("administrator", "creator")
            and getattr(member, "can_restrict_members", False)
        )

    if not is_authorized:
        await message.reply_text("🚫 У вас нет прав на исключение пользователей.")
        await debug_log(context, f"[KICK] ❌ Нет прав на кик у {user.full_name if user else 'неизвестно'}")
        return

    parts = message.text.strip().split()
    command = parts[0].lower()
    raw_args = parts[1:]
    target = None

    if message.reply_to_message:
        target = message.reply_to_message.from_user

    elif raw_args:
        arg = raw_args[0]
        try:
            if arg.isdigit():
                member = await context.bot.get_chat_member(chat.id, int(arg))
            elif arg.startswith("@"):
                member = await context.bot.get_chat_member(chat.id, arg)
            else:
                await message.reply_text("⚠️ Укажите корректного пользователя (реплай, ID или @username).")
                return
            target = member.user
        except Exception as e:
            await message.reply_text("⚠️ Не удалось найти пользователя.")
            await debug_log(context, f"[KICK] ❌ Ошибка поиска пользователя по {arg}: {e}")
            return
    else:
        await message.reply_text("⚠️ Укажите пользователя (реплай, ID или @username).")
        return

    if not target:
        await message.reply_text("⚠️ Не удалось определить пользователя.")
        await debug_log(context, "[KICK] ❌ Цель кика не определена")
        return

    target_member = await context.bot.get_chat_member(chat.id, target.id)
    if target_member.status in ("administrator", "creator"):
        await message.reply_text("🚫 Нельзя исключить администратора.")
        await debug_log(context, f"[KICK] 🚫 Попытка исключить администратора: {target.full_name}")
        return

    try:
        await context.bot.ban_chat_member(chat.id, target.id, until_date=0)
        await debug_log(context, f"[KICK] ✅ Исключён: {target.full_name} ({target.id})")
        mention = target.mention_html()
        await message.reply_html(f"👢 {mention} был исключён из группы.")
    except Exception as e:
        await message.reply_text(f"❌ Не удалось исключить: {e}")
        await debug_log(context, f"[KICK] ❌ Ошибка при исключении {target.id}: {e}")

    if command.startswith("!kick"):
        try:
            await message.delete()
            await debug_log(context, "[KICK] 🗑 Команда !kick удалена из чата")
        except:
            pass

# МУТ ПОЛЬЗОВАТЕЛЯ
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat = update.effective_chat
    user = update.effective_user
    sender_chat = message.sender_chat

    await debug_log(context, f"[MUTE] 🛡 /mute вызван: {user.full_name if user else 'None'}, sender_chat={sender_chat.title if sender_chat else '—'}")

    is_anonymous_admin = (
        user and user.is_bot and user.username == "GroupAnonymousBot"
        and sender_chat and sender_chat.id == chat.id
    )

    is_authorized = False
    if is_anonymous_admin:
        await debug_log(context, "[MUTE] ✅ Анонимный админ подтверждён — разрешено")
        is_authorized = True
    elif user:
        member = await context.bot.get_chat_member(chat.id, user.id)
        is_authorized = (
            member.status in ("administrator", "creator")
            and getattr(member, "can_restrict_members", False)
        )

    if not is_authorized:
        await message.reply_text("🚫 У вас нет прав на обеззвучивание.")
        await debug_log(context, f"[MUTE] ❌ Нет прав на /mute у {user.full_name if user else 'неизвестно'}")
        return

    parts = message.text.strip().split()
    if not parts:
        await message.reply_text("⚠️ Укажите пользователя или ответьте на сообщение. Пример: /mute @user 10min")
        return

    command = parts[0].lower()
    raw_args = parts[1:]
    target = None
    duration = None

    if message.reply_to_message:
        target = message.reply_to_message.from_user
        if raw_args:
            duration = raw_args[0]
        else:
            await message.reply_text("⚠️ Укажите длительность. Пример: /mute 5min")
            return

    elif len(raw_args) >= 2:
        target_str, duration = raw_args[0], raw_args[1]
        try:
            if target_str.isdigit():
                member = await context.bot.get_chat_member(chat.id, int(target_str))
            elif target_str.startswith("@"):
                member = await context.bot.get_chat_member(chat.id, target_str)
            else:
                await message.reply_text("⚠️ Укажите корректного пользователя (ID или @username).")
                return
            target = member.user
        except Exception as e:
            await message.reply_text("⚠️ Не удалось найти пользователя.")
            await debug_log(context, f"[MUTE] ❌ Ошибка поиска пользователя по {target_str}: {e}")
            return
    else:
        await message.reply_text("⚠️ Укажите пользователя и длительность. Пример: /mute @user 10min или /mute 5min в ответ")
        return

    if not target:
        await message.reply_text("⚠️ Не удалось определить пользователя.")
        await debug_log(context, "[MUTE] ❌ Цель мута не определена")
        return

    target_member = await context.bot.get_chat_member(chat.id, target.id)
    if target_member.status in ("administrator", "creator"):
        await message.reply_text("🚫 Нельзя обеззвучить администратора.")
        await debug_log(context, f"[MUTE] 🚫 Попытка обеззвучить администратора: {target.full_name}")
        return

    until_date = None
    msk_display = "навсегда"

    if duration:
        duration = duration.replace(" ", "")
        time_match = re.match(r"(\d+)([a-zA-Zа-яА-Я]+)", duration)
        if not time_match:
            await message.reply_text(
                "⚠️ Укажите корректную длительность. Примеры: 10min, 2h, 3d, 1mon, 1y\n\n"
                "Поддерживаемые единицы:\n"
                "- мин: min, m, мин\n"
                "- часы: h, ч\n"
                "- дни: d, д, day\n"
                "- месяцы: mon, mo, мес\n"
                "- годы: y, yr, г"
            )
            await debug_log(context, f"[MUTE] ❌ Не распарсилась длительность: {duration}")
            return

        value, unit = time_match.groups()
        try:
            value = int(value)
        except:
            await message.reply_text("⚠️ Неверное значение времени.")
            return

        unit = unit.lower()
        now = datetime.utcnow()

        if unit in ("min", "m", "мин"):
            until_date = now + timedelta(minutes=value)
        elif unit in ("h", "ч"):
            until_date = now + timedelta(hours=value)
        elif unit in ("d", "д", "day"):
            until_date = now + timedelta(days=value)
        elif unit in ("mon", "mo", "мес"):
            until_date = now + timedelta(days=30 * value)
        elif unit in ("y", "yr", "г"):
            until_date = now + timedelta(days=365 * value)
        else:
            await message.reply_text(
                "⚠️ Неверный формат времени. Примеры: 10min, 2h, 3d, 1mon, 1y\n\n"
                "Поддерживаемые единицы:\n"
                "- мин: min, m, мин\n"
                "- часы: h, ч\n"
                "- дни: d, д, day\n"
                "- месяцы: mon, mo, мес\n"
                "- годы: y, yr, г"
            )
            await debug_log(context, f"[MUTE] ❌ Неподдерживаемый юнит: {unit}")
            return

        msk_display = (until_date + timedelta(hours=3)).strftime("%Y-%m-%d %H:%M")

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target.id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        await debug_log(context, f"[MUTE] ✅ Обеззвучен: {target.full_name} до {until_date}")
        await message.reply_text(
            f"🔇 {target.full_name} обеззвучен до {msk_display} по МСК."
        )
    except Exception as e:
        await message.reply_text(f"❌ Не удалось обеззвучить: {e}")
        await debug_log(context, f"[MUTE] ❌ Ошибка при обеззвучивании {target.id}: {e}")

    if command.startswith("!mute"):
        try:
            await message.delete()
            await debug_log(context, "[MUTE] 🗑 Команда !mute удалена из чата")
        except:
            pass

# РАЗМУТ ПОЛЬЗОВАТЕЛЯ
async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat = update.effective_chat
    user = update.effective_user
    sender_chat = message.sender_chat

    await debug_log(context, f"[UNMUTE] 🛡 /unmute вызван: {user.full_name if user else 'None'}, sender_chat={sender_chat.title if sender_chat else '—'}")

    is_anonymous_admin = (
        user and user.is_bot and user.username == "GroupAnonymousBot"
        and sender_chat and sender_chat.id == chat.id
    )

    is_authorized = False
    if is_anonymous_admin:
        await debug_log(context, "[UNMUTE] ✅ Анонимный админ подтверждён — разрешено")
        is_authorized = True
    elif user:
        member = await context.bot.get_chat_member(chat.id, user.id)
        is_authorized = (
            member.status in ("administrator", "creator")
            and getattr(member, "can_restrict_members", False)
        )

    if not is_authorized:
        await message.reply_text("🚫 У вас нет прав на размут.")
        await debug_log(context, f"[UNMUTE] ❌ Нет прав на /unmute у {user.full_name if user else 'неизвестно'}")
        return

    parts = message.text.strip().split()
    command = parts[0].lower()
    raw_args = parts[1:]
    target = None

    if message.reply_to_message:
        target = message.reply_to_message.from_user

    elif raw_args:
        arg = raw_args[0]
        try:
            if arg.isdigit():
                member = await context.bot.get_chat_member(chat.id, int(arg))
            elif arg.startswith("@"):
                member = await context.bot.get_chat_member(chat.id, arg)
            else:
                await message.reply_text("⚠️ Укажите корректного пользователя (реплай, ID или @username).")
                return
            target = member.user
        except Exception as e:
            await message.reply_text("⚠️ Не удалось найти пользователя.")
            await debug_log(context, f"[UNMUTE] ❌ Ошибка поиска пользователя по {arg}: {e}")
            return
    else:
        await message.reply_text("⚠️ Укажите пользователя (реплай, ID или @username).")
        return

    if not target:
        await message.reply_text("⚠️ Не удалось определить пользователя.")
        await debug_log(context, "[UNMUTE] ❌ Цель размутирования не определена")
        return

    try:
        await context.bot.restrict_chat_member(
            chat_id=chat.id,
            user_id=target.id,
            permissions=ChatPermissions(can_send_messages=True)
        )
        await debug_log(context, f"[UNMUTE] ✅ Размучен: {target.full_name} ({target.id})")
        mention = target.mention_html()
        await message.reply_html(f"🔊 {mention} был размучен.")
    except Exception as e:
        await message.reply_text(f"❌ Не удалось размутить: {e}")
        await debug_log(context, f"[UNMUTE] ❌ Ошибка при размуте {target.id}: {e}")

    if command.startswith("!unmute"):
        try:
            await message.delete()
            await debug_log(context, "[UNMUTE] 🗑 Команда !unmute удалена из чата")
        except:
            pass

# ПРАВИЛА ЧАТА - ВЫВЕСТИ
async def show_rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules = context.bot_data.get("rules", {})
    user = update.effective_user

    await debug_log(context, f"[RULES] 📥 /rules вызвал: {user.full_name if user else 'неизвестный'}")

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
    chat = update.effective_chat
    user = update.effective_user
    sender_chat = message.sender_chat

    # 💥 Игнорируем альбомы
    if message.media_group_id:
        await debug_log(context, f"[SET_RULES] ⛔ Пропущено сообщение из альбома (media_group_id={message.media_group_id})")
        return

    # ⚠️ Только для /set_rules (в тексте или подписи)
    text_to_check = message.text or message.caption
    if not text_to_check or not text_to_check.strip().startswith("/set_rules"):
        return

    await debug_log(
        context,
        f"[SET_RULES] 🛡 /set_rules вызвал: {user.full_name if user else 'None'} | sender_chat={sender_chat.title if sender_chat else '—'}, chat_id={chat.id}"
    )

    is_authorized = False

    is_anonymous_admin = (
        user and user.is_bot and user.username == "GroupAnonymousBot"
        and sender_chat and sender_chat.id == chat.id
    )

    if is_anonymous_admin:
        await debug_log(context, "[SET_RULES] ✅ Анонимный админ подтверждён — разрешено")
        is_authorized = True
    elif user:
        member = await context.bot.get_chat_member(chat.id, user.id)
        is_authorized = (
            member.status in ("administrator", "creator")
            and getattr(member, "can_change_info", False)
        )

    if not is_authorized:
        await message.reply_text("🚫 У вас нет прав для изменения правил.")
        await debug_log(context, f"[SET_RULES] ❌ Отказано — нет прав у {user.full_name if user else '—'}")
        return

    text = message.caption if message.caption else message.text
    photo = message.photo[-1].file_id if message.photo else None

    if not text and not photo:
        await message.reply_text("❗ Отправьте текст, фото или и то, и другое.")
        await debug_log(context, "[SET_RULES] ❌ Ничего не передано — ни текста, ни фото")
        return

    # Удаление команды /set_rules из текста
    if text:
        text = text.replace("/set_rules", "").strip()

    context.bot_data["rules"] = {
        "text": text,
        "photo_file_id": photo
    }

    await debug_log(context, f"[SET_RULES] ✅ Правила обновлены. Текст: {text[:60]}{'...' if len(text) > 60 else ''}, Фото: {'есть' if photo else 'нет'}")
    await message.delete()
    await context.bot.send_message(chat.id, "✅ Правила обновлены.")



# ❗️❗️❗️ АВТОФИЛЬТРЫ БОТА ---------------------------------------------------------

# ПРОВЕРКА НИКА НА АРАБСКИЕ СИМВОЛЫ ПРИ ВХОДЕ
ARABIC_REGEX = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')

async def check_arabic_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    if not user:
        await debug_log(context, "[ARABIC] ⚠️ Нет пользователя в update — возможно, это системное сообщение")
        return

    full_name = f"{user.first_name or ''} {user.last_name or ''}"
    await debug_log(context, f"[ARABIC] 🔍 Проверка ника на арабский: user_id={user.id}, full_name='{full_name}'")

    if ARABIC_REGEX.search(full_name):
        await debug_log(context, f"[ARABIC] ❌ Найдены арабские символы в имени: user_id={user.id}")

        try:
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=user.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            await debug_log(context, f"[ARABIC] 🔇 Пользователь замучен за арабский ник: user_id={user.id}")

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔁 Проверить ник", callback_data=f"check_nick:{user.id}")]
            ])

            await update.message.reply_text(
                "❌ Ваше имя (никнейм) содержит арабские символы. Вы были замучены навсегда.\n"
                "Поменяйте имя (никнейм) и нажмите кнопку ниже для повторной проверки.",
                reply_markup=keyboard
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
    await debug_log(context, f"[ARABIC_BTN] 🔍 Кнопка проверки ника: user_id={user.id}, full_name='{full_name}'")

    if ARABIC_REGEX.search(full_name):
        await debug_log(context, f"[ARABIC_BTN] ❌ Арабские символы всё ещё в имени: user_id={user.id}")

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Проверить снова", callback_data=f"check_nick:{user.id}")]
        ])

        await query.edit_message_text(
            "❌ Имя (никнейм) всё ещё содержит арабские символы. Поменяйте и попробуйте снова.",
            reply_markup=keyboard
        )
    else:
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=user.id,
                permissions=ChatPermissions(can_send_messages=True)
            )
            await query.edit_message_text("✅ Имя (никнейм) изменёно. Мут снят.")
            await debug_log(context, f"[ARABIC_BTN] ✅ Арабские символы удалены — мут снят: user_id={user.id}")
        except Exception as e:
            await debug_log(context, f"[ARABIC_BTN] ❗ Ошибка при размуте: {e}")


# ПРОВЕРКА НИКА НА ПУСТОЙ
INVALID_NAME_REGEX = re.compile(r'^[\s.]+$')

async def check_empty_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user = update.effective_user
    chat = update.effective_chat

    if not message or not user:
        return

    name = f"{user.first_name or ''}{user.last_name or ''}".strip()
    await debug_log(context, f"[EMPTY_NAME] 🔍 Проверка имени: user_id={user.id}, name='{name}'")

    if not name or INVALID_NAME_REGEX.match(name):
        await debug_log(context, f"[EMPTY_NAME] ❌ Имя невалидно: user_id={user.id}, name='{name}'")
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=user.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            await debug_log(context, f"[EMPTY_NAME] 🔇 Замучен за пустое/некорректное имя: user_id={user.id}")

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔁 Проверить имя (никнейм)", callback_data=f"check_name:{user.id}")]
            ])

            await message.reply_text(
                "❌ Ваше имя (никнейм) отсутствует или состоит только из пробелов/точек. Вы были замучены навсегда.\n"
                "Пожалуйста, установите нормальное имя (никнейм) в профиле и нажмите кнопку ниже для повторной проверки.",
                reply_markup=keyboard
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

    await debug_log(context, f"[NAME_BTN] 🔍 Проверка кнопкой имени: user_id={user.id}, name='{name}'")

    if not name or INVALID_NAME_REGEX.match(name):
        await debug_log(context, f"[NAME_BTN] ❌ Имя всё ещё невалидно: user_id={user.id}")
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Проверить снова", callback_data=f"check_name:{user.id}")]
        ])
        await query.edit_message_text(
            "❌ Имя (никнейм) всё ещё отсутствует или слишком подозрительное. Установите нормальное имя.",
            reply_markup=keyboard
        )
    else:
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=user.id,
                permissions=ChatPermissions(can_send_messages=True)
            )
            await query.edit_message_text("✅ Имя (никнейм) принято. Мут снят.")
            await debug_log(context, f"[NAME_BTN] ✅ Мут снят: user_id={user.id}, name='{name}'")
        except Exception as e:
            await debug_log(context, f"[NAME_BTN] ❗ Ошибка при размуте: {e}")

# ПРОВЕРКА НА ПУСТОЙ ЮЗЕРНЕЙМ
async def check_empty_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user = update.effective_user
    chat = update.effective_chat

    if not message or not user:
        return

    await debug_log(context, f"[USERNAME_EMPTY] 🔍 Проверка username: user_id={user.id}, username={user.username}")

    if not user.username:
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=user.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            await debug_log(context, f"[USERNAME_EMPTY] 🔇 Мут за отсутствие username: user_id={user.id}")

            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔁 Проверить username", callback_data=f"check_username:{user.id}")]
            ])

            await message.reply_text(
                "❌ У вас не установлен username (имя пользователя). Вы были замучены навсегда.\n"
                "Пожалуйста, укажите его в профиле и нажмите кнопку ниже для повторной проверки.",
                reply_markup=keyboard
            )
        except Exception as e:
            await debug_log(context, f"[USERNAME_EMPTY] ❗ Ошибка при муте: {e}")

# КНОПКА ПРОВЕРКИ НА ПУСТОЙ ЮЗЕРНЕЙМ
async def handle_check_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    chat = query.message.chat

    await debug_log(context, f"[USERNAME_BTN] 🔍 Кнопка проверки username: user_id={user.id}, username={user.username}")

    if not user.username:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔁 Проверить снова", callback_data=f"check_username:{user.id}")]
        ])
        await query.edit_message_text(
            "❌ Username (имя пользователя) всё ещё не установлено. Пожалуйста, обновите профиль и попробуйте снова.",
            reply_markup=keyboard
        )
        await debug_log(context, f"[USERNAME_BTN] ❌ Username по-прежнему отсутствует: user_id={user.id}")
    else:
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=user.id,
                permissions=ChatPermissions(can_send_messages=True)
            )
            await query.edit_message_text("✅ Username (имя пользователя) найдено. Мут снят.")
            await debug_log(context, f"[USERNAME_BTN] ✅ Username установлен, мут снят: user_id={user.id}")
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
        await debug_log(context, f"[SPAM_CHECK] ⏭️ Пропущена команда от {user.id}: {message.text!r}")
        return

    await debug_log(context, f"[SPAM_CHECK] 📨 Сообщение от {user.id}: {message.text!r}")

    # Хранилище спам-трекинга
    user_data = context.chat_data.setdefault("spam_tracker", {})
    entry = user_data.get(user.id, {"text": "", "count": 0})

    if message.text == entry["text"]:
        entry["count"] += 1
        await debug_log(context, f"[SPAM_CHECK] 🔁 Повтор #{entry['count']} от {user.id}")
    else:
        entry["text"] = message.text
        entry["count"] = 1
        await debug_log(context, f"[SPAM_CHECK] ✏️ Новый текст от {user.id}, счётчик сброшен")

    user_data[user.id] = entry

    if entry["count"] >= 3:
        try:
            until_date = update.message.date + timedelta(hours=1)
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_date
            )
            await message.reply_text(
                f"🚫 Пользователь {user.full_name} замучен на 1 час за спам одинаковыми сообщениями."
            )
            entry["count"] = 0
            await debug_log(context, f"[SPAM_CHECK] 🔇 {user.full_name} ({user.id}) замучен на 1 час за спам")
        except Exception as e:
            await debug_log(context, f"[SPAM_CHECK] ❗ Ошибка при муте за спам: {e}")

# КАПЧА ПРИ ВХОДЕ - ВЫВОД
CAPTCHA_EMOJIS = ["🫖", "☕️", "🧋", "🍵", "🍺", "🧃", "🥤", "🥃"]

async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for user in update.message.new_chat_members:
        if user.is_bot:
            continue

        chat_id = update.effective_chat.id
        await debug_log(context, f"[CAPTCHA_JOIN] 🆕 Новый участник: {user.full_name} (ID: {user.id})")

        # Мутим при входе
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            await debug_log(context, f"[CAPTCHA_JOIN] 🔇 Пользователь {user.id} замучен до прохождения капчи")
        except Exception as e:
            await debug_log(context, f"[CAPTCHA_JOIN] ❗ Ошибка при муте нового пользователя: {e}")

        # Формируем капчу
        correct = random.choice(CAPTCHA_EMOJIS)
        fake = random.sample([e for e in CAPTCHA_EMOJIS if e != correct], 3)
        options = fake + [correct]
        random.shuffle(options)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(e, callback_data=f"captcha:{user.id}:{e}:{correct}")]
            for e in options
        ])

        try:
            msg = await context.bot.send_message(
                chat_id=chat_id,
                text=f"👋 Привет, {user.full_name}!\nДавай убедимся, что ты не бот!\nНажми на эмодзи: {correct}",
                reply_markup=keyboard
            )
            await debug_log(context, f"[CAPTCHA_JOIN] 📩 Капча выдана пользователю {user.id}, сообщение: {msg.message_id}")
            context.chat_data[user.id] = {"captcha_msg_id": msg.message_id}
        except Exception as e:
            await debug_log(context, f"[CAPTCHA_JOIN] ❗ Ошибка при отправке капчи: {e}")

        try:
            context.job_queue.run_once(
                kick_if_no_captcha,
                when=300,
                data={"chat_id": chat_id, "user_id": user.id},
                name=str(user.id)
            )
            await debug_log(context, f"[CAPTCHA_JOIN] ⏱ Таймер кика установлен для user_id={user.id}")
        except Exception as e:
            await debug_log(context, f"[CAPTCHA_JOIN] ❗ Ошибка при установке таймера кика: {e}")


# ОБРАБОТКА НАЖАТИЯ КАПЧИ
async def handle_captcha_press(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    chat_id = query.message.chat.id
    parts = query.data.split(":")
    uid, pressed, correct = int(parts[1]), parts[2], parts[3]

    await debug_log(context, f"[CAPTCHA_PRESS] 🔘 Нажата кнопка капчи: user_id={user.id}, нажал={pressed}, правильный={correct}")

    if user.id != uid:
        await query.answer("Это не ваша капча", show_alert=True)
        await debug_log(context, f"[CAPTCHA_PRESS] ⛔ Попытка нажать чужую капчу: {user.id} != {uid}")
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
            await debug_log(context, f"[CAPTCHA_PRESS] 🗑 Удалено сообщение капчи: msg_id={msg_id}")
    except Exception as e:
        await debug_log(context, f"[CAPTCHA_PRESS] ❗ Ошибка при удалении капчи: {e}")

    if pressed == correct:
        try:
            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user.id,
                permissions=ChatPermissions(can_send_messages=True)
            )
            await context.bot.send_message(chat_id, f"✅ {user.full_name}, добро пожаловать!")
            await debug_log(context, f"[CAPTCHA_PRESS] 🔓 Размут пользователя: {user.id}")
        except Exception as e:
            await debug_log(context, f"[CAPTCHA_PRESS] ❗ Ошибка при размуте: {e}")
    else:
        try:
            await context.bot.send_message(chat_id, "❌ Неверный выбор. Вы были удалены.")
            await context.bot.ban_chat_member(chat_id, user.id)
            await debug_log(context, f"[CAPTCHA_PRESS] 🚫 Пользователь {user.id} кикнут за неверную капчу")
        except Exception as e:
            await debug_log(context, f"[CAPTCHA_PRESS] ❗ Ошибка при кике: {e}")

# КАПЧА - АВТОКИК ПО ТАЙМЕРУ
async def kick_if_no_captcha(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    chat_id = data["chat_id"]
    user_id = data["user_id"]

    await debug_log(context, f"[CAPTCHA_TIMEOUT] ⏰ Таймер истёк — кик: user_id={user_id}")
    try:
        await context.bot.ban_chat_member(chat_id, user_id)
        await context.bot.unban_chat_member(chat_id, user_id)
        await debug_log(context, f"[CAPTCHA_TIMEOUT] 👢 Пользователь {user_id} был кикнут по таймеру капчи")
    except Exception as e:
        await debug_log(context, f"[CAPTCHA_TIMEOUT] ❗ Ошибка при автокике user_id={user_id}: {e}")


# ❗️❗️❗️ АВТОСООБЩЕНИЯ БОТА ---------------------------------------------------------
# АВТОСООБЩЕНИЕ ПРО РАЗМУТ, РАЗБАН И ТД
async def chat_member_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    old = update.chat_member.old_chat_member
    new = update.chat_member.new_chat_member
    chat = update.effective_chat
    user = new.user

    await debug_log(
        context,
        f"[AUTOMSG] Изменение прав у {user.full_name} ({user.id}): {old.status} → {new.status}"
    )

    # ✅ Разбан
    if old.status == "kicked" and new.status == "member":
        await context.bot.send_message(
            chat.id,
            f"✅ {user.mention_html()} был разбанен.",
            parse_mode="HTML"
        )
        await debug_log(context, f"[AUTOMSG] Подтверждён разбан: {user.full_name} ({user.id})")

    # ✅ Размут
    if old.can_send_messages is False and new.can_send_messages is True:
        await context.bot.send_message(
            chat.id,
            f"🔊 {user.mention_html()} был размучен.",
            parse_mode="HTML"
        )
        await debug_log(context, f"[AUTOMSG] Подтверждён размут: {user.full_name} ({user.id})")

# ❗️❗️❗️ ХЕНДЛЕРЫ БОТА ---------------------------------------------------------

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    job_queue = app.job_queue

    # 0–3 — фильтры на сообщения
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, check_arabic_name), group=0)
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, check_spam), group=1)
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, check_empty_name), group=2)
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, check_empty_username), group=3)

    # 4 — вход в группу
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member), group=4)

    # 5 — просмотр правил
    app.add_handler(CommandHandler("rules", show_rules), group=5)
    

    # 6 — установка правил (обрабатывает текст и подпись с фото)
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, set_rules), group=6)

    # 7 — админ-модерация
    app.add_handler(CommandHandler("ban", ban_user), group=7)
    app.add_handler(MessageHandler(filters.Regex(r"^!?unban"), unban_user), group=7)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^!ban"), ban_user), group=7)
    app.add_handler(CommandHandler("mute", mute_user), group=7)
    app.add_handler(MessageHandler(filters.Regex(r"^!?unmute"), unmute_user), group=7)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r"^!mute"), mute_user), group=7)
    app.add_handler(MessageHandler(filters.Regex(r"^!?kick"), kick_user), group=7)

    # 8 — пересылка из каналов
    app.add_handler(MessageHandler(filters.UpdateType.CHANNEL_POST, forward_by_hashtag), group=8)

    # 9 — автосообщение про размут
    app.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.CHAT_MEMBER), group=9)
    app.add_handler(ChatMemberHandler(chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER), group=9)

    app.add_handler(CommandHandler("thread_id", thread_id_command), group=99)
    app.add_handler(CommandHandler("chat_id", show_chat_id), group=99)
    app.add_handler(CallbackQueryHandler(handle_check_nick, pattern=r'^check_nick:'))
    app.add_handler(CallbackQueryHandler(handle_check_name, pattern=r'^check_name:'))
    app.add_handler(CallbackQueryHandler(handle_check_username, pattern=r'^check_username:'))
    app.add_handler(CallbackQueryHandler(handle_captcha_press, pattern=r"^captcha:"))
    app.post_init = set_bot_commands
    debug_log_sync("Бот запущен. Ждёт сообщений из тем...")
    app.run_polling()
