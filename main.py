import logging
import sqlite3
import yaml
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, ContextTypes, filters

# Загрузка конфигурации
with open('config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            user_id INTEGER,
            message_id INTEGER,
            forwarded_message_id INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def add_message(user_id, message_id, forwarded_message_id):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO messages (user_id, message_id, forwarded_message_id) VALUES (?, ?, ?)',
                   (user_id, message_id, forwarded_message_id))
    conn.commit()
    conn.close()

def get_user_id(forwarded_message_id):
    conn = sqlite3.connect('bot_data.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM messages WHERE forwarded_message_id = ?', (forwarded_message_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Приветственное сообщение
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(config['welcome_message'])

# Обработка входящих сообщений от пользователей
async def handle_message(update: Update, context: CallbackContext):
    user_message = update.message
    user_id = update.message.chat_id

    # Пересылаем сообщение в группу и добавляем ID пользователя в базу данных
    forwarded_message = await context.bot.forward_message(
        chat_id=config['group_id'],
        from_chat_id=user_id,
        message_id=user_message.message_id
    )
    add_message(user_id, user_message.message_id, forwarded_message.message_id)

    # Отправляем подтверждение пользователю
    await update.message.reply_text(config['confirmation_message'])

# Обработка ответов из группы
async def forward_to_user(update: Update, context: CallbackContext):
    if update.message.reply_to_message:
        forwarded_message_id = update.message.reply_to_message.message_id
        user_id = get_user_id(forwarded_message_id)
        if user_id:
            # Проверяем тип медиафайла и пересылаем его соответствующим методом
            if update.message.text:
                await context.bot.send_message(chat_id=user_id, text=update.message.text)
            elif update.message.photo:
                await context.bot.send_photo(chat_id=user_id, photo=update.message.photo[-1].file_id, caption=update.message.caption)
            elif update.message.video:
                await context.bot.send_video(chat_id=user_id, video=update.message.video.file_id, caption=update.message.caption)
            elif update.message.document:
                await context.bot.send_document(chat_id=user_id, document=update.message.document.file_id, caption=update.message.caption)
            elif update.message.audio:
                await context.bot.send_audio(chat_id=user_id, audio=update.message.audio.file_id, caption=update.message.caption)
            elif update.message.voice:
                await context.bot.send_voice(chat_id=user_id, voice=update.message.voice.file_id, caption=update.message.caption)
            elif update.message.sticker:
                await context.bot.send_sticker(chat_id=user_id, sticker=update.message.sticker.file_id)
            else:
                logger.error(f"Неизвестный тип медиафайла в сообщении: {update.message}")
        else:
            logger.error(f"Не удалось определить ID пользователя из сообщения с ID {forwarded_message_id}")

def main():
    # Инициализация базы данных
    init_db()

    # Создание апдейтера и диспетчера
    application = (
        Application.builder().token(config['token']).build()
    )

    # Обработчики команд и сообщений
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(~filters.COMMAND & ~filters.REPLY, handle_message))
    application.add_handler(MessageHandler(filters.REPLY, forward_to_user))

    # Запуск бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
