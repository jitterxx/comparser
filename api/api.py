# -*- coding: utf-8 -*-


"""

"""
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.append('../')

from configuration import *
from objects import *
import cherrypy
from bs4 import BeautifulSoup
from mako.lookup import TemplateLookup


__author__ = 'sergey'

lookup = TemplateLookup(directories=["./templates"], output_encoding="utf-8",
                        input_encoding="utf-8", encoding_errors="replace")


def ShowNotification(error):
    print "Show Notification to WEB."
    return str(error)


class API(object):

    def _cp_dispatch(self, vpath):
        """
        Обработка REST URL
        """

        if len(vpath) == 3 and vpath[0] == "message":
            cherrypy.request.params['uuid'] = vpath[1]
            print "PATH : ", vpath
            return ShowNotification(vpath[1])
        else:
            print "Вывод переадресации : ", vpath
            return ShowNotification("Неверный адрес.")

        return vpath


class Root(object):

    api = API()

    @cherrypy.expose
    def index(self):
        return "index page"


cherrypy.config.update("server.config")

if __name__ == '__main__':
    cherrypy.quickstart(Root(), '/', "app.config")
