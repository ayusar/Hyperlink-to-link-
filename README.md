import os
import re
import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(name)

# Configuration (Replace with your values)
BOT_TOKEN = "YOUR_BOT_TOKEN"
CHANNEL_ID = "YOUR_CHANNEL_ID"  # Should start with -100 for channels

async def process_and_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message = update.effective_message
        if not message or not message.text:
            logger.warning("Received message without text content")
            return

        logger.info(f"Received raw message:\n{message.text}")
        logger.debug(f"Message entities: {message.entities}")

        # Process message text
        clean_text = process_message_text(message.text, message.entities)
        logger.info(f"After entity processing:\n{clean_text}")
        
        # Additional cleanup for raw text formatting
        clean_text = clean_raw_text(clean_text)
        logger.info(f"After raw text cleaning:\n{clean_text}")
        
        # Remove deal time line using regex
        clean_text = remove_deal_time(clean_text)
        logger.info(f"After time removal:\n{clean_text}")
        
        # Send to channel
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=clean_text,
            disable_web_page_preview=True
        )
        logger.info("Message successfully forwarded to channel")

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        logger.error(f"Failed message content:\n{message.text if message else 'No message'}")

def process_message_text(text: str, entities: list) -> str:
    """Replace text links with URLs using both Telegram entities and raw text parsing"""
    # First process Telegram entities
    processed = process_telegram_entities(text, entities)
    
    # Then process raw text formatting
    return process_text_links(processed)

def process_telegram_entities(text: str, entities: list) -> str:
    """Handle Telegram message entities for links"""
    if not entities:
        logger.debug("No entities found in message")
        return text

    logger.info(f"Processing {len(entities)} entities")
    sorted_entities = sorted(entities, key=lambda e: e.offset)
    parts = []
    current_pos = 0

    for entity in sorted_entities:
        logger.debug(f"Processing entity: {entity.type} at {entity.offset}-{entity.offset + entity.length}")
        
        if entity.offset > len(text) or entity.offset + entity.length > len(text):
            logger.warning(f"Entity out of bounds: {entity}")
            continue

        # Add text before entity
        parts.append(text[current_pos:entity.offset])
        current_pos = entity.offset

        # Handle entity types
        if entity.type == "text_link":
            logger.debug(f"Found text_link entity: {entity.url}")
            parts.append(entity.url)
            current_pos += entity.length
        elif entity.type == "url":
            url_content = text[entity.offset:entity.offset + entity.length]
            logger.debug(f"Found url entity: {url_content}")
            parts.append(url_content)
            current_pos += entity.length
        else:
            other_content = text[entity.offset:entity.offset + entity.length]
            logger.debug(f"Keeping other entity ({entity.type}): {other_content}")
            parts.append(other_content)
            current_pos += entity.length

    # Add remaining text
    parts.append(text[current_pos:])
    return "".join(parts)

def process_text_links(text: str) -> str:
    """Process raw text for Markdown/HTML links that weren't parsed as entities"""
    logger.debug("Processing raw text links")
    
    # Handle Markdown links [text](url)
    md_links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', text)
    if md_links:
        logger.info(f"Found {len(md_links)} Markdown links")
    text = re.sub(
        r'\[([^\]]+)\]\(([^)]+)\)',
        lambda m: m.group(2),
        text
    )
    
    # Handle HTML links <a href="url">text</a>
    html_links = re.findall(r'<a\s+href="([^"]+)"[^>]*>([^<]+)</a>', text, re.IGNORECASE)
    if html_links:
        logger.info(f"Found {len(html_links)} HTML links")
    text = re.sub(
        r'<a\s+href="([^"]+)"[^>]*>([^<]+)</a>',
        lambda m: m.group(1),
        text,
        flags=re.IGNORECASE
    )
    
    # Remove any remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    
    return text

def clean_raw_text(text: str) -> str:
    """Additional cleaning for raw text formatting"""
    logger.debug("Cleaning raw text formatting")
    # Remove bold/italic Markdown
    text = re.sub(r'[*_]{1,2}(.+?)[*_]{1,2}', r'\1', text)
    # Remove code formatting
    text = re.sub(r'{1,3}(.+?){1,3}', r'\1', text)
    return text

def remove_deal_time(text: str) -> str:
    """Remove lines containing deal time using regex"""
    logger.debug("Removing deal time")
    return re.sub(
        r'\n?[⏳⌛😱]*\s*Deal Time:.*(\n|$)',
        '',
        text,
        flags=re.IGNORECASE
    ).strip()

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, process_and_forward))
    
    logger.info("Starting bot...")
    application.run_polling()

if name == "main":
    main()
