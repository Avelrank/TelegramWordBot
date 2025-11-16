"""
Telegram бот для генерации аудио
Направления: EN→RU, EN→UK
"""

import io
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from gtts import gTTS
from pydub import AudioSegment
import tempfile

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем токен из переменной окружения (для безопасности)
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8586424822:AAHOvZlko-7_xV9Kc_mL96RsG61RDm0kfHQ')

# Настройки по умолчанию для каждого пользователя
user_settings = {}

DEFAULT_SETTINGS = {
    'repeat_count': 3,
    'pause_ms': 500,
    'direction': 'en-ru'  # По умолчанию EN→RU
}

# Доступные направления перевода
TRANSLATION_DIRECTIONS = {
    'en-ru': {
        'name': '🇬🇧 English → 🇷🇺 Русский',
        'source': 'en',
        'target': 'ru',
        'flag_source': '🇬🇧',
        'flag_target': '🇷🇺',
        'example': 'apple - яблоко\ncat - кот\nbook - книга'
    },
    'en-uk': {
        'name': '🇬🇧 English → 🇺🇦 Українська',
        'source': 'en',
        'target': 'uk',
        'flag_source': '🇬🇧',
        'flag_target': '🇺🇦',
        'example': 'apple - яблуко\ncat - кіт\nbook - книга'
    }
}

def get_user_settings(user_id):
    """Получить настройки пользователя"""
    if user_id not in user_settings:
        user_settings[user_id] = DEFAULT_SETTINGS.copy()
    return user_settings[user_id]

def parse_word_pairs(text):
    """Парсинг пар слов из текста"""
    pairs = []
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue

        for sep in [' - ', ' — ', ' – ', ': ', ' : ', ' = ', ' | ']:
            if sep in line:
                parts = line.split(sep, 1)
                if len(parts) == 2:
                    pairs.append({
                        'source': parts[0].strip(),
                        'target': parts[1].strip()
                    })
                break
    return pairs

