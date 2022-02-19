""" Distributed under GNU Affero GPL.

    alexander 1 15/02/2022

    Copyright (C) 2021 - 2022 Davide Leone

    You can contact me at leonedavide[at]protonmail.com

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as
    published by the Free Software Foundation, either version 3 of the
    License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>."""

from telegram import InlineQueryResultCachedAudio, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, MessageHandler, Filters, InlineQueryHandler, ChosenInlineResultHandler, \
    CallbackQueryHandler, CommandHandler
import logging
import json
import yaml
import random
import telegram


def audio_message(update, context):
    """
    This function is used to process an audio file received from an admin. If it is a new audio, it is added to the
    database; otherwise a number of information and a keyboard to list/de-list or see/remove the description associated
    to the audio are sent to the admin.
    """

    logging.info('An audio file with ID {} was received from user {}'.format(update.message.audio.file_unique_id,
                                                                             update.effective_chat.id))

    if update.message.audio.performer is None or update.message.audio.title is None:
        logging.warning('The audio file received did not contain the required metadata')
        update.message.reply_text(text=messages_text['error_metadata'], quote=True)

    else:

        if update.message.audio.file_unique_id in list(database_audio.keys()):

            if database_audio[update.message.audio.file_unique_id]['listed'] is True:
                keyboard = [[
                    InlineKeyboardButton(
                        text=messages_text['delist_keyboard'],
                        callback_data="listed {}".format(update.message.audio.file_unique_id)
                    )]]
            else:
                keyboard = [[
                    InlineKeyboardButton(
                        text=messages_text['list_keyboard'],
                        callback_data="listed {}".format(update.message.audio.file_unique_id)
                    )]]

            if database_audio[update.message.audio.file_unique_id]['description'] == '':
                pass
            else:
                keyboard += [[
                    InlineKeyboardButton(
                        text=messages_text['remove_description_keyboard'],
                        callback_data="rmdescription {}".format(update.message.audio.file_unique_id)
                    )]]
                keyboard += [[
                    InlineKeyboardButton(
                        text=messages_text['show_description_keyboard'],
                        callback_data="shdescription {}".format(update.message.audio.file_unique_id)
                    )]]

            update.message.reply_text(
                text=messages_text['old_audio'].format(**database_audio[update.message.audio.file_unique_id]),
                parse_mode=telegram.ParseMode.HTML,
                reply_to_message_id=update.message.message_id,
                reply_markup=InlineKeyboardMarkup(keyboard))

        else:
            database_audio[update.message.audio.file_unique_id] = {
                'added_by': update.effective_chat.id,
                'description': '',
                'file_id': update.message.audio.file_id,
                'listed': True,
                'performer': update.message.audio.performer.lower(),
                'title': update.message.audio.title.lower(),
                'unique_result_id': update.message.audio.file_unique_id,
                'views': 0
            }

            with open(database_filename, 'w') as fo:
                json.dump(database_audio, fo)

            update.message.reply_text(
                text=messages_text['new_audio'].format(**database_audio[update.message.audio.file_unique_id]),
                parse_mode=telegram.ParseMode.HTML,
                reply_to_message_id=update.message.message_id,
                reply_markup=InlineKeyboardMarkup(
                    [[
                        InlineKeyboardButton(
                            text=messages_text['delist_keyboard'],
                            callback_data="delist {}".format(update.message.audio.file_unique_id)
                        )]]))


def change_listed_status(update, context):
    """
    This function is used when an admin presses the inline keyboard to list or de-list an audio file.
    """

    logging.info('change_listed_status function called')

    if update.callback_query.from_user.id in id_admin:
        if database_audio[update.callback_query.message.reply_to_message.audio.file_unique_id]['listed'] is True:
            database_audio[update.callback_query.message.reply_to_message.audio.file_unique_id]['listed'] = False
            text = messages_text['delisted_success'].format(
                **database_audio[update.callback_query.message.reply_to_message.audio.file_unique_id])
        else:
            database_audio[update.callback_query.message.reply_to_message.audio.file_unique_id]['listed'] = True
            text = messages_text['listed_success'].format(
                **database_audio[update.callback_query.message.reply_to_message.audio.file_unique_id])

        with open(database_filename, 'w') as fo:
            json.dump(database_audio, fo)
        update.callback_query.edit_message_text(text=text, parse_mode=telegram.ParseMode.HTML, reply_markup=None)

    else:
        # I could not find a python-telegram-bot filter that filters inline callback by their chat IDs
        logging.warning("A callback query was received from user {}, who doesn't seem to be an admin!".format(
            update.callback_query.from_user.id))


