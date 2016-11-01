#!/usr/bin/python -t
# coding: utf8

"""
Классификация текстов(документов), сообщений и т.д.

1. Содержит модели классификаторов
2. Для каждой модели определены методы загрузки данных из базы, тренировки и извлечения признаков

"""

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])

import re
import os
import json




train = list()
answer = list()
count = 0

class msg_data(object):
    message_text = ''
    message_title = ''
    category = ''
    in_reply_to = ''
    references = ''
    recipients = ''
    cc_recipients = ''


for current_cat in ['normal', 'conflict']:
    file_list = list()
    for root, dirs, f_list in os.walk("vipct_train_data/{}/".format(current_cat)):
        for oo in f_list:
            if 'class.nfo' != oo:
                file_list.append('vipct_train_data/{}/{}'.format(current_cat, oo))

    print("Готовим категорию: {} - {} сообщений".format(current_cat, len(file_list)))

    for ff in file_list:
        f = open(ff, 'r')
        ss = f.read()
        one = json.loads(ss)
        new = msg_data()
        new.message_text = one['message_text']
        new.message_title = one['message_title']
        new.category = one['category']
        new.in_reply_to = one['in_reply_to']
        new.references = one['references']
        new.recipients = one['recipients']
        new.cc_recipients = one['cc_recipients']

        train.append(new)
        answer.append(one['category'])

print "Count Train: %s" % len(train)