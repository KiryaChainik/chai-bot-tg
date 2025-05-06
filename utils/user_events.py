from datetime import datetime

from sqlalchemy import insert, select

from database import get_async_session
from models.events_log import EventLog
from models.users import User, UserStatus


async def log_event(user, event_type: str, details: str = "", session=None):
    if session is None:
        async for session in get_async_session():
            await _log_with_session(user, event_type, details, session)
    else:
        await _log_with_session(user, event_type, details, session)


async def _log_with_session(user, event_type, details, session):
    result = await session.execute(select(User).where(User.user_id == user.id))
    existing_user = result.scalar_one_or_none()

    if not existing_user:
        await session.execute(
            insert(User).values(
                user_id=user.id,
                first_name=user.first_name,
                last_name=user.last_name or None,
                status=UserStatus.active,
                joined_at=datetime.utcnow(),
            )
        )

    await session.execute(
        insert(EventLog).values(
            user_id=user.id,
            event_type=event_type,
            event_details=details,
            created_at=datetime.utcnow(),
        )
    )
    await session.commit()  # 💥 ВОТ ЭТО НУЖНО
