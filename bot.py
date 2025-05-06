# ❗️❗️❗️ ИМПОРТ БИБЛИОТЕК ТГ ДЛЯ БОТА ---------------------------------------------------------
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dotenv import load_dotenv
from handlers.forward import forward_by_hashtag
from handlers.warn import warn_user, full_unwarn, unwarn, unwarn_all_users
from config import BOT_TOKEN
from handlers.automsg import chat_member_update
from handlers.leave import on_user_left
from handlers.captcha import (
    on_new_member,
    handle_captcha_press,
)
from handlers.commands import set_bot_commands, show_chat_id, thread_id_command
from handlers.filters import (
    check_arabic_name,
    check_empty_name,
    check_empty_username,
    handle_check_nick,
    handle_check_name,
    handle_check_username,
    check_spam,
)
from handlers.moderation import ban_user, unban_user, kick_user, mute_user, unmute_user
from handlers.rules import show_rules, set_rules
from utils.logger import debug_log_sync

load_dotenv()
DEBUG_CHAT_ID = int(os.getenv("DEBUG_CHAT_ID"))

from telegram.ext import (
    ChatMemberHandler,
    CallbackQueryHandler,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
)

# ❗️❗️❗️ ХЕНДЛЕРЫ БОТА ---------------------------------------------------------

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    job_queue = app.job_queue

    # 0–3 — фильтры на сообщения
    app.add_handler(
        MessageHandler(filters.TEXT & filters.ChatType.GROUPS, check_arabic_name),
        group=0,
    )
    app.add_handler(
        MessageHandler(filters.TEXT & filters.ChatType.GROUPS, check_spam), group=1
    )
    app.add_handler(
        MessageHandler(filters.TEXT & filters.ChatType.GROUPS, check_empty_name),
        group=2,
    )
    app.add_handler(
        MessageHandler(filters.TEXT & filters.ChatType.GROUPS, check_empty_username),
        group=3,
    )
    app.add_handler(CallbackQueryHandler(handle_check_nick, pattern=r"^check_nick:"))
    app.add_handler(CallbackQueryHandler(handle_check_name, pattern=r"^check_name:"))
    app.add_handler(
        CallbackQueryHandler(handle_check_username, pattern=r"^check_username:")
    )

    # 4 — вход|выход в группу
    app.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, on_new_member), group=4
    )
    app.add_handler(CallbackQueryHandler(handle_captcha_press, pattern=r"^captcha:"))
    app.add_handler(
        MessageHandler(filters.StatusUpdate.LEFT_CHAT_MEMBER, on_user_left), group=4
    )

    # 5-6 —  правила чата
    app.add_handler(CommandHandler("rules", show_rules), group=5)
    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO, set_rules), group=6)

    # 7 — админ-модерация
    app.add_handler(CommandHandler("ban", ban_user), group=7)
    app.add_handler(MessageHandler(filters.Regex(r"^!?unban"), unban_user), group=7)
    app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(r"^!ban"), ban_user), group=7
    )
    app.add_handler(CommandHandler("mute", mute_user), group=7)
    app.add_handler(MessageHandler(filters.Regex(r"^!?unmute"), unmute_user), group=7)
    app.add_handler(
        MessageHandler(filters.TEXT & filters.Regex(r"^!mute"), mute_user), group=7
    )
    app.add_handler(MessageHandler(filters.Regex(r"^!?kick"), kick_user), group=7)
    # /warn — остаётся в чате
    app.add_handler(CommandHandler("warn", warn_user), group=7)

    # !warn — удаляется после обработки
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^!warn(\s|$)"),
            lambda u, c: warn_user(u, c, auto_delete=True),
        ),
        group=7,
    )
    # /full_unwarn — оставляет команду
    app.add_handler(CommandHandler("full_unwarn", full_unwarn), group=7)

    # !full_unwarn — удаляет команду
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^!full_unwarn(\s|$)"),
            lambda u, c: full_unwarn(u, c, auto_delete=True),
        ),
        group=7,
    )

    # /unwarn — оставляет команду
    app.add_handler(CommandHandler("unwarn", unwarn), group=7)

    # !unwarn — удаляет команду
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^!unwarn(\s|$)"),
            lambda u, c: unwarn(u, c, auto_delete=True),
        ),
        group=7,
    )

    # /unwarn_all_users — оставляет команду
    app.add_handler(CommandHandler("unwarn_all_users", unwarn_all_users), group=7)

    # !unwarn_all_users — удаляет команду
    app.add_handler(
        MessageHandler(
            filters.Regex(r"^!unwarn_all_users(\s|$)"),
            lambda u, c: unwarn_all_users(u, c, auto_delete=True),
        ),
        group=7,
    )

    # 8 — пересылка из каналов
    app.add_handler(
        MessageHandler(filters.UpdateType.CHANNEL_POST, forward_by_hashtag), group=8
    )

    # 9 — автосообщение про размут
    app.add_handler(
        ChatMemberHandler(chat_member_update, ChatMemberHandler.CHAT_MEMBER), group=9
    )
    app.add_handler(
        ChatMemberHandler(chat_member_update, ChatMemberHandler.MY_CHAT_MEMBER), group=9
    )

    app.add_handler(CommandHandler("chat_id", show_chat_id), group=99)
    app.add_handler(CommandHandler("thread_id", thread_id_command), group=99)
    app.post_init = set_bot_commands

    debug_log_sync("Бот запущен. Ждёт сообщений из тем...")
    app.run_polling()
