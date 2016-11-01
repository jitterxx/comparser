# -*- coding: utf-8 -*-


"""
    Скрипт подготовки данных для обучения нейронной сети .
    Выгружает данные в виде текстовых файлов, один файл - один пример.
    Данные внутри примера выгружены в формате - JSON.
    Обучение происходит на отдельной машине с достаточным количеством RAM и CPU.
"""


import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])


import objects as CPO
from sqlalchemy import func
import re
import os
import uuid
import shutil
import json

__author__ = 'sergey'


# Инициализация переменных и констант
try:
    CPO.initial_configuration()
except Exception as e:
    print("Ошибка чтения настроек CPO.initial_configuration(). {}".format(str(e)))
    raise e


PATH = "{}/{}_train_data".format(sys.argv[2], sys.argv[1])

cats = CPO.GetCategory().keys()

train_data_ready = False

session = CPO.Session()

for current_cat in cats:
    print("Готовим категорию: {}".format(current_cat))
    try:
        count = session.query(CPO.UserTrainData).filter(CPO.UserTrainData.category == current_cat).count()

        resp = session.query(CPO.UserTrainData, CPO.Msg).\
            join(CPO.Msg, CPO.Msg.message_id == CPO.UserTrainData.message_id).\
            filter(CPO.UserTrainData.category == current_cat).all()

        count2 = session.query(CPO.TrainData).filter(CPO.TrainData.category == current_cat,
                                                     CPO.TrainData.train_epoch != 0).count()

        resp2 = session.query(CPO.TrainData, CPO.Msg).\
            join(CPO.Msg, CPO.Msg.message_id == CPO.TrainData.message_id).\
            filter(CPO.TrainData.category == current_cat,
                   CPO.TrainData.train_epoch != 0).all()

    except Exception as e:
        print(str(e))
        train_data_ready = False
        session.close()
        raise e
    else:
        print("{} - сообщений".format(count + count2))
        CAT_PATH = "{}/{}".format(PATH, current_cat)

        if os.path.exists(CAT_PATH):
            print("Удаляем каталог и старые данные")
            shutil.rmtree(CAT_PATH)

        print("Создаем новый каталог: {}".format(CAT_PATH))
        os.makedirs(CAT_PATH)
        for one, two in resp:
            msg_obj = dict()
            msg_obj['message_id'] = one.message_id
            msg_obj['sender'] = one.sender
            msg_obj['sender_name'] = one.sender_name
            msg_obj['recipients'] = one.recipients
            msg_obj['recipients_name'] = one.recipients_name
            msg_obj['cc_recipients'] = one.cc_recipients
            msg_obj['cc_recipients_name'] = one.cc_recipients_name
            msg_obj['message_title'] = one.message_title
            msg_obj['message_text'] = one.message_text
            msg_obj['orig_date'] = one.orig_date.__str__()
            msg_obj['create_date'] = one.create_date.__str__()
            msg_obj['category'] = one.category
            msg_obj['train_epoch'] = one.train_epoch
            msg_obj['in_reply_to'] = two.in_reply_to
            msg_obj['references'] = two.references

            filename = uuid.uuid4().__str__()
            f = file("{}/{}".format(CAT_PATH, filename), "w")
            f.write(json.dumps(msg_obj))
            f.write("\n\n")
            f.close()

        for one, two in resp2:
            msg_obj = dict()
            msg_obj['message_id'] = one.message_id
            msg_obj['sender'] = one.sender
            msg_obj['sender_name'] = one.sender_name
            msg_obj['recipients'] = one.recipients
            msg_obj['recipients_name'] = one.recipients_name
            msg_obj['cc_recipients'] = one.cc_recipients
            msg_obj['cc_recipients_name'] = one.cc_recipients_name
            msg_obj['message_title'] = one.message_title
            msg_obj['message_text'] = one.message_text
            msg_obj['orig_date'] = one.orig_date.__str__()
            msg_obj['create_date'] = one.create_date.__str__()
            msg_obj['category'] = one.category
            msg_obj['train_epoch'] = one.train_epoch
            msg_obj['in_reply_to'] = two.in_reply_to
            msg_obj['references'] = two.references

            filename = uuid.uuid4().__str__()
            f = file("{}/{}".format(CAT_PATH, filename), "w")
            f.write(json.dumps(msg_obj))
            f.write("\n\n")
            f.close()

        print("Записываем информация о категории в class.nfo")
        f = file("{}/{}".format(CAT_PATH, "class.nfo"), "w")
        f.write("Name: {}\n".format(current_cat))
        f.write("Size: {}\n".format(int(count + count2)))
        f.close()



session.close()


