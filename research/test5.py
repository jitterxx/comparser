#!/usr/bin/python -t
# coding: utf8

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
import mod_classifier_new as clf
import datetime
from configuration import *
import objects as CPO
import sqlalchemy

import uuid

session = CPO.Session()

resp = session.query(CPO.TrainData).all()
train = list()
answer = list()

for one in resp:
    train.append(one)
    answer.append(one.category)

resp = session.query(CPO.Msg).filter(CPO.Msg.isclassified == 0).all()
test = list()
test_answer = list()

print len(resp)
for one in resp:
    test.append(one)



nclf = clf.ClassifierNew()
nclf.init_and_fit_new(debug=True)
for one in test:
    print one.message_text
    print ""
    pred = nclf.classify_new(data=one, debug=True)
    print pred
    print "*" * 30
    raw_input()



session.close()
