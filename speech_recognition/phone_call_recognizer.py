#!/usr/bin/python -t
# coding: utf8

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])

import datetime
import re
import time
from configuration import *
import objects as CPO
import uuid
import requests

from pydub import AudioSegment, playback
import pydub.silence

from googleapiclient import discovery
import httplib2
from oauth2client.client import GoogleCredentials
import base64
import json
from gcloud import storage
import os

import logging

logging.basicConfig(format='%(asctime)s.%(msecs)d %(levelname)s in \'%(module)s\' at line %(lineno)d: %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S',
                    level=logging.DEBUG,
                    filename='{}/{}.log'.format(os.path.expanduser("~"), os.path.basename(sys.argv[0])))

def prepare_audio_file(file_name=None, temp_path=None, file_format=None):
    parts = list()

    track = AudioSegment.from_file(file=file_name, format=file_format)

    logging.debug("Исходная запись:")
    logging.debug("Каналы - {}".format(track.channels))
    logging.debug("Ширина полосы - {} bit".format(track.frame_width*8))
    logging.debug("Длительность - {}".format(track.duration_seconds))
    logging.debug("Частота - {}".format(track.frame_rate))
    logging.debug("-"*30)

    # приводим к 16000hz 16bit
    logging.debug("# приводим к 16000hz 16bit")
    if track.frame_rate != 16000:
        track = track.set_frame_rate(frame_rate=16000)
    if track.sample_width != 2:
        track = track.set_sample_width(sample_width=2)

    logging.debug("# Выравниваем громкость...")
    if track.channels == 2:
        mono_channels = track.split_to_mono()

        # Выравниваем громкость на каналах
        for i in range(0, len(mono_channels)):
            mono_channels[i] = mono_channels[i].apply_gain(-mono_channels[i].max_dBFS)

        logging.debug("# Объединяем каналы в один...")
        track = mono_channels[0].overlay(mono_channels[1])
    else:
        # Выравниваем громкость, если один канал, до максимального уровня
        track = track.apply_gain(-track.max_dBFS)

    logging.debug("Обработанная запись:")
    logging.debug("Каналы - {}".format(track.channels))
    logging.debug("Ширина полосы - {} bit".format(track.frame_width*8))
    logging.debug("Длительность - {}".format(track.duration_seconds))
    logging.debug("Частота - {}".format(track.frame_rate))
    logging.debug("-"*30)

    if PHONE_CALL_SPLIT_SILENCE:
        logging.debug("# Режем по паузам")
        # Режем по паузам
        chunks = pydub.silence.split_on_silence(track,
                                                # must be silent for at least half a second
                                                min_silence_len=500,
                                                # consider it silent if quieter than -16 dBFS
                                                silence_thresh=-45,
                                                keep_silence=200
                                                )

        logging.debug("Кол-во отрезков: {}".format(len(chunks)))

        # конвертируем в PCM
        logging.debug("# конвертируем отрезки в PCM")

        tmp_filename = uuid.uuid4().__str__()[:6]
        tmp_list = list()
        for i, chunk in enumerate(chunks):
            fname = temp_path + "/" + tmp_filename + "-{0}".format(i) + ".pcm"
            chunk.export(out_f=fname, format="u16le", parameters=["-acodec", "pcm_s16le"])
            tmp_list.append(tmp_filename + "-{0}".format(i) + ".pcm")
            logging.debug(" - файл {} сконвертирован".format(tmp_filename + "-{0}".format(i) + ".pcm"))

        return tmp_list
    else:
        # конвертируем в PCM
        logging.debug("# конвертируем в PCM")
        tmp_filename = uuid.uuid4().__str__()[:6]
        track.export(out_f=temp_path + "/" + tmp_filename + ".pcm", format="u16le", parameters=["-acodec", "pcm_s16le"])
        logging.debug(" - файл {} сконвертирован".format(temp_path + "/" + tmp_filename + ".pcm"))
        return [tmp_filename + ".pcm"]

