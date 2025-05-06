import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DEBUG_CHAT_ID = int(os.getenv("DEBUG_CHAT_ID"))

SOURCE_CHAT_ID = -1001887222284
TARGET_CHAT_ID = -1002443521655
TOPIC_ID_BY_HASHTAG = {
    "#барахолка": 2,
    "#оцените_сетап": 6,
    "#почувствуй_боль": 7,
    "#кккомбо": 9,
    "#тесты_магниток": 11,
    "#коллекция": 12,
    "#новости": 17,
    "#тесты_мышек": 20,
}
