#!/usr/bin/python -t
# coding: utf8

import sqlalchemy
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import and_
from configuration import *
import datetime
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


class TrainAPIRecords(Base):

    __tablename__ = "train_api"

    id = Column(sqlalchemy.Integer, primary_key=True)
    uuid = Column(sqlalchemy.String(256))
    message_id = Column(sqlalchemy.String(256))
    category = Column(sqlalchemy.String(256))
    date = Column(sqlalchemy.DATETIME())
    user_action = Column(sqlalchemy.Integer)
    user_answer = Column(sqlalchemy.String(45))

class UserTrainData(Base):

    __tablename__ = "user_train_data"

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
    category = Column(sqlalchemy.String(255))

    def __init__(self):
        message_id = ""
        sender = ""
        sender_name = ""
        recipients = ""
        recipients_name = ""
        cc_recipients = ""
        cc_recipients_name = ""
        message_title = ""
        message_text = ""
        orig_date = datetime.datetime.now()
        create_date = datetime.datetime.now()
        category = ""



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
        session.close()

    return category


def set_user_train_data(uuid, category):
    # 1. записать указанный емайл и категорию в пользовательские тренировочные данные
    # 2. Пометить в таблице train_api ответ.

    session = Session()

    try:
        query = session.query(TrainAPIRecords).filter(TrainAPIRecords.uuid == uuid).one()
    except Exception as e:
        session.close()
        raise e
    else:
        if not query:
            return [False, "Сообщение не найдено."]

        if query.user_action == 0:
            message_id = query.message_id
            query.user_action = 1
            query.user_answer = category
            session.commit()
        else:
            return [False, "Для этого сообщения ответ был получен ранее."]

    train_data = UserTrainData()
    train_data.message_id = query.message_id
    train_data.category = category
    train_data.message_text = query.message_text
    train_data.message_title = query.message_title

    try:
        session.add(train_data)
        session.commit()
    except Exception as e:
        raise e
    finally:
        session.close()

    return [True, "Ваш ответ принят. Спасибо за участие!"]
