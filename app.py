import os
import json
import traceback
import random

from enum import Enum
from loguru import logger
from chalice import Chalice

from telegram.ext import (
    Dispatcher,
    MessageHandler,
    Filters, CommandHandler,
)
from telegram import ParseMode, Update, Bot

from chalicelib.api import search
from chalicelib.utils import generate_transcription, send_typing_action

# Telegram token
TOKEN = os.environ["TELEGRAM_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]

# Chalice Lambda app

APP_NAME = "daniel-search-bot-serverless-v2"
MESSAGE_HANDLER_LAMBDA = "message-handler-lambda"

app = Chalice(app_name=APP_NAME)
app.debug = True

# Telegram bot
bot = Bot(token=TOKEN)
dispatcher = Dispatcher(bot, None, use_context=True)


class Stage(Enum):
    LOCAL = 'local'
    DEV = 'dev'
    PROD = 'prod'


STAGE = Stage(os.environ['STAGE'])


#####################
# Telegram Handlers #
#####################

def get_random_waiting_text():
    with open('chalicelib/ui/ui_searching.json', 'r') as f:
        data = json.load(f)
    return random.choice(data['responses'])


def send_waiting_message(context, chat_id):
    waiting_text = get_random_waiting_text()
    context.bot.send_message(
        chat_id=chat_id,
        text=waiting_text,
        disable_web_page_preview=True
    )


@send_typing_action(send_waiting_message)
def process_voice_message(update, context):
    # Get the voice message from the update object
    voice_message = update.message.voice
    # Get the file ID of the voice message
    file_id = voice_message.file_id
    # Use the file ID to get the voice message file from Telegram
    file = bot.get_file(file_id)
    # Download the voice message file
    transcript_msg = generate_transcription(file)

    chat_id = update.message.chat_id
    if is_bad_word(transcript_msg):
        bad_word_warning = get_random_bad_word_warning()
        context.bot.send_message(
            chat_id=chat_id,
            text=bad_word_warning['bad_words_response'],
            parse_mode=ParseMode.HTML,
        )
        return

    logger.info(transcript_msg)
    message = search(transcript_msg)

    context.bot.send_message(
        chat_id=chat_id,
        text=message,
        parse_mode=ParseMode.HTML,
    )


def is_bad_word(text):
    # TODO: add profanity check
    return False


def get_random_bad_word_warning():
    with open('chalicelib/ui/ui_badwords.json', 'r') as f:
        badwords = json.load(f)
    return random.choice(badwords)


@send_typing_action(send_waiting_message)
def process_message(update, context):
    chat_id = update.message.chat_id
    chat_text = update.message.text

    if is_bad_word(chat_text):
        bad_word_warning = get_random_bad_word_warning()
        context.bot.send_message(
            chat_id=chat_id,
            text=bad_word_warning['bad_words_response'],
            parse_mode=ParseMode.HTML,
        )
        return

    try:
        message = search(chat_text)
        logger.info(message)
    except Exception as e:
        app.log.error(e)
        app.log.error(traceback.format_exc())
        context.bot.send_message(
            chat_id=chat_id,
            text="Упс! Кажется, что-то пошло не так 😬 Но не волнуйтесь, наши кодовые мастера уже вовсю трудятся над исправлением проблемы! ⚙️",
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )
    else:
        context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True
        )


#####################
# Commands #
#####################

def get_random_greeting():
    with open('chalicelib/ui/ui_greetings.json', 'r') as f:
        greetings = json.load(f)
    return random.choice(greetings)


def start_command(update, context):
    greeting = get_random_greeting()
    context.bot.send_message(
        chat_id=update.message.chat_id,
        text=f"{greeting['greeting']}\n\n{greeting['description']}\n\n{greeting['prompt']}",
        parse_mode=ParseMode.HTML,
    )


def help_command(update, context):
    start_command(update, context)


############################
# Lambda Handler functions #
############################


@app.lambda_function(name=MESSAGE_HANDLER_LAMBDA)
def message_handler(event, context):
    dispatcher.add_handler(CommandHandler("start", start_command))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(MessageHandler(Filters.text, process_message))
    dispatcher.add_handler(MessageHandler(Filters.voice, process_voice_message))

    try:
        dispatcher.process_update(Update.de_json(json.loads(event["body"]), bot))
    except Exception as e:
        logger.error(e)
        return {"statusCode": 500}

    return {"statusCode": 200}


logger.info(f"STAGE: {STAGE}")
if STAGE == Stage.LOCAL:
    @app.route('/message_handler', methods=['POST'], content_types=['application/json'])
    def message_handler_route():
        request = app.current_request
        raw_body = request.raw_body
        json_body = json.loads(raw_body)
        response = {"body": json.dumps(json_body)}
        return message_handler(response, None)
