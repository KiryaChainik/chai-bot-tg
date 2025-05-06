import telegram
from telegram import Update
from telegram.ext import ContextTypes

from utils.logger import debug_log, debug_log_sync


# ПОДСКАЗКИ ПО КОМАНДАМ
async def set_bot_commands(application):
    group_ids = [-1002443521655]  # ← сюда добавляй все нужные chat_id

    # Установка глобального меню кнопок
    await application.bot.set_chat_menu_button(
        menu_button=telegram.MenuButtonCommands()
    )
    debug_log_sync("[CMD] ✅ Установлено глобальное меню команд")

    for chat_id in group_ids:
        debug_log_sync(f"[CMD] ⚙️ Настройка команд для группы {chat_id}")

        # Команды для всех пользователей в группе
        await application.bot.set_my_commands(
            commands=[
                telegram.BotCommand("menu", "Показать все доступные команды бота"),
                telegram.BotCommand("rules", "Показать правила группы"),
            ],
            scope=telegram.BotCommandScopeChat(chat_id=chat_id),
        )

        # Команды только для админов
        await application.bot.set_my_commands(
            commands=[
                telegram.BotCommand("menu", "Показать все доступные команды бота"),
                telegram.BotCommand("rules", "Показать правила группы"),
                telegram.BotCommand("set_rules", "Установить правила"),
                telegram.BotCommand("ban", "Забанить пользователя"),
                telegram.BotCommand("unban", "Разбанить пользователя"),
                telegram.BotCommand("kick", "Исключить пользователя"),
                telegram.BotCommand("mute", "Обеззвучить пользователя"),
                telegram.BotCommand("unmute", "Снять мут"),
            ],
            scope=telegram.BotCommandScopeChatAdministrators(chat_id=chat_id),
        )

    # Резерв: глобальные команды по умолчанию
    await application.bot.set_my_commands(
        commands=[
            telegram.BotCommand("rules", "Показать правила группы"),
        ],
        scope=telegram.BotCommandScopeDefault(),
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
        await debug_log(
            context, f"[MENU] 📥 {user.full_name} ({user.id}) нажал кнопку 'Правила'"
        )
    elif data == "menu_rights":
        await query.message.reply_text(
            "🔐 У вас есть базовые права. Если вы админ — используйте /ban, /mute и другие."
        )
        await debug_log(
            context, f"[MENU] 📥 {user.full_name} ({user.id}) нажал кнопку 'Мои права'"
        )


# ПОЛУЧЕНИЕ ID ЧАТА ПО КОМАНДЕ
async def show_chat_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    user = update.effective_user

    await update.message.reply_text(f"chat_id: {chat.id}")
    await debug_log(
        context, f"[CHAT_ID] ℹ️ {user.full_name} ({user.id}) запросил chat_id: {chat.id}"
    )


# ПОЛУЧЕНИЕ ID ТРЕДА ПО КОМАНДЕ
async def thread_id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message or update.channel_post
    if not message:
        await debug_log(
            context, "[THREAD_ID] ⚠️ Нет message — ни обычного, ни channel_post"
        )
        return

    chat = message.chat
    user = message.from_user or message.sender_chat

    if not chat.is_forum:
        await message.reply_text("❌ Это не форум. Команда работает только в темах.")
        await debug_log(
            context,
            f"[THREAD_ID] ℹ️ Команда вызвана вне форума пользователем: {user.full_name if hasattr(user, 'full_name') else user.title}",
        )
        return

    if not message.message_thread_id:
        await message.reply_text("⚠️ Это не сообщение внутри темы форума.")
        await debug_log(
            context, f"[THREAD_ID] ⚠️ Команда вызвана вне темы. Чат: {chat.id}"
        )
        return

    await message.reply_text(
        f"📌 ID этой темы (message_thread_id): {message.message_thread_id}"
    )
    await debug_log(
        context,
        f"[THREAD_ID] 📌 Запрос от {user.full_name if hasattr(user, 'full_name') else user.title}: {message.message_thread_id}",
    )
