import os
import json
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import pymongo
import requests

# --- НАСТРОЙКИ (ЭТИ ПЕРЕМЕННЫЕ НУЖНО БУДЕТ ЗАДАТЬ В RENDER) ---
# Получить токен у @BotFather
BOT_TOKEN = "8345325076:AAFreetpBya03pUSwABL6VgrCFQ644mJt-s"
# Ваш Telegram ID (узнать у @userinfobot)
ADMIN_ID = 1743237033
# Строка подключения к MongoDB Atlas
MONGODB_URI = "mongodb+srv://makarychev887_db_user:VjHYgC26wBnnmMUW@cluster0.omk9t2w.mongodb.net/?appName=Cluster0"
DB_NAME = "neimark_secure" # Имя базы данных

# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- ПОДКЛЮЧЕНИЕ К MONGODB ---
def get_db():
    """Подключается к MongoDB и возвращает объект коллекции."""
    if not MONGODB_URI:
        logger.error("MONGODB_URI не задана!")
        return None
    try:
        client = pymongo.MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = client[DB_NAME]
        # Проверка подключения
        client.admin.command('ping')
        logger.info("Успешное подключение к MongoDB")
        return db["users"] # Возвращаем коллекцию 'users'
    except Exception as e:
        logger.error(f"Ошибка подключения к MongoDB: {e}")
        return None

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
def get_users_collection():
    """Возвращает коллекцию пользователей или None при ошибке."""
    if not hasattr(get_db, 'collection'):
        # Ленивое подключение: подключаемся только при первом обращении
        collection = get_db()
        get_db.collection = collection
    return get_db.collection

def send_message(chat_id, text):
    """Отправляет сообщение через Bot API (для уведомлений)."""
    if not BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления: {e}")

# --- ОБРАБОТЧИКИ КОМАНД БОТА ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Доступ запрещён.")
        return
    await update.message.reply_text(
        "🔐 *NEIMARK Secure — Административный бот*\n\n"
        "Доступные команды:\n"
        "/users — список всех пользователей\n"
        "/stats — статистика системы\n"
        "/logs — последние события (локально)"
    )

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /users."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Доступ запрещён.")
        return

    collection = get_users_collection()
    if collection is None:
        await update.message.reply_text("❌ Ошибка подключения к базе данных.")
        return

    try:
        users = list(collection.find({}))
        if not users:
            await update.message.reply_text("📭 Пользователей пока нет.")
            return

        msg = "📋 *Список пользователей:*\n\n"
        for u in users:
            profile = json.loads(u.get('profile_data', '{}')) if u.get('profile_data') else {}
            name = profile.get('fullname', 'не указано')
            course = profile.get('course', '—')
            created = u['created_at'][:10]
            msg += f"👤 {u['username']} ({name})\n   🎓 {course}\n   📅 {created}\n\n"
            if len(msg) > 3800:
                await update.message.reply_text(msg)
                msg = ""
        if msg:
            await update.message.reply_text(msg)
    except Exception as e:
        logger.error(f"Ошибка в /users: {e}")
        await update.message.reply_text(f"❌ Ошибка при получении списка пользователей.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /stats."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Доступ запрещён.")
        return

    collection = get_users_collection()
    if collection is None:
        await update.message.reply_text("❌ Ошибка подключения к базе данных.")
        return

    try:
        count = collection.count_documents({})
        await update.message.reply_text(f"📊 *Статистика*\n\n👥 Всего пользователей: {count}")
    except Exception as e:
        logger.error(f"Ошибка в /stats: {e}")
        await update.message.reply_text(f"❌ Ошибка получения статистики.")

async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /logs."""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Доступ запрещён.")
        return
    await update.message.reply_text("📜 Логи безопасности хранятся локально на устройстве пользователя.")

# --- ГЛАВНАЯ ФУНКЦИЯ ЗАПУСКА БОТА ---
def main():
    if not BOT_TOKEN or not ADMIN_ID or not MONGODB_URI:
        logger.error("ОШИБКА: Не заданы переменные окружения BOT_TOKEN, ADMIN_ID или MONGODB_URI!")
        return

    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("users", users))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("logs", logs))

    # Запускаем бота в режиме polling
    logger.info("Бот запущен и готов к работе...")
    application.run_polling()

if __name__ == "__main__":
    main()
