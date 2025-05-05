import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from types import SimpleNamespace

import pytest
from telegram import Message, Chat, User

from bot import ban_user


@pytest.mark.asyncio
async def test_ban_user_by_reply(mocker):
    chat = Chat(id=12345, type="group")
    target_user = User(id=777, is_bot=False, first_name="Target")
    from_user = User(id=999, is_bot=False, first_name="Admin")

    reply_msg = Message(
        message_id=2,
        date=None,
        chat=chat,
        from_user=target_user,
        text="hi",
        message_thread_id=None,
    )

    message = Message(
        message_id=1,
        date=None,
        chat=chat,
        from_user=from_user,
        text="/ban",
        reply_to_message=reply_msg,
    )

    bot = mocker.AsyncMock()
    message.set_bot(bot)
    reply_msg.set_bot(bot)

    update = SimpleNamespace(
        message=message, effective_chat=chat, effective_user=from_user
    )
    context = SimpleNamespace(
        bot=bot,
        bot_data={},
        chat_data={},
    )

    bot.get_chat_member.side_effect = [
        SimpleNamespace(status="administrator", can_restrict_members=True),
        SimpleNamespace(status="member"),
    ]

    await ban_user(update, context)

    bot.ban_chat_member.assert_called_once_with(chat.id, target_user.id)
