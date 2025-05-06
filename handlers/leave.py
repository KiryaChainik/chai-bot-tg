from datetime import datetime

from sqlalchemy import update as sql_update
from telegram import Update
from telegram.ext import ContextTypes

from database import async_session
from models.users import User
from utils.user_events import log_event


async def on_user_left(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.left_chat_member
    chat_id = update.effective_chat.id

    await context.bot.send_message(
        chat_id=chat_id,
        text=f"👋 Пока-пока, {user.first_name} (@{user.username or 'user'})",
    )

    async with async_session() as session:
        await session.execute(
            sql_update(User)
            .where(User.user_id == user.id)
            .values(left_at=datetime.utcnow())
        )
        await session.commit()
        await log_event(user, "left", "Пользователь вышел из чата", session)
