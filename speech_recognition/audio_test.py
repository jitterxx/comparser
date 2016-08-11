#!/usr/bin/python -t
# coding: utf8

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])

import datetime
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


AUDIO_PATH = "/home/sergey/Downloads/Telegram Desktop/"
TEMP_PATH = "audio_temp/"
# AUDIO_FILE = "2015_12_21+10-45-34+zavladenie+Outgoing+to+sergey.spevak+.mp3"
AUDIO_FILE = "W1a15verTJyfsFmD_a1P3JjX0u8LBEmBsFDqev3zvpM.mp3"
SPLIT_SILENCE = False


def prepare_audio_file(file=None, path=None, file_format=None):
    parts = list()

    track = AudioSegment.from_file(file=AUDIO_PATH + AUDIO_FILE, format=file_format)

    print track.channels
    print track.frame_width
    print track.duration_seconds
    print track.frame_rate
    print "-"*30

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

    # приводим к 16000hz 16bit
    print "# приводим к 16000hz 16bit"
    if track.frame_rate != 16000:
        track = track.set_frame_rate(frame_rate=16000)
    if track.sample_width != 2:
        track = track.set_sample_width(sample_width=2)

    SPLIT_SILENCE = True

    if SPLIT_SILENCE:
        # Режем по паузам
        chunks = pydub.silence.split_on_silence(track,
                                                # must be silent for at least half a second
                                                min_silence_len=450,
                                                # consider it silent if quieter than -16 dBFS
                                                silence_thresh=-45,
                                                keep_silence=200
                                                )

        print "Кол-во отрезков:", len(chunks)

        # конвертируем в PCM
        tmp_filename = uuid.uuid4().__str__()[:6]
        tmp_list = list()
        for i, chunk in enumerate(chunks):
            fname = TEMP_PATH + tmp_filename + "-{0}".format(i) + ".pcm"
            chunk.export(out_f=fname, format="u16le", parameters=["-acodec", "pcm_s16le"])
            tmp_list.append(tmp_filename + "-{0}".format(i) + ".pcm")

        return tmp_list
    else:
        # конвертируем в PCM
        print "# конвертируем в PCM"
        tmp_filename = uuid.uuid4().__str__()[:6]
        track.export(out_f=TEMP_PATH + tmp_filename + ".pcm", format="u16le", parameters=["-acodec", "pcm_s16le"])
        return [tmp_filename + ".pcm"]


