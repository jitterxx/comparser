# -*- coding: utf-8 -*-


"""
    Скрипт подготовки дополнительных данных для обучения нейронной сети клиента.
    Выгружает данные в виде текстовых файлов, подготовленных для тренировки сети в DeepDetect.
    Третий параметр - категория из которой надо выгружать данные. Лимит - 50 образцов.
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

__author__ = 'sergey'


# Инициализация переменных и констант
try:
    CPO.initial_configuration()
except Exception as e:
    print("Ошибка чтения настроек CPO.initial_configuration(). {}".format(str(e)))
    raise e


PATH = "{}/{}_train_data".format(sys.argv[2], sys.argv[1])


session = CPO.Session()

cats = CPO.GetCategory().keys()

for current_cat in cats:
    print("Готовим категорию: {}".format(current_cat))
    try:
        count = session.query(CPO.TrainData).filter(CPO.TrainData.category == current_cat).count()

        resp = session.query(CPO.TrainData).filter(CPO.TrainData.category == current_cat).all()
    except Exception as e:
        print(str(e))
        train_data_ready = False
        raise e
    else:
        print("{} - сообщений".format(count))
        CAT_PATH = "{}/{}".format(PATH, current_cat)

        if os.path.exists(CAT_PATH):
            print("Удаляем каталог и старые данные")
            shutil.rmtree(CAT_PATH)

        print("Создаем новый каталог: {}".format(CAT_PATH))
        os.makedirs(CAT_PATH)
        for one in resp:
            filename = uuid.uuid4().__str__()
            f = file("{}/{}".format(CAT_PATH, filename), "w")
            f.write(one.message_text)
            f.write(one.message_title)
            f.close()

        print("Записываем информация о категории в class.nfo")
        f = file("{}/{}".format(CAT_PATH, "class.nfo"), "w")
        f.write("Name: {}\n".format(current_cat))
        f.write("Size: {}\n".format(count))
        f.close()

    finally:
        session.close()