"""
def recognize_call(file_name=None):

    parts = prepare_audio_file(file_name=file_name, path=AUDIO_PATH, file_format="mp3")
    print parts

    if len(parts) == 1:
        file_name = parts[0]
        # готовим к отправке файл
        print "# готовим к отправке файл: %s" % PHONE_CALL_TEMP + file_name
        raw_input()

        # Google speech api

        # Application default credentials provided by env variable
        # GOOGLE_APPLICATION_CREDENTIALS
        credentials = GoogleCredentials.get_application_default().create_scoped(
            ['https://www.googleapis.com/auth/cloud-platform'])
        http = httplib2.Http()
        credentials.authorize(http)

        file_size = os.path.getsize(PHONE_CALL_TEMP + file_name)
        if file_size*1.4 > 1024*1024:
            print "Файл больше 1Мб, отправляем через Google Cloud Store..."
            store_service = discovery.build("storage", 'v1', credentials=credentials)
            BUCKET = "conversation-parser-speech.appspot.com"

            client = storage.Client()
            bucket = client.get_bucket(BUCKET)
            blob = bucket.blob(file_name)
            blob.upload_from_filename(PHONE_CALL_TEMP + file_name, content_type="binary/octet-stream")
            print "Файл загружен в Cloud store (%s)" % blob.public_url
            req_content = {"uri": "gs://{0}/{1}".format(BUCKET,file_name)}

        else:
            print "Файл меньше 1Мб, отправляем прямой запрос..."
            file_content = open(PHONE_CALL_TEMP + file_name, 'rb').read()
            # Base64 encode the binary audio file for inclusion in the request.
            speech_content = base64.b64encode(file_content)
            req_content = {"content": speech_content.decode('UTF-8')}


        # Transcribe the given audio file asynchronously.
        # speech_file: the name of the audio file.

        # [START construct_request]
        speech_service = discovery.build('speech', 'v1beta1', http=http)
        service_request = speech_service.speech().asyncrecognize(
            body={
                'config': {
                    # There are a bunch of config options you can specify. See
                    # https://goo.gl/EPjAup for the full list.
                    'encoding': 'LINEAR16',  # raw 16-bit signed LE samples
                    'sampleRate': 16000,  # 16 khz
                    # See https://goo.gl/DPeVFW for a list of supported languages.
                    'languageCode': 'ru-RU',  # a BCP-47 language tag
                },
                'audio': req_content
                })
        # [END construct_request]
        # [START send_request]
        response = service_request.execute()
        print(json.dumps(response))

        # [END send_request]

        # запоминаем идентификатор запроса на распознавание
        name = response['name']
        # Создаем запрос для проверкаи результата по идентификатору запроса
        service_request = speech_service.operations().get(name=name)

        sleep_period = file_size // 5*1024*1024  # 5 мб одна минута
        sleep_period = 60  # 60 секунд, вычисляется из размера файла (распознавание 1 минуты занимает около 1 минуты)

        while True:
            # Give the server a few seconds to process.
            print('Waiting for server processing...')
            print "Проверка будет сделана через {0} секунд".format(sleep_period)
            time.sleep(sleep_period)
            sleep_period = 60  # проверяем каждую минуту

            # Get the long running operation with response.
            response = service_request.execute()

            if 'done' in response and response['done']:
                print "Получен ответ."
                break

        print(json.dumps(response['response']['results']))
        print "Формитируем ответ..."

        a = response['response']['results']
        for alt in a:
            print '["alternatives"]', len(alt["alternatives"])
            print alt["alternatives"][0]["confidence"]
            print unicode(str(alt["alternatives"][0]["transcript"]), "unicode-escape")

    elif len(parts) >= 2:
        # отправялем по частям
        async_req_ids = list()
        # Google speech api

        # Application default credentials provided by env variable
        # GOOGLE_APPLICATION_CREDENTIALS
        credentials = GoogleCredentials.get_application_default().create_scoped(
            ['https://www.googleapis.com/auth/cloud-platform'])
        http = httplib2.Http()
        credentials.authorize(http)
        speech_service = discovery.build('speech', 'v1beta1', http=http)

        chunks = list()

        print "Отправляем запросы в Google speech api..."
        for i in range(0, min(30, len(parts))):
            file_name = parts[i]
            print "Читаем отрезок: ", file_name
            file_size = os.path.getsize(PHONE_CALL_TEMP + file_name)

            chunks.append(open(PHONE_CALL_TEMP + file_name, "rb").read())

            if file_size*1.4 > 1024*1024:
                print "Файл больше 1Мб, отправляем через Google Cloud Store..."
                store_service = discovery.build("storage", 'v1', credentials=credentials)
                BUCKET = "conversation-parser-speech.appspot.com"

                client = storage.Client()
                bucket = client.get_bucket(BUCKET)
                blob = bucket.blob(file_name)
                blob.upload_from_filename(PHONE_CALL_TEMP + file_name, content_type="binary/octet-stream")
                print "Файл загружен в Cloud store (%s)" % blob.public_url
                req_content = {"uri": "gs://{0}/{1}".format(BUCKET, file_name)}

            else:
                print "Файл меньше 1Мб, отправляем прямой запрос..."
                file_content = open(PHONE_CALL_TEMP + file_name, 'rb').read()
                # Base64 encode the binary audio file for inclusion in the request.
                speech_content = base64.b64encode(file_content)
                req_content = {"content": speech_content.decode('UTF-8')}

            context = {"phrases": PHONE_CONTEXT_PHRASES}

            # [START construct_request]
            service_request = speech_service.speech().asyncrecognize(
                body={
                    'config': {
                        # There are a bunch of config options you can specify. See
                        # https://goo.gl/EPjAup for the full list.
                        'encoding': 'LINEAR16',  # raw 16-bit signed LE samples
                        'sampleRate': 16000,  # 16 khz
                        # See https://goo.gl/DPeVFW for a list of supported languages.
                        'languageCode': 'ru-RU',  # a BCP-47 language tag
                        'speechContext': context
                    },
                    'audio': req_content
                    })
            # [END construct_request]
            # [START send_request]
            try:
                response = service_request.execute()
            except Exception as e:
                print "Ошибка.", str(e)
                raw_input("Продолжить?")
            else:
                async_req_ids.append(speech_service.operations().get(name=response['name']))
                print "Запрос #{0} принят. Идентификатор: {1}".format(i, response['name'])

                # удаляем временный файл
                os.remove(PHONE_CALL_TEMP + file_name)

        print "Все запросы приняты... Продолжить?"
        raw_input()
        result = [None for i in range(len(async_req_ids))]
        # Получаем ответы на запросы

        for i in range(0, len(async_req_ids)):
            print "Запрашиваем ответ для части {0}.".format(i)
            recieved = False
            while not recieved:
                resp = async_req_ids[i].execute()
                if 'done' in resp and resp['done']:
                    print "Получен ответ для части {0}.".format(i)
                    if resp['response'].get('results'):
                        result[i] = resp['response'].get('results')[0]['alternatives'][0]['transcript']
                    else:
                        result[i] = ""
                    recieved = True
                else:
                    print "Ждем 10 сек..."
                    time.sleep(10)

        print "Итоговый результат распознавания:"
        for one in result:
            print " - ", one

    else:
        print "Ошибка."
"""

def run_recognize_call(file_name=None):

    parts = prepare_audio_file(file_name=file_name, temp_path=PHONE_CALL_TEMP, file_format="mp3")
    logging.debug("Файл разбит на {} частей.".format(len(parts)))

    if len(parts) == 1:
        file_name = parts[0]
        # готовим к отправке файл
        logging.debug("# готовим к отправке файл: {}".format(PHONE_CALL_TEMP + "/" + file_name))
        raw_input()

        # Google speech api

        # Application default credentials provided by env variable
        # GOOGLE_APPLICATION_CREDENTIALS
        credentials = GoogleCredentials.get_application_default().create_scoped(
            ['https://www.googleapis.com/auth/cloud-platform'])
        http = httplib2.Http()
        credentials.authorize(http)

        file_size = os.path.getsize(PHONE_CALL_TEMP + "/" + file_name)
        if file_size*1.4 > 1024*1024:
            logging.debug("Файл больше 1Мб, отправляем через Google Cloud Store...")
            # store_service = discovery.build("storage", 'v1', credentials=credentials)
            BUCKET = "conversation-parser-speech.appspot.com"

            client = storage.Client()
            bucket = client.get_bucket(BUCKET)
            blob = bucket.blob(file_name)
            blob.upload_from_filename(PHONE_CALL_TEMP + "/" + file_name, content_type="binary/octet-stream")
            logging.debug("Файл загружен в Cloud store ({})".format(blob.public_url))
            req_content = {"uri": "gs://{0}/{1}".format(BUCKET,file_name)}

        else:
            logging.debug("Файл меньше 1Мб, отправляем прямой запрос...")
            file_content = open(PHONE_CALL_TEMP + "/" + file_name, 'rb').read()
            # Base64 encode the binary audio file for inclusion in the request.
            speech_content = base64.b64encode(file_content)
            req_content = {"content": speech_content.decode('UTF-8')}

        """
        Transcribe the given audio file asynchronously.
        speech_file: the name of the audio file.
        """
        raw_input()

        # [START construct_request]
        speech_service = discovery.build('speech', 'v1beta1', http=http)
        service_request = speech_service.speech().asyncrecognize(
            body={
                'config': {
                    # There are a bunch of config options you can specify. See
                    # https://goo.gl/EPjAup for the full list.
                    'encoding': 'LINEAR16',  # raw 16-bit signed LE samples
                    'sampleRate': 16000,  # 16 khz
                    # See https://goo.gl/DPeVFW for a list of supported languages.
                    'languageCode': 'ru-RU',  # a BCP-47 language tag
                    'speechContext': {"phrases": PHONE_CONTEXT_PHRASES}
                },
                'audio': req_content
                })
        # [END construct_request]

        # запоминаем идентификатор запроса на распознавание
        try:
            # [START send_request]
            response = service_request.execute()
            logging.debug("Ответ сервиса: {}".format(json.dumps(response)))
            # [END send_request]
            name = response['name']
        except Exception as e:
            logging.error("Ошибка отправки запроса на распознавание. UUID не получен!!! {}".format(str(e)))
            raise e
        else:
            # Возвращаем код запроса
            return [name]

        """
        # Создаем запрос для проверкаи результата по идентификатору запроса
        service_request = speech_service.operations().get(name=name)

        sleep_period = file_size // 5*1024*1024  # 5 мб одна минута
        sleep_period = 60  # 60 секунд, вычисляется из размера файла (распознавание 1 минуты занимает около 1 минуты)

        while True:
            # Give the server a few seconds to process.
            print('Waiting for server processing...')
            print "Проверка будет сделана через {0} секунд".format(sleep_period)
            time.sleep(sleep_period)
            sleep_period = 60  # проверяем каждую минуту

            # Get the long running operation with response.
            response = service_request.execute()

            if 'done' in response and response['done']:
                print "Получен ответ."
                break

        print(json.dumps(response['response']['results']))
        print "Формитируем ответ..."

        a = response['response']['results']
        for alt in a:
            print '["alternatives"]', len(alt["alternatives"])
            print alt["alternatives"][0]["confidence"]
            print unicode(str(alt["alternatives"][0]["transcript"]), "unicode-escape")
        """

    elif len(parts) >= 2:
        # отправялем по частям
        async_req_ids = list()
        # Google speech api

        # Application default credentials provided by env variable
        # GOOGLE_APPLICATION_CREDENTIALS
        credentials = GoogleCredentials.get_application_default().create_scoped(
            ['https://www.googleapis.com/auth/cloud-platform'])
        http = httplib2.Http()
        credentials.authorize(http)
        speech_service = discovery.build('speech', 'v1beta1', http=http)

        chunks = list()

        logging.debug("Отправляем запросы в Google speech api...")
        for i in range(0, len(parts)):
            file_name = parts[i]
            logging.debug("Читаем отрезок: {}".format(file_name))
            file_size = os.path.getsize(PHONE_CALL_TEMP + "/" + file_name)

            chunks.append(open(PHONE_CALL_TEMP + "/" + file_name, "rb").read())

            if file_size*1.4 > 1024*1024:
                logging.debug("Файл больше 1Мб, отправляем через Google Cloud Store...")
                store_service = discovery.build("storage", 'v1', credentials=credentials)
                BUCKET = "conversation-parser-speech.appspot.com"

                client = storage.Client()
                bucket = client.get_bucket(BUCKET)
                blob = bucket.blob(file_name)
                blob.upload_from_filename(PHONE_CALL_TEMP + "/" + file_name, content_type="binary/octet-stream")
                logging.debug("Файл загружен в Cloud store (%s)" % blob.public_url)
                req_content = {"uri": "gs://{0}/{1}".format(BUCKET, file_name)}

            else:
                logging.debug("Файл меньше 1Мб, отправляем прямой запрос...")
                file_content = open(PHONE_CALL_TEMP + "/" + file_name, 'rb').read()
                # Base64 encode the binary audio file for inclusion in the request.
                speech_content = base64.b64encode(file_content)
                req_content = {"content": speech_content.decode('UTF-8')}

            # [START construct_request]
            service_request = speech_service.speech().asyncrecognize(
                body={
                    'config': {
                        # There are a bunch of config options you can specify. See
                        # https://goo.gl/EPjAup for the full list.
                        'encoding': 'LINEAR16',  # raw 16-bit signed LE samples
                        'sampleRate': 16000,  # 16 khz
                        # See https://goo.gl/DPeVFW for a list of supported languages.
                        'languageCode': 'ru-RU',  # a BCP-47 language tag
                        'speechContext': {"phrases": PHONE_CONTEXT_PHRASES}
                    },
                    'audio': req_content
                    })
            # [END construct_request]
            # [START send_request]
            try:
                response = service_request.execute()
            except Exception as e:
                logging.error("Ошибка отправки запроса на распознавание по частям. UUID не получен!!!. {}".format(str(e)))
                logging.error("Часть с ошибкой {}".format(i))
                # удаляем временный файл
                os.remove(PHONE_CALL_TEMP + "/" + file_name)
                # raise e
            else:
                async_req_ids.append(response['name'])
                #async_req_ids.append(speech_service.operations().get(name=response['name']))
                logging.debug("Запрос #{0} принят. Идентификатор: {1}".format(i, response['name']))

                # удаляем временный файл
                os.remove(PHONE_CALL_TEMP + "/" + file_name)

        logging.debug("Все запросы приняты... ")
        return async_req_ids

        """

        result = [None for i in range(len(async_req_ids))]
        # Получаем ответы на запросы

        for i in range(0, len(async_req_ids)):
            print "Запрашиваем ответ для части {0}.".format(i)
            recieved = False
            while not recieved:
                resp = async_req_ids[i].execute()
                if 'done' in resp and resp['done']:
                    print "Получен ответ для части {0}.".format(i)
                    if resp['response'].get('results'):
                        result[i] = resp['response'].get('results')[0]['alternatives'][0]['transcript']
                    else:
                        result[i] = ""
                    recieved = True
                else:
                    print "Ждем 10 сек..."
                    time.sleep(10)

        print "Итоговый результат распознавания:"
        for one in result:
            print " - ", one
        """

    else:
        logging.debug("Ошибка.")