def create_audio(pairs, settings, direction='en-ru'):
    """Создание аудиофайла из пар слов"""
    dir_info = TRANSLATION_DIRECTIONS[direction]
    source_lang = dir_info['source']
    target_lang = dir_info['target']

    combined = AudioSegment.empty()
    pause = AudioSegment.silent(duration=settings['pause_ms'])
    long_pause = AudioSegment.silent(duration=settings['pause_ms'] * 2)

    temp_files = []

    try:
        for pair in pairs:
            # Исходное слово (повторить N раз)
            for i in range(settings['repeat_count']):
                temp_source = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
                temp_files.append(temp_source.name)

                tts_source = gTTS(text=pair['source'], lang=source_lang, slow=False)
                tts_source.save(temp_source.name)

                audio_source = AudioSegment.from_mp3(temp_source.name)
                combined += audio_source + pause

            # Целевое слово (перевод)
            temp_target = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_files.append(temp_target.name)

            tts_target = gTTS(text=pair['target'], lang=target_lang, slow=False)
            tts_target.save(temp_target.name)

            audio_target = AudioSegment.from_mp3(temp_target.name)
            combined += audio_target + long_pause

        # Сохранение итогового файла
        output = io.BytesIO()
        combined.export(output, format='mp3', bitrate='128k')
        output.seek(0)

        return output

    finally:
        # Удаление временных файлов
        for temp_file in temp_files:
            try:
                os.unlink(temp_file)
            except:
                pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    keyboard = [
        [InlineKeyboardButton("🇬🇧 English → 🇷🇺 Русский", callback_data='dir_en-ru')],
        [InlineKeyboardButton("🇬🇧 English → 🇺🇦 Українська", callback_data='dir_en-uk')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = """
🎧 <b>Вітаю! Welcome! Привет!</b>

Я створюю аудіо для вивчення англійських слів!
I create audio for learning English words!
Я создаю аудио для изучения английских слов!

<b>📚 Оберіть напрямок перекладу:</b>
<b>📚 Choose translation direction:</b>
<b>📚 Выберите направление перевода:</b>
"""
    await update.message.reply_text(
        welcome_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def direction_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора направления перевода"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    settings = get_user_settings(user_id)

    # Извлекаем направление из callback_data
    direction = query.data.split('_')[1]
    settings['direction'] = direction

    dir_info = TRANSLATION_DIRECTIONS[direction]

    # Разные тексты для разных направлений
    if direction == 'en-ru':
        instruction_text = f"""
✅ <b>Выбрано направление:</b>
{dir_info['name']}

📝 <b>Как использовать:</b>
Отправьте список слов в формате:

<code>{dir_info['example']}</code>

Я создам MP3 файл, где:
• Английское слово × {settings['repeat_count']} раза
• Русский перевод × 1 раз

🎵 <b>Отправьте слова и получите аудио!</b>
"""
    else:  # en-uk
        instruction_text = f"""
✅ <b>Обрано напрямок:</b>
{dir_info['name']}

📝 <b>Як використовувати:</b>
Надішліть список слів у форматі:

<code>{dir_info['example']}</code>

Я створю MP3 файл, де:
• Англійське слово × {settings['repeat_count']} рази
• Український переклад × 1 раз

🎵 <b>Надішліть слова і отримайте аудіо!</b>
"""

    await query.edit_message_text(
        instruction_text,
        parse_mode='HTML'
    )

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /settings"""
    user_id = update.effective_user.id
    settings = get_user_settings(user_id)

    current_dir = settings['direction']
    dir_info = TRANSLATION_DIRECTIONS[current_dir]

    keyboard = [
        [InlineKeyboardButton(
            f"🌍 Напрямок: {dir_info['flag_source']}→{dir_info['flag_target']}",
            callback_data='change_direction'
        )],
        [InlineKeyboardButton(
            f"🔁 Повторення: {settings['repeat_count']}",
            callback_data='change_repeat'
        )],
        [InlineKeyboardButton(
            f"⏱️ Пауза: {settings['pause_ms']}мс",
            callback_data='change_pause'
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    settings_text = """
⚙️ <b>Налаштування / Settings / Настройки</b>

Оберіть параметр для зміни:
Choose parameter to change:
Выберите параметр для изменения:
"""

    await update.message.reply_text(
        settings_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка настроек"""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    settings = get_user_settings(user_id)

    if query.data == 'change_direction':
        keyboard = [
            [InlineKeyboardButton("🇬🇧 → 🇷🇺 English → Русский", callback_data='dir_en-ru')],
            [InlineKeyboardButton("🇬🇧 → 🇺🇦 English → Українська", callback_data='dir_en-uk')],
            [InlineKeyboardButton("« Назад / Back", callback_data='back_settings')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🌍 Оберіть напрямок / Choose direction:",
            reply_markup=reply_markup
        )

    elif query.data == 'change_repeat':
        keyboard = [
            [InlineKeyboardButton("1", callback_data='repeat_1'),
             InlineKeyboardButton("2", callback_data='repeat_2'),
             InlineKeyboardButton("3", callback_data='repeat_3')],
            [InlineKeyboardButton("4", callback_data='repeat_4'),
             InlineKeyboardButton("5", callback_data='repeat_5'),
             InlineKeyboardButton("7", callback_data='repeat_7')],
            [InlineKeyboardButton("« Назад / Back", callback_data='back_settings')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🔁 Скільки разів повторювати?\nHow many times to repeat?\nСколько раз повторять?",
            reply_markup=reply_markup
        )

    elif query.data == 'change_pause':
        keyboard = [
            [InlineKeyboardButton("300мс", callback_data='pause_300'),
             InlineKeyboardButton("500мс", callback_data='pause_500'),
             InlineKeyboardButton("800мс", callback_data='pause_800')],
            [InlineKeyboardButton("1000мс", callback_data='pause_1000'),
             InlineKeyboardButton("1500мс", callback_data='pause_1500')],
            [InlineKeyboardButton("« Назад / Back", callback_data='back_settings')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⏱️ Пауза між словами:\nPause between words:\nПауза между словами:",
            reply_markup=reply_markup
        )

    elif query.data.startswith('repeat_'):
        count = int(query.data.split('_')[1])
        settings['repeat_count'] = count
        await query.edit_message_text(
            f"✅ Встановлено / Set / Установлено: {count}× повторень / repeats / повторений"
        )

    elif query.data.startswith('pause_'):
        pause = int(query.data.split('_')[1])
        settings['pause_ms'] = pause
        await query.edit_message_text(
            f"✅ Встановлено / Set / Установлено: {pause}мс пауза / pause / пауза"
        )

    elif query.data == 'back_settings':
        await settings_command(update, context)

async def process_words(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка сообщения со словами"""
    user_id = update.effective_user.id
    text = update.message.text
    settings = get_user_settings(user_id)

    # Парсинг пар слов
    pairs = parse_word_pairs(text)

    if not pairs:
        await update.message.reply_text(
            "❌ Не знайдено пар слів / No word pairs found / Не найдено пар слов\n\n"
            "Формат / Format:\n"
            "<code>apple - яблуко\ncat - кіт</code>",
            parse_mode='HTML'
        )
        return

    direction = settings['direction']
    dir_info = TRANSLATION_DIRECTIONS[direction]

    # Отправка статуса
    status_msg = await update.message.reply_text(
        f"🎙️ Створюю аудіо / Creating audio / Создаю аудио...\n\n"
        f"📊 Пар слів / Pairs / Пар слов: {len(pairs)}\n"
        f"🌍 {dir_info['name']}\n"
        f"🔁 Повторень / Repeats / Повторений: {settings['repeat_count']}×"
    )

    try:
        # Создание аудио
        audio_file = create_audio(pairs, settings, direction)

        # Формирование текста с парами слов
        words_text = f"📚 <b>Your words. Let's get started!</b>\n\n"
        for i, pair in enumerate(pairs, 1):
            words_text += f"{i}. <b>{pair['source']}</b> {dir_info['flag_source']}→{dir_info['flag_target']} {pair['target']}\n"

        words_text += f"\n🫶🏼 <b>You're getting better every day!</b>\n"
        words_text += f"<b>Sincerely yours, LinguaBird❤️"

        # Удаление статусного сообщения
        await status_msg.delete()

        # Отправка аудио и текста
        filename = f"english_to_{dir_info['target']}.mp3"
        await update.message.reply_audio(
            audio=audio_file,
            filename=filename,
            title=f"{dir_info['flag_source']} English → {dir_info['flag_target']} {dir_info['target'].upper()}",
            performer="English Learning Bot",
            caption=words_text,
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error creating audio: {e}")
        await status_msg.edit_text(
            f"❌ Error:\n{str(e)}\n\n"
            f"Try again: /start"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """
📖 <b>Help</b>

<b>Commands:</b>
/start - Start
/settings - Settings
/help - Help

<b>Як використовувати / How to use / Как использовать:</b>

1️⃣ Choose translation direction

2️⃣ Send words in format:

<code>apple - яблуко
cat - кіт
dog - собака</code>

3️⃣ Get MP3 audio!

<b>Available directions:</b>
🇬🇧 → 🇷🇺 English → Русский
🇬🇧 → 🇺🇦 English → Українська
"""
    await update.message.reply_text(help_text, parse_mode='HTML')

async def example_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /example"""
    user_id = update.effective_user.id
    settings = get_user_settings(user_id)
    direction = settings['direction']
    dir_info = TRANSLATION_DIRECTIONS[direction]

    example_text = f"""
📝 <b>Example</b>

<b>Current direction:</b>
{dir_info['name']}

<b>Send this text:</b>

<code>{dir_info['example']}</code>

I'll create audio! 🎵
"""
    await update.message.reply_text(example_text, parse_mode='HTML')

def main():
    """Запуск бота"""
    print("=" * 60)
    print("🤖 Запуск Telegram бота...")
    print("📚 English Learning Bot")
    print("=" * 60)

    if BOT_TOKEN == "ВСТАВЬТЕ_ВАШ_ТОКЕН_СЮДА":
        print("\n❌ ОШИБКА: Токен не настроен!")
        print("Установите переменную окружения BOT_TOKEN")
        print("или измените строку в коде")
        print("\nExport: export BOT_TOKEN='ваш_токен'")
        print("или в коде: BOT_TOKEN = 'ваш_токен'")
        return

    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()

    # Регистрация обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("example", example_command))
    application.add_handler(CommandHandler("settings", settings_command))

    # Обработчики callback'ов
    application.add_handler(CallbackQueryHandler(direction_callback, pattern='^dir_'))
    application.add_handler(CallbackQueryHandler(settings_callback))

    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_words))

    # Запуск бота
    print("\n✅ Бот успешно запущен!")
    print("📱 Доступные направления:")
    print("   🇬🇧 → 🇷🇺 English → Русский")
    print("   🇬🇧 → 🇺🇦 English → Українська")
    print("\n⏹️  Для остановки нажмите Ctrl+C")
    print("=" * 60 + "\n")

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()


    8586424822:AAHOvZlko-7_xV9Kc_mL96RsG61RDm0kfHQ
    git config --global user.name "Pavel"
    git config --global user.email "Mailovavel@gmail.com"
    git remote add origin https://github.com/Avelrank/TelegramWordBot.git
    pyaudioop-lts==0.2.1.post1

    git add .
    git commit -m "Correcting an outgoing message"
    git push origin main