if __name__ == '__main__':

    parts = prepare_audio_file(file=AUDIO_FILE, path=AUDIO_PATH, file_format="mp3")
    print parts

    if len(parts) == 1:
        file_name = parts[0]
        # готовим к отправке файл
        print "# готовим к отправке файл: %s" % TEMP_PATH + file_name
        raw_input()

        # Google speech api

        # Application default credentials provided by env variable
        # GOOGLE_APPLICATION_CREDENTIALS
        credentials = GoogleCredentials.get_application_default().create_scoped(
            ['https://www.googleapis.com/auth/cloud-platform'])
        http = httplib2.Http()
        credentials.authorize(http)

        file_size = os.path.getsize(TEMP_PATH + file_name)
        if file_size*1.4 > 1024*1024:
            print "Файл больше 1Мб, отправляем через Google Cloud Store..."
            store_service = discovery.build("storage", 'v1', credentials=credentials)
            BUCKET = "conversation-parser-speech.appspot.com"

            client = storage.Client()
            bucket = client.get_bucket(BUCKET)
            blob = bucket.blob(file_name)
            blob.upload_from_filename(TEMP_PATH + file_name, content_type="binary/octet-stream")
            print "Файл загружен в Cloud store (%s)" % blob.public_url
            req_content = {"uri": "gs://{0}/{1}".format(BUCKET,file_name)}

        else:
            print "Файл меньше 1Мб, отправляем прямой запрос..."
            file_content = open(TEMP_PATH + file_name, 'rb').read()
            # Base64 encode the binary audio file for inclusion in the request.
            speech_content = base64.b64encode(file_content)
            req_content = {"content": speech_content.decode('UTF-8')}


        """Transcribe the given audio file asynchronously.
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
            file_size = os.path.getsize(TEMP_PATH + file_name)

            chunks.append(open(TEMP_PATH + file_name, "rb").read())

            if file_size*1.4 > 1024*1024:
                print "Файл больше 1Мб, отправляем через Google Cloud Store..."
                store_service = discovery.build("storage", 'v1', credentials=credentials)
                BUCKET = "conversation-parser-speech.appspot.com"

                client = storage.Client()
                bucket = client.get_bucket(BUCKET)
                blob = bucket.blob(file_name)
                blob.upload_from_filename(TEMP_PATH + file_name, content_type="binary/octet-stream")
                print "Файл загружен в Cloud store (%s)" % blob.public_url
                req_content = {"uri": "gs://{0}/{1}".format(BUCKET, file_name)}

            else:
                print "Файл меньше 1Мб, отправляем прямой запрос..."
                file_content = open(TEMP_PATH + file_name, 'rb').read()
                # Base64 encode the binary audio file for inclusion in the request.
                speech_content = base64.b64encode(file_content)
                req_content = {"content": speech_content.decode('UTF-8')}

            context = {"phrases": ['документ', "нотариус", "печать", "электронная подпись", "встреча", "подать", "комплект",
                                   "стоимость", "регистрация", "налоговая", "расчетный", "счет", "привезем", "банк",
                                   "мы", "получим", "паспорт", "копия", "одна", "нас", "диалог", "юрбюро точка ру", "бюро",
                                   "yurburo.ru", "точка ру", "но"]}

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
        # Yandex speechkit
        content_file = open(parts_list[0], 'r')
        content = content_file.read()

        post_body = ""
        chunk_size = 500000

        while len(content) > 0:
            size = min(len(content), chunk_size)
            post_body += hex(size)[2:]
            post_body += '\r\n'
            post_body += content[:size]
            post_body += '\r\n'

            content = content[size:]

        post_body += '0\r\n\r\n'

        content_file.close()


        def body_data_gen(content_file_name=None):
            content_file = open("audio_temp/6a5cba.pcm", 'r')
            content = content_file.read()

            chunk_size = 100000

            while len(content) > 0:
                post_body = b""
                size = min(len(content), chunk_size)
                post_body += b"%s\r\n" % hex(size)[2:]
                post_body += b"%s\r\n" % content[:size]
                content = content[size:]
                yield post_body

            content_file.close()
            post_body = b"0\r\n\r\n"
            yield post_body

        def body_data_gen4(content_file_name=None):
            content_file = open("audio_temp/6a5cba.pcm", 'rb')
            content = content_file.read()
            content_file.close()

            chunk_size = 500000

            while len(content) > 0:
                print "Отправляю часть..."
                size = min(len(content), chunk_size)
                content = content[size:]
                yield "%s\r\n%s\r\n" % (hex(size)[2:], content[:size])

            print "Отправляю завершающую часть..."
            yield "0\r\n\r\n"

        def body_data_gen3(content_file_name=None):
            content_file = open(content_file_name, 'r')
            content = content_file.read()

            post_body = b""
            chunk_size = 500000

            post_body += b"%s\r\n" % hex(chunk_size)[2:]
            post_body += b"%s\r\n" % content[:chunk_size]
            yield post_body

            post_body = b"0\r\n\r\n"
            content_file.close()
            yield post_body

        def body_data_gen2(content_file_name, chunksize=500000, start_from=0, max_count=None):
            count = 0
            for f in [open(content_file_name, 'r')]:
                chunk = f.read(chunksize)
                while chunk:
                    if start_from <= count:
                        if max_count is None or count < start_from + max_count:
                            yield chunk
                    count += 1
                    chunk = f.read(chunksize)
                f.close()

        def read_chunks(content_file_name, chunksize=500000):
            print "Открываю файл: %s" % content_file_name
            result = list()
            for f in [open(content_file_name, 'rb')]:
                chunk = f.read(chunksize)
                while chunk:
                    print "Читаем часть длинной %s" % len(chunk)
                    result.append(chunk)
                    chunk = f.read(chunksize)
                f.close()

            return result

        def body_data_gen5(chunks=None):

            for one in chunks:
                print "Отправляю часть (%s)..." % len(one)
                yield "%s\r\n%s\r\n" % (hex(len(one))[2:], one)
                time.sleep(1)

            print "Завершаю передачу..."
            yield "0\r\n\r\n"

        # формируем запрос
        print "# формируем запрос"
        REQ_UUID = uuid.uuid4().hex
        REQ_TOPIC = "notes"
        REQ_KEY = "e04eec9d-35e2-4bfa-8173-c51f19f5c379"
        REQ_LANG = "ru-RU"
        headers = {"Content-Type": "audio/x-pcm;bit=16;rate=16000", "Transfer-Encoding": "chunked"}
        # headers = {"Content-Type": "audio/x-pcm;bit=16;rate=16000", "Content-Length": len("0")}
        parameters = {"uuid": REQ_UUID, "key": REQ_KEY, "topic": REQ_TOPIC, "lang": REQ_LANG}

        chunks = read_chunks(parts_list[0])

        req = requests.post(url="https://asr.yandex.net/asr_xml", params=parameters, headers=headers,
                            data=body_data_gen5(chunks))

        while True:
            if req.status_code == 200:
                print req.status_code
                print "ok"
                break
            else:
                print req.status_code


        print req.headers
        print req.content
        print req.text
        print req.raw.read(decode_content=True)

        import httplib

        def write_chunk(conn, data):
            print "Отправляем данные (%s)..." % len(data)
            conn.send("%s\r\n" % hex(len(data))[2:])
            conn.send("%s\r\n" % data)

        def dynamically_generate_data(content_file_name, chunksize=600000):
            for f in [open(content_file_name, 'rb')]:
                chunk = f.read(chunksize)
                while chunk:
                    print "Читаем часть длинной %s" % len(chunk)
                    yield chunk
                    chunk = f.read(chunksize)
                f.close()


        conn = httplib.HTTPSConnection(host="asr.yandex.net", port=443)
        url = "asr_xml?key=%s&uuid=%s&topic=%s&lang=%s" % (REQ_KEY, REQ_UUID, REQ_TOPIC, REQ_LANG)
        conn.putrequest('POST', url)
        conn.putheader('Content-Type', 'audio/x-pcm;bit=16;rate=16000')
        conn.putheader('Transfer-Encoding', 'chunked')
        conn.endheaders()

        for new_chunk in read_chunks(parts_list[0]):
            write_chunk(conn, new_chunk)
        conn.send('0\r\n')

        resp = conn.getresponse()
        print(resp.status, resp.reason)
        conn.close()
        """