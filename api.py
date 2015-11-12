# -*- coding: utf-8 -*-


"""

"""
import sys
reload(sys)
sys.setdefaultencoding("utf-8")

from configuration import *
from objects import *
import cherrypy
from bs4 import BeautifulSoup
from mako.lookup import TemplateLookup


__author__ = 'sergey'

lookup = TemplateLookup(directories=["./templates"], output_encoding="utf-8",
                        input_encoding="utf-8", encoding_errors="replace")

class ShowNotification(object):

    def _cp_dispatch(self, vpath):
        """
        Обработка REST URL
        """
        print "ShowNotification"
        print vpath
        return self

    @cherrypy.expose
    def index(self, error=None):
        print "Show Notification class"
        print str(error)
        return str(error)


class UserTrain(object):
    def _cp_dispatch(self, vpath):
        """
        Обработка REST URL
        """
        print "UserTrain"
        print vpath
        return self

    @cherrypy.expose
    def index(self, uuid=None, category=None):
        if uuid and category:
            # 1. записать указанный емайл и категорию в пользовательские тренировочные данные
            # 2. Пометить в таблице train_api ответ.
            try:
                status = set_user_train_data(uuid, category)
            except Exception as e:
                print str(e)
                return ShowNotification().index("Произошла внутренняя ошибка.")

        return status[1]


class API(object):

    def _cp_dispatch(self, vpath):
        """
        Обработка REST URL
        """
        print len(vpath)
        print vpath

        if len(vpath) == 3 and vpath[0] == "message":
            cherrypy.request.params['uuid'] = vpath[1]
            cherrypy.request.params['category'] = vpath[2]
            print "TRUE."
            return UserTrain()
        else:
            print "FALSE. PATH : %s" % (vpath)
            cherrypy.request.params['error'] = "Неверный адрес."
            return ShowNotification()

        return []

    @cherrypy.expose
    def index(self):
        return ShowNotification().index("Неверный адрес api.")



class Root(object):

    api = API()

    @cherrypy.expose
    def index(self):
        tmpl = lookup.get_template("index.html")

        return tmpl.render()

    @cherrypy.expose
    def landing(self, customer_email=None, customer_phone=None):
        if not customer_email:
            customer_email = "не указан"
        if not customer_phone or customer_phone == "+7":
            customer_phone = "не указан"

        try:
            landing_customer_contacts(customer_email, customer_phone, cherrypy.request.headers)
        except Exception as e:
            print "Ошибка при попытке отправить контакты с лендинга. %s " % str(e)

        print customer_email, customer_phone,  cherrypy.request.headers

        raise cherrypy.HTTPRedirect("/")


cherrypy.config.update("server.config")

if __name__ == '__main__':
    cherrypy.quickstart(Root(), '/', "app.config")