def inline_query(update, context):
    """
    This function is used to answer to inline queries. The software is supposed to search for the audio files that
    best suit the query and list them. The software will first simplify the query, then compare it with any audio in
    the database. An audio associated text is made by its title, the associated performer and a customizable
    description; this is what each query is compared against.
    If a query such as "hell world" is compared against the associated text "hello world", the word "world" is fully
    contained into the associated text, while the word "hell" is quasi-contained being contained into the word "hello".
    The software will proceed to compare the query with each associated text, giving 1 point to the associated text for
    each word fully contained and 0.5 point for each word quasi-contained. An audio associated text receives a perfect
    score when it contains each and every word of the query. This is by definition a 100% score.
    When responding to the query with a list of audio, they are listed in the following order: audio with a 100% score,
    audio with an 80% or more score, audio with a 40% or more score and (optionally) audio with less than 40% score.
    Each category is separately sorted; the first two with the method specified in the config.yaml file, while the last
    two are sorted by the score percentage (and when this percentage is the same, by the aforementioned specified
    method).
    """
    logging.info('inline_query function called')

    query = ''.join(filter(lambda x: (str.isalnum(x) or str.isspace(x)), update.inline_query.query)).lower()
    # To simplify the comparison only alphabetical and numerical characters, and spaces are left.
    results = [[], [], [], [], []]
    logging.info('The query {} was received from user {}'.format(query, update.inline_query.from_user.id))

    for audio in [x for x in database_audio.values() if x['listed'] is True]:
        audio_text_content = (audio['title'] + ' ' + audio['performer'] + ' ' + audio['description'])
        audio_text_content = ''.join(filter(lambda x: (str.isalnum(x) or str.isspace(x)), audio_text_content)).lower()
        audio['words_matched'] = len([x for x in query.split() if x in audio_text_content.split()]) + \
                                 0.5 * len(
            [x for x in query.split() if x in [x for y in audio_text_content.split() if x in y and x not in
                                               [x for x in query.split() if x in audio_text_content.split()]]])

        if audio['words_matched'] >= len(query.split()):  # 100%
            results[0].append(audio)
            logging.debug('{} matched 100% of the words of the query'.format(audio['title']))
        elif audio['words_matched'] >= len(query.split()) / 1.25:  # 80%
            results[1].append(audio)
            logging.debug('{} matched 80% or more of the words of the query'.format(audio['title']))
        elif audio['words_matched'] >= len(query.split()) * 0.4:  # 40%
            results[2].append(audio)
            logging.debug('{} matched 40% or more of the words of the query'.format(audio['title']))

        elif append_less_relevant_results is True:
            results[3].append(audio)
            logging.debug('{} matched less than 40% of the words of the query'.format(audio['title']))
        else:
            results[3] = []

    if sorting_algorithm == 'views':
        results[0].sort(reverse=True, key=lambda x: x['views'])
        results[1].sort(reverse=True, key=lambda y: y['views'])
        results[2].sort(reverse=True, key=lambda z: z['views'])
        results[2].sort(reverse=True, key=lambda z: z['words_matched'])
    elif sorting_algorithm == 'title':
        results[0].sort(reverse=False, key=lambda x: x['title'])
        results[1].sort(reverse=False, key=lambda y: y['title'])
        results[2].sort(reverse=False, key=lambda z: z['title'])
        results[2].sort(reverse=True, key=lambda z: z['words_matched'])
    elif sorting_algorithm == 'performer':
        results[0].sort(reverse=False, key=lambda x: x['performer'])
        results[1].sort(reverse=False, key=lambda y: y['performer'])
        results[2].sort(reverse=False, key=lambda z: z['performer'])
        results[2].sort(reverse=True, key=lambda z: z['words_matched'])
    elif sorting_algorithm == 'words_matched':
        results[1].sort(reverse=True, key=lambda x: x['words_matched'])
        results[2].sort(reverse=True, key=lambda z: z['words_matched'])

    results[3].sort(reverse=True, key=lambda z: z['words_matched'])

    max_allowed = 50  # According to Telegram API Documentation "No more than 50 results per query are allowed"
    answer = []

    for result in (results[0] + results[1] + results[2] + results[3]):

        if random.randint(0, send_caption_every) == send_caption_every - 1:
            # If configured to do so, the software has to add a custom caption every x audio files.
            # Instead of having to rely on a database, it does simply add this caption with a probability of 1/x.
            # For example, if it is supposed to add the custom caption every 4 files, it will instead add the custom
            # caption to any audio with a probability of 25%.
            caption = custom_caption
        else:
            caption = None

        answer.append(InlineQueryResultCachedAudio(
            id=result['unique_result_id'],
            audio_file_id=result['file_id'],
            caption=caption,
            parse_mode=telegram.ParseMode.HTML
        ))
        max_allowed -= 1
        if max_allowed == 0:
            break

    logging.info('The query was successfully processed and {} audio were given in response'.format(
        len(database_audio) - len(results[0] + results[1] + results[2])))
    update.inline_query.answer(answer, cache_time=cache_time)


