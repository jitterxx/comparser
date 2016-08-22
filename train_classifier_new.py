#!/usr/bin/python -t
# coding: utf8

"""
Фильтрация и классификация текстов(документов), сообщений и т.д.

"""
from operator import itemgetter
import re
import argparse
import math
from configuration import *
import objects as CPO
from sqlalchemy import func
import sys
reload(sys)
sys.setdefaultencoding("utf-8")



session = CPO.Session()
# Проверяем что данные для обучения удовлетворяют условиям.
# В каждой категории больше 10 примеров

train_data_ready = False

cats = CPO.GetCategory().keys()

try:
    resp = session.query(func.count(CPO.UserTrainData.category), CPO.UserTrainData.category).\
        group_by(CPO.UserTrainData.category).\
        all()
except Exception as e:
    print("Ошибка получения данных из UserTrainData. {}".format(str(e)))
    raise e
else:
    for count, cat in resp:
        print("Проверяем категорию - {}, количество примеров - {}".format(cat, count))
        if cat in cats and count >= 10:
            train_data_ready = True
            print("\t ок")
        elif cat in cats and count < 10:
            train_data_ready = False
            print("\t Недостаточно примеров")
        else:
            train_data_ready = False

exit()


if train_data_ready:
    print("# Примеров для работы достаточно. Ошибок не обнаружено. \n Копируем данные...")
    # Копируем данные обучения текущей эпохи в train_data из user_train_data и чистим последнюю.
    try:
        utd = session.query(CPO.UserTrainData).all()
    except Exception as e:
        print "Ошибка при чтении User_train_data. %s" % str(e)
        raise e
    else:
        # переносим записи из user_train_data в train_data
        for one in utd:
            new = CPO.TrainData()
            new.message_id = one.message_id
            new.sender = one.sender
            new.sender_name = one.sender_name
            new.recipients = one.recipients
            new.recipients_name = one.recipients_name
            new.cc_recipients = one.cc_recipients
            new.cc_recipients_name = one.cc_recipients_name
            new.message_title = one.message_title
            new.message_text = one.message_text
            new.orig_date = one.orig_date
            new.create_date = one.create_date
            new.category = one.category
            new.train_epoch = one.train_epoch
            try:
                session.add(new)
                session.commit()
            except Exception as e:
                raise e

        # чистим user_train_data
        try:
            for one in utd:
                session.delete(one)
            session.commit()
        except Exception as e:
            raise e

        # Обновляем эпоху
        CPO.update_epoch()
    finally:
        session.close()
else:
    print("# Примеров для работы НЕ достаточно. Добавьте недостающие данные.")