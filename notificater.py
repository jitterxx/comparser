#!/usr/bin/python -t
# coding: utf8

import sqlalchemy
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from configuration import *
import re
import sys
reload(sys)
sys.setdefaultencoding("utf-8")

__author__ = 'sergey'

sql_uri = "mysql://%s:%s@%s/clear_data?charset=utf8" % (db_user, db_pass, db_host)

Base = declarative_base()
Engine = sqlalchemy.create_engine(sql_uri, pool_size=20)
Session = sqlalchemy.orm.sessionmaker(bind=Engine)

"""
1. Читаем результаты классификации из базы
2. Если классификация попадает в условия, то формируем сообщение в адрес менеджера
"""


class Msg(Base):

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


def notify():
    session = Session()

    query = session.query(Msg).filter(Msg.isclassified == 1).all()
    for msg in query:
        print msg.message_id
        cats = re.split(":", msg.category)
        print cats

    session.close()


notify()