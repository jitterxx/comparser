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


import re
from configuration import *
import objects as CPO

import numpy as np
from time import time
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.feature_selection import SelectKBest, chi2
from sklearn.linear_model import RidgeClassifier
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC
from sklearn.linear_model import SGDClassifier
from sklearn.linear_model import Perceptron
from sklearn.linear_model import PassiveAggressiveClassifier
from sklearn.naive_bayes import BernoulliNB, MultinomialNB, GaussianNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neighbors import NearestCentroid
from sklearn.ensemble import RandomForestClassifier
from sklearn.utils.extmath import density
from sklearn import metrics
from sklearn import svm
from sklearn.feature_selection import SelectFromModel
from sklearn.ensemble import ExtraTreesClassifier

import pymorphy2

morph = pymorphy2.MorphAnalyzer()


class ClassifierNew(object):
    clf = None
    clf2 = None
    clf3 = None
    outlier = None
    vectorizer = None
    debug = False

    def init_and_fit(self, debug=False):
        """
        Инициализация классификаторов и определителя аномалий.
        Создание объектов и тренировка.

        :return:
        """

        session = CPO.Session()
        self.debug = debug

        # Загружаем тренировочные данные
        try:
            resp = session.query(CPO.TrainData).all()
        except Exception as e:
            print "Error. Mod_classifier_new. Ошибка загрузки данных для тренировки. %s" % str(e)
            raise e
        else:
            train = list()
            answer = list()
            # Нормальные сообщения тестовые данные
            for one in resp:
                train.append(one.message_title + one.message_text)
                answer.append(one.category)

            if self.debug:
                print "Count Train: %s" % len(train)

        # данные для обучения детектора аномалий
        try:
            resp = session.query(CPO.TrainData).filter(CPO.TrainData.category == "normal").all()
        except Exception as e:
            print "Error. Mod_classifier_new. Ошибка загрузки данных для детектора аномалий. %s" % str(e)
            raise e
        else:
            train_anom = list()
            for one in resp:
                train_anom.append(one.message_title + one.message_text)
            if self.debug:
                print "Count for Anomaly Train: %s" % len(train_anom)

        # Готовим векторизатор
        use_hashing = False
        t0 = time()
        if use_hashing:
            vectorizer = HashingVectorizer(stop_words=STOP_WORDS, analyzer='word', non_negative=True, n_features=60000,
                                           tokenizer=features_extractor)
            X_train = vectorizer.transform(train)
        else:
            vectorizer = TfidfVectorizer(sublinear_tf=True, max_df=1, stop_words=STOP_WORDS, analyzer='word',
                                         tokenizer=features_extractor)
            X_train = vectorizer.fit_transform(train)

        self.vectorizer = vectorizer

        if self.debug:
            duration = time() - t0
            print "TRAIN data"
            print("done in %fs at %0.3fText/s" % (duration, len(train) / duration))
            print("n_samples: %d, n_features: %d" % X_train.shape)
            print "\n"

        t0 = time()
        X_train_anom = vectorizer.transform(train_anom)
        if self.debug:
            duration = time() - t0
            print "Anomaly TRAIN data"
            print("done in %fs at %0.3fText/s" % (duration, len(train_anom) / duration))
            print("n_samples: %d, n_features: %d" % X_train_anom.shape)
            print "\n"

        # Создаем классификатор
        self.clf = Perceptron(n_iter=60, class_weight="balanced")
        t0 = time()
        # Тренируем классификатор
        self.clf.fit(X_train, answer)
        train_time = time() - t0
        if self.debug:
            print("train time: %0.3fs" % train_time)

        # Создаем определитель аномалий
        self.outlier = svm.OneClassSVM(nu=0.5, kernel="poly", gamma=0.1, degree=5)
        t0 = time()
        # Тренируем определитель аномалий
        self.outlier.fit(X_train_anom)
        train_time = time() - t0
        if self.debug:
            print("train time: %0.3fs" % train_time)

    def init_and_fit_new(self, debug=False):
        """
        Инициализация классификаторов.
        Создание объектов и тренировка.

        :return:
        """

        session = CPO.Session()
        self.debug = debug

        # Загружаем тренировочные данные
        try:
            resp = session.query(CPO.TrainData).all()
        except Exception as e:
            print "Error. Mod_classifier_new. Ошибка загрузки данных для тренировки. %s" % str(e)
            raise e
        else:
            if not resp:
                print("# Данных для обучения не найдено.")
                print("# Создаем заглушки для обучения.")
                # Создаем заглушки для обучения
                resp = list()
                cats = CPO.GetCategory().values()
                for i in cats:
                    new = CPO.TrainData()
                    new.message_id = str(i.id)
                    new.message_text = i.category
                    new.category = i.code
                    new.train_epoch = 0
                    resp.append(new)

            # Проводим обучение
            train = list()
            answer = list()
            # Нормальные сообщения тестовые данные
            for one in resp:
                train.append(one)
                answer.append(one.category)

            if self.debug:
                print "Count Train: %s" % len(train)

        # Готовим векторизатор
        use_hashing = True
        t0 = time()
        if use_hashing:
            #vectorizer = HashingVectorizer(stop_words=STOP_WORDS, analyzer='word', non_negative=True, n_features=60000,
            #                               tokenizer=mytoken, preprocessor=specfeatures_new)
            vectorizer = HashingVectorizer(stop_words=STOP_WORDS, analyzer='word', non_negative=True, n_features=60000,
                                           tokenizer=mytoken, preprocessor=specfeatures_new2)

            X_train = vectorizer.transform(train)
        else:
            vectorizer = TfidfVectorizer(sublinear_tf=True, max_df=1, stop_words=STOP_WORDS, analyzer='word',
                                         tokenizer=mytoken, preprocessor=features_extractor2)
            X_train = vectorizer.fit_transform(train)

        self.vectorizer = vectorizer

        if self.debug:
            duration = time() - t0
            print "TRAIN data"
            print("done in %fs at %0.3fText/s" % (duration, len(train) / duration))
            print("n_samples: %d, n_features: %d" % X_train.shape)
            print "\n"

        # Создаем классификаторы
        self.clf = list()

        self.clf.append(Perceptron(n_iter=1000, class_weight="balanced", alpha=1e-06, penalty="l1"))
        self.clf.append(MultinomialNB(alpha=0.1))
        self.clf.append(BernoulliNB(alpha=0.1, binarize=0.0))
        """
        self.clf.append(
            Pipeline([
                ('feature_selection',SelectFromModel(LinearSVC(penalty="l2", dual=False, tol=1e-3,
                                                               class_weight="balanced"))),
                ('classification', Perceptron(n_iter=50, class_weight="balanced", alpha=1e-06, penalty="l1"))
            ])
        )

        self.clf.append(
            Pipeline([
                ('feature_selection', SelectFromModel(ExtraTreesClassifier(n_estimators=15, random_state=0,
                                                                           class_weight="balanced"))),
                ('classification', LinearSVC(penalty="l2", dual=False, tol=1e-3, class_weight="balanced"))
            ])
        )
        """
        t0 = time()
        # Тренируем классификатор
        for one in self.clf:
            one.fit(X_train, answer)
        train_time = time() - t0
        if self.debug:
            print("train time: %0.3fs" % train_time)

    def classify_new2(self, data=None, debug=False):
        """
        Классификация образца классификатором.
        Проверка результата классификации детектором аномалий.
        Если детектор и классификатор определяют образец как аномалию (т.е. - conflict), соглашаемся.
        Если детектор считаем аномалией, а классфикатор нет, возращаем результат детектора.

        :return:
        """

        test = [data]
        X_test = self.vectorizer.transform(test)

        pred = list()
        complex_pred = dict()
        for one in self.clf:
            p = one.predict(X_test)
            pred.append(p)
            if p[0] in complex_pred.keys():
                complex_pred[p[0]] += 1
            else:
                complex_pred[p[0]] = 1

        if self.debug:
            print("Классификация: {}".format(pred))
            print("Комплексный итог: {}".format(complex_pred))

        for one in complex_pred.keys():
            if complex_pred[one] >= 2:
                return one, "{0}-1:{0}-1:{0}-1".format(one)

        """
        if (float(complex_pred) / 3) > 0.5:
            return "normal", "normal-1:" + "-0.5:".join(pred) + "-0.5"
        else:
            return "conflict", "conflict-1:" + "-0.5:".join(pred) + "-0.5"
        """


