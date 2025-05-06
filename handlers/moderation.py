from telegram import Update
from telegram.ext import ContextTypes


# 🚫 БАН
async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat = update.effective_chat
    user = update.effective_user
    sender_chat = message.sender_chat

    await debug_log(
        context,
        f"[BAN] 🛡 Команда /ban вызвана: {user.full_name if user else '—'}, sender_chat={sender_chat.title if sender_chat else '—'}",
    )

    is_anonymous_admin = (
        user
        and user.is_bot
        and user.username == "GroupAnonymousBot"
        and sender_chat
        and sender_chat.id == chat.id
    )

    is_authorized = False
    if is_anonymous_admin:
        await debug_log(context, "[BAN] ✅ Анонимный админ подтверждён — разрешено")
        is_authorized = True
    elif user:
        member = await context.bot.get_chat_member(chat.id, user.id)
        is_authorized = member.status in ("administrator", "creator") and getattr(
            member, "can_restrict_members", False
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
                await debug_log(
                    context, f"[BAN] ❌ Полный текст ошибки при username: {repr(e)}"
                )
                return
        else:
            await message.reply_text(
                "⚠️ Укажите корректного пользователя (реплай, ID или @username)."
            )
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
        await debug_log(
            context, f"[BAN] 🚫 Попытка бана администратора: {target.full_name}"
        )
        return

    try:
        await context.bot.ban_chat_member(chat.id, target.id)
        await debug_log(
            context, f"[BAN] ✅ Забанен: {target.full_name} (ID: {target.id})"
        )
        mention = target.mention_html()
        await message.reply_html(f"🚫 {mention} был забанен.")
        await log_event(target, "ban", f"Команда: {command}")
    except Exception as e:
        await message.reply_text(f"❌ Не удалось забанить: {e}")
        await debug_log(
            context, f"[BAN] ❌ Ошибка при бане {target.full_name}: {repr(e)}"
        )

    if command.startswith("!ban"):
        try:
            await message.delete()
            await debug_log(context, "[BAN] 🗑 Команда !ban удалена из чата")
        except:
            pass
    ...


# ✅ РАЗБАН
async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat = update.effective_chat
    user = update.effective_user
    sender_chat = message.sender_chat

    await debug_log(
        context,
        f"[UNBAN] 📥 Команда /unban вызвана: {user.full_name if user else sender_chat.title}",
    )

    is_authorized = False
    if (
        user
        and user.username == "GroupAnonymousBot"
        and sender_chat
        and sender_chat.id == chat.id
    ):
        is_authorized = True
        await debug_log(context, "[UNBAN] ✅ Подтверждён анонимный админ")
    elif user:
        try:
            member = await context.bot.get_chat_member(chat.id, user.id)
            is_authorized = member.status in ("administrator", "creator") and getattr(
                member, "can_restrict_members", False
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
        result = await context.bot.unban_chat_member(
            chat.id, target_id, only_if_banned=True
        )
        mention = f"<a href='tg://user?id={target_id}'>{target_name or target_id}</a>"
        if result:
            await message.reply_html(f"✅ {mention} был разбанен.")
            await debug_log(context, f"[UNBAN] ✅ Разбанен: {target_name or target_id}")
        else:
            await message.reply_text("⚠️ Пользователь не был в бане.")
            await debug_log(
                context, f"[UNBAN] ℹ️ Пользователь {target_id} не находился в бане"
            )
    except Exception as e:
        await message.reply_text(f"❌ Не удалось разбанить: {e}")
        await debug_log(
            context, f"[UNBAN] ❌ Ошибка при разблокировке {target_id}: {e}"
        )
    ...


# 👢 КИК
async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat = update.effective_chat
    user = update.effective_user
    sender_chat = message.sender_chat

    await debug_log(
        context,
        f"[KICK] 🛡 /kick вызван: {user.full_name if user else 'None'}, sender_chat={sender_chat.title if sender_chat else '—'}",
    )

    is_anonymous_admin = (
        user
        and user.is_bot
        and user.username == "GroupAnonymousBot"
        and sender_chat
        and sender_chat.id == chat.id
    )

    is_authorized = False
    if is_anonymous_admin:
        await debug_log(context, "[KICK] ✅ Анонимный админ подтверждён — разрешено")
        is_authorized = True
    elif user:
        member = await context.bot.get_chat_member(chat.id, user.id)
        is_authorized = member.status in ("administrator", "creator") and getattr(
            member, "can_restrict_members", False
        )

    if not is_authorized:
        await message.reply_text("🚫 У вас нет прав на исключение пользователей.")
        await debug_log(
            context,
            f"[KICK] ❌ Нет прав на кик у {user.full_name if user else 'неизвестно'}",
        )
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
                await message.reply_text(
                    "⚠️ Укажите корректного пользователя (реплай, ID или @username)."
                )
                return
            target = member.user
        except Exception as e:
            await message.reply_text("⚠️ Не удалось найти пользователя.")
            await debug_log(
                context, f"[KICK] ❌ Ошибка поиска пользователя по {arg}: {e}"
            )
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
        await debug_log(
            context, f"[KICK] 🚫 Попытка исключить администратора: {target.full_name}"
        )
        return

    try:
        await context.bot.ban_chat_member(chat.id, target.id, until_date=0)
        await debug_log(
            context, f"[KICK] ✅ Исключён: {target.full_name} ({target.id})"
        )
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
    ...


# 🔇 МУТ
async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat = update.effective_chat
    user = update.effective_user
    sender_chat = message.sender_chat

    await debug_log(
        context,
        f"[MUTE] 🛡 /mute вызван: {user.full_name if user else 'None'}, sender_chat={sender_chat.title if sender_chat else '—'}",
    )

    is_anonymous_admin = (
        user
        and user.is_bot
        and user.username == "GroupAnonymousBot"
        and sender_chat
        and sender_chat.id == chat.id
    )

    is_authorized = False
    if is_anonymous_admin:
        await debug_log(context, "[MUTE] ✅ Анонимный админ подтверждён — разрешено")
        is_authorized = True
    elif user:
        member = await context.bot.get_chat_member(chat.id, user.id)
        is_authorized = member.status in ("administrator", "creator") and getattr(
            member, "can_restrict_members", False
        )

    if not is_authorized:
        await message.reply_text("🚫 У вас нет прав на обеззвучивание.")
        await debug_log(
            context,
            f"[MUTE] ❌ Нет прав на /mute у {user.full_name if user else 'неизвестно'}",
        )
        return

    parts = message.text.strip().split()
    if not parts:
        await message.reply_text(
            "⚠️ Укажите пользователя или ответьте на сообщение. Пример: /mute @user 10min"
        )
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
                await message.reply_text(
                    "⚠️ Укажите корректного пользователя (ID или @username)."
                )
                return
            target = member.user
        except Exception as e:
            await message.reply_text("⚠️ Не удалось найти пользователя.")
            await debug_log(
                context, f"[MUTE] ❌ Ошибка поиска пользователя по {target_str}: {e}"
            )
            return
    else:
        await message.reply_text(
            "⚠️ Укажите пользователя и длительность. Пример: /mute @user 10min или /mute 5min в ответ"
        )
        return

    if not target:
        await message.reply_text("⚠️ Не удалось определить пользователя.")
        await debug_log(context, "[MUTE] ❌ Цель мута не определена")
        return

    target_member = await context.bot.get_chat_member(chat.id, target.id)
    if target_member.status in ("administrator", "creator"):
        await message.reply_text("🚫 Нельзя обеззвучить администратора.")
        await debug_log(
            context, f"[MUTE] 🚫 Попытка обеззвучить администратора: {target.full_name}"
        )
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
            await debug_log(
                context, f"[MUTE] ❌ Не распарсилась длительность: {duration}"
            )
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
            permissions=telegram.ChatPermissions(can_send_messages=False),
            until_date=until_date,
        )
        await debug_log(
            context, f"[MUTE] ✅ Обеззвучен: {target.full_name} до {until_date}"
        )
        await message.reply_text(
            f"🔇 {target.full_name} обеззвучен до {msk_display} по МСК."
        )
        await log_event(target, "mute", f"до {until_date}")
    except Exception as e:
        await message.reply_text(f"❌ Не удалось обеззвучить: {e}")
        await debug_log(
            context, f"[MUTE] ❌ Ошибка при обеззвучивании {target.id}: {e}"
        )

    if command.startswith("!mute"):
        try:
            await message.delete()
            await debug_log(context, "[MUTE] 🗑 Команда !mute удалена из чата")
        except:
            pass
    ...


# 🔊 РАЗМУТ
async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    chat = update.effective_chat
    user = update.effective_user
    sender_chat = message.sender_chat

    await debug_log(
        context,
        f"[UNMUTE] 🛡 /unmute вызван: {user.full_name if user else 'None'}, sender_chat={sender_chat.title if sender_chat else '—'}",
    )

    is_anonymous_admin = (
        user
        and user.is_bot
        and user.username == "GroupAnonymousBot"
        and sender_chat
        and sender_chat.id == chat.id
    )

    is_authorized = False
    if is_anonymous_admin:
        await debug_log(context, "[UNMUTE] ✅ Анонимный админ подтверждён — разрешено")
        is_authorized = True
    elif user:
        member = await context.bot.get_chat_member(chat.id, user.id)
        is_authorized = member.status in ("administrator", "creator") and getattr(
            member, "can_restrict_members", False
        )

    if not is_authorized:
        await message.reply_text("🚫 У вас нет прав на размут.")
        await debug_log(
            context,
            f"[UNMUTE] ❌ Нет прав на /unmute у {user.full_name if user else 'неизвестно'}",
        )
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
                await message.reply_text(
                    "⚠️ Укажите корректного пользователя (реплай, ID или @username)."
                )
                return
            target = member.user
        except Exception as e:
            await message.reply_text("⚠️ Не удалось найти пользователя.")
            await debug_log(
                context, f"[UNMUTE] ❌ Ошибка поиска пользователя по {arg}: {e}"
            )
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
            permissions=telegram.ChatPermissions(can_send_messages=True),
        )
        await debug_log(
            context, f"[UNMUTE] ✅ Размучен: {target.full_name} ({target.id})"
        )
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
    ...