def get_recognize_result(recognize_uuid=None):
    """
    Получения результатов распознавания для асинхронных запросов
    :param uuid:
    :return:
    """

    if not isinstance(recognize_uuid, list):
        logging.error("{}. Ошибка. Получен неверный список UUID для проверки. ".format(__name__))
        return None

    # Application default credentials provided by env variable
    # GOOGLE_APPLICATION_CREDENTIALS
    credentials = GoogleCredentials.get_application_default().create_scoped(
        ['https://www.googleapis.com/auth/cloud-platform'])
    http = httplib2.Http()
    credentials.authorize(http)
    speech_service = discovery.build('speech', 'v1beta1', http=http)

    async_req_ids = list()
    try:
        for one in recognize_uuid:
            async_req_ids.append(speech_service.operations().get(name=one))

    except Exception as e:
        raise e

    try:
        result = [None for i in range(len(async_req_ids))]
        # Получаем ответы на запросы

        for i in range(0, len(async_req_ids)):
            logging.debug("Запрашиваем ответ для части {0}.".format(i))
            recieved = False
            while not recieved:
                resp = async_req_ids[i].execute()
                if 'done' in resp and resp['done']:
                    logging.debug("Получен ответ для части {0}.".format(i))
                    if resp['response'].get('results'):
                        result[i] = resp['response'].get('results')[0]['alternatives'][0]['transcript']
                    else:
                        result[i] = ""
                    recieved = True
                else:
                    logging.debug("Ждем 10 сек...")
                    time.sleep(10)

        # print "Итоговый результат распознавания:"
        text = ""
        for one in result:
            # print " - ", one
            text += "-- {}... <br>\n".format(one)

    except Exception as e:
        raise e
    else:
        return text


