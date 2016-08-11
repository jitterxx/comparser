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



# Google speech api

from googleapiclient import discovery
import httplib2
from oauth2client.client import GoogleCredentials
import base64
import json
from gcloud import storage
import os


# Application default credentials provided by env variable
# GOOGLE_APPLICATION_CREDENTIALS
credentials = GoogleCredentials.get_application_default().create_scoped(
    ['https://www.googleapis.com/auth/cloud-platform'])
http = httplib2.Http()
credentials.authorize(http)



# запоминаем идентификатор запроса на распознавание
name = "2246522785523936395"
print "Проверяем ответ на запрос: {0}".format(name)

# Создаем запрос для проверкаи результата по идентификатору запроса
speech_service = discovery.build('speech', 'v1beta1', http=http)
service_request = speech_service.operations().get(name=name)
sleep_period = 60  # проверяем каждую минуту

while True:
    # Give the server a few seconds to process.
    print('Waiting for server processing...')
    print "Проверка будет сделана через {0} секунд".format(sleep_period)
    time.sleep(sleep_period)

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
    #print unicode(str(alt["alternatives"][0]["transcript"]), "unicode-escape")
    print str(alt["alternatives"][0]["transcript"])


