import time
import uuid
import os
import json
import openai
from functools import wraps

import boto3
import wget
from loguru import logger
from telegram import ChatAction
from googletrans import Translator

from threading import Thread


class TypingThread(Thread):
    def __init__(self, context, chat_id):
        Thread.__init__(self)
        self.context = context
        self.chat_id = chat_id
        self.done = False

    def run(self):
        while not self.done:
            self.context.bot.send_chat_action(
                chat_id=self.chat_id, action=ChatAction.TYPING
            )
            time.sleep(3)

    def stop(self):
        self.done = True


def send_typing_action(pre_func=None):
    """Sends typing action while processing func command."""

    def decorator(func):
        @wraps(func)
        def command_func(update, context, *args, **kwargs):
            chat_id = update.effective_message.chat_id

            if pre_func:
                pre_func(context, chat_id)

            typing_thread = TypingThread(context, chat_id)
            typing_thread.start()
            try:
                result = func(update, context, *args, **kwargs)
            finally:
                typing_thread.stop()

            return result

        return command_func

    return decorator



def generate_transcription(file):
    # AWS needed clients
    s3_client = boto3.client("s3")
    transcribe_client = boto3.client("transcribe")

    local_path = "/tmp/voice_message.ogg"
    message_id = str(uuid.uuid4())

    s3_bucket = os.environ["VOICE_MESSAGES_BUCKET"]
    s3_prefix = os.path.join(message_id, "audio_file.ogg")
    remote_s3_path = os.path.join("s3://", s3_bucket, s3_prefix)

    file.download(local_path)
    s3_client.upload_file(local_path, s3_bucket, s3_prefix)

    job_name = f"transcription_job_{message_id}"
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        MediaFormat="ogg",
        LanguageCode="ru-RU",
        Media={"MediaFileUri": remote_s3_path},
    )

    # Wait for the transcription job to complete
    job_status = None
    while job_status != "COMPLETED":
        status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        job_status = status["TranscriptionJob"]["TranscriptionJobStatus"]

    # Get the transcript once the job is completed
    transcript = status["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
    logger.info(transcript)

    output_location = f"/tmp/output_{message_id}.json"
    wget.download(transcript, output_location)

    with open(output_location) as f:
        output = json.load(f)
    return output["results"]["transcripts"][0]["transcript"]


def google_translate(text: str, src: str, target: str):
    translator = Translator()
    translation = translator.translate(text, src=src, dest=target)
    return translation.text


def generate_embedding(_text: str):
    response = openai.Embedding.create(model="text-embedding-ada-002", input=_text)
    return response["data"][0]["embedding"], response["usage"]["total_tokens"]