if __name__ == '__main__':

    logging.debug("####### Начало работы #########")
    try:
        request_limit = int(sys.argv[1])
    except Exception as e:
        logging.debug("Лимит не задан, используем стандартный - 10. {}".format(str(e)))
        request_limit = 10

    logging.debug("# Лимит запросов: {}".format(request_limit))

    # Проверяем наличие задач на распознавание и получаем ответы по recognize_uuid
    logging.debug("# Проверяем наличие задач на распознавание и получаем ответы по recognize_uuid")
    session = CPO.Session()
    try:
        resp = session.query(CPO.PhoneCall).filter(CPO.PhoneCall.is_recognized == 0,
                                                   CPO.func.isnull(CPO.PhoneCall.recognize_uuid) == False,
                                                   CPO.PhoneCall.recognize_uuid != "").\
            limit(request_limit)

    except Exception as e:
        logging.error("Ошибка при получении данных звонков. {}".format(str(e)))
        raise e
    else:
        if resp.count() == 0:
            logging.debug("# Активных запросов на распознавание нет.")
        else:
            for record in resp:
                logging.debug("Получаем результат для: {} - {} - {} - {}".
                              format(record.call_id, record.call_status, record.is_recognized, record.recognize_uuid))
                # raw_input()
                # запрашиваем результат в Speech api
                try:
                    text = get_recognize_result(recognize_uuid=re.split(",", record.recognize_uuid))
                except Exception as e:
                    logging.error("Ошибка при получении результата распознавания ID - {}". format(record.call_id))
                    logging.error(str(e))
                else:
                    if text:
                        # Ставим статус в phone_call_raw_data, если распознавание прошло без ошибок
                        logging.debug("Результат получен. \n Транскрипт: \n {} \n".
                                      format(text))

                        try:
                            # Пишем результат в clear_data
                            CPO.create_new_clear_phone_record(call_data=record, text=text)
                        except Exception as e:
                            logging.error("Ошибка записи clear_data для ID - {}. {}".format(record.call_id, str(e)))
                        else:
                            logging.debug("Результат в clear_data записан.")
                            record.recognize_uuid = None
                            record.is_recognized = 1
                            session.commit()
                            logging.debug("Запись отмечена как обработанная.")
                            try:
                                # удаляем файл с записью
                                os.remove(record.record_file)
                            except Exception as e:
                                logging.error("Ошибка удаления записи {}. {}".format(record.record_file, str(e)))
                            else:
                                logging.debug("Запись разговора удалена - {}.".format(record.record_file))


    finally:
        session.close()

    # Запускаем распознавание для новых звонков
    logging.debug("# Запускаем распознавание для новых звонков")
    # raw_input()

    session = CPO.Session()
    try:
        resp = session.query(CPO.PhoneCall).filter(CPO.PhoneCall.duration >= PHONE_CALL_DURATION_FOR_RECOGNIZE,
                                                   CPO.PhoneCall.call_status == PHONE_CALL_STATUS_FOR_RECOGNIZE,
                                                   CPO.PhoneCall.is_recognized == 0,
                                                   CPO.or_(CPO.func.isnull(CPO.PhoneCall.recognize_uuid),
                                                           CPO.PhoneCall.recognize_uuid == str())).limit(10)
    except Exception as e:
        logging.error("Ошибка при получении данных звонков. {}".format(str(e)))
        raise e
    else:
        if resp.count() == 0:
            logging.debug("# Новых звонков на распознавание нет.")
        else:

            for record in resp:
                logging.debug("Запускаем распознавание для: {} - {} - {} - {}".format(record.call_id,
                                                                                      record.call_status,
                                                                                      record.is_recognized,
                                                                                      record.recognize_uuid))
                # raw_input("Начать?")
                try:
                    recognize_uuid = run_recognize_call(file_name=record.record_file)
                except Exception as e:
                    logging.error("Ошибка при старте распознавания записи ID - {}.".format(record.call_id), str(e))
                else:
                    if recognize_uuid:
                        # Запоминаем UUID задачи распознавания и ждем результат
                        record.recognize_uuid = ",".join(recognize_uuid)
                        record.is_recognized = 0
                        session.commit()
                        logging.debug("Идентификаторы: {}. \n Идентификаторы задач распознавания записаны.".
                                      format(recognize_uuid))


    finally:
        session.close()

    logging.debug("####### Завершение работы #########")
