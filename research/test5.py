#!/usr/bin/python -t
# coding: utf8

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])

import datetime
from configuration import *
import objects as CPO
import pydub
from pydub import silence, playback

AUDIO_PATH = "/home/sergey/Downloads/"
AUDIO_FILE = "2015_12_21+10-45-34+zavladenie+Outgoing+to+sergey.spevak+.mp3"

track = pydub.AudioSegment.from_file(file=AUDIO_PATH + AUDIO_FILE, format="mp3")

mono_channels = track.split_to_mono()

# Выравниваем громкость на каналах
for i in range(0, len(mono_channels)):
    print mono_channels[i].max_dBFS
    print mono_channels[i].rms
    mono_channels[i] = mono_channels[i].apply_gain(-mono_channels[i].max_dBFS)

track = mono_channels[0].overlay(mono_channels[1])


chunks = silence.split_on_silence(track,
                                        # must be silent for at least half a second
                                        min_silence_len=450,
                                        # consider it silent if quieter than -16 dBFS
                                        silence_thresh=-45,
                                        keep_silence=200
                                        )

print "Кол-во отрезков:", len(chunks)
for i in chunks:
    playback.play(i)
    raw_input()

print "Позиции отрезков с тишиной:"
for one in silence.detect_nonsilent(track, min_silence_len=300, silence_thresh=-40):
    print "Отрезок с {0} по {1} секунды".format(one[0]/1000.0, one[1]/1000.0)
