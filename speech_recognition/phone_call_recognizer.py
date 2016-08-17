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


# AUDIO_PATH = "/home/sergey/Downloads/Telegram Desktop/"
# AUDIO_PATH = PHONE_CALL_TEMP
# TEMP_PATH = "audio_temp/"
# AUDIO_FILE = "2015_12_21+10-45-34+zavladenie+Outgoing+to+sergey.spevak+.mp3"
# AUDIO_FILE = "W1a15verTJyfsFmD_a1P3JjX0u8LBEmBsFDqev3zvpM.mp3"
# SPLIT_SILENCE = True


def prepare_audio_file(file_name=None, temp_path=None, file_format=None):
    parts = list()

    track = AudioSegment.from_file(file=file_name, format=file_format)

    print track.channels
    print track.frame_width
    print track.duration_seconds
    print track.frame_rate
    print "-"*30

    # приводим к 16000hz 16bit
    print "# приводим к 16000hz 16bit"
    if track.frame_rate != 16000:
        track = track.set_frame_rate(frame_rate=16000)
    if track.sample_width != 2:
        track = track.set_sample_width(sample_width=2)

    if track.channels == 2:
        mono_channels = track.split_to_mono()

        # Выравниваем громкость на каналах
        for i in range(0, len(mono_channels)):
            print mono_channels[i].max_dBFS
            print mono_channels[i].rms
            mono_channels[i] = mono_channels[i].apply_gain(-mono_channels[i].max_dBFS)

        track = mono_channels[0].overlay(mono_channels[1])
    else:
        # Выравниваем громкость, если один канал, до максимального уровня
        track = track.apply_gain(-track.max_dBFS)

    print track.channels
    print track.frame_width
    print track.duration_seconds
    print track.frame_rate
    print "-"*30

    if PHONE_CALL_SPLIT_SILENCE:
        # Режем по паузам
        chunks = pydub.silence.split_on_silence(track,
                                                # must be silent for at least half a second
                                                min_silence_len=500,
                                                # consider it silent if quieter than -16 dBFS
                                                silence_thresh=-45,
                                                keep_silence=200
                                                )

        # print "Кол-во отрезков:", len(chunks)

        # конвертируем в PCM
        tmp_filename = uuid.uuid4().__str__()[:6]
        tmp_list = list()
        for i, chunk in enumerate(chunks):
            fname = temp_path + "/" + tmp_filename + "-{0}".format(i) + ".pcm"
            chunk.export(out_f=fname, format="u16le", parameters=["-acodec", "pcm_s16le"])
            tmp_list.append(tmp_filename + "-{0}".format(i) + ".pcm")

        return tmp_list
    else:
        # конвертируем в PCM
        print "# конвертируем в PCM"
        tmp_filename = uuid.uuid4().__str__()[:6]
        track.export(out_f=temp_path + "/" + tmp_filename + ".pcm", format="u16le", parameters=["-acodec", "pcm_s16le"])
        return [tmp_filename + ".pcm"]


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


def run_recognize_call(file_name=None):

    parts = prepare_audio_file(file_name=file_name, temp_path=PHONE_CALL_TEMP, file_format="mp3")
    print "Файл разбит на {} частей.".format(len(parts))

    if len(parts) == 1:
        file_name = parts[0]
        # готовим к отправке файл
        print "# готовим к отправке файл: %s" % PHONE_CALL_TEMP + "/" + file_name
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
            print "Файл больше 1Мб, отправляем через Google Cloud Store..."
            store_service = discovery.build("storage", 'v1', credentials=credentials)
            BUCKET = "conversation-parser-speech.appspot.com"

            client = storage.Client()
            bucket = client.get_bucket(BUCKET)
            blob = bucket.blob(file_name)
            blob.upload_from_filename(PHONE_CALL_TEMP + "/" + file_name, content_type="binary/octet-stream")
            print "Файл загружен в Cloud store (%s)" % blob.public_url
            req_content = {"uri": "gs://{0}/{1}".format(BUCKET,file_name)}

        else:
            print "Файл меньше 1Мб, отправляем прямой запрос..."
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
            print(json.dumps(response))
            # [END send_request]
            name = response['name']
        except Exception as e:
            print "Ошибка отправки запроса на распознавание. UUID не получен!!!", str(e)
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

        print "Отправляем запросы в Google speech api..."
        for i in range(0, len(parts)):
            file_name = parts[i]
            print "Читаем отрезок: ", file_name
            file_size = os.path.getsize(PHONE_CALL_TEMP + "/" + file_name)

            chunks.append(open(PHONE_CALL_TEMP + "/" + file_name, "rb").read())

            if file_size*1.4 > 1024*1024:
                print "Файл больше 1Мб, отправляем через Google Cloud Store..."
                store_service = discovery.build("storage", 'v1', credentials=credentials)
                BUCKET = "conversation-parser-speech.appspot.com"

                client = storage.Client()
                bucket = client.get_bucket(BUCKET)
                blob = bucket.blob(file_name)
                blob.upload_from_filename(PHONE_CALL_TEMP + "/" + file_name, content_type="binary/octet-stream")
                print "Файл загружен в Cloud store (%s)" % blob.public_url
                req_content = {"uri": "gs://{0}/{1}".format(BUCKET, file_name)}

            else:
                print "Файл меньше 1Мб, отправляем прямой запрос..."
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
                print "Ошибка отправки запроса на распознавание по частям. UUID не получен!!!", str(e)
                print "Часть с ошибкой {}".format(i)
                # удаляем временный файл
                os.remove(PHONE_CALL_TEMP + "/" + file_name)
                # raise e
            else:
                async_req_ids.append(response['name'])
                #async_req_ids.append(speech_service.operations().get(name=response['name']))
                print "Запрос #{0} принят. Идентификатор: {1}".format(i, response['name'])

                # удаляем временный файл
                os.remove(PHONE_CALL_TEMP + "/" + file_name)

        print "Все запросы приняты... "
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
        print "Ошибка."