def remove_description(update, context):
    """
    This function is used when an admin presses the inline keyboard to remove the description of an audio file.
    """

    logging.info('remove_description function called')

    if update.callback_query.from_user.id in id_admin:

        database_audio[update.callback_query.message.reply_to_message.audio.file_unique_id]['description'] = ''

        with open(database_filename, 'w') as fo:
            json.dump(database_audio, fo)
        update.callback_query.edit_message_text(text=messages_text['remove_description_success'].format(
            **database_audio[update.callback_query.message.reply_to_message.audio.file_unique_id]),
            parse_mode=telegram.ParseMode.HTML, reply_markup=None)

    else:
        # I could not find a python-telegram-bot filter that filters inline callback by their chat IDs
        logging.warning("A callback query was received from user {}, who doesn't seem to be an admin!".format(
            update.callback_query.from_user.id))


def set_audio_description(update, context):
    """
    This function is used to change the "description" value of an audio in the database. To change the "description",
    an admin has to send the new description (in form of a text message) in response to an audio message in the chat
    with the Bot.
    """

    logging.info('set_audio_description function called. A message was received from user {}'.format(
        update.effective_chat.id))

    if update.message.reply_to_message.audio is None:
        welcome(update, context)

    else:
        if update.message.reply_to_message.audio.file_unique_id in database_audio.keys():
            database_audio[update.message.reply_to_message.audio.file_unique_id][
                'description'] = update.message.text.lower()

            with open(database_filename, 'w') as fo:
                json.dump(database_audio, fo)

            update.message.reply_text(
                text=messages_text['description_updated'].format(
                    **database_audio[update.message.reply_to_message.audio.file_unique_id]),
                parse_mode=telegram.ParseMode.HTML,
                reply_to_message_id=update.message.message_id)
        else:
            update.message.reply_text(
                text=messages_text['error_audio_unknown'],
                parse_mode=telegram.ParseMode.HTML,
                reply_to_message_id=update.message.message_id)


def show_description(update, context):
    """
    This function is used when an admin presses the inline keyboard to show the description of an audio file. The
    description is sent to the admin as a text message, with no parse_mode.
    """

    logging.info('show_description function called')

    if update.callback_query.from_user.id in id_admin:
        audio_file_id = update.callback_query.message.reply_to_message.audio.file_unique_id

        if database_audio[audio_file_id]['description'] != '':

            if update.callback_query.message is None:
                # According to Telegram documentation: "message content and message date will not be available if the
                # message is too old" https://core.telegram.org/bots/api#callbackquery
                update.callback_query.bot.send_message(chat_id=update.callback_query.from_user.id,
                                                       text=database_audio[audio_file_id]['description'])
            else:
                update.callback_query.message.reply_text(text=database_audio[audio_file_id]['description'],
                                                         quote=True)
            update.callback_query.answer()
        else:
            update.callback_query.answer(text=messages_text['answer_no_description'], show_alert=True)

    else:
        # I could not find a python-telegram-bot filter that filters inline callback by their chat IDs
        logging.warning("A callback query was received from user {}, who doesn't seem to be an admin!".format(
            update.callback_query.from_user.id))


