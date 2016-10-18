# -*- coding: utf-8 -*-


"""
    Скрипт подготовки данных для обучения нейронной сети клиента.
    Выгружает данные в виде текстовых файлов, подготовленных для тренировки сети в DeepDetect.
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

__author__ = 'sergey'


session = CPO.Session()
PATH = "./{}_train_data".format(sys.argv[1])

cats = CPO.GetCategory().keys()

limit = 20

try:
    resp = session.query(CPO.TrainData.category, func.count(CPO.TrainData.category)).\
        group_by(CPO.TrainData.category).\
        all()
except Exception as e:
    print(str(e))
    raise e
else:
    cat_min = 100000
    for cat, count in resp:
        if int(count) < cat_min:
            cat_min = int(count)
    if cat_min != 0:
        limit = cat_min
        print("Будет сформирована выборка из - {} примеров в каждой категории.".format(cat_min))
    else:
        print("Недостаточно данных для формирования обучающей выборки. В одной из категорий - {} примеров".format(cat_min))
        exit()

exit()


for current_cat in cats:
    print("Готовим категорию: {}".format(current_cat))
    try:
        count = session.query(CPO.TrainData).filter(CPO.TrainData.category == current_cat).limit(limit).count()

        resp = session.query(CPO.TrainData).filter(CPO.TrainData.category == current_cat).limit(limit)
    except Exception as e:
        print(str(e))
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
            f.write(one.message_title)
            f.write("\n\n")
            f.write(one.message_text)
            f.write("\n\n")
            f.close()

        print("Записываем информация о категории в class.nfo")
        f = file("{}/{}".format(CAT_PATH, "class.nfo"), "w")
        f.write("Name: {}\n".format(current_cat))
        f.write("Size: {}\n".format(count))
        f.close()

session.close()