def get_recognize_result(recognize_uuid=None):
    """
    Получения результатов распознавания для асинхронных запросов
    :param uuid:
    :return:
    """

    if not isinstance(recognize_uuid, list):
        print "{}. Ошибка. Получен неверный список UUID для проверки. ".format(__name__)
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

        # print "Итоговый результат распознавания:"
        text = ""
        for one in result:
            # print " - ", one
            text += "-- {}... \n".format(one)

    except Exception as e:
        raise e
    else:
        return text


if __name__ == '__main__':

    # Проверяем наличие задач на распознавание и получаем ответы по recognize_uuid
    print "# Проверяем наличие задач на распознавание и получаем ответы по recognize_uuid"
    session = CPO.Session()
    try:
        resp = session.query(CPO.PhoneCall).filter(CPO.PhoneCall.is_recognized == 0,
                                                   CPO.func.isnull(CPO.PhoneCall.recognize_uuid) == False).limit(1)

    except Exception as e:
        print "Ошибка при получении данных звонков. {}".format(str(e))
        raise e
    else:
        if resp.count() == 0:
            print "{}. Активных запросов на распознавание нет.".format(__name__)
        else:
            for record in resp:
                print "Получаем результат для: {} - {} - {} - {}".format(record.call_id, record.call_status,
                                                                         record.is_recognized, record.recognize_uuid)
                raw_input()
                # запрашиваем результат в Speech api
                try:
                    text = get_recognize_result(recognize_uuid=re.split(",", record.recognize_uuid))
                except Exception as e:
                    print "Ошибка при получении результата распознавания ID - {}". format(record.call_id)
                else:
                    if text:
                        # Ставим статус в phone_call_raw_data, если распознавание прошло без ошибок
                        print "Результат получен. \n Транскрипт: \n {} \n Пишем результат в clear_data.".format(text)

                        try:
                            # Пишем результат в clear_data
                            CPO.create_new_clear_phone_record(call_data=record, text=text)
                        except Exception as e:
                            print "Ошибка записи clear_data для ID - {}. {}".format(record.call_id, str(e))
                        else:
                            record.recognize_uuid = None
                            record.is_recognized = 1
                            session.commit()
                            print "Запись отмечена как обработанная."

    finally:
        session.close()

    # Запускаем распознавание для новых звонков
    print "# Запускаем распознавание для новых звонков"
    raw_input()
    session = CPO.Session()
    try:
        resp = session.query(CPO.PhoneCall).filter(CPO.PhoneCall.duration >= PHONE_CALL_DURATION_FOR_RECOGNIZE,
                                                   CPO.PhoneCall.call_status == PHONE_CALL_STATUS_FOR_RECOGNIZE,
                                                   CPO.PhoneCall.is_recognized == 0,
                                                   CPO.func.isnull(CPO.PhoneCall.recognize_uuid)).limit(1)
    except Exception as e:
        print "Ошибка при получении данных звонков. {}".format(str(e))
        raise e
    else:
        for record in resp:
            print "Запускаем распознавание для: {} - {} - {} - {}".format(record.call_id, record.call_status,
                                                                          record.is_recognized, record.recognize_uuid)
            raw_input("Начать?")
            try:
                recognize_uuid = run_recognize_call(file_name=record.record_file)
            except Exception as e:
                print "Ошибка при старте распознавания записи ID - {}.".format(record.call_id), str(e)
            else:
                if recognize_uuid:
                    # Запоминаем UUID задачи распознавания и ждем результат
                    record.recognize_uuid = ",".join(recognize_uuid)
                    record.is_recognized = 0
                    session.commit()


    finally:
        session.close()
