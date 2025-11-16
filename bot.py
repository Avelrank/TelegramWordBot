import io
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
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
        'name': 'English → Русский',
        'source': 'en',
        'target': 'ru',
        'example': 'apple - яблоко\ncat - кот\nbook - книга'
    },
    'en-uk': {
        'name': 'Vocabulary',
        'source': 'en',
        'target': 'uk',
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
        [InlineKeyboardButton("English → Русский", callback_data='dir_en-ru')],
        [InlineKeyboardButton("Vocabulary", callback_data='dir_en-uk')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = """Привет! Я создаю аудио для изучения английских слов! Выберите направление перевода:"""
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

    # Инструкция на русском для обоих направлений
    instruction_text = f"""Выбрано направление: {dir_info['name']}
Как использовать: Отправьте список слов в формате:
<code>{dir_info['example']}</code>
Я создам MP3 файл, где:
• Английское слово × {settings['repeat_count']} раза
• Перевод × 1 раз
Отправьте слова и получите аудио!"""

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
            f"Направление: {dir_info['name']}",
            callback_data='change_direction'
        )],
        [InlineKeyboardButton(
            f"Повторения: {settings['repeat_count']}",
            callback_data='change_repeat'
        )],
        [InlineKeyboardButton(
            f"Пауза: {settings['pause_ms']}мс",
            callback_data='change_pause'
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    settings_text = """Настройки
Выберите параметр для изменения:"""
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
            [InlineKeyboardButton("English → Русский", callback_data='dir_en-ru')],
            [InlineKeyboardButton("Vocabulary", callback_data='dir_en-uk')],
            [InlineKeyboardButton("« Назад", callback_data='back_settings')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Выберите направление:",
            reply_markup=reply_markup
        )
    elif query.data == 'change_repeat':
        keyboard = [
            [InlineKeyboardButton("1", callback_data='repeat_1'), InlineKeyboardButton("2", callback_data='repeat_2'), InlineKeyboardButton("3", callback_data='repeat_3')],
            [InlineKeyboardButton("4", callback_data='repeat_4'), InlineKeyboardButton("5", callback_data='repeat_5'), InlineKeyboardButton("7", callback_data='repeat_7')],
            [InlineKeyboardButton("« Назад", callback_data='back_settings')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Сколько раз повторять?",
            reply_markup=reply_markup
        )
    elif query.data == 'change_pause':
        keyboard = [
            [InlineKeyboardButton("300мс", callback_data='pause_300'), InlineKeyboardButton("500мс", callback_data='pause_500'), InlineKeyboardButton("800мс", callback_data='pause_800')],
            [InlineKeyboardButton("1000мс", callback_data='pause_1000'), InlineKeyboardButton("1500мс", callback_data='pause_1500')],
            [InlineKeyboardButton("« Назад", callback_data='back_settings')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "Пауза между словами:",
            reply_markup=reply_markup
        )
    elif query.data.startswith('repeat_'):
        count = int(query.data.split('_')[1])
        settings['repeat_count'] = count
        await query.edit_message_text(
            f"Установлено: {count}× повторений"
        )
    elif query.data.startswith('pause_'):
        pause = int(query.data.split('_')[1])
        settings['pause_ms'] = pause
        await query.edit_message_text(
            f"Установлено: {pause}мс пауза"
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
            "Не найдено пар слов\n\n"
            "Формат:\n"
            "<code>apple - яблоко\ncat - кот</code>",
            parse_mode='HTML'
        )
        return

    direction = settings['direction']
    dir_info = TRANSLATION_DIRECTIONS[direction]

    # Отправка статуса
    status_msg = await update.message.reply_text(
        f"Создаю аудио...\n\n"
        f"Пар слов: {len(pairs)}\n"
        f"{dir_info['name']}\n"
        f"Повторений: {settings['repeat_count']}×"
    )

    try:
        # Создание аудио
        audio_file = create_audio(pairs, settings, direction)

        # Формирование текста с парами слов
        words_text = f"📚 <b>Ваши слова. Начнём!</b>\n\n"
        for i, pair in enumerate(pairs, 1):
            words_text += f"{i}. <b>{pair['source']}</b> → {pair['target']}\n"
        words_text += f"\n🫶🏼 <b>Вы становитесь лучше каждый день!</b>\n"
        words_text += f"Sincerely yours, LinguaBird❤️\n"
        words_text += "После окончания аудио остановите воспроизведение."

        # Удаление статусного сообщения
        await status_msg.delete()

        # Отправка аудио и текста
        filename = f"english_to_{dir_info['target']}.mp3"
        await update.message.reply_audio(
            audio=audio_file,
            filename=filename,
            title=f"English → {dir_info['name']}",
            performer="English Learning Bot",
            caption=words_text,
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error creating audio: {e}")
        await status_msg.edit_text(
            f"Ошибка:\n{str(e)}\n\n"
            f"Попробуйте снова: /start"
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    help_text = """Help
Команды:
/start - Запуск
/settings - Настройки
/help - Помощь
/example - Пример

Как использовать:
1. Выберите направление перевода
2. Отправьте слова в формате:
<code>apple - яблоко
cat - кот
dog - собака</code>
3. Получите MP3 аудио!

Доступные направления:
English → Русский
Vocabulary"""
    await update.message.reply_text(help_text, parse_mode='HTML')

async def example_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /example"""
    user_id = update.effective_user.id
    settings = get_user_settings(user_id)
    direction = settings['direction']
    dir_info = TRANSLATION_DIRECTIONS[direction]

    example_text = f"""Пример
Текущее направление: {dir_info['name']}
Отправьте этот текст:
<code>{dir_info['example']}</code>
Я создам аудио!"""
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
    print(" English → Русский")
    print(" Vocabulary")
    print("\n⏹️ Для остановки нажмите Ctrl+C")
    print("=" * 60 + "\n")

    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()