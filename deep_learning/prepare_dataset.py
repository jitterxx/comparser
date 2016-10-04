# -*- coding: utf-8 -*-


"""

"""
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])


import objects as CPO
import cherrypy
import re
import os
import uuid
import shutil

__author__ = 'sergey'


session = CPO.Session()
PATH = "./conparser_data"

cats = CPO.GetCategory().keys()

for current_cat in cats:
    print("Готовим категорию: {}".format(current_cat))
    try:
        count = session.query(CPO.TrainData).filter(CPO.TrainData.category == current_cat).count()

        resp = session.query(CPO.TrainData).filter(CPO.TrainData.category == current_cat).all()
    except Exception as e:
        print(str(e))
    else:
        print(count)
        CAT_PATH = "{}/{}".format(PATH, current_cat)

        if os.path.exists(CAT_PATH):
            print("Удаляем каталог и старые данные")
            shutil.rmtree(CAT_PATH)

        print("Создаем новый...")
        os.makedirs(CAT_PATH)
        for one in resp:
            filename = uuid.uuid4().__str__()
            f = file("{}/{}".format(CAT_PATH, filename), "w")
            f.write(one.message_title)
            f.write("\n\n")
            f.write(one.message_text)
            f.write("\n\n")
            f.close()

        print("Информация о категории...")
        f = file("{}/{}".format(CAT_PATH, "class.nfo"), "w")
        f.write("Name: {}\n".format(current_cat))
        f.write("Size: {}\n".format(count))
        f.close()


session.close()

