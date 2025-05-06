from datetime import datetime, timedelta

from pytz import timezone
from sqlalchemy import delete, select
from sqlalchemy import insert
from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes

from database import async_session
from models.events_log import EventLog
from models.users import User, UserStatus
from models.violations import Violation
from utils.logger import debug_log


async def warn_user(
        update: Update, context: ContextTypes.DEFAULT_TYPE, auto_delete: bool = False
):
    message = update.message
    chat = update.effective_chat
    sender = update.effective_user
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if message.text.startswith("!warn"):
        parts = message.text.split(maxsplit=1)
        reason = parts[1] if len(parts) > 1 else "Без причины"
    else:
        reason = " ".join(context.args) if context.args else "Без причины"

    if not target:
        await message.reply_text("⚠️ Используй /warn или !warn в ответ на сообщение.")
        return

    async with async_session() as session:
        # проверка, существует ли пользователь в users
        result = await session.execute(select(User).where(User.user_id == target.id))
        existing_user = result.scalar_one_or_none()

        # если нет — создаём
        if not existing_user:
            await session.execute(
                insert(User).values(
                    user_id=target.id,
                    first_name=target.first_name,
                    last_name=target.last_name or None,
                    status=UserStatus.active,
                )
            )
        # 1. Добавляем запись о варне в violations
        await session.execute(
            insert(Violation).values(
                user_id=target.id,
                reason=reason,
                created_at=datetime.utcnow(),
            )
        )

        # 2. Считаем количество варнов
        result = await session.execute(
            select(Violation).where(Violation.user_id == target.id)
        )
        warn_count = len(result.fetchall())

        # 3. Логируем событие в events_log
        await session.execute(
            insert(EventLog).values(
                user_id=target.id,
                event_type="warn",
                event_details=f"Причина: {reason}" if reason else "",
                created_at=datetime.utcnow(),
            )
        )

        await session.commit()

        # 4. Уведомление в DEBUG
        await debug_log(
            context,
            f"[WARN] ⚠️ {target.full_name} (ID: {target.id}) получил предупреждение #{warn_count}. Причина: {reason}",
        )

        # 5. Ответ в чат
        warn_text = (
            f"⚠️ Вы получили предупреждение!\n" f"У вас {warn_count} предупреждений.\n"
        )
        if reason != "Без причины":
            warn_text += f"Причина: {reason}\n"
        warn_text += (
            f"\nНа 4 и 8 предупреждениях — мут на 5 дней.\n"
            f"На 10 предупреждениях — бан навсегда."
        )
        await message.reply_text(warn_text)

        # 6. Автомут на 4 и 8 варне
        if warn_count in [4, 8]:
            until_date = datetime.utcnow() + timedelta(days=5)
            await context.bot.restrict_chat_member(
                chat_id=chat.id,
                user_id=target.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until_date,
            )
            await session.execute(
                insert(EventLog).values(
                    user_id=target.id,
                    event_type="auto_mute",
                    event_details=f"Мут на 5 дней (варн #{warn_count})",
                    created_at=datetime.utcnow(),
                )
            )
            await session.commit()

            # сообщение в чат об обеззвучивании
            msk_time = until_date.replace(tzinfo=timezone("UTC")).astimezone(
                timezone("Europe/Moscow")
            )
            await message.reply_text(
                f"🔇 {target.full_name} был обеззвучен на 5 дней, до {msk_time.strftime('%Y-%m-%d %H:%M:%S')} по МСК."
            )

            await debug_log(
                context,
                f"[WARN] 🤐 Автомут {target.full_name} на 5 дней (варн #{warn_count})",
            )

        # 7. Автобан на 10 варне
        if warn_count == 10:
            await context.bot.ban_chat_member(chat.id, target.id)
            await session.execute(
                insert(EventLog).values(
                    user_id=target.id,
                    event_type="auto_ban",
                    event_details="Бан за 10 предупреждений",
                    created_at=datetime.utcnow(),
                )
            )
            await session.commit()

            await message.reply_text(f"🔨 {target.full_name} был забанен навсегда.")

            await debug_log(
                context, f"[WARN] 🔨 Автобан {target.full_name} за 10 варнов"
            )

    # 8. Автоудаление команды (!warn)
    if auto_delete:
        try:
            await message.delete()
        except:
            pass


