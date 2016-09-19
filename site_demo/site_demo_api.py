# -*- coding: utf-8 -*-


"""

"""
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])

import objects as CPO
import cherrypy
import mod_classifier_new as clf
import re

__author__ = 'sergey'

debug = True


class Root(object):

    @cherrypy.expose
    def classify(self, text=None):
        print("Original text: {}".format(text))
        try:
            # Очистка текста. Оставляем только буквы, пробелы и цифры
            text = re.sub(u"[^а-яА-Я0-9 ]+", u"", text, re.UNICODE).strip()
            print("Cleared text: {}".format(text))

            # Создаем структуру данных для анализа стандартным классификатором
            class new_entry():
                message_text = u""
                message_title = u""
                recipients = u""
                cc_recipients = u""
                references = u""

            text_entry = new_entry()
            text_entry.message_text = text

        except Exception as e:
            if debug:
                print("Ошибка при подготовке текста. {}".format(str(e)))
            cherrypy.response.status = 500
            return "Error. Text prepare error."
        # классификация
        try:
            short_answer, answer = predictor.classify_new2(data=text_entry, debug=debug)
        except Exception as e:
            if debug:
                print("Ошибка классификации текста. {}".format(str(e)))
            cherrypy.response.status = 500
            return "Error. Classification error."

        else:
            if debug:
                print("Категория: {} {}".format(short_answer, answer))
                print('*'*100,'\n')
            cherrypy.response.status = 200
            return short_answer


# Инициализация переменных и констант
try:
    CPO.initial_configuration()
except Exception as e:
    print("Ошибка чтения настроек CPO.initial_configuration(). {}".format(str(e)))
    raise e

# Инициализация классификатора
# Создаем классификатор и инициализируем его
if debug:
    print "Создаем классификатор и инициализируем его"

predictor = clf.ClassifierNew()
predictor.init_and_fit_new(debug=debug)

cherrypy.config.update("site_demo_server.config")

if __name__ == '__main__':
    cherrypy.quickstart(Root(), '/', "site_demo_app.config")
