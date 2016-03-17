#!/usr/bin/python -t
# coding: utf8

"""
Классификация текстов(документов), сообщений и т.д.

1. Содержит модели классификаторов
2. Для каждой модели определены методы загрузки данных из базы, тренировки и извлечения признаков

"""

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
from sklearn.naive_bayes import BernoulliNB, MultinomialNB
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neighbors import NearestCentroid
from sklearn.ensemble import RandomForestClassifier
from sklearn.utils.extmath import density
from sklearn import metrics
from sklearn import svm
import pymorphy2

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

morph = pymorphy2.MorphAnalyzer()


class ClassifierNew(object):
    clf = None
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
        use_hashing = True
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

    def classify(self, data=None):
        """
        Классификация образца классификатором.
        Проверка результата классификации детектором аномалий.
        Если детектор и классификатор определяют образец как аномалию (т.е. - conflict), соглашаемся.
        Если детектор считаем аномалией, а классфикатор нет, возращаем результат детектора.

        :return:
        """

        # Загружаем тренировочные данные
        # Готовим векторизатор
        # Тренируем классификатор
        # Тренируем определитель аномалий

        test = [data.message_title + data.message_text]

        X_test = self.vectorizer.transform(test)

        pred = self.clf.predict(X_test)

        outlier = self.outlier.predict(X_test)

        if self.debug:
            print "Классификация: %s" % pred
            print "Детектор аномалий: %s" % outlier

        if pred[0] == "conflict" and outlier[0] == 1:
            return "normal" + "-1:" + pred[0] + "-" + str(outlier[0])

        if pred[0] == "conflict" and outlier[0] == -1:
            return pred[0] + "-1:" + pred[0] + "-0"

        if pred[0] == "normal" and outlier[0] == -1:
            return pred[0] + "-1:" + pred[0] + "-0"
        
        if pred[0] == "normal" and outlier[0] == 1:
            return pred[0] + "-1:" + pred[0] + "-" + str(outlier[0])

        return None


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
    for s in splitter.split(entry):
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

"""

session = CPO.Session()

resp = session.query(CPO.TrainData).filter(CPO.or_((CPO.TrainData.train_epoch == -1),
                                                   (CPO.TrainData.train_epoch == 0),
                                                   (CPO.TrainData.train_epoch == 0))).all()
train = list()
answer = list()

for one in resp:
    train.append(one.message_title + one.message_text)
    answer.append(one.category)

resp = session.query(CPO.TrainData).filter(CPO.or_((CPO.TrainData.train_epoch == 1),
                                                   (CPO.TrainData.train_epoch == 1))).all()
test = list()
test_answer = list()
test_id = list()
for one in resp:
    test.append(one.message_title + one.message_text)
    test_answer.append(one.category)
    test_id.append(one.id)

#test = train
#test_answer = answer

print "Count Train: %s, Test: %s" % (len(train), len(test))
categories = ["conflict", "normal"]
use_hashing = False


t0 = time()
if use_hashing:
    vectorizer = HashingVectorizer(stop_words=STOP_WORDS, analyzer='word', non_negative=True, n_features=60000,
                                   tokenizer=specfeatures)
    X_train = vectorizer.transform(train)
else:
    vectorizer = TfidfVectorizer(sublinear_tf=True, max_df=1, stop_words=STOP_WORDS, analyzer='word',
                                 tokenizer=specfeatures)
    X_train = vectorizer.fit_transform(train)

duration = time() - t0
print "TRAIN"
print("done in %fs at %0.3fText/s" % (duration, len(train) / duration))
print("n_samples: %d, n_features: %d" % X_train.shape)
print()

print("Extracting features from the test data using the same vectorizer")
t0 = time()
X_test = vectorizer.transform(test)
duration = time() - t0
print "TEST"
print("done in %fs at %0.3f Text/s" % (duration, len(test) / duration))
print("n_samples: %d, n_features: %d" % X_test.shape)
print()

if use_hashing:
    feature_names = None
else:
    feature_names = vectorizer.get_feature_names()

select_chi2 = 0
if select_chi2:
    print("Extracting %d best features by a chi-squared test" % select_chi2)
    t0 = time()
    ch2 = SelectKBest(chi2, k=select_chi2)
    X_train = ch2.fit_transform(X_train, answer)
    X_test = ch2.transform(X_test)
    if feature_names:
        # keep selected feature names
        feature_names = [feature_names[i] for i
                           in ch2.get_support(indices=True)]
    print("done in %fs" % (time() - t0))
    print ""

if feature_names:
    feature_names = np.asarray(feature_names)


def trim(s):

    return s if len(s) <= 80 else s[:77] + "..."


# Benchmark classifiers
def benchmark(clf):
    print('_' * 80)
    print("Training: ")
    print(clf)
    t0 = time()
    clf.fit(X_train, answer)
    train_time = time() - t0
    print("train time: %0.3fs" % train_time)

    t0 = time()
    pred = clf.predict(X_test)
    test_time = time() - t0
    print("test time:  %0.3fs" % test_time)

    score = metrics.accuracy_score(test_answer, pred)
    print("accuracy:   %0.3f" % score)

    if hasattr(clf, 'coef_'):
        print("dimensionality: %d" % clf.coef_.shape[1])
        print("density: %f" % density(clf.coef_))

        if False and feature_names is not None:
            print("top 10 keywords per class:")
            for i, category in enumerate(categories):
                top10 = np.argsort(clf.coef_[i])[-10:]
                print(trim("%s: %s"
                      % (category, " ".join(feature_names[top10]))))
        print ""

    print("classification report:")
    print(metrics.classification_report(test_answer, pred, target_names=categories))

    print("confusion matrix:")
    print(metrics.confusion_matrix(test_answer, pred))

    print()
    clf_descr = str(clf).split('(')[0]

    raw_input()
    return clf_descr, score, train_time, test_time, pred


results = []
for clf, name in (
        #(RidgeClassifier(tol=1e-2, solver="sag"), "Ridge Classifier"),
        (Perceptron(n_iter=60, class_weight="balanced"), "Perceptron"),
        #(PassiveAggressiveClassifier(n_iter=50), "Passive-Aggressive"),

        #(KNeighborsClassifier(n_neighbors=5, algorithm="ball_tree"), "kNN"),
        # (RandomForestClassifier(n_estimators=10), "Random forest"),

    ):

    print('=' * 80)
    print(name)
    results.append(benchmark(clf))

for penalty in ["l2", "l1"]:
    continue
    print('=' * 80)
    print("%s penalty" % penalty.upper())
    # Train Liblinear model
    results.append(benchmark(LinearSVC(loss='squared_hinge', penalty=penalty, class_weight="balanced",
                                            dual=False, tol=1e-3)))

    # Train SGD model
    #results.append(benchmark(SGDClassifier(alpha=.0001, n_iter=50,
    #                                       penalty=penalty)))

# Train SGD with Elastic Net penalty
#print('=' * 80)
#print("Elastic-Net penalty")
#results.append(benchmark(SGDClassifier(alpha=.0001, n_iter=50,
#                                       penalty="elasticnet")))

print('=' * 80)
print("SGD")
results.append(benchmark(SGDClassifier(alpha=.0001, n_iter=70, penalty="l2", loss="squared_hinge",
                                       class_weight="balanced")))


# Train NearestCentroid without threshold
#print('=' * 80)
#print("NearestCentroid (aka Rocchio classifier)")
#results.append(benchmark(NearestCentroid()))

# Train sparse Naive Bayes classifiers
print('=' * 80)
print("Naive Bayes")
results.append(benchmark(MultinomialNB(alpha=.01)))
results.append(benchmark(BernoulliNB(alpha=.01)))

#for i in range(0, len(results[0][4])):
#    if results[0][4][i] != results[1][4][i]:
#        print test_id[i], "-", results[0][4][i], " : ", results[1][4][i], " - ", test_answer[i]

#print('=' * 80)
#print("LinearSVC with L1-based feature selection")
# The smaller C, the stronger the regularization.
# The more regularization, the more sparsity.
#results.append(benchmark(Pipeline([
#  ('feature_selection', LinearSVC(penalty="l1", dual=False, tol=1e-3)),
#  ('classification', LinearSVC(class_weight="balanced"))
#])))


for i in range(0, len(test)):
    if test_answer[i] == "conflict":
        print test_id[i], " - ", test_answer[i]
        for j in range(0, len(results)):
            print "\t", results[j][4][i]

session.close()
"""