def stat_command(update, context):
    """
    This function is used to answer to the /stat command by providing useful statistics.
    """

    logging.info('stat_command function called. A message was received from user {}'.format(update.effective_chat.id))

    total_views = 0
    for audio in database_audio.values():
        total_views += audio['views']

    update.message.reply_text(
        text=messages_text['stat_command'].format(**{
            'audio': len(database_audio),
            'views': total_views}),
        parse_mode=telegram.ParseMode.HTML)


def update_views(update, context):
    """
    This function is used to record each time an audio has been selected.
    You need to activate inline feedback. See here: https://core.telegram.org/bots/inline#collecting-feedback
    Only a fraction of feedbacks may be passed to the Bot, based on the settings you have chosen with BotFather,
    To correct for this, a "probability_setting" value is used to count each feedback as 1, 10, 1000 or 10000 views.
    """

    logging.info('update_views function called')
    for audio in database_audio.values():
        if audio['unique_result_id'] == update.chosen_inline_result.result_id:
            audio['views'] += 1 * probability_setting
            with open(database_filename, 'w') as fo:
                json.dump(database_audio, fo)
            break


def welcome(update, context):
    """
    This function is used to answer to /start, /help and /info commands and generic text messages by providing a
    simple welcome message.
    """

    logging.info('welcome function called. A message was received from user {}'.format(update.effective_chat.id))
    update.message.reply_text(
        text=messages_text['welcome'].format(**
                                             {'username': bot_get_me['username'],
                                              'first_name': bot_get_me['first_name']}),
        parse_mode=telegram.ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            [[
                InlineKeyboardButton(
                    text=messages_text['source_code_keyboard'],
                    url=source_url
                )]]))


with open('config.yaml') as fo:
    config = yaml.load(fo, Loader=yaml.FullLoader)

append_less_relevant_results = config['append_less_relevant_results']  # Type: bool
cache_time = config['cache_time']  # Type: int
custom_caption = config['custom_caption']  # Type: str
database_filename = config['database_filename']  # Type: str
id_admin = list(config['id_admin'])  # Type: list of int
log_filename = config['log_filename']  # Type: str
logging_level = config['logging_level']  # Type: str
messages_text = config['messages_text']  # Type: list of str
probability_setting = config['probability_setting']  # Type: int
send_caption_every = config['send_caption_every']  # Type: int
sorting_algorithm = config['sorting_algorithm']  # Type: str
source_url = config['source_url']  # Type: str
token = config['token']  # Type: str

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    filename=log_filename,
                    level=logging_level,
                    filemode='w')

try:
    with open(database_filename, 'r') as fo:
        database_audio = json.load(fo)

except (FileNotFoundError, json.decoder.JSONDecodeError):
    logging.error('An error occurred while trying to load the database file; it will be created anew')
    database_audio = {}
    with open(database_filename, 'w') as fo:
        json.dump(database_audio, fo)

updater = Updater(token=token)
bot_get_me = updater.bot.get_me()

logging.info('alexander was started. Bot started with username: {} Configuration loaded. {} audio loaded'.format(
    bot_get_me['username'], len(database_audio)))

if not bot_get_me['supports_inline_queries']:  # Checks if inline queries have been activated by BotFather
    logging.error('It seems you have not activated inline queries for this Bot. Please contact BotFather!')

updater.dispatcher.add_handler(CommandHandler(filters=Filters.chat_type.private & Filters.chat(id_admin),
                                              command='stat', callback=stat_command))
updater.dispatcher.add_handler(
    MessageHandler(filters=Filters.chat_type.private & Filters.text & Filters.reply & Filters.chat(id_admin),
                   callback=set_audio_description))
updater.dispatcher.add_handler(
    MessageHandler(filters=Filters.chat_type.private & Filters.audio & Filters.chat(id_admin),
                   callback=audio_message))
updater.dispatcher.add_handler(MessageHandler(filters=Filters.chat_type.private,
                                              callback=welcome, run_async=True))

updater.dispatcher.add_handler(InlineQueryHandler(callback=inline_query, run_async=True))
updater.dispatcher.add_handler(ChosenInlineResultHandler(update_views))
updater.dispatcher.add_handler(CallbackQueryHandler(callback=change_listed_status, pattern="^listed."))
updater.dispatcher.add_handler(CallbackQueryHandler(callback=show_description, pattern="^shdescription."))
updater.dispatcher.add_handler(CallbackQueryHandler(callback=remove_description, pattern="^rmdescription."))
updater.start_polling()