async def full_unwarn(
        update: Update, context: ContextTypes.DEFAULT_TYPE, auto_delete: bool = False
):
    message = update.message

    # Целевой пользователь — это тот, на чьё сообщение ответили командой
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if not target:
        await message.reply_text(
            "⚠️ Используй команду в ответ на сообщение пользователя."
        )
        return

    async with async_session() as session:
        # Удаляем все варны пользователя
        await session.execute(delete(Violation).where(Violation.user_id == target.id))
        await session.execute(
            insert(EventLog).values(
                user_id=target.id,
                event_type="full_unwarn",
                event_details="Сняты все предупреждения",
                created_at=datetime.utcnow(),
            )
        )
        await session.commit()

        # Проверяем, сколько осталось (по идее — 0)
        result = await session.execute(
            select(Violation).where(Violation.user_id == target.id)
        )
        remaining = len(result.fetchall())

    # Сообщаем пользователю
    await message.reply_text(
        f"✅ Вы были помилованы и все предупреждения были сняты. Кол-во предупреждений = {remaining}"
    )

    # Удаляем команду, если вызвана через !команду
    if auto_delete:
        try:
            await message.delete()
        except:
            pass


async def unwarn(
        update: Update, context: ContextTypes.DEFAULT_TYPE, auto_delete: bool = False
):
    message = update.message
    target = message.reply_to_message.from_user if message.reply_to_message else None
    if not target:
        await message.reply_text(
            "⚠️ Используй команду в ответ на сообщение пользователя."
        )
        return

    async with async_session() as session:
        # Находим все предупреждения пользователя
        result = await session.execute(
            select(Violation)
            .where(Violation.user_id == target.id)
            .order_by(Violation.created_at.asc())
        )
        violations = result.scalars().all()

        # Если есть хотя бы одно — удаляем самое старое
        if violations:
            await session.delete(violations[0])
            await session.execute(
                insert(EventLog).values(
                    user_id=target.id,
                    event_type="unwarn",
                    event_details="Снято 1 предупреждение",
                    created_at=datetime.utcnow(),
                )
            )
            await session.commit()

        # Считаем, сколько осталось
        result = await session.execute(
            select(Violation).where(Violation.user_id == target.id)
        )
        remaining = len(result.fetchall())

    await message.reply_text(
        f"➖ С вас снято 1 предупреждение. Кол-во предупреждений = {remaining}"
    )

    if auto_delete:
        try:
            await message.delete()
        except:
            pass


async def unwarn_all_users(
        update: Update, context: ContextTypes.DEFAULT_TYPE, auto_delete: bool = False
):
    message = update.message
    user = update.effective_user
    user_id = user.id if user else None

    async with async_session() as session:
        # Проверяем, есть ли user_id, и если пользователя нет в БД — создаем
        if user_id is not None:
            result = await session.execute(select(User).where(User.user_id == user_id))
            if not result.scalar_one_or_none():
                await session.execute(
                    insert(User).values(
                        user_id=user_id,
                        first_name=user.first_name,
                        last_name=user.last_name or None,
                        status=UserStatus.active,
                    )
                )

        # Удаляем все предупреждения
        await session.execute(delete(Violation))

        # Если user_id есть — логируем действие
        if user_id is not None:
            await session.execute(
                insert(EventLog).values(
                    user_id=user_id,
                    event_type="unwarn_all_users",
                    event_details="Сняты все предупреждения для всех пользователей",
                    created_at=datetime.utcnow(),
                )
            )

        await session.commit()

    # Уведомление в чат
    await message.reply_text("🙌 Все были помилованы. Их предупреждения обнулены!")

    # Если нужно — удаляем команду
    if auto_delete:
        try:
            await message.delete()
        except:
            pass
