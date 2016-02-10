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
from mod_classifier import fisherclassifier, specfeatures
import uuid
import re

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

__author__ = 'sergey'

sql_uri = "mysql://%s:%s@%s:%s/%s?charset=utf8" % (db_user, db_pass, db_host, db_port, db_name)

Base = declarative_base()
Engine = sqlalchemy.create_engine(sql_uri, pool_size=20, pool_recycle=3600)
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
        self.message_id = ""
        self.sender = ""
        self.sender_name = ""
        self.recipients = ""
        self.recipients_name = ""
        self.cc_recipients = ""
        self.cc_recipients_name = ""
        self.message_title = ""
        self.message_text = ""
        self.orig_date = datetime.datetime.now()
        self.create_date = datetime.datetime.now()
        self.category = ""



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
    except sqlalchemy.orm.exc.NoResultFound:
        session.close()
        return [False, "Сообщение не найдено."]
    except Exception as e:
        session.close()
        raise e
    else:

        if query.user_action == 0:
            message_id = query.message_id
            query.user_action = 1
            query.user_answer = category
            session.commit()
        else:
            return [False, "Для этого сообщения ответ был получен ранее."]

    try:
        query = session.query(Msg).filter(Msg.message_id == message_id).one()
    except Exception as e:
        session.close()
        raise e

    train_data = UserTrainData()
    train_data.message_id = message_id
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


def landing_customer_contacts(customer_email=None, customer_phone=None, customer_name=None, customer_session=None,
                              pd=None):
    """
    Функция отправки контактных данных полученных с лендинга.

    :param customer_email:
    :param customer_phone:
    :param customer_name:
    :param customer_session:
    :param pd:
    :return:
    """

    msg = email.MIMEMultipart.MIMEMultipart()
    from_addr = "info@conparser.ru"
    to_addr = "sergey@reshim.com, ramil@reshim.com"

    msg['From'] = from_addr
    msg['To'] = to_addr
    text = "\tИмя: %s \n" % customer_name
    text += "\tE-mail: %s \n\tТелефон: %s \n" % (customer_email, customer_phone)
    text += "\tОтметка об обработке персональных данных: %s \n" % pd
    text += "\tДата и время: %s \n" % datetime.datetime.now()
    text += "Параметры сессии: \n "
    for a,b in customer_session.items():
        text += "\t%s : %s \n" % (a, b)

    msg['Subject'] = Header("Контакты с лендинга Conversation parser", "utf8")
    body = "Оставлены контакты. \n" + text
    msg.preamble = "This is a multi-part message in MIME format."
    msg.epilogue = "End of message"

    msg.attach(email.MIMEText.MIMEText(body, "plain", "UTF-8"))

    smtp = SMTP_SSL()
    smtp.connect(smtp_server)
    smtp.login(from_addr, "Cthutq123")
    text = msg.as_string()
    smtp.sendmail(from_addr, to_addr.split(","), text)
    smtp.quit()


def demo_classify(description):

    answer = ["", 0]

    #Указана БД классификатора, работаем используя лимит
    #Создаем объект классификатора
    f_cl = fisherclassifier(specfeatures)

    #Подключаем данные обучения
    f_cl.setdb(db_name)
    f_cl.loaddb()
    f_cl.unsetdb()

    row = dict()
    row['message_title'] = ""
    row['message_text'] = description

    msg = Msg()
    msg.message_id = uuid.uuid4().__str__()
    msg.cc_recipients = msg.cc_recipients_name = msg.sender_name = msg.sender = msg.message_title = msg.recipients = \
        msg.recipients_name = ""
    msg.message_text = description
    msg.isclassified = 1
    msg.notified = 1
    msg.orig_date = datetime.datetime.now()
    msg.create_date = datetime.datetime.now()
    msg.category = ""

    try:
        cats = f_cl.classify_mr(row, default='0')
        print "Полный ответ классификатора: %s" % cats
    except Exception as e:
        print str(e)
        raise e

    for one in cats:
        if answer[1] <= float(one.values()[0]):
            answer[0] = one.keys()[0]
            answer[1] = float(one.values()[0])

    msg.category = str(answer[0]) + "-" + str(answer[1])

    print "Обработанный ответ классификатора: %s" % answer

    record = TrainAPIRecords()
    record.message_id = msg.message_id
    record.date = datetime.datetime.now()
    record.uuid = record_uid = uuid.uuid4().__str__()
    record.category = msg.category
    record.user_action = 0
    record.user_answer = ""

    session = Session()
    try:
        session.add(msg)
        session.commit()
    except Exception as e:
        session.close()
        print "Ошибка записи MSG." + str(e)
        raise e
    else:
        print "Новый MSG записан."

    try:
        session.add(record)
        session.commit()
    except Exception as e:
        print "Ошибка записи TRAIN_API ." + str(e)
        raise e
    finally:
        session.close()

    return answer, record_uid


def get_message_for_train(msg_uuid):
    session = Session()
    try:
        query = session.query(TrainAPIRecords).filter(TrainAPIRecords.uuid == msg_uuid).one()
    except sqlalchemy.orm.exc.NoResultFound:
        session.close()
        return [False, "API. Описание не найдено."]
    except Exception as e:
        session.close()
        raise e
    else:
        try:
            msg = session.query(Msg).filter(Msg.message_id == query.message_id).one()
        except sqlalchemy.orm.exc.NoResultFound:
            session.close()
            return [False, "MSG. Описание не найдено."]
        except Exception as e:
            session.close()
            raise e
        else:
            desc = msg.message_text
            answer = re.split("-", msg.category)

    session.close()

    return [True, desc, answer]

