#!/usr/bin/python -t
# coding: utf8

import sqlalchemy
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import and_
from configuration import *
import re
import email
from email.header import Header
from smtplib import SMTP_SSL

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

__author__ = 'sergey'

sql_uri = "mysql://%s:%s@%s/%s?charset=utf8" % (db_user, db_pass, db_host, db_name)

Base = declarative_base()
Engine = sqlalchemy.create_engine(sql_uri, pool_size=20)
Session = sqlalchemy.orm.sessionmaker(bind=Engine)


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
    notified = Column(sqlalchemy.Integer)


class Category(Base):
    __tablename__ = "category"

    id = Column(sqlalchemy.Integer, primary_key=True)
    code = Column(sqlalchemy.String(45))
    category = Column(sqlalchemy.String(256))
    minimum = Column(sqlalchemy.Float)


def GetCategory():
    category = dict()
    session = Session()

    try:
        query = session.query(Category).all()
    except Exception as e:
        raise e
    else:
        for one in query:
            category[one.code] = one
    finally:
        session.clsoe()

    return category


