#!/usr/bin/python -t
# coding: utf8

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])

import datetime
from configuration import *
import objects as CPO
import uuid
import requests

from pydub import AudioSegment, playback
import pydub.silence

AUDIO_PATH = "/home/sergey/Downloads/"
TEMP_PATH = "audio_temp/"
AUDIO_FILE = "2015_12_21+10-45-34+zavladenie+Outgoing+to+sergey.spevak+.mp3"
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

    if SPLIT_SILENCE:
        # Режем по паузам
        chunks = pydub.silence.split_on_silence(track,
                                                # must be silent for at least half a second
                                                min_silence_len=500,
                                                # consider it silent if quieter than -16 dBFS
                                                silence_thresh=-13,
                                                keep_silence=100
                                                )

        print "Кол-во отрезков:", len(chunks)

        # конвертируем в PCM
        tmp_filename = uuid.uuid4().__str__()[:6]
        tmp_list = list()
        for i, chunk in enumerate(chunks):
            fname = TEMP_PATH + tmp_filename + "-{0}".format(i) + ".pcm"
            chunk.export(out_f=fname, format="u16le", parameters=["-acodec", "pcm_s16le"])
            tmp_list.append(fname)

        return tmp_list
    else:
        # конвертируем в PCM
        print "# конвертируем в PCM"
        tmp_filename = uuid.uuid4().__str__()[:6]
        fname = TEMP_PATH + tmp_filename + ".pcm"
        track.export(out_f=fname, format="u16le", parameters=["-acodec", "pcm_s16le"])
        return [fname]


if __name__ == '__main__':

    parts_list = prepare_audio_file(file=AUDIO_FILE, path=AUDIO_PATH, file_format="mp3")

    # готовим к отправке файл
    print "# готовим к отправке файл: %s" % parts_list[0]
    if len(parts_list) == 1:
        """
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
        """

        def body_data_gen():
            content_file = open("audio_temp/6a5cba.pcm", 'r')
            content = content_file.read()

            post_body = b""
            chunk_size = 500000

            while len(content) > 0:
                size = min(len(content), chunk_size)
                post_body += b"%s\r\n" % hex(size)[2:]
                post_body += b"%s\r\n" % content[:size]
                yield post_body
                content = content[size:]
                post_body = b""

            post_body += b"0\r\n\r\n"
            content_file.close()
            yield post_body

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


        # формируем запрос
        print "# формируем запрос"
        REQ_UUID = uuid.uuid4().hex
        REQ_TOPIC = "notes"
        REQ_KEY = "e04eec9d-35e2-4bfa-8173-c51f19f5c379"
        REQ_LANG = "ru-RU"
        headers = {"Content-Type": "audio/x-pcm;bit=16;rate=16000", "Transfer-Encoding": "chunked"}
        # headers = {"Content-Type": "audio/x-pcm;bit=16;rate=16000", "Content-Length": len("0")}
        parameters = {"uuid": REQ_UUID, "key": REQ_KEY, "topic": REQ_TOPIC, "lang": REQ_LANG}
        data = "0\r\n\r\n"

        req = requests.post(url="https://asr.yandex.net/asr_xml", params=parameters, headers=headers,
                            data=body_data_gen3(parts_list[0]))

        while True:
            if req.status_code == 200:
                print req.status_code
                print "ok"
                break
            else:
                print req.status_code


        print req.headers
        print req.text
        print req.status_code
