import json
import os
import random

import pinecone

from chalicelib.utils import google_translate, generate_embedding
from loguru import logger

# Telegram token
PINECONE_ENV = os.environ["PINECONE_ENV"]
PINECONE_API_KEY = os.environ["PINECONE_API_KEY"]


class TextSearch:
    def __init__(self, index):
        self.index = index

    def search(self, query_embedding, top_k=5):
        # number of top text to be retrieved from database
        top_texts_count = 20
        # assumed to be less than that
        max_meanings_count = 2000
        similar_texts = self.index.query(query_embedding, namespace="text", top_k=top_texts_count,
                                         include_metadata=True)
        similar_meanings = self.index.query(query_embedding, namespace="meaning", top_k=max_meanings_count,
                                            include_metadata=True)

        ordered_texts = self.order_by_joint_relevance(similar_texts, similar_meanings)

        top_texts = {}
        for text in ordered_texts:
            video_id = text['id'].split('-')[0]
            if video_id not in top_texts or text['relevance'] > top_texts[video_id]['relevance']:
                top_texts[video_id] = text

        return sorted(top_texts.values(), key=lambda x: x['relevance'], reverse=True)[:top_k]

    @staticmethod
    def _compute_text_score(text, similar_meanings):
        metadata = text["metadata"]
        try:
            meaning_id = metadata["meaning_id"]
        except KeyError:
            logger.info(f"KeyError occurred for text with id: {text['id']}")
        else:
            for chapter in similar_meanings["matches"]:
                if chapter['id'] == meaning_id:
                    return chapter['score']

            return None

    def order_by_joint_relevance(self, texts, meanings):
        mapped_results = []
        for text in texts['matches']:
            text_relevance = text['score']
            meaning_relevance = self._compute_text_score(text, meanings)
            if meaning_relevance is not None:
                mapped_results.append({
                    'id': text['id'],
                    'relevance': 0.4 * text_relevance + 0.6 * meaning_relevance,
                    'text_relevance': text_relevance,
                    'meaning_relevance': meaning_relevance,
                    'text': text['metadata']['text'],
                    'url': f"{text['metadata']['url']}&t={int(text['metadata']['start'])}",
                    'start': text['metadata']['start'],
                    'title': text['metadata']['title'],
                    'published': str(text['metadata']['published'])
                })
        return sorted(mapped_results, key=lambda t: t['relevance'], reverse=True)


def remove_capslock(text):
    if len(text) == 1:
        return text
    processed_words = []
    for word in text.split():
        if word[0].isupper() and any(c.islower() for c in word[1:]):
            processed_words.append(word)
        else:
            processed_words.append(word.lower())
    res = ' '.join(processed_words)
    res = res[0].upper() + res[1:]
    return res


def _search(query, top_k):
    processed_query = google_translate(query, "ru", "en")

    logger.info(f"Embedding model Open AI is used for search")
    query_embedding, tokens_count = generate_embedding(processed_query)
    logger.info(f"Number of tokens to build an embedding for a user query: {tokens_count}")

    index_name = 'daniel-index-v2'
    # initialize connection to pinecone (get API key at app.pinecone.io)
    pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENV)
    # connect to index
    index = pinecone.Index(index_name)
    # view index stats
    index.describe_index_stats()

    text_search = TextSearch(index)
    top_results = text_search.search(query_embedding, top_k)

    return top_results


def get_random_response():
    with open('chalicelib/ui/ui_results.json', 'r', encoding='utf-8') as f:
        responses = json.load(f)["responses"]
    return random.choice(responses)


def search(query):
    logger.info(f"User query: {query}")
    results = _search(query, 5)
    logger.info(f"Results: {len(results)}")

    if len(results) > 0:
        answer = '{}\n\n'.format(get_random_response())
        for count, result in enumerate(results, start=1):
            answer += '{}) {}\n{}\n\n' \
                .format(count, remove_capslock(result['title']), f'{result["url"]}')
    else:
        answer = "Ой, кажется, я не смог найти точный ответ на ваш вопрос 🤔 " \
                 "Можете уточнить вопрос для более точного поиска? 🎯"

    return answer