def features_extractor(entry):
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

    # Подсчитать количество слов, написанных заглавными буквами
    uc = 0
    for i in range(len(summarywords)):
        word = morph.parse(summarywords[i])[0]  # Берем первый вариант разбора
        if "Abbr" in word.tag or "Name" in word.tag or "Surn" in word.tag or "Patr" in word.tag:
            # print "Не используем", word.normal_form
            pass
        else:
            # print "Используем", word.normal_form
            w = word.normal_form
            f[w] = 1
            if w.isupper():
                uc += 1
            # Выделить в качестве признаков пары слов из резюме
            if i < len(summarywords)-1:
                j = i + 1
                word = morph.parse(summarywords[j])[0]  # Берем первый вариант разбора
                if "Abbr" in word.tag or "Name" in word.tag or "Surn" in word.tag or "Patr" in word.tag:
                    # print "Не используем", word.normal_form
                    pass
                else:
                    twowords = ' '.join([w, word.normal_form])
                    # print 'Two words: ',twowords,'\n'
                    f[twowords] = 1

    # UPPERCASE – специальный признак, описывающий степень "крикливости"
    if (len(summarywords)) and (float(uc)/len(summarywords) > 0.3):
        f['UPPERCASE'] = 1

    #for one in f:
    #    print one
    # raw_input()

    return f

