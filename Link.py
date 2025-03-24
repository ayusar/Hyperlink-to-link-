import asyncio
import re
import logging
from aiogram import Bot, Dispatcher, Router, types

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(name)

# Configuration (Replace with your values)
BOT_TOKEN = "7140932110:AAES0E-TDdzh0yW-8UTtm52-EADWtkxuawU"
CHANNEL_ID = -1002357568043  # as an integer

# Initialize bot
bot = Bot(token=BOT_TOKEN)

# Create a Router instance to register handlers
router = Router()

def convert_utf16_offset_to_python_index(text: str, utf16_offset: int) -> int:
    """
    Converts a UTF-16 code unit offset (as provided by Telegram) to a Python string index.
    """
    current_units = 0
    for i, char in enumerate(text):
        # Determine how many UTF-16 code units this character occupies.
        units = len(char.encode("utf-16-le")) // 2
        if current_units + units > utf16_offset:
            return i
        current_units += units
    return len(text)

def process_message_text(text: str, entities: list = None) -> str:
    """
    Replace text links with URLs (for text_link entities) and handle URL entities,
    converting UTF-16 based offsets to Python string indexes.
    """
    if not entities:
        return text

    # Convert each entity's offsets from UTF-16 to Python indexes
    python_entities = []
    for entity in entities:
        start = convert_utf16_offset_to_python_index(text, entity.offset)
        end = convert_utf16_offset_to_python_index(text, entity.offset + entity.length)
        python_entities.append((start, end, entity.type, getattr(entity, "url", None)))
    python_entities.sort(key=lambda x: x[0])

    parts = []
    current_pos = 0

    for start, end, etype, url in python_entities:
        if current_pos < start:
            parts.append(text[current_pos:start])
        if etype == "text_link" and url:
            parts.append(url)
        elif etype == "url":
            parts.append(text[start:end])
        else:
            parts.append(text[start:end])
        current_pos = end

    if current_pos < len(text):
        parts.append(text[current_pos:])
    return "".join(parts)
def remove_deal_time(text: str) -> str:
    """Remove lines containing 'Deal Time:' using regex."""
    return re.sub(
        r'\n?😱 Deal Time:.*(\n|$)',
        '',
        text,
        flags=re.IGNORECASE
    ).strip()

def cleanup_buy_now(text: str) -> str:
    """Remove trailing 'Buy Now' (case-insensitive) if present."""
    return re.sub(r'\s*Buy Now\s*$', '', text, flags=re.IGNORECASE).strip()

@router.message()
async def process_and_forward(message: types.Message):
    try:
        # Check for a photo message with a caption first
        if message.photo:
            # Get the caption and its entities if available
            if message.caption:
                text = message.caption
                entities = message.caption_entities
            else:
                text = ""
                entities = None

            clean_text = process_message_text(text, entities) if text else ""
            clean_text = remove_deal_time(clean_text)
            clean_text = cleanup_buy_now(clean_text)

            # Get the largest photo (highest resolution)
            photo = message.photo[-1].file_id
            await bot.send_photo(
                chat_id=CHANNEL_ID,
                photo=photo,
                caption=clean_text,
                disable_notification=True
            )
            logger.info("Photo message processed and forwarded to channel")

        # Otherwise process a plain text message
        elif message.text:
            text = message.text
            entities = message.entities
            clean_text = process_message_text(text, entities)
            clean_text = remove_deal_time(clean_text)
            clean_text = cleanup_buy_now(clean_text)

            await bot.send_message(
                chat_id=CHANNEL_ID,
                text=clean_text,
                disable_web_page_preview=True
            )
            logger.info("Text message processed and forwarded to channel")

        else:
            logger.info("Message does not contain text, caption, or photo")
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)

async def main():
    dp = Dispatcher()
    dp.include_router(router)
    logger.info("Bot is starting...")
    await dp.start_polling(bot)

if name == "main":
    asyncio.run(main())
