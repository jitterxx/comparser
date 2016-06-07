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
from user_agents import parse
from auth import AuthController, require, member_of, name_is, all_of, any_of


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
    def index(self, error=None, url=None):
        tmpl = lookup.get_template("error.html")
        if not url:
            url = "/demo"
        print str(error)
        return tmpl.render(error=error, url=url)


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

        return ShowNotification().index(status[1])


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
            return ShowNotification().index("Неверный адрес.")

        return []

    @cherrypy.expose
    def index(self):
        return ShowNotification().index("Неверный адрес api.")


class ControlCenter(object):

    """
        Центр управления для сотрудников. Вся информация и функции для работы с системой.
        Уведомления, статистика, результаты.
    """
    lookup = TemplateLookup(directories=["./templates/controlcenter"], output_encoding="utf-8",
                            input_encoding="utf-8", encoding_errors="replace")

    auth = AuthController()

    @cherrypy.expose
    @require(member_of("users"))
    def index(self):
        """
        Основная страница центра управления.
        """

        tmpl = lookup.get_template("error.html")

        return tmpl.render(error="Главная страница центра управления")


class Authentication(object):
    """
        Авторизация пользователей.
    """
    pass


class Root(object):
    """
        Основой сервис для запуска API и центров управления
    """

    api = API()
    control_center = ControlCenter()


    @cherrypy.expose
    def index(self, ads=None):
        """
        Основная страница лендинга.

        :param ads: код объявления по которому произошел переход.
        :return:
        """

        tmpl = lookup.get_template("index.html")

        if not ads:
            ads = "organic"
        print "ads :", ads

        try:
            user_agent = parse(cherrypy.request.headers['User-Agent'])
        except Exception as e:
            print "Ошибка определения типа клиента. %s" % str(e)
            user_agent = ""

        return tmpl.render(user_agent=user_agent, ads_code=ads)



cherrypy.config.update("server.config")

if __name__ == '__main__':
    cherrypy.quickstart(Root(), '/', "app.config")