def features_extractor2(entry):
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


def specfeatures_new(entry):
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
            titlewords.append(s)

    uc = 0
    for i in range(len(titlewords)):
        word = morph.parse(titlewords[i])[0]  # Берем первый вариант разбора
        if "Abbr" in word.tag or "Name" in word.tag or "Surn" in word.tag or "Patr" in word.tag:
            # print "Не используем", word.normal_form
            pass
        else:
            # print "Используем", word.normal_form
            w = word.normal_form
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
            summarywords.append(s)

    # print 'sum words: ',summarywords

    # Подсчитать количество слов, написанных заглавными буквами
    uc = 0
    for i in range(len(summarywords)):
        word = morph.parse(summarywords[i])[0]  # Берем первый вариант разбора
        if "Abbr" in word.tag or "Name" in word.tag or "Surn" in word.tag or "Patr" in word.tag:
            # print "Не используем", word.normal_form
            pass
        else:
            # print "Используем", word.normal_form
            w = word.normal_form
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
    else:
        f["MANYRECIPIENTS"] = 0

    # Сколкьо сообщений в цепочке
    count = 0
    if entry.references:
        s = re.split(" ", entry.references)
        count = len(s)

    if count > 3:
        f["MANYREPLY"] = 1
    else:
        f["MANYREPLY"] = 0

    #for one in f.keys():
    #    print one, " : ", f[one]

    #print "*" * 30
    #raw_input()

    return f

def specfeatures_new2(entry):
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
            titlewords.append(s)

    uc = 0
    for i in range(len(titlewords)):
        word = morph.parse(titlewords[i])[0]  # Берем первый вариант разбора
        if "Abbr" in word.tag or "Name" in word.tag or "Surn" in word.tag or "Patr" in word.tag:
            # print "Не используем", word.normal_form
            pass
        else:
            # print "Используем", word.normal_form
            w = word.normal_form
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
            summarywords.append(s)

    # print 'sum words: ',summarywords

    # Подсчитать количество слов, написанных заглавными буквами
    uc = 0
    for i in range(len(summarywords)):
        word = morph.parse(summarywords[i])[0]  # Берем первый вариант разбора
        if "Abbr" in word.tag or "Name" in word.tag or "Surn" in word.tag or "Patr" in word.tag:
            # print "Не используем", word.normal_form
            pass
        else:
            # print "Используем", word.normal_form
            w = word.normal_form
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
    else:
        f["MANYRECIPIENTS"] = 0

    # Сколкьо сообщений в цепочке
    count = 0
    if entry.references:
        s = re.split(" ", entry.references)
        count = len(s)

    if count > 3:
        f["MANYREPLY"] = 1
    else:
        f["MANYREPLY"] = 0

    #for one in f.keys():
    #    print one, " : ", f[one]

    #print "*" * 30
    #raw_input()

    return f


def mytoken(entry):

    return entry
