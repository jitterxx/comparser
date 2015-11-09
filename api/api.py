# -*- coding: utf-8 -*-


"""

"""
from configuration import *
import sqlalchemy
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
import cherrypy
from bs4 import BeautifulSoup
from mako.lookup import TemplateLookup

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

__author__ = 'sergey'

sql_uri = "mysql://%s:%s@%s/Raw_data?charset=utf8" % (db_user, db_pass, db_host)

Base = declarative_base()
Engine = sqlalchemy.create_engine(sql_uri, pool_size=20)
Session = sqlalchemy.orm.sessionmaker(bind=Engine)

lookup = TemplateLookup(directories=["./templates"], output_encoding="utf-8",
                        input_encoding="utf-8", encoding_errors="replace")


class ClearedMsg(Base):

    __tablename__ = "email_cleared_data"

    id = Column(sqlalchemy.Integer, primary_key=True)
    message_id = Column(sqlalchemy.String(256))
    sender = Column(sqlalchemy.String(256))
    sender_name = Column(sqlalchemy.String(256))
    recipients = Column(sqlalchemy.TEXT())
    recipients_name = Column(sqlalchemy.TEXT())
    cc_recipients = Column(sqlalchemy.TEXT())
    cc_recipients_name = Column(sqlalchemy.TEXT())
    message_title = Column(sqlalchemy.TEXT())
    message_text = Column(sqlalchemy.TEXT())
    orig_date = Column(sqlalchemy.DATETIME())
    create_date = Column(sqlalchemy.DATETIME())
    isclassified = Column(sqlalchemy.Integer)
    category = Column(sqlalchemy.String(256))



def ShowNotification(error):
    return str(error)


class Message(object):

    def _cp_dispatch(self, vpath):
        """
        Обработка REST URL
        """

        if len(vpath) == 1 and vpath[1] == 'add':
            cherrypy.request.params['uuid'] = vpath[0]
            print "Показываем объект : ", vpath
            return ShowNotification("")
        elif len(vpath) == 2 and vpath[1] == 'edit':
            cherrypy.request.params['uuid'] = vpath[0]
            print "Редактируем объект : ", vpath
            return ShowNotification("")
        elif len(vpath) == 2 and vpath[1] == 'save':
            print "Сохраняем объект : ", vpath
            cherrypy.request.params['uuid'] = vpath[0]
            return ShowNotification("")
        elif len(vpath) == 2 and vpath[1] == 'addlink':
            cherrypy.request.params['uuid'] = vpath[0]
            print "Связываем объект : ", vpath
            return ShowNotification("")
        elif len(vpath) == 2 and vpath[1] == 'savelink':
            cherrypy.request.params['object_uuid'] = vpath[0]
            print "Сохраняем связь..."
            return ShowNotification("")
        elif len(vpath) == 2 and vpath[1] == 'use':
            cherrypy.request.params['case_uuid'] = vpath[0]
            print "Используем кейс..."
            return self
        elif len(vpath) == 0:
            print "Вывод переадресации : ", vpath
            return self

        return vpath


class Root(object):

    @cherrypy.expose
    def index(self):
        tmpl = lookup.get_template("dashboard.html")
        return tmpl.render()

cherrypy.config.update("server.config")

if __name__ == '__main__':
    cherrypy.quickstart(Root(), '/', "app.config")
