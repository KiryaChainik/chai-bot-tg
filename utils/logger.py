import asyncio

from telegram.error import RetryAfter, TimedOut

from config import DEBUG_CHAT_ID


def debug_log_sync(text: str):
    print(f"[DEBUG] {text}")


async def debug_log(context, text: str):
    print(f"[DEBUG] {text}")
    try:
        await context.bot.send_message(
            chat_id=DEBUG_CHAT_ID, text=f"{text}", disable_notification=True
        )
    except RetryAfter as e:
        print(f"[DEBUG] Flood control: спим {e.retry_after} сек")
        await asyncio.sleep(e.retry_after)
        try:
            await context.bot.send_message(
                chat_id=DEBUG_CHAT_ID, text=f"{text}", disable_notification=True
            )
        except Exception as e:
            print(f"[DEBUG] Ошибка при повторной попытке логирования: {e}")
    except TimedOut as e:
        print(f"[DEBUG] Timeout при логировании: {e}")
    except Exception as e:
        print(f"[DEBUG] Ошибка при логировании: {e}")
