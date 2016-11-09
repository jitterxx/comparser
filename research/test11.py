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
from configuration import *
import objects as CPO
from sqlalchemy import func

import numpy as np
from time import time
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import Perceptron
from sklearn.naive_bayes import BernoulliNB, MultinomialNB, GaussianNB
from sklearn import svm
from sklearn.model_selection import GridSearchCV
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.externals import joblib


import pymorphy2

morph = pymorphy2.MorphAnalyzer()


def features_extractor_t(entry):
    """ Функция для получения признаков(features) из текста
    Выделяет следующие признаки:
    1. email отправителя
    2. email получателей
    3. Слова из темы сообщения
    4. Все пары слов из темы сообщения
    5. Определенные сочетания из темы сообщения
    6. Слова из текста
    7. Все пары слов из текста
    8. Определенные пары слов из текста (specwords)
    9. Оригинальное время создания сообщения, только HH:MM\

    """
    splitter = re.compile('\\W*', re.UNICODE)
    f = {}

    # Извлечь слова из резюме
    summarywords = list()
    for s in splitter.split(entry.message_text + entry.message_title):
        if (2 < len(s) < 20 and s not in STOP_WORDS) or (s not in STOP_WORDS and s in [u"не", u"ни"]):
            summarywords.append(s)

    # print 'sum words: ',summarywords

    uc = 0
    for i in range(len(summarywords)):
        w = summarywords[i]
        if f.get(w):
            f[w] += 1
        else:
            f[w] = 1

        # Подсчитать количество слов, написанных заглавными буквами
        if w.isupper():
            uc += 1

        # Выделить в качестве признаков пары слов из резюме
        if i < len(summarywords)-1:
            j = i + 1
            word = summarywords[j]
            two_words = ' '.join([w, word])
            # print 'Two words: ',twowords,'\n'
            if f.get(two_words):
                f[two_words] += 1
            else:
                f[two_words] = 1


    return f


def specfeatures_t2(entry):

    tt = ""

    tt += entry.message_title + "\n"
    tt += entry.message_text + "\n"

    return tt


def specfeatures_t(entry):
    """ Функция для получения признаков(features) из текста
    Выделяет следующие признаки:
    1. email отправителя
    2. email получателей
    3. Слова из темы сообщения
    4. Все пары слов из темы сообщения
    5. Определенные сочетания из темы сообщения
    6. Слова из текста
    7. Все пары слов из текста
    8. Определенные пары слов из текста (specwords)
    9. Оригинальное время создания сообщения, только HH:MM\

    """
    import pymorphy2

    morph = pymorphy2.MorphAnalyzer()

    splitter = re.compile('\\W*', re.UNICODE)
    find_n = re.compile('\d+', re.UNICODE)
    find_questions = re.compile('\?{1,5}', re.UNICODE)
    f = dict()
    results = list()
    # print entry.message_text

    # Ищем вопросительные знаки
    quest = find_questions.findall(entry.message_text)
    f['QUESTION'] = len(quest)

    # Извлечь и аннотировать слова из заголовка
    titlewords = list()
    for s in splitter.split(entry.message_title):
        if 2 <= len(s) < 20 and s not in STOP_WORDS:
            titlewords.append(s.lower())

    uc = 0
    for i in range(len(titlewords)):
        w = titlewords[i]
        results.append(w)
        if f.get(w):
            f["title:" + w] += 1
        else:
            f["title:" + w] = 1
        if w.isupper():
            uc += 1

    # UPPERCASE – специальный признак, описывающий степень "крикливости"
    if (len(titlewords)) and (float(uc)/len(titlewords) > 0.1):
        f["title:UPPERCASE"] = 1

    # Извлечь слова из резюме
    summarywords = list()
    for s in splitter.split(entry.message_text):
        if (2 < len(s) < 20 and s not in STOP_WORDS) or (s not in STOP_WORDS and s in [u"не", u"ни"]):
            summarywords.append(s.lower())

    # print 'sum words: ',summarywords

    uc = 0
    for i in range(len(summarywords)):
        w = summarywords[i]
        number = find_n.search(w)
        if number:
            # print "NUMBER : ", number.string
            if f.get("NUMBER"):
                f['NUMBER'] += 1
            else:
                f['NUMBER'] = 1
        else:
            results.append(w)
            if f.get(w):
                f[w] += 1
            else:
                f[w] = 1
            if w.isupper():
                uc += 1

    # Выделить в качестве признаков пары слов из резюме
    for i in range(len(results) - 1):
        twowords = ' '.join([results[i], results[i + 1]])
        # print 'Two words: ',twowords,'\n'
        if f.get(twowords):
            f[twowords] += 1
        else:
            f[twowords] = 1

    # UPPERCASE – специальный признак, описывающий степень "крикливости"
    if (len(summarywords)) and (float(uc)/len(summarywords) > 0.3):
        f['UPPERCASE'] = 1

    # Несколько адресатов или один
    count = 0
    if entry.recipients != "empty" and entry.recipients:
        s = re.split(":", entry.recipients)
        count = len(s)

    if entry.cc_recipients != "empty" and entry.cc_recipients:
        s = re.split(":", entry.cc_recipients)
        count += len(s)

    if count > 1:
        f["MANYRECIPIENTS"] = 1

    # Сколкьо сообщений в цепочке
    count = 0
    if entry.references:
        s = re.split(" ", entry.references)
        count = len(s)

    if count > 3:
        f["MANYREPLY"] = 1

    for one in f.keys():
        print one, " : ", f[one]

    print "*" * 30
    raw_input()

    return f


def mytoken_t(entry):

    return entry




class ClassifierNew(object):
    clf = None
    outlier = None
    vectorizer = None
    scaler = None
    debug = False

    def init_and_fit_files(self, debug=False):
        """
        Инициализация классификаторов и тренировка.
        Чтение данных из файлов.

        :return:
        """

        session = CPO.Session()
        self.debug = debug

        cats = CPO.GetCategory().keys()

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
            print("../deep_learning/new_train_data/{}/".format(current_cat))
            file_list = list()
            for root, dirs, f_list in os.walk("../deep_learning/new_train_data/{}/".format(current_cat)):
                for oo in f_list:
                    if 'class.nfo' != oo:
                        file_list.append('../deep_learning/new_train_data/{}/{}'.format(current_cat, oo))

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

        # Готовим векторизатор
        use_hashing = True
        t0 = time()


        #vectorizer = HashingVectorizer(stop_words=STOP_WORDS, analyzer='word', non_negative=True, n_features=60000,
        #                               tokenizer=mytoken, preprocessor=specfeatures_new)
        vectorizer = HashingVectorizer(stop_words=CPO.STOP_WORDS, analyzer='word', non_negative=True, n_features=10000,
                                       tokenizer=mytoken_t, preprocessor=specfeatures_t,
                                       norm='l1')
        vectorizer = HashingVectorizer(analyzer='word', n_features=10000, non_negative=True, norm='l1',
                                       tokenizer=mytoken_t, preprocessor=specfeatures_t)

        vectorizer = TfidfVectorizer(sublinear_tf=False, max_df=2, stop_words=[], analyzer='word',
                                     preprocessor=specfeatures_t2, lowercase=True)

        vectorizer = TfidfVectorizer(analyzer='char',
                                     preprocessor=specfeatures_t2)


        F_train = vectorizer.fit_transform(train)

        for one in vectorizer.get_feature_names():
            print one

        print len(vectorizer.get_feature_names())





predictor = ClassifierNew()
predictor.init_and_fit_files(debug=True)