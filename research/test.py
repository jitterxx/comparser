#!/usr/bin/python -t
# coding: utf8

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['/home/sergey/dev/conflict analyser'])

import objects as CPO
from configuration import *

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
from sklearn.feature_selection import SelectFromModel
from sklearn.ensemble import ExtraTreesClassifier
import test_func

import pymorphy2
morph = pymorphy2.MorphAnalyzer()

session = CPO.Session()

resp = session.query(CPO.TrainData).filter(CPO.or_((CPO.TrainData.train_epoch == -1),
                                                   (CPO.TrainData.train_epoch == 0),
                                                   (CPO.TrainData.train_epoch == 1))).all()
train = list()
answer = list()

for one in resp:
    train.append(one)
    answer.append(one.category)

resp = session.query(CPO.UserTrainData).all()
test = list()
test_answer = list()
test_id = list()
for one in resp:
    clear = session.query(CPO.Msg).filter(CPO.Msg.message_id == one.message_id).one_or_none()
    if clear:
        test.append(clear)
    else:
        test.append(one)
    test_answer.append(one.category)
    test_id.append(one.id)

#test = train
#test_answer = answer

print "Count Train: %s, Test: %s" % (len(train), len(test))
categories = ["conflict", "normal"]
use_hashing = True


t0 = time()
if use_hashing:
    vectorizer = HashingVectorizer(stop_words=STOP_WORDS, analyzer='word', non_negative=True, n_features=60000,
                                   tokenizer=test_func.mytoken, preprocessor=test_func.specfeatures_new)
    #vectorizer = HashingVectorizer(stop_words=STOP_WORDS, non_negative=True, n_features=60000)

    X_train = vectorizer.transform(train)
else:
    vectorizer = TfidfVectorizer(sublinear_tf=True, max_df=0.5, stop_words=STOP_WORDS, analyzer='word',
                                 tokenizer=test_func.mytoken, preprocessor=test_func.specfeatures_new,
                                 use_idf=True, norm="l1")
    # vectorizer = TfidfVectorizer(max_df=0.75, max_features=5000, use_idf=False, norm="l1")

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
    """Trim string to fit on terminal (assuming 80-column display)"""
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

from sklearn.svm import SVC

results = []
for clf, name in (
        # (RidgeClassifier(tol=1e-2, solver="sag"), "Ridge Classifier"),
        (Perceptron(n_iter=500, class_weight="balanced", alpha=1e-06, penalty="l2"), "Perceptron"),
        # (PassiveAggressiveClassifier(n_iter=50), "Passive-Aggressive"),
        # (SVC(C=0.01, kernel="rbf", class_weight="balanced"), "SVC"),
        # (KNeighborsClassifier(n_neighbors=5, algorithm="ball_tree"), "kNN"),
        # (RandomForestClassifier(n_estimators=10), "Random forest"),

    ):

    print('=' * 80)
    print(name)
    results.append(benchmark(clf))

for penalty in ["l1"]:
    continue
    #print('=' * 80)
    #print("%s penalty" % penalty.upper())
    # Train Liblinear model
    #results.append(benchmark(LinearSVC(loss='squared_hinge', penalty=penalty, class_weight="balanced",
    #                                        dual=False, tol=1e-3)))

    # Train SGD model
    # results.append(benchmark(SGDClassifier(alpha=.0001, n_iter=50,
    #                                        penalty=penalty)))

# Train SGD with Elastic Net penalty
# print('=' * 80)
# print("Elastic-Net penalty")
# results.append(benchmark(SGDClassifier(alpha=.0001, n_iter=50,
#                                        penalty="elasticnet")))

#print('=' * 80)
#print("SGD")
#results.append(benchmark(SGDClassifier(alpha=.0001, n_iter=70, penalty="l2", loss="squared_hinge",
#                                       class_weight="balanced")))


# Train NearestCentroid without threshold
#print('=' * 80)
#print("NearestCentroid (aka Rocchio classifier)")
#results.append(benchmark(NearestCentroid()))

# Train sparse Naive Bayes classifiers
# print('=' * 80)
# print("Naive Bayes")
# results.append(benchmark(MultinomialNB(alpha=.01)))
# results.append(benchmark(BernoulliNB(alpha=.01)))

#for i in range(0, len(results[0][4])):
#    if results[0][4][i] != results[1][4][i]:
#        print test_id[i], "-", results[0][4][i], " : ", results[1][4][i], " - ", test_answer[i]

print('=' * 80)
print("CLASSIFY with feature selection")
# The smaller C, the stronger the regularization.
# The more regularization, the more sparsity.
results.append(benchmark(Pipeline([
  ('feature_selection', SelectFromModel(LinearSVC(penalty="l2", dual=False, tol=1e-3, class_weight="balanced"))),
  # ('feature_selection', SelectFromModel(Perceptron(n_iter=70, class_weight="balanced", alpha=1e-06, penalty="l2"))),
  # ('feature_selection', SelectFromModel(ExtraTreesClassifier(n_estimators=20, random_state=0, class_weight="balanced"))),
  # ('classification', SGDClassifier(alpha=.0001, n_iter=70, penalty="l2", loss="squared_hinge", class_weight="balanced"))
  # ('classification', LinearSVC(class_weight="balanced"))
  ('classification', Perceptron(n_iter=50, class_weight="balanced", alpha=1e-06, penalty="l1"))
])))

results.append(benchmark(Pipeline([
  # ('feature_selection', SelectFromModel(LinearSVC(penalty="l1", dual=False, tol=1e-3, class_weight="balanced"))),
  # ('feature_selection', SelectFromModel(Perceptron(n_iter=70, class_weight="balanced", alpha=1e-06, penalty="l2"))),
  ('feature_selection', SelectFromModel(ExtraTreesClassifier(n_estimators=15, random_state=0, class_weight="balanced"))),
  # ('classification', SGDClassifier(alpha=.0001, n_iter=70, penalty="l2", loss="squared_hinge", class_weight="balanced"))
  ('classification', LinearSVC(penalty="l2", dual=False, tol=1e-3, class_weight="balanced"))
  # ('classification', Perceptron(n_iter=50, class_weight="balanced", alpha=1e-06, penalty="l2"))
])))

all_res = list()
for i in range(0, len(test)):
    all_res.append(0)
    # идем по всем рузультатам складываем оценки и считаем среднее
    for j in range(0, len(results)):
        if results[j][4][i] == "normal":
            all_res[i] += 1
    print test_id[i], " - ", test_answer[i]
    print "Взвешенная оценка (%s классфикаторов): %s" % (len(results), float(all_res[i])/len(results))
    for j in range(0, len(results)):
        print "\t", results[j][4][i]

    raw_input()

    #if test_answer[i] == "conflict":
    #    print test_id[i], " - ", test_answer[i]
    #    for j in range(0, len(results)):
    #        print "\t", results[j][4][i]

session.close()