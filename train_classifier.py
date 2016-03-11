#!/usr/bin/python -t
# coding: utf8

"""
Фильтрация и классификация текстов(документов), сообщений и т.д.

"""
from operator import itemgetter
import re
import argparse
import mod_classifier as cl
import mysql.connector
import math
from configuration import *
import objects as CPO
import sys
reload(sys)
sys.setdefaultencoding("utf-8")


try:
    # Создаем объект классификатора
    f_cl = cl.fisherclassifier(cl.specfeatures)

    # Подключаем данные обучения
    f_cl.setdb(db_name)

    f_cl.loaddb()
    cat = f_cl.category_code
    minimums = f_cl.minimums

    for i in cat.keys():
        print "Категория: ", cat[i], "(", i, ") : ", minimums[i]

    # Обучаем модель на тестовых данных из базы
    f_cl.sql_train()

    # Добучаем модель на корректированных данных от пользователей
    f_cl.user_train()

    # Закрываем соединение с БД
    f_cl.unsetdb()
except Exception as e:
    print "Произошла ошибка при обучении классификатора. %s" % str(e)
else:
    # Копируем данные обучения текущей эпохи в train_data из user_train_data и чистим последнюю.
    session = CPO.Session()
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











