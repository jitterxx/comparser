#!/usr/bin/python -t
# coding: utf8
import os
import sys
reload(sys)
sys.setdefaultencoding("utf-8")

import sqlalchemy
from sqlalchemy import Table, Column, Integer, ForeignKey, and_, or_, func
from sqlalchemy.ext.declarative import declarative_base
from configuration import *
import datetime
import email
from email.header import Header, decode_header
from smtplib import SMTP_SSL
# from mod_classifier import fisherclassifier, specfeatures
import uuid
import re
from dateutil.parser import *
from dateutil.tz import tzutc, tzlocal

__author__ = 'sergey'

sql_uri = "mysql://%s:%s@%s:%s/%s?charset=utf8" % (db_user, db_pass, db_host, db_port, db_name)

Base = declarative_base()
Engine = sqlalchemy.create_engine(sql_uri, pool_size=20, pool_recycle=3600)
Session = sqlalchemy.orm.sessionmaker(bind=Engine)


def create_tables():
    """
    Функция пересоздания таблиц  базе данных MySQL.

    Все таблицы пересоздаются согласно объявлению классов наследованных от Base. Если таблица в БД существует,
    то ничего не происходит.

    :return: нет
    """

    Base.metadata.create_all(Engine)


def get_exception_list():
    """
    Формируем список исключений

    :return:
    """

    return EXCEPTION_EMAIL


# Текущая эпоха обучения. Значение должно быть считано из БД
CURRENT_TRAIN_EPOCH = None


class Settings(Base):
    """
    train_epoch - этот параметр храниит номер эпохи обучения ядра системы классификации. Нужен для разделения данных
    на наборы по которым проходило обучение, распознавание и проверка результата. Наборы нужны для расчета статистики
    ошибок, проверки результатов и сравнения эффективности наборов обучения ядра.
    """
    __tablename__ = "settings"
    __table_args__ = TABLE_ARGS

    id = Column(sqlalchemy.Integer, primary_key=True)
    train_epoch = Column(sqlalchemy.Integer, default=0)  # хранит номер текущей эпохи обучения


# Читаем текущую эпоху из БД
def read_epoch():

    session = Session()
    try:
        resp = session.query(Settings).one()
    except sqlalchemy.orm.exc.NoResultFound:
        new_set = Settings()
        new_set.train_epoch = 0
        session.add(new_set)
        session.commit()
    except Exception as e:
        raise e
    else:
        return resp.train_epoch
    finally:
        session.close()


def update_epoch():

    global CURRENT_TRAIN_EPOCH

    session = Session()
    try:
        resp = session.query(Settings).one()
    except Exception as e:
        raise e
    else:
        try:
            resp.train_epoch = int(CURRENT_TRAIN_EPOCH) + 1
            session.commit()
        except Exception as e:
            raise e
        else:
            CURRENT_TRAIN_EPOCH = int(CURRENT_TRAIN_EPOCH) + 1

    finally:
        session.close()


class MsgRaw(Base):

    __tablename__ = "email_raw_data"
    __table_args__ = TABLE_ARGS

    id = Column(sqlalchemy.Integer, primary_key=True)
    message_id = Column(sqlalchemy.String(256))
    sender = Column(sqlalchemy.String(256))
    recipient = Column(sqlalchemy.TEXT())
    cc_recipient = Column(sqlalchemy.TEXT())
    message_title = Column(sqlalchemy.TEXT())
    message_text = Column(sqlalchemy.TEXT())
    message_text_html = Column(sqlalchemy.TEXT())
    orig_date = Column(sqlalchemy.DATETIME())
    create_date = Column(sqlalchemy.DATETIME())
    iscleared = Column(sqlalchemy.Integer)
    isbroken = Column(sqlalchemy.Integer)
    references = Column(sqlalchemy.TEXT())
    in_reply_to = Column(sqlalchemy.String(256))
    orig_date_str = Column(sqlalchemy.String(256))

    def __init__(self):
        self.cc_recipients = ""
        self.message_text = ""
        self.message_title = ""
        self.message_text_html = ""
        self.isbroken = 0
        self.iscleared = 0
        self.create_date = datetime.datetime.now()


def line_decoder (text_line):
    s_text_line = text_line.split(" ")
    # print 'split: ',s_text_line
    # print 'Количество циклов: ',len(s_text_line)
    # print 'Пошел цикл...'+'\n'
    result=''

    for i in range (len(s_text_line)):
        # print 'Шаг номер ',i,':\n'
        data=''
        coding=''
        # print 'Split item & num: ',s_text_line[i], i,'\n'
        data, coding = decode_header(s_text_line[i])[0]
        # print 'Decoded data, coding: ',data, coding,'\n'
        if coding == None:
            result = result + ' ' + data
        else:
            result = result + data.decode(coding,'replace')

    # print 'Decoded data, coding: ',result, coding,'\n'
    return result


def remove_tags(data):

    # Оставляем все теги для html сообщений в MsgRaw таблице
    """
    # remove the newlines
    data = data.replace("\n", " ")
    data = data.replace("\r", " ")

    # replace consecutive spaces into a single one
    data = " ".join(data.split())

    # get only the body content
    bodyPat = re.compile(r'<body[^<>]*?>(.*?)</body>', re.I)
    if re.findall(bodyPat, data) :
        result = re.findall(bodyPat, data)
        data = result[0]

    # now remove the java script
    p = re.compile(r'<script[^<>]*?>.*?</script>')
    data = p.sub('', data)

    # remove the css styles
    p = re.compile(r'<style[^<>]*?>.*?</style>')
    data = p.sub('', data)

    # remove html comments
    p = re.compile(r'')
    data = p.sub('', data)

    # remove all the tags
    p = re.compile(r'<[^<]*?>')
    data = p.sub('', data)
    """

    return data


def email_part_analyse(msg_part=None, debug=False):
    """
    Функция для работы с мультипарт сообщениями. Запускает рекурсию при вложенности.

    :param msg_part: multipart сообщение
    :return:
    """

    if msg_part:
        # 3 части: plain, html, other text
        text_part = ["", "", ""]
    else:
        return ""

    for part in msg_part.get_payload():
        if debug:
            print "***** Анализ части сообщения *****"
        part_type = part.get_content_type()
        part_charset = part.get_param('charset')
        part_transfer_encode = part['Content-Transfer-Encoding']
        part_is_attach = part.has_key('Content-Disposition')
        part_filename = part.get_param("filename")
        skip_part = False

        if (part_charset == 'None') or part_is_attach:
            skip_part = True

        if debug:
            print 'Part is attach: %s' % part_is_attach
            print 'Part type: ', part_type
            print 'Part charset: ', part_charset
            print 'Part transf encode: ', part_transfer_encode
            print "Пропустить часть: %s" % skip_part
            print "Filename: %s " % part_filename

        if (part_type == "text/plain" or part_type == "text") and part_charset:
            # Как только нашли обычный текст, выводим с перекодировкой
            dirty_part = part.get_payload(decode=True)
            text_part[0] += unicode(dirty_part, str(part_charset), "ignore").encode('utf8', 'replace')
            if debug:
                print 'Text in plain: ', text_part[0], '\n'
        elif part_type == "text/html" and part_charset:
            # Если нашли текст в HTML, чистим от разметки и выводим с перекодировкой
            dirty_part = part.get_payload(decode=True)
            html = unicode(dirty_part, str(part_charset), "ignore").encode('utf8', 'replace')
            text_part[1] += remove_tags(html)
            if debug:
                print 'Text in HTML: ', text_part[1], '\n'
        elif part_type == "multipart/alternative" or part_type == "multipart/related":
            # часть сама является составной, ищем блоки и делаем анализ
            text_part_new = email_part_analyse(msg_part=part)
            text_part[0] = text_part[0] + text_part_new[0]
            text_part[1] = text_part[1] + text_part_new[1]
            text_part[2] = text_part[2] + text_part_new[2]
        else:
            # Если тип части не текст, пробуем раскодировать
            try:
                dirty_part = part.get_payload(decode=True)
                html = unicode(dirty_part, str(part_charset), "ignore").encode('utf8', 'replace')
            except Exception as e:
                if debug:
                    print "Ошибка раскодирования части. %s" % str(e)
                pass
            else:
                text_part[2] += remove_tags(html)

        """
        if not skip_part:
            if part_type == "text/plain" or part_type == "text":
                # Как только нашли обычный текст, выводим с перекодировкой
                dirty = part.get_payload(decode=True)
                text += unicode(dirty, str(part_charset), "ignore").encode('utf8', 'replace')
                if debug:
                    print 'Message in plain: ', text, '\n'
            elif part_type == "text/html":
                # Если нашли текст в HTML, чистим от разметки и выводим с перекодировкой
                dirty = part.get_payload(decode=True)
                html = unicode(dirty, str(part_charset), "ignore").encode('utf8', 'replace')
                text += remove_tags(html)
                if debug:
                    print 'Message in HTML: ', text, '\n'
            else:
                # Если тип части не известен, пробуем раскодировать
                try:
                    dirty = part.get_payload(decode=True)
                    html = unicode(dirty, str(part_charset), "ignore").encode('utf8', 'replace')
                except Exception as e:
                    print "Ошибка раскодирования части. %s" % str(e)
                    text += ""
                else:
                    text += remove_tags(html)

                if debug:
                    print 'Message in UNKNOWN format: ', text, '\n'

        else:
            #text = text + u'Часть содержит не текст.\n'
            #+ '\n'.join(part.values())
            if debug:
               print "Часть содержит не текст.\n"
        """
        if debug:
            print "***** Конец части сообщения *****"

    return text_part


def parse_message(msg=None, debug=False):
    msg_id = ""
    subject = ""
    cc = ""
    to = ""
    from_ = ""
    date_hdr = ""
    text = ""
    text2 = ["", "", ""]

    msg_id = msg['message-id']

    # Заголовки для составления бесед-тредов
    if msg.get('References'):
        references = msg.get('References')
    else:
        references = ""

    if msg.get('In-Reply-To'):
        in_reply_to = msg.get('In-Reply-To')
    else:
        in_reply_to = ""

    subject = msg.get('Subject', 'No subject provided')
    subject = line_decoder(subject)

    date_raw = msg.get('Date')
    p = re.compile('[(]')
    if date_raw:
        date_hdr = p.split(date_raw,1)[0]
    else:
        date_hdr = ""

    msg_datetime = datetime.datetime.now()

    """
    try:
        dt = parse(date_hdr).replace(tzinfo=None)
    except Exception as e:
        print "Ошибка времени из сообщения. %s" % str(e)
    else:
        msg_datetime = dt
    """

    # Вычисляем время создания сообщения в UTC
    try:
        dt = parse(date_hdr).astimezone(tzutc()).replace(tzinfo=None)
    except Exception as e:
        print "Email_eater. Ошибка считывания времени из сообщения в UTC. %s" % str(e)
    else:
        msg_datetime = dt

    if debug:
        print "Format datetime: ", msg_datetime

    text = ""

    # Проверяем параметры сообщения
    broken_msg = False
    # Если параметр не определен, ставим empty
    cc = msg.get('Cc')
    if not cc:
        cc = "empty"
    cc = line_decoder(cc)

    to = msg.get('To')
    if not to:
        to = "empty"
        broken_msg = True
    to = line_decoder(to)

    from_ = msg.get('From')
    if not from_:
        from_ = "empty"
        broken_msg = True
    from_ = line_decoder(from_)

    maintype = msg.get_content_maintype()
    main_charset = msg.get_content_charset()
    is_multipart = msg.is_multipart()

    content_type = msg.get_content_type()
    content_charset = msg.get_content_charset()

    if debug:
        print "MID:", msg_id
        print "References: ", references
        print "In-Reply-To: ", in_reply_to
        print "From: ", from_
        print "To: ", to
        print 'Main type: ', maintype
        print 'Main charset', main_charset
        print "Multipart: ", msg.is_multipart()
        print "Charset: ", content_charset
        print "type :", content_type
        print 'Subj: ',subject
        print 'Date: ',date_hdr
        print "\n"

    if is_multipart:
        # Если это мультипарт, ищем текстовую часть письма
        if debug:
            print "** Multipart message **"
        # Если это мультипарт, то передаем его на обработку
        text2 = email_part_analyse(msg_part=msg, debug=debug)
        if debug:
            print msg.get_payload()
            print len(msg.get_payload())
            print "= "*30
            for one in text2[:2]:
                print one
                print "- "*30

    elif content_type == "text/plain" and content_charset:
        dirty = msg.get_payload(decode=True)
        text2[0] = unicode(dirty, str(main_charset), "ignore").encode('utf8', 'replace')
        if debug:
            print "** NOT Multipart message **"
            print 'Text in plain: ', text2[0], '\n'
    elif content_type == "text/html" and content_charset:
        dirty = msg.get_payload(decode=True)
        html = unicode(dirty, str(main_charset), "ignore").encode('utf8', 'replace')
        text2[1] = remove_tags(html)
        if debug:
            print "** NOT Multipart message **"
            print 'Text in HTML: ', text2[1], '\n'
    elif not main_charset or not maintype:
        if debug:
            print 'Не указан main_charset. Битое сообщение.'
        # Если не определены параметры в заголовках, считаем что это битое сообщение не декодируем
        text2[2] = msg.get_payload(decode=True)
        broken_msg = True
    else:
        # Все остальное
        if debug:
            print 'Все остальное. Сообщение без обработки.'
        text2[2] = msg.get_payload(decode=True)
        broken_msg = True

    text += text2[0]

    return [msg_id, from_, to, cc, subject, text2[0], text2[1], msg_datetime, int(broken_msg), references, in_reply_to, date_hdr]


class Msg(Base):

    __tablename__ = "email_cleared_data"
    __table_args__ = TABLE_ARGS

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
    isclassified = Column(sqlalchemy.Integer, default=0)
    category = Column(sqlalchemy.String(256), default="")
    notified = Column(sqlalchemy.Integer, default=0)
    references = Column(sqlalchemy.TEXT())
    in_reply_to = Column(sqlalchemy.String(256))

    def __init__(self):
        self.isclassified = 0
        self.category = ""
        self.notified = 0


class MsgErr(Base):

    __tablename__ = "email_err_cleared_data"
    __table_args__ = TABLE_ARGS

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
    references = Column(sqlalchemy.TEXT())
    in_reply_to = Column(sqlalchemy.String(256))


def get_clear_message(msg_id=None, for_day=None, msg_id_list=None):

    if msg_id:
        session = Session()
        try:
            result = session.query(Msg).filter(Msg.message_id == msg_id).one_or_none()
        except Exception as e:
            print "Get_clear_message(). Ошибка получения сообщения. MSGID: %s. %s" % (msg_id, str(e))
            raise e
        else:
            return result
        finally:
            session.close()

    elif for_day:
        # получаем сообщения за определенный день
        start = datetime.datetime.strptime("%s-%s-%s 00:00:00" % (for_day.year, for_day.month, for_day.day),
                                           "%Y-%m-%d %H:%M:%S")
        end = datetime.datetime.strptime("%s-%s-%s 23:59:59" % (for_day.year, for_day.month, for_day.day),
                                         "%Y-%m-%d %H:%M:%S")
        session = Session()
        try:
            result = session.query(Msg).filter(and_(Msg.create_date >= start,
                                                    Msg.create_date <= end)).order_by(Msg.create_date.desc()).all()
        except Exception as e:
            print "Get_clear_message(). Ошибка получения сообщений за день: %s. %s" % (for_day, str(e))
            raise e
        else:
            return result
        finally:
            session.close()
    elif msg_id_list:
        session = Session()
        try:
            resp = session.query(Msg).filter(Msg.message_id.in_(msg_id_list)).all()
        except Exception as e:
            print "Get_clear_message(). Ошибка получения сообщений по списку. %s" % str(e)
            raise e
        else:
            result = dict()
            for one in resp:
                result[one.message_id] = one

            return result
        finally:
            session.close()

    else:
        session = Session()
        try:
            resp = session.query(Msg).order_by(Msg.orig_date.desc()).all()
        except Exception as e:
            raise e
        else:
            result = dict()
            for one in resp:
                result[one.message_id] = one

            return result
        finally:
            session.close()


def get_only_cat_message(for_day=None, cat=None, client_access_list=None, empl_access_list=None):
    """
    Получение сообщений только указанной категории.

    :param for_day: день за который нужны сообщения
    :param cat: к какой категории должны относиться сообщения

    :return: словарь
    """

    if for_day and cat:
        # получаем сообщения за определенный день
        start = datetime.datetime.strptime("%s-%s-%s 00:00:00" % (for_day.year, for_day.month, for_day.day),
                                           "%Y-%m-%d %H:%M:%S")
        end = datetime.datetime.strptime("%s-%s-%s 23:59:59" % (for_day.year, for_day.month, for_day.day),
                                         "%Y-%m-%d %H:%M:%S")
        session = Session()
        try:
            result = session.query(Msg).filter(and_(Msg.create_date >= start,
                                                    Msg.create_date <= end),
                                               Msg.category.like(cat + "%")).order_by(Msg.create_date.desc()).all()
        except Exception as e:
            print "Get_only_cat_message(). Ошибка получения сообщений за день: %s. %s" % (for_day, str(e))
            raise e
        else:
            # ДОполнительно к списку сообщений, возвращаем список с их идентификаторами.
            # Необходимо для поиска данных в других функциях
            only_msg_id = list()
            for one in result:
                only_msg_id.append(one.message_id)
            return result, only_msg_id
        finally:
            session.close()

    else:
        return None


def get_raw_message(msg_id=None):
    session = Session()

    try:
        resp = session.query(MsgRaw).order_by(MsgRaw.orig_date.desc()).all()
    except Exception as e:
        raise e
    else:
        result = dict()
        for one in resp:
            result[one.message_id] = one

        return result
    finally:
        session.close()


class TrainAPIRecords(Base):

    __tablename__ = "train_api"
    __table_args__ = TABLE_ARGS

    id = Column(sqlalchemy.Integer, primary_key=True)
    uuid = Column(sqlalchemy.String(256))
    message_id = Column(sqlalchemy.String(256))
    auto_cat = Column(sqlalchemy.String(256), default="")
    category = Column(sqlalchemy.String(256))
    date = Column(sqlalchemy.DATETIME())
    user_action = Column(sqlalchemy.Integer)
    user_answer = Column(sqlalchemy.String(45))
    train_epoch = Column(sqlalchemy.Integer)


def get_train_record(msg_id=None, uuid=None, for_epoch=None):

    if msg_id:
        # записи о проверках для данного сообщения
        session = Session()
        try:
            result = session.query(TrainAPIRecords).filter(TrainAPIRecords.message_id == msg_id).one()
        except sqlalchemy.orm.exc.NoResultFound:
            print "get_train_record. Сообщение еще не классифицированно. MSGID: %s" % msg_id
            return None
        except sqlalchemy.orm.exc.MultipleResultsFound:
            print "get_train_record. Найдено много тренировочных записей. MSGID: %s" % msg_id
            return None
        except Exception as e:
            print "get_train_record. Ошибка. %s" % str(e)
            raise e
        else:
            return result
        finally:
            session.close()

    elif uuid:
        # Возвращает запись о проверке сообщения по указанному UUID проверки
        session = Session()
        try:
            result = session.query(TrainAPIRecords).filter(TrainAPIRecords.uuid == uuid).one()
        except sqlalchemy.orm.exc.NoResultFound:
            print "get_train_record(uuid). Сообщение еще не классифицированно. MSGID: %s" % msg_id
            return None
        except sqlalchemy.orm.exc.MultipleResultsFound:
            print "get_train_record(uuid). Найдено много тренировочных записей. MSGID: %s" % msg_id
            return None
        except Exception as e:
            print "get_train_record(uuid). Ошибка. %s" % str(e)
            raise e
        else:
            return result
        finally:
            session.close()
    else:
        # все записи о проверках
        session = Session()

        try:
            if isinstance(for_epoch, int):
                resp = session.query(TrainAPIRecords).filter(TrainAPIRecords.train_epoch == for_epoch).all()
            else:
                resp = session.query(TrainAPIRecords).all()
        except Exception as e:
            print "get_train_record. Ошибка. %s" % str(e)
            raise e
        else:
            result = dict()
            for one in resp:
                # print one.message_id
                result[one.message_id] = one

            return result
        finally:
            session.close()


def get_cat_train_api_records(for_day=None, client_access_list=None, empl_access_list=None, actions_msg_id=None):
    """
    Получение записей из API для сообщений только в указанный день.

    :param for_day: день за который нужны сообщения
    :param client_access_list:
    :param empl_access_list:
    :param actions_msg_id: список идентификаторов сообщений для которых запрашиваются записи

    :return: словарь
    """

    if for_day:
        # получаем сообщения за определенный день
        start = datetime.datetime.strptime("%s-%s-%s 00:00:00" % (for_day.year, for_day.month, for_day.day),
                                           "%Y-%m-%d %H:%M:%S")
        end = datetime.datetime.strptime("%s-%s-%s 23:59:59" % (for_day.year, for_day.month, for_day.day),
                                         "%Y-%m-%d %H:%M:%S")
        session = Session()
        try:
            if actions_msg_id:
                result = session.query(TrainAPIRecords).\
                    filter(and_(TrainAPIRecords.date >= start,
                                TrainAPIRecords.date <= end,
                                TrainAPIRecords.message_id.in_(actions_msg_id))).all()
            else:
                result = session.query(TrainAPIRecords).filter(and_(TrainAPIRecords.date >= start,
                                                                    TrainAPIRecords.date <= end)).all()
        except Exception as e:
            print "get_cat_train_api_records(). Ошибка получения TrainAPI records за день: %s. %s" % (for_day, str(e))
            raise e
        else:
            result1 = dict()
            for one in result:
                result1[one.message_id] = one
            return result1
        finally:
            session.close()

    else:
        return None


def get_dialogs(for_day=None, cat=None, client_access_list=None, empl_access_list=None):
    """
    Получаем диалоги для вывода

    :param for_day: день
    :param cat: категории которые ищем
    :param client_access_list: список клиентов
    :param empl_access_list: список сотрудников
    :return:
    """

    if for_day and cat:
        if not isinstance(cat, list):
            cat = [cat]

        # получаем сообщения за определенный день
        start = datetime.datetime.strptime("%s-%s-%s 00:00:00" % (for_day.year, for_day.month, for_day.day),
                                           "%Y-%m-%d %H:%M:%S")
        end = datetime.datetime.strptime("%s-%s-%s 23:59:59" % (for_day.year, for_day.month, for_day.day),
                                         "%Y-%m-%d %H:%M:%S")

        session = Session()
        # Получаем список сообщений за указанный промежуток с учетом списков доступа
        try:
            """
            resp = session.query(Msg).\
                filter(and_(Msg.create_date >= start, Msg.create_date <= end), Msg.isclassified == 1).\
                order_by(Msg.create_date.desc()).all()
            """

            resp = session.query(Msg).\
                filter(and_(Msg.create_date >= start, Msg.create_date <= end), Msg.isclassified == 1,
                       or_(*[Msg.category.like(c + "%") for c in cat])).\
                order_by(Msg.create_date.desc()).all()

        except Exception as e:
            print "Get_dialogs(). Ошибка получения сообщений за день: %s. %s" % (for_day, str(e))
            session.close()
            raise e
        else:
            message_id_list = list()
            message_list = dict()
            for message in resp:
                try:
                    fields = str(message.sender).split(",") + \
                             str(message.recipients).split(",") + \
                             str(message.cc_recipients).split(",")
                except Exception as e:
                    print "CPO.Get_dialogs(). Ошибка получения полей ОТ,КОМУ, КОПИЯ из сообщения: %s. %s" % \
                          (message, str(e))
                    fields = list()

                # print "ALL fields: %s" % fields
                # формируем список емайлов и доменов из письма
                emails = list()
                for one in fields:
                    if one != "empty":
                        emails.append(one)
                        try:
                            domain = one.split("@")[1]
                        except IndexError:
                            emails.append(one)
                        except Exception as e:
                            print "CPO.Get_dialogs(). Ошибка получения доменного имени из : %s. %s" % (one, str(e))
                        else:
                            emails.append(domain)

                # удаляем дубликаты
                emails = set(emails)
                emails = list(emails)

                # print "Emails : %s" % emails
                # print "Client access list: %s" % client_access_list

                # список доступных емайлов и доменов уже получен в client_access_list
                # ищем пересечение, если оно есть, добавляем сообщение в список message_id_list и message_list
                client_access_list = set(client_access_list)
                result = client_access_list.intersection(emails)

                # print "INTERSECTION : %s" % result

                if result:
                    message_id_list.append(message.message_id)
                    message_list[message.message_id] = message

        # Получаем список индентификаторов сообщений (нужен для получения самих сообщений)
        try:
            resp = session.query(TrainAPIRecords).\
                filter(and_(TrainAPIRecords.date >= start,
                            TrainAPIRecords.date <= end,
                            TrainAPIRecords.message_id.in_(message_id_list)),
                       or_(and_(TrainAPIRecords.user_action == 1, TrainAPIRecords.user_answer.in_(cat)),
                           and_(TrainAPIRecords.user_action == 0, TrainAPIRecords.auto_cat.in_(cat)))).\
                order_by(TrainAPIRecords.date.desc()).all()
        except Exception as e:
            print "Get_dialogs(). Ошибка получения ID сообщений за день: %s. %s" % (for_day, str(e))
            session.close()
            raise e
        else:
            # message_id_list = list()
            api_list = dict()
            checked = list()
            unchecked = list()
            for one in resp:
                # message_id_list.append(one.message_id)
                api_list[one.message_id] = one

                if one.user_action == 0:
                    # unchecked
                    unchecked.append(one.message_id)
                else:
                    # checked
                    checked.append(one.message_id)

            # """
            print "API list len: %s" % len(api_list.keys())
            print "MSG ID list len: %s" % len(message_id_list)

            message_id_list = list(set(api_list.keys()).intersection(set(message_id_list)))

            print "MSG ID list len (intersection): %s" % len(message_id_list)
            # """

        # Получаем сами сообщения
        """
        try:
            resp = session.query(Msg).\
                filter(Msg.message_id.in_(message_id_list)).order_by(Msg.create_date.desc()).all()
        except Exception as e:
            print "Get_dialogs(). Ошибка получения сообщений за день: %s. %s" % (for_day, str(e))
            session.close()
            raise e
        else:
            message_list = dict()
            for one in resp:
                message_list[one.message_id] = one


        # Получаем не проверенные сообщения
        try:
            resp = session.query(TrainAPIRecords.message_id).\
                filter(and_(TrainAPIRecords.message_id.in_(message_id_list),
                            TrainAPIRecords.user_action == 0)).\
                order_by(TrainAPIRecords.date.desc()).all()
        except Exception as e:
            print "Get_dialogs(). Ошибка получения не проверенных ID сообщений за день: %s. %s" % (for_day, str(e))
            session.close()
            raise e
        else:
            unchecked = [r for r, in resp]

        # Получаем проверенные сообщения и ищем не закрытые задачи
        try:
            resp = session.query(TrainAPIRecords.message_id).\
                filter(and_(TrainAPIRecords.message_id.in_(message_id_list),
                            TrainAPIRecords.user_action == 1)).\
                order_by(TrainAPIRecords.date.desc()).all()
        except Exception as e:
            print "Get_dialogs(). Ошибка получения проверенных ID сообщений за день: %s. %s" % (for_day, str(e))
            session.close()
            raise e
        else:
            checked = [r for r, in resp]
        """

        session.close()
        return api_list, message_list, message_id_list, unchecked, checked
    else:
        return None


def get_dialogs_warn(for_msg_id=None, for_cat=None):
    pass



class UserTrainData(Base):
    """
    Данные собираемые системой для текущей эпохи обучения.
    Будут использованы для обучения ядра и добавлены в train_data с указанием эпохи. После обучения ядра на них, \
    удаляются из данной таблицы.
    """

    __tablename__ = "user_train_data"
    __table_args__ = TABLE_ARGS

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
    train_epoch = Column(sqlalchemy.Integer)

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


class TrainData(Base):
    """
    Данные собираемые системой по всем эпохам обучения.
    Используются для:
     - накопительного обучения системы при начале новой эпохи
     - перекрестной проверки всех эпох обучения
     - хранения исторических данных для анализа.
    """

    __tablename__ = "train_data"
    __table_args__ = TABLE_ARGS

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
    references = Column(sqlalchemy.TEXT())
    in_reply_to = Column(sqlalchemy.String(256))
    category = Column(sqlalchemy.String(255))
    train_epoch = Column(sqlalchemy.Integer)

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
        self.train_epoch = CURRENT_TRAIN_EPOCH


class Category(Base):
    __tablename__ = "category"
    __table_args__ = TABLE_ARGS

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
            train_epoch = query.train_epoch
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
    train_data.references = query.references
    train_data.in_reply_to = query.in_reply_to
    train_data.sender = query.sender
    train_data.sender_name = query.sender_name
    train_data.recipients = query.recipients
    train_data.recipients_name = query.recipients_name
    train_data.cc_recipients = query.cc_recipients
    train_data.cc_recipients_name =  query.cc_recipients_name
    train_data.message_text = query.message_text
    train_data.message_title = query.message_title
    train_data.train_epoch = train_epoch

    try:
        session.add(train_data)
        session.commit()
    except Exception as e:
        raise e
    finally:
        session.close()

    return [True, "Спасибо. Ваш ответ принят."]


def landing_customer_contacts(customer_email, customer_phone, customer_session):
    """
    Функция отправки контактных данных полученных с лендинга.

    :return:
    """

    msg = email.MIMEMultipart.MIMEMultipart()
    from_addr = "info@conparser.ru"
    to_addr = "sergey@reshim.com, ramil@reshim.com"

    msg['From'] = from_addr
    msg['To'] = to_addr
    text = "\tE-mail: %s \n\tТелефон: %s \n" % (customer_email, customer_phone)
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


"""
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
"""


# Используется только в демо
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


class MsgThread(Base):

    __tablename__ = "threads"
    __table_args__ = TABLE_ARGS

    id = Column(sqlalchemy.Integer, primary_key=True)
    message_id = Column(sqlalchemy.String(256))  # ИД сообщения которое относиться к диалогу
    thread_uuid = Column(sqlalchemy.String(256))  # код диалога
    orig_date_utc = Column(sqlalchemy.DATETIME())  # Дата получения оригинального сообщения в виде UTC

    def __init__(self):
        self.message_id = ""
        self.thread_uuid = ""
        self.orig_date_utc = ""


def get_thread(thread_uuid=None, message_id=None):
    """
    Получить тред(все сообщения) по ИД или по MSG-ID сообщения входящего в него.

    :param thread_uuid:
    :param message_id:
    :return:
    """

    session = Session()

    if thread_uuid:
        try:
            resp = session.query(MsgThread).filter(MsgThread.thread_uuid == thread_uuid).all()
        except Exception as e:
            print "get_thread. Ошибка при получении треда. %s" % str(e)
            raise e
        else:
            return resp
        finally:
            session.close()

    if message_id:
        try:
            resp = session.query(MsgThread).filter(MsgThread.message_id == message_id).one_or_none()
        except sqlalchemy.orm.exc.NoResultFound:
            print "get_thread. Сообщение не входит ни в один тред. MSGID: %s" % message_id
            return None
        except sqlalchemy.orm.exc.MultipleResultsFound:
            print "get_thread. Найдено много тредов с этим сообщением. MSGID: %s" % message_id
            return None
        except Exception as e:
            print "get_thread. Ошибка при получении сообщения. %s" % str(e)
            raise e
        else:
            try:
                resp2 = session.query(MsgThread).filter(MsgThread.thread_uuid == resp.thread_uuid).all()
            except Exception as e:
                print "get_thread. Ошибка при получении треда. %s" % str(e)
                raise e
            else:
                return resp2

        finally:
            session.close()


def get_thread_messages(message_id=None, thread_uuid=None):
    """
    Получить все сообщения в треде по ИД или по MSG-ID сообщения входящего в него.

    :param thread_uuid:
    :param message_id:
    :return: словарь. Ключи - MSGID, значения - сообщения MsgRaw
    """

    session = Session()

    if thread_uuid:
        pass
        return list()

    if message_id:
        try:
            resp = session.query(MsgThread).filter(MsgThread.message_id == message_id).one()
        except sqlalchemy.orm.exc.NoResultFound:
            print "get_thread_messages. Сообщение не входит ни в один тред. MSGID: %s" % message_id
            return None
        except sqlalchemy.orm.exc.MultipleResultsFound:
            print "get_thread_messages. Найдено много тредов с этим сообщением. MSGID: %s" % message_id
            return None
        except Exception as e:
            print "get_thread_messages. Ошибка при получении сообщения. %s" % str(e)
            raise e
        else:

            # получаем список MSGID сообщений в треде
            try:
                resp2 = session.query(MsgThread).filter(MsgThread.thread_uuid == resp.thread_uuid).all()
            except Exception as e:
                print "get_thread_messages. Ошибка при получении треда. %s" % str(e)
                raise e
            else:

                messages = dict()
                # Получаем сами сообщения
                for one in resp2:
                    try:
                        resp3 = session.query(MsgRaw).filter(MsgRaw.message_id == one.message_id).one_or_none()
                    except Exception as e:
                        pass
                        resp3 = None
                    else:
                        messages[one.message_id] = resp3

                return messages

        finally:
            session.close()


def add_message_to_thread(msg=None):
    """
    Добавляет сообщение в тред или создает новый.

    :param msg: сообщение (формат MsgRaw)
    :return:
    """

    raw_ref = list()
    if msg.references:
        for one in re.split("\s+|[,]\s+", str(msg.references)):
            if one:
                raw_ref.append(one)

    try:
        orig_date_utc = parse(msg.orig_date_str).astimezone(tzutc()).replace(tzinfo=None)
    except Exception as e:
        print "MSGID: ", msg.message_id
        print "Create date: ", msg.orig_date_str
        print "add_message_to_thread(). Ошибка считывания времени в UTC. %s" % str(e)
        orig_date_utc = None

    session = Session()
    try:
        # ищем сообщение в тредах
        resp = session.query(MsgThread).filter(MsgThread.message_id == msg.message_id).one_or_none()
    except Exception as e:
        print "add_message_to_thread(). Ошибка при поиске сообщения в тредах. MSGID: %s " % msg.message_id
        print "add_message_to_thread(). Ошибка: ", str(e)
        raise e

    else:
        if resp:
            not_found = False
        else:
            not_found = True

        # если не найдено - обрабатываем
        if not_found:
            new_ref = list()
            if raw_ref or msg.in_reply_to:
                # Формируем список для поиска
                if msg.in_reply_to and raw_ref:
                    if msg.in_reply_to in raw_ref:
                        ref = raw_ref
                    else:
                        ref = raw_ref + [msg.in_reply_to]
                elif msg.in_reply_to and not raw_ref:
                    ref = [msg.in_reply_to]
                elif not msg.in_reply_to and raw_ref:
                    ref = raw_ref
                else:
                    ref = list()

                # Ищем для сообщения существующий код треда по msg-id в references и in-reply-to
                tread_id = None
                for one in ref:
                    try:
                        # ищем сообщение в тредах
                        resp = session.query(MsgThread).filter(MsgThread.message_id == one).one_or_none()
                    except Exception as e:
                        resp = None
                        pass

                    if resp:
                        # запоминаем код треда
                        tread_id = resp.thread_uuid
                    else:
                        # если сообщение не обрабатывалось, запоминаем его для обработки
                        new_ref.append(one)

                # если код треда найден
                if tread_id:
                    """
                    # Записываем в тред само сообщение
                    new = MsgThread()
                    new.message_id = msg.message_id
                    new.thread_uuid = tread_id
                    new.orig_date_utc = orig_date_utc
                    try:
                        session.add(new)
                        session.commit()
                    except Exception as e:
                        print "add_message_to_thread(). Ошибка записи сообщения в тред. MSGID: %s" % msg.message_id
                        print "add_message_to_thread(). Ошибка: ", str(e)
                        raise e
                    """
                    pass
                # если код не найден, то это новое сообщение в новом треде
                else:
                    # Создаем новый тред
                    tread_id= uuid.uuid4().__str__()
                    """
                    # Записываем в тред само сообщение
                    new = MsgThread()
                    new.message_id = msg.message_id
                    new.thread_uuid = tread_id
                    new.orig_date_utc = orig_date_utc
                    try:
                        session.add(new)
                        session.commit()
                    except Exception as e:
                        print "add_message_to_thread(). Ошибка записи сообщения в тред. MSGID: %s" % msg.message_id
                        print "add_message_to_thread(). Ошибка: ", str(e)
                        raise e
                    """

                # Записываем в тред все новые msg_id из references и in-reply-to
                # Делаем это перед записью самого сообщения
                for one in new_ref:
                    try:
                        # ищем сообщение в MsgRaw используем orig_date_str
                        resp = session.query(MsgRaw).filter(MsgRaw.message_id == one).one_or_none()
                    except Exception as e:
                        pass
                        resp = None

                    new = MsgThread()
                    new.message_id = one
                    new.thread_uuid = tread_id
                    if resp:
                        try:
                            orig_date_utc = parse(resp.orig_date_str).astimezone(tzutc()).replace(tzinfo=None)
                        except Exception as e:
                            print "MSGID: ", msg.message_id
                            print "Create date: ", msg.orig_date_str
                            print "add_message_to_thread(). Ошибка считывания времени в UTC. %s" % str(e)
                            orig_date_utc = None
                        new.orig_date_utc = orig_date_utc
                    else:
                        new.orig_date_utc = None

                    try:
                        session.add(new)
                        session.commit()
                    except Exception as e:
                        print "add_message_to_thread(). Ошибка записи сообщения в тред. MSGID: %s" % msg.message_id
                        print "add_message_to_thread(). Ошибка: ", str(e)
                        raise e

                # Записываем в тред само сообщение
                new = MsgThread()
                new.message_id = msg.message_id
                new.thread_uuid = tread_id
                new.orig_date_utc = orig_date_utc
                try:
                    session.add(new)
                    session.commit()
                except Exception as e:
                    print "add_message_to_thread(). Ошибка записи сообщения в тред. MSGID: %s" % msg.message_id
                    print "add_message_to_thread(). Ошибка: ", str(e)
                    raise e

            else:
                # если в сообщении   пустые References и InReplyTo, то считаем его новым (первым в треде)
                # Иногда это не так и надо искать другими методами (например, по полю Тема)
                # TODO: искать другими методами (например, по полю Тема)
                new_id = uuid.uuid4().__str__()
                new = MsgThread()
                new.message_id = msg.message_id
                new.thread_uuid = new_id
                new.orig_date_utc = orig_date_utc
                try:
                    session.add(new)
                    session.commit()
                except Exception as e:
                    print "add_message_to_thread(). Ошибка записи сообщения в тред. MSGID: %s" % msg.message_id
                    print "add_message_to_thread(). Ошибка: ", str(e)
                    raise e

    finally:
        session.close()


def create_full_thread_html_document(msg_id=None):
    """
    Функция возвращает по идентфиикатору сообщения полный тред переписки в которой оно учавствовало

    :param msg_id: идентификатор сообщения
    :return:
    """

    from mako.lookup import TemplateLookup
    lookup = TemplateLookup(directories=["./templates"], output_encoding="utf-8",
                            input_encoding="utf-8", encoding_errors="replace")

    try:
        messages = get_thread_messages(message_id=msg_id)
    except Exception as e:
        print "notificater. create_attach(). Ошибка: ", str(e)
        raise e
    else:
        if messages:
            # HTML приложение с тредом
            tmpl = lookup.get_template("email_thread_template.html")
            attach_in_html = tmpl.render(orig_msg=msg_id, messages=messages)

            return attach_in_html
        else:
            return ""


def control_center_full_thread_html_document(msg_id=None):
    """
    Функция возвращает по идентфиикатору сообщения полный тред переписки в которой оно учавствовало

    :param msg_id: идентификатор сообщения
    :return:
    """

    from mako.lookup import TemplateLookup
    lookup = TemplateLookup(directories=["./templates/controlcenter"], output_encoding="utf-8",
                            input_encoding="utf-8", encoding_errors="replace")

    try:
        messages = get_thread_messages(message_id=msg_id)
    except Exception as e:
        print "CPO.control_center_full_thread_html_document(). Ошибка: ", str(e)
        raise e
    else:
        if messages:
            # HTML приложение с тредом
            tmpl = lookup.get_template("control_center_email_thread_template.html")
            attach_in_html = tmpl.render(orig_msg=msg_id, messages=messages)

            return attach_in_html
        else:
            return ""


class User(Base):
    """
    Класс для работы с объектами Пользователей системы.

    Список свойств класса:

    :parameter id: sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    :parameter uuid: идентифкатор (sqlalchemy.Column(sqlalchemy.String(50), default=uuid.uuid1()))
    :parameter name: имя пользователя (sqlalchemy.Column(sqlalchemy.String(256)))
    :parameter surname: фамилия пользователя (sqlalchemy.Column(sqlalchemy.String(256)))
    :parameter login: логин пользователя (sqlalchemy.Column(sqlalchemy.String(50)))
    :parameter password: пароль пользователя (sqlalchemy.Column(sqlalchemy.String(20)))
    :parameter disabled: индикатор использования аккаунта пользователя(0 - используется, 1 - отключен \
    (sqlalchemy.Column(sqlalchemy.Integer))
    :parameter access_groups: список групп доступа в которые входит пользователь

    """

    EDIT_FIELDS = ['name', 'surname', 'password']
    ALL_FIELDS = {'name': 'Имя', 'surname': 'Фамилия',
                  'login': 'Логин', 'password': 'Пароль',
                  'id': 'id', 'uuid': 'uuid',
                  'access_groups': 'Группы доступа'}
    VIEW_FIELDS = ['name', 'surname', 'login', 'password', 'access_groups']
    ADD_FIELDS = ['name', 'surname', 'login', 'password', 'access_groups']
    NAME = "Сотрудник"

    STATUS = {0: 'Используется', 1: 'Не используется'}

    __tablename__ = 'users'
    __table_args__ = TABLE_ARGS

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    uuid = sqlalchemy.Column(sqlalchemy.String(50), default=uuid.uuid1())
    name = sqlalchemy.Column(sqlalchemy.String(256), default="")
    surname = sqlalchemy.Column(sqlalchemy.String(256), default="")
    login = sqlalchemy.Column(sqlalchemy.String(256), default="")
    password = sqlalchemy.Column(sqlalchemy.String(256), default="")
    access_groups = sqlalchemy.Column(sqlalchemy.String(256), default="")
    disabled = Column(Integer, default=0)
    email = sqlalchemy.Column(sqlalchemy.String(256), default="")

    def __init__(self):
        self.uuid = uuid.uuid1()
        self.access_groups = str("admin,users")
        self.disabled = 0
        self.list_access_groups = list()
        self.list_access_groups = re.split(",", self.access_groups)

    def read(self):
        self.list_access_groups = list()
        if not self.access_groups == "":
            self.list_access_groups = re.split(",", self.access_groups)


"""
Функция получения объекта пользователь по логину
"""

def get_user_by_login(login):
    """
    Получить данные пользователя по логину.
    Информация о событиях записывается в лог приложения.

    :parameter login: логин пользователя

    :returns: объект класса User. None, если объект не найден или найдено несколько.
    """

    session = Session()
    try:
        user = session.query(User).filter(User.login == login).one()
    except sqlalchemy.orm.exc.NoResultFound:
        print "Пользователь не найден"
        return None
    except sqlalchemy.orm.exc.MultipleResultsFound:
        # status = [False,"Такой логин существует. Задайте другой."]
        print "Найдено множество пользователей."
        return None
    else:
        print "Пользователь найден"
        return user
    finally:
        session.close()


def get_user_by_uuid(user_uuid=None):
    """
    Получить данные пользователя по UUID.
    Информация о событиях записывается в лог приложения.

    :parameter user_uuid: UUID пользователя

    :returns: объект класса User. None, если объект не найден или найдено несколько.
    """

    session = Session()
    try:
        user = session.query(User).filter(User.uuid == user_uuid).one()
    except sqlalchemy.orm.exc.NoResultFound:
        print "Пользователь не найден"
        return None
    except sqlalchemy.orm.exc.MultipleResultsFound:
        # status = [False,"Такой логин существует. Задайте другой."]
        print "Найдено множество пользователей."
        return None
    else:
        print "Пользователь найден"
        return user
    finally:
        session.close()


def get_all_users(sort=None, disabled=False):
    """
    Получить данные всех пользователей.

    :param sort: один из вариантов для сортировки ['name', 'surname', 'login']
    :returns: список пользователей отсортированный по указанному полю
    """

    session = Session()
    try:
        if disabled:
            dis = [0, 1]
        else:
            dis = [0]

        if sort == "name":
            resp = session.query(User).filter(User.disabled == 0).order_by(User.name.desc()).all()
        elif sort == "surname":
            resp = session.query(User).filter(User.disabled.in_(dis)).order_by(User.surname.desc()).all()
        elif sort == "login":
            resp = session.query(User).filter(User.disabled == 0).order_by(User.login.desc()).all()
        else:
            resp = session.query(User).filter(User.disabled == 0).all()
    except Exception as e:
        print "get_all_user(). Ошибка: %s" % str(e)
        return list()
    else:
        return resp
    finally:
        session.close()


def get_all_users_dict(disabled=False):
    """
    Получить данные всех пользователей в виде словаря. UUID - ключ.

    :param disabled: включать в результат отключенных или нет
    :returns: словарь пользователей
    """

    session = Session()
    try:
        if disabled:
            dis = [0, 1]
        else:
            dis = [0]
        resp = session.query(User).filter(User.disabled.in_(dis)).all()
    except Exception as e:
        print "CPO.Get_all_user_dict(). Ошибка: %s" % str(e)
        return dict()
    else:
        resp1 = dict()
        for one in resp:
            resp1[one.uuid] = one
        return resp1
    finally:
        session.close()


def change_users_status(user_uuid=None):
    """
    Меняет статус пользователя между состояниями.

    :param user_uuid:
    :return:
    """

    session = Session()
    try:
        user = session.query(User).filter(User.uuid == user_uuid).one()
    except Exception as e:
        print "change_users_status(). Ошибка. %s" % str(e)
        raise e
    else:
        if user.disabled:
            user.disabled = 0
        else:
            user.disabled = 1
        session.commit()

    finally:
        session.close()


def create_user(name=None, surname=None, login=None, password=None, email=None, access_groups=None, status=None):

    print login
    print name
    print surname
    print email
    print password
    print access_groups
    print status

    for one in access_groups:
        if one not in ACCESS_GROUPS.keys():
            exc = ValueError("Указана не существующая группа доступа < %s >." % one)
            raise exc

    print "Проверка групп пройдена."

    session = Session()
    try:
        new_user = User()
        new_user.uuid = uuid.uuid4().__str__()
        new_user.name = str(name)
        new_user.surname = str(surname)
        new_user.login = str(login)
        new_user.password = str(password)
        new_user.email = str(email)
        new_user.disabled = int(status)
        print ",".join(access_groups)
        new_user.access_groups = ",".join(access_groups)

        session.add(new_user)
        session.commit()

        print "Пользователь создан."

    except Exception as e:
        print "CPO.create_user(). Ошибка при создании пользователя. %s" % str(e)
        raise e
    else:
        pass
    finally:
        session.close()


def update_user(user_uuid=None, name=None, surname=None, login=None, password=None, email=None,
                access_groups=None, status=None):

    print user_uuid
    print login
    print name
    print surname
    print email
    print password
    print access_groups
    print status

    for one in access_groups:
        if one not in ACCESS_GROUPS.keys():
            exc = ValueError("Указана не существующая группа доступа < %s >." % one)
            raise exc

    print "Проверка групп пройдена."

    session = Session()
    try:
        new_user = session.query(User).filter(User.uuid == user_uuid).one()
    except Exception as e:
        print "CPO.update_user(). Ошибка при получении пользователя. %s" % str(e)
        raise e

    try:

        new_user.name = str(name)
        new_user.surname = str(surname)
        new_user.login = str(login)
        new_user.password = str(password)
        new_user.email = str(email)
        new_user.disabled = int(status)
        print ",".join(access_groups)
        new_user.access_groups = ",".join(access_groups)

        session.commit()

        print "Пользователь изменен."

    except Exception as e:
        print "CPO.update_user(). Ошибка при изменении пользователя. %s" % str(e)
        raise e
    else:
        pass
    finally:
        session.close()


class WatchMarker(Base):

    __tablename__ = "watch_marker"
    __table_args__ = TABLE_ARGS

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    client_marker = sqlalchemy.Column(sqlalchemy.String(256), default="")  # маркер для поиска в полях сообщений
    user_uuid = sqlalchemy.Column(sqlalchemy.String(256), default="")  # user uuid
    channel_type = sqlalchemy.Column(Integer, default=0)  # id of channel type for CLIENT_CHANNEL_TYPE. Def: 0=email


def get_watch_list(user_uuid=None, is_admin=False):

    if user_uuid:
        # будет возвращен словарь из маркеров для указанного пользователя

        session = Session()
        try:
            if is_admin:
                resp = session.query(WatchMarker).all()
            else:
                resp = session.query(WatchMarker).filter(WatchMarker.user_uuid == user_uuid).all()
        except sqlalchemy.orm.exc.NoResultFound as e:
            print "CPO.get_watch_list(). Ничего не найдено для пользователя %s. %s" % (user_uuid, str(e))
            return list()
        except Exception as e:
            print "CPO.get_watch_list(). Ошибка при поиске для пользователя %s. %s" % (user_uuid, str(e))
            raise e
        else:
            result = list()
            for one in resp:
                result.append(one.client_marker)

            # Убираем дубли
            result = list(set(result))

            return result
        finally:
            session.close()
    else:
        # возвращен словарь маркеров и привязаных к ним сотрудников
        session = Session()
        try:
            resp = session.query(WatchMarker).all()
        except sqlalchemy.orm.exc.NoResultFound as e:
            print "CPO.get_watch_list(). Список маркеров пуст. %s" % str(e)
            return dict()
        except Exception as e:
            print "CPO.get_watch_list(). Ошибка при поиске. %s" % str(e)
            raise e
        else:
            result = dict()
            for one in resp:
                if one.client_marker in result.keys():
                    result[one.client_marker].append(one.user_uuid)
                else:
                    result[one.client_marker] = list()
                    result[one.client_marker].append(one.user_uuid)

            return result
        finally:
            session.close()


def create_watch_rec(user_uuid=None, client_marker=None):

    if user_uuid and client_marker:
        session = Session()
        try:
            # Ищем похожую запись
            resp = session.query(WatchMarker).filter(and_(WatchMarker.user_uuid.in_(user_uuid),
                                                           WatchMarker.client_marker == client_marker)).all()
        except Exception as e:
            print "CPO.create_watch_rec(). Ошибка поиска уже созданной записи наблюдения. %s" % str(e)
            raise e
        else:
            check = list()
            for one in resp:
                check.append(one.user_uuid)

            for new_uuid in user_uuid:
                if new_uuid not in check:
                    # если не найдено, создаем новую
                    try:
                        new_watch = WatchMarker()
                        new_watch.client_marker = client_marker
                        new_watch.user_uuid = new_uuid

                        session.add(new_watch)
                        session.commit()
                    except Exception as e:
                        print "CPO.create_watch_rec(). Ошибка создания watch записи. %s" % str(e)
                        raise e

            return [True, "ok"]

        finally:
            session.close()
    else:
        exc = ValueError("Не указаны необходимые параметры: user_uuid, client_marker")
        print "CPO.create_watch_rec(). Ошибка выполнения функции. %s" % str(exc)
        raise exc


def delete_watch_rec(user_uuid=None, client_marker=None):
    if user_uuid and client_marker:
        session = Session()
        try:
            # Ищем похожую запись
            check = session.query(WatchMarker).filter(and_(WatchMarker.user_uuid == user_uuid,
                                                           WatchMarker.client_marker == client_marker)).one_or_none()
        except Exception as e:
            print "CPO.delete_watch_rec(). Ошибка поиска watch записи. %s" % str(e)
            raise e

        else:
            if check:
                # если найдено удаляем
                try:
                    session.delete(check)
                    session.commit()
                except Exception as e:
                    print "CPO.delete_watch_rec(). Ошибка удаления watch записи. %s" % str(e)
                    raise
                else:
                    return [True, "ok"]

        finally:
            session.close()
    else:
        exc = ValueError("Не указаны необходимые параметры: user_uuid, client_marker")
        print "CPO.delete_watch_rec(). Ошибка выполнения функции. %s" % str(exc)
        raise exc


def get_watchers_for_email(message=None):
    """
    Вернуть список емайлов на которые надо отправить уведомления по этому сообщению.
    Проверяем поля ОТ, КОМУ, КОПИЯ.

    :param message:
    :return:
    """

    marker_dict = get_watch_list()

    # print "\n","*"*30,"\n"
    # print "Marker dict: %s" % marker_dict
    # print "MSG sender field: %s" % message.sender, type(message.sender)
    # print "MSG recipients field: %s" % message.recipients, type(message.recipients)
    # print "MSG cc_recipients field: %s" % message.cc_recipients, type(message.cc_recipients)

    fields = str(message.sender).split(",") + str(message.recipients).split(",") + str(message.cc_recipients).split(",")

    # print "Fields list: %s" % fields

    emails = list()
    for one in fields:
        if one != "empty":
            emails.append(one)
            try:
                domain = one.split("@")[1]
            except IndexError:
                emails.append(one)
            except Exception as e:
                print "CPO.get_watchers_for_email(). Ошибка получения доменного имени из : %s. %s" % (one, str(e))
            else:
                emails.append(domain)

    # удаляем дубликаты
    emails = set(emails)
    emails = list(emails)

    # print "Emails SET: %s" % emails

    # получаем список пользователей
    try:
        users = get_all_users_dict()
    except Exception as e:
        print "CPO.get_watchers_for_email(). Ошибка получения списка пользователей. %s" % str(e)
        # Что-то делаем если список не получен, возвращаем спец список для таких случаев
        return FAIL_NOTIFY_LIST
    else:
        # print "Users list: %s" % users

        result = list()
        user_list = list()
        for marker in marker_dict.keys():

            # print "Marker: %s" % marker

            # для каждого маркера, проверяем его наличие
            if marker in emails and marker_dict.get(marker):
                user_list += marker_dict.get(marker)

        for one in user_list:
            # print "Email for user: %s" % one

            # Получаем емайл пользователей
            try:
                user = users[one]
            except Exception as e:
                print "CPO.get_watchers_for_email(). Ошибка получения пользователя по UUID < %s >. %s"\
                      % (one, str(e))
            else:
                if user.email and user.email not in result:
                    print "Email: %s" % user.email
                    result.append(user.email)

        if not result:
            # Возвращаем спец список для таких случаев
            return FAIL_NOTIFY_LIST

        return result


def get_watch_domain_list():

    marker_dict = get_watch_list()
    domains = list()

    for one in marker_dict.keys():
        try:
            domain = one.split("@")[1]
        except IndexError:
            domains.append(one)
        except Exception as e:
            print "CPO.get_watchers_for_email(). Ошибка получения доменного имени из : %s. %s" % (one, str(e))
            return ""
        else:
            domains.append(domain)

    domains = set(domains)
    domains = list(domains)

    return "|".join(domains)


class Task(Base):

    __tablename__ = 'tasks'
    __table_args__ = TABLE_ARGS

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    uuid = sqlalchemy.Column(sqlalchemy.String(50), default=uuid.uuid1())  # Task UUID
    responsible = sqlalchemy.Column(sqlalchemy.String(256), default="")  # User UUID
    message_id = sqlalchemy.Column(sqlalchemy.String(256), default="")  # Message ID
    comment = sqlalchemy.Column(sqlalchemy.TEXT, default="")
    status = Column(Integer, default=0)


def get_tasks(msg_id_list=None, task_status=None):
    """
    Получить задачи для сообщений из списка.

    :param msg_id_list:
    :return:
    """

    session = Session()

    try:
        if msg_id_list:
            if task_status == "not closed":
                result = session.query(Task).\
                    filter(and_(Task.message_id.in_(msg_id_list),
                                Task.status != TASK_CLOSED_STATUS)).all()
            else:
                result = session.query(Task).filter(Task.message_id.in_(msg_id_list)).all()
        else:
            # result = session.query(Task).all()
            return dict()
    except Exception as e:
        print "Objects.get_tasks(). Ошибка получения Tasks. %s" % str(e)
        raise e
    else:
        result1 = dict()
        for one in result:
            result1[one.message_id] = one
        return result1
    finally:
        session.close()


def get_task_by_uuid(task_uuid=None):
    """
    Получить задачу по uuid.

    :param task_uuid:
    :return:
    """

    if task_uuid:
        session = Session()

        try:
            result = session.query(Task).filter(Task.uuid == task_uuid).one()
        except Exception as e:
            print "Objects.get_task_by_uuid(). Ошибка получения задачи. %s" % str(e)
            raise e
        else:
            return result
        finally:
            session.close()


def get_tasks_grouped(user_uuid=None, grouped="status", sort="time"):

    session = Session()
    try:
        if sort == "time":
            resp = session.query(Task).filter(Task.responsible == user_uuid).\
                order_by(Task.id.desc()).all()
        else:
            resp = session.query(Task).filter(Task.responsible == user_uuid).\
                order_by(Task.id.desc()).all()

    except Exception as e:
        print "Objects.get_tasks_grouped(). Ошибка получения Tasks. %s" % str(e)
        raise e
    else:
        result = dict()
        task_msgid_list = list()
        if grouped == "status":
            for one in resp:
                task_msgid_list.append(one.message_id)
                if result.get(one.status):
                    result[one.status].append(one)
                else:
                    result[one.status] = list()
                    result[one.status].append(one)
        return result, task_msgid_list
    finally:
        session.close()


def create_task(responsible=None, message_id=None, comment=None, status=None):
    """
    Создание таски для сообщения из WARNING_CATEGORY.

    :param responsible:
    :param message_id:
    :param comment:
    :param status:
    :return:
    """

    session = Session()

    new_task = Task()
    if responsible:
        new_task.responsible = responsible
    else:
        excp = ValueError("Ответственный должен быть указан обязательно.")
        raise excp

    if message_id:
        new_task.message_id = message_id
    else:
        excp = ValueError("Идентификатор сообщения должен быть указан обязательно.")
        raise excp

    if comment:
        new_task.comment = comment

    if status:
        new_task.status = status

    try:
        new_task.uuid = uuid.uuid4().__str__()
        session.add(new_task)
        session.commit()
    except Exception as e:
        print "Objects.create_task(). Ошибка создания Task. %s" % str(e)
        raise e
    else:
        return new_task.uuid
    finally:
        session.close()


def change_task_status(api_uuid=None, status=None, message=None, task_uuid=None):
    """
    Функция смены статуса задач, параметры обязательные.

    :param api_uuid:
    :param status:
    :param message:
    :return:
    """

    if status and message and api_uuid:

        try:
            api_train_rec = get_train_record(uuid=api_uuid)
        except Exception as e:
            print "CPO.change_task_status(). Не могу сменить статус задачи. Ошибка: %s" % str(e)

        else:
            if api_train_rec:
                session = Session()
                try:
                    # получаем задачу по MSG_ID
                    task = session.query(Task).filter(Task.message_id == api_train_rec.message_id).one()
                except sqlalchemy.orm.exc.NoResultFound as e:
                    print "change_task_status. Задача для сообщения %s не найдена. " % api_train_rec.message_id
                    raise e
                except sqlalchemy.orm.exc.MultipleResultsFound as e:
                    print "change_task_status. Найдено много задач для сообщения %s. " % api_train_rec.message_id
                    raise e
                except Exception as e:
                    print "change_task_status. Ошибка. %s" % str(e)
                    raise e

                else:
                    # Записываем сообщение и новый статус задачи
                    cur_time = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
                    message = "<p><i class='task_comment_time'>%s</i> %s</p>" % (cur_time, str(message))
                    if task.comment:
                        task.comment = str(task.comment) + str(message)
                    else:
                        task.comment = str(message)
                    task.status = int(status)

                    session.commit()
                finally:
                    session.close()
    elif status and task_uuid:
        session = Session()
        try:
            # получаем задачу по TASK_UUID
            task = session.query(Task).filter(Task.uuid == task_uuid).one()
        except sqlalchemy.orm.exc.NoResultFound as e:
            print "change_task_status. Задача с UUID %s не найдена. " % task_uuid
            raise e
        except sqlalchemy.orm.exc.MultipleResultsFound as e:
            print "change_task_status. Найдено много задач c UUID %s. " % task_uuid
            raise e
        except Exception as e:
            print "change_task_status. Ошибка при поиске по UUID. %s" % str(e)
            raise e

        else:
            # Записываем сообщение и новый статус задачи
            task.status = int(status)

            session.commit()
        finally:
            session.close()


def change_task_responsible(task_uuid=None, responsible=None):
    """
    Функция смены ответственного задач, параметры обязательные.

    :return:
    """

    if responsible and task_uuid:
        session = Session()
        try:
            # получаем задачу по TASK_UUID
            task = session.query(Task).filter(Task.uuid == task_uuid).one()
        except sqlalchemy.orm.exc.NoResultFound as e:
            print "change_task_responsible. Задача с UUID %s не найдена. " % task_uuid
            raise e
        except sqlalchemy.orm.exc.MultipleResultsFound as e:
            print "change_task_responsible. Найдено много задач c UUID %s. " % task_uuid
            raise e
        except Exception as e:
            print "change_task_responsible. Ошибка при поиске по UUID. %s" % str(e)
            raise e

        else:
            # Записываем сообщение и новый статус задачи
            task.responsible = str(responsible)

            session.commit()
        finally:
            session.close()


def add_task_comment(task_uuid=None, comment=None):
    """
    Функция комментирования задач, параметры обязательные.

    :return:
    """

    if comment and task_uuid:
        session = Session()
        try:
            # получаем задачу по TASK_UUID
            task = session.query(Task).filter(Task.uuid == task_uuid).one()
        except sqlalchemy.orm.exc.NoResultFound as e:
            print "add_task_comment. Задача с UUID %s не найдена. " % task_uuid
            raise e
        except sqlalchemy.orm.exc.MultipleResultsFound as e:
            print "add_task_comment. Найдено много задач c UUID %s. " % task_uuid
            raise e
        except Exception as e:
            print "add_task_comment. Ошибка при поиске по UUID. %s" % str(e)
            raise e

        else:
            # TODO: проверка comment на кросс-скрипты. ТОлько допустимые символы.

            cur_time = datetime.datetime.now().strftime("%d-%m-%Y %H:%M")
            comment = "<p><i class='task_comment_time'>%s</i> %s</p>" % (cur_time, str(comment))

            # Записываем сообщение и новый статус задачи
            if task.comment:
                task.comment = str(task.comment) + str(comment)
            else:
                task.comment = str(comment)

            session.commit()
        finally:
            session.close()


class PredictionStatistics(Base):

    __tablename__ = 'prediction_statistics'
    __table_args__ = TABLE_ARGS

    id = Column(sqlalchemy.Integer, primary_key=True)
    week_number = Column(sqlalchemy.Integer, default=0)
    date = Column(sqlalchemy.DATETIME())
    category = Column(sqlalchemy.String(256), default="")
    msg_all = Column(sqlalchemy.Integer, default=0)
    msg_in_cat = Column(sqlalchemy.Integer, default=0)
    msg_in_cat_check = Column(sqlalchemy.Integer, default=0)
    msg_in_cat_wrong = Column(sqlalchemy.Integer, default=0)
    error_in_cat = Column(sqlalchemy.Float, default=0.0)
    accuracy_in_cat = Column(sqlalchemy.Float, default=0.0)
    full_accuracy = Column(sqlalchemy.Float, default=0.0)
    train_epoch = Column(sqlalchemy.Integer, default=0)


def pred_stat_compute(for_day=None):

    global CURRENT_TRAIN_EPOCH
    CURRENT_TRAIN_EPOCH = read_epoch()

    if not for_day or not CURRENT_TRAIN_EPOCH:
        exc = ValueError("Не указаны параметры.")
        raise exc
    else:
        # правильные даты
        start_date = datetime.datetime.strptime("%s-%s-%s 00:00:00" %
                                                (for_day.year, for_day.month, for_day.day),
                                                "%Y-%m-%d %H:%M:%S")
        end_date = datetime.datetime.strptime("%s-%s-%s 23:59:59" % (for_day.year, for_day.month, for_day.day),
                                              "%Y-%m-%d %H:%M:%S")

    # print "Start_date: ", start_date
    # print "End_date: ", end_date

    # Общее количество классифицированных сообщений
    session = Session()

    try:
        resp = session.query(Msg).filter(and_(Msg.create_date >= start_date,
                                              Msg.create_date <= end_date,
                                              Msg.isclassified == 1)).count()
    except Exception as e:
        print str(e)
        session.close()
        raise e
    else:
        msg_all = int(resp)
        print "общее количество классифицированных сообщений: %s" % resp

    cat = GetCategory().keys()
    msg_cat = dict()
    msg_cat_check = dict()
    msg_in_cat_wrong = dict()
    error_in_cat = dict()
    accuracy_in_cat = dict()

    # Количество сообщений, определенных системой, во всех категориях
    for c in cat:
        msg_cat[c] = 0
        msg_cat_check[c] = 0
        msg_in_cat_wrong[c] = 0
        error_in_cat[c] = 0.0
        accuracy_in_cat[c] = 0.0

    try:
        resp = session.query(TrainAPIRecords.auto_cat, func.count(TrainAPIRecords.auto_cat)).\
            filter(and_(TrainAPIRecords.date >= start_date, TrainAPIRecords.date <= end_date,
                        TrainAPIRecords.train_epoch == CURRENT_TRAIN_EPOCH)).\
            group_by(TrainAPIRecords.auto_cat).all()
    except Exception as e:
        print str(e)
        session.close()
        raise e
    else:

        for n, c in resp:
            msg_cat[n] = c

        print "Количество сообщений, определенных системой, во всех категориях: %s" % resp

    # Количество сообщений, проверенных пользователями, во всех категориях
    try:
        resp = session.query(TrainAPIRecords.auto_cat, func.count(TrainAPIRecords.auto_cat)).\
            filter(and_(TrainAPIRecords.date >= start_date, TrainAPIRecords.date <= end_date,
                        TrainAPIRecords.train_epoch == CURRENT_TRAIN_EPOCH,
                        TrainAPIRecords.user_action == 1)).\
            group_by(TrainAPIRecords.auto_cat).all()
    except Exception as e:
        print str(e)
        session.close()
        raise e
    else:
        for n,c in resp:
            msg_cat_check[n] = c
        print "Количество сообщений, проверенных пользователями, во всех категориях: %s" % resp

    # Количество сообщений во всех категориях, где авто-категория не совпадает с проверочной
    try:
        resp = session.query(TrainAPIRecords.auto_cat, func.count(TrainAPIRecords.auto_cat)).\
            filter(and_(TrainAPIRecords.date >= start_date, TrainAPIRecords.date <= end_date,
                        TrainAPIRecords.train_epoch == CURRENT_TRAIN_EPOCH,
                        TrainAPIRecords.user_action == 1,
                        TrainAPIRecords.user_answer != TrainAPIRecords.auto_cat)).\
            group_by(TrainAPIRecords.auto_cat).all()
    except Exception as e:
        print str(e)
        session.close()
        raise e
    else:
        for n,c in resp:
            msg_in_cat_wrong[n] = c
        print "Количество сообщений во всех категориях, где авто-категория не совпадает с проверочной: %s" % resp

    try:
        try:
            full_accuracy = 1.0 - float(sum([t for t in msg_in_cat_wrong.values()]))/sum([t for t in msg_cat_check.values()])
        except ZeroDivisionError as e:
            print "Full accuracy. Деление на 0."
            full_accuracy = 0.0
        else:
            print "Общая точность системы: ", full_accuracy

        # Удаляем старую статистику за этот день
        try:
            resp = session.query(PredictionStatistics).filter(and_(PredictionStatistics.date >= start_date,
                                                                   PredictionStatistics.date <= end_date)).delete()
            session.commit()
        except Exception as e:
            print str(e)
        else:
            print "Старые данные удалены. for_day = %s" % for_day
            # raw_input()

        for c in cat:

            try:
                error_in_cat[c] = float(msg_in_cat_wrong[c])/msg_cat_check[c]
            except ZeroDivisionError as e:
                print "Erron_in_cat. Деление на 0."
                pass

            try:
                accuracy_in_cat[c] = 1.0 - error_in_cat[c]
            except ZeroDivisionError as e:
                print "accuracy_in_cat. Деление на 0."
                pass

            new_stat = PredictionStatistics()
            new_stat.date = for_day
            new_stat.msg_all = msg_all
            new_stat.category = str(c)
            new_stat.msg_in_cat = msg_cat[c]
            new_stat.msg_in_cat_check = msg_cat_check[c]
            new_stat.msg_in_cat_wrong = msg_in_cat_wrong[c]
            new_stat.error_in_cat = error_in_cat[c]
            new_stat.accuracy_in_cat = accuracy_in_cat[c]
            new_stat.full_accuracy = full_accuracy
            new_stat.train_epoch = CURRENT_TRAIN_EPOCH

            print "Процент ошибок определения системой категории %s: " % c, error_in_cat[c]
            print "Точность системы в категории %s: " % c, accuracy_in_cat[c]
            print "\n"

            session.add(new_stat)
            session.commit()

    except Exception as e:
        print str(e)
        pass

    session.close()


def pred_stat_get_data(start_date=None, end_date=None):
    """
        Возвращает рассчитанные по дням статистические данные за период.

    :param start_date:
    :param end_date:
    :return:
    """

    if not start_date and not end_date:
        exc = ValueError("Не указаны параметры.")
        raise exc
    else:
        # правильные даты
        start_date = datetime.datetime.strptime("%s-%s-%s 00:00:00" %
                                                (start_date.year, start_date.month, start_date.day),
                                                "%Y-%m-%d %H:%M:%S")
        end_date = datetime.datetime.strptime("%s-%s-%s 23:59:59" % (end_date.year, end_date.month, end_date.day),
                                              "%Y-%m-%d %H:%M:%S")
        print start_date, end_date
    session = Session()
    try:
        resp = session.query(PredictionStatistics.date, PredictionStatistics.category, PredictionStatistics).\
            filter(and_(PredictionStatistics.date >= start_date,
                        PredictionStatistics.date <= end_date)).\
            order_by(PredictionStatistics.date).all()

    except Exception as e:
        print str(e)
        session.close()
        raise e
    else:

        return resp


def pred_stat_get_data_agr(start_date=None, end_date=None):
    """
        Возвращает рассчитанные по дням статистические данные за период.
        Возвращаются суммы за период для: msg_all, msg_in_cat, msg_in_cat_check, msg_in_cat_wrong, error_in_cat
        Рассчитываются данные для: accuracy_in_cat, full_accuracy

    :param start_date:
    :param end_date:
    :return:
    """

    if not start_date and not end_date:
        exc = ValueError("Не указаны параметры.")
        raise exc
    else:
        # правильные даты
        start_date = datetime.datetime.strptime("%s-%s-%s 00:00:00" %
                                                (start_date.year, start_date.month, start_date.day),
                                                "%Y-%m-%d %H:%M:%S")
        end_date = datetime.datetime.strptime("%s-%s-%s 23:59:59" % (end_date.year, end_date.month, end_date.day),
                                              "%Y-%m-%d %H:%M:%S")
        print start_date, end_date

    session = Session()
    full_result = dict()

    for cat in GetCategory().keys():

        result = dict(start_date=start_date,
                      end_date=end_date,
                      cat=str(),
                      msg_all=0,
                      msg_in_cat=0,
                      msg_in_cat_check=0,
                      msg_in_cat_wrong=0,
                      error_in_cat=0,
                      accuracy_in_cat=0.0,
                      full_accuracy=0.0)

        result["cat"] = cat
        # считаем msg_all, msg_in_cat, msg_in_cat_check, msg_in_cat_wrong, error_in_cat
        try:
            resp = session.query(func.sum(PredictionStatistics.msg_all),
                                 func.sum(PredictionStatistics.msg_in_cat),
                                 func.sum(PredictionStatistics.msg_in_cat_check),
                                 func.sum(PredictionStatistics.msg_in_cat_wrong)).\
                filter(and_(PredictionStatistics.date >= start_date,
                            PredictionStatistics.date <= end_date,
                            PredictionStatistics.category == cat)).all()
        except Exception as e:
            print str(e)
            raise e
        else:
            if resp[0][0]:
                result["msg_all"] = int(resp[0][0])
                result["msg_in_cat"] = int(resp[0][1])
                result["msg_in_cat_check"] = int(resp[0][2])
                result["msg_in_cat_wrong"] = int(resp[0][3])

                # считаем accuracy_in_cat
                if result["msg_in_cat_check"] != 0:
                    result["error_in_cat"] = float(result["msg_in_cat_wrong"]) / result["msg_in_cat_check"]
                    result["accuracy_in_cat"] = 1.0 - result["error_in_cat"]
                else:
                    result["error_in_cat"] = 0.0
                    result["accuracy_in_cat"] = 0.0

            full_result[cat] = result

    # считаем full_accuracy
    full_error = 0
    full_check = 0
    for cat in full_result.keys():
        full_error += full_result[cat]["msg_in_cat_wrong"]
        full_check += full_result[cat]["msg_in_cat_check"]

    for cat in full_result.keys():
        try:
            full_result[cat]["full_accuracy"] = 1.0 - float(full_error) / full_check
        except ZeroDivisionError:
            full_result[cat]["full_accuracy"] = 0.0

    return full_result


class ViolationStatistics(Base):

    __tablename__ = 'violation_statistics'
    __table_args__ = TABLE_ARGS

    id = Column(sqlalchemy.Integer, primary_key=True)
    week_number = Column(sqlalchemy.Integer, default=0)
    start_date = Column(sqlalchemy.DATETIME())
    end_date = Column(sqlalchemy.DATETIME())
    violation_type = Column(sqlalchemy.Integer, default=0)


class CauseTag(Base):

    __tablename__ = 'cause_tags'
    __table_args__ = TABLE_ARGS

    id = Column(sqlalchemy.Integer, primary_key=True)
    tag = sqlalchemy.Column(sqlalchemy.String(256), default="")


def create_tag(tag=None):

    session = Session()

    try:
        new_tag = CauseTag()
        new_tag.tag = str(tag)
        session.add(new_tag)
        session.commit()
    except Exception as e:
        print str(e)
        raise e
    else:
        return new_tag.id
    finally:
        session.close()


def search_tag(search_string=None, task_tags=None):

    session = Session()

    try:
        resp = session.query(CauseTag).filter(and_(CauseTag.tag.like(search_string),
                                                   not CauseTag.id.in_(task_tags))).order_by(CauseTag.tag.desc()).all()
    except Exception as e:
        print str(e)
        raise e
    else:
        return resp
    finally:
        session.close()


def get_tags(tags_id=None):

    session = Session()

    try:
        if tags_id:
            # только входящие в список
            resp = session.query(CauseTag).filter(CauseTag.id.in_(tags_id)).\
                order_by(CauseTag.tag.desc()).all()
        else:
            # все теги
            resp = session.query(CauseTag).order_by(CauseTag.tag.desc()).all()
    except Exception as e:
        print str(e)
        raise e
    else:
        result = dict()
        for one in resp:
            result[one.id] = one
        return result
    finally:
        session.close()


class TaskCauseTag(Base):
    __tablename__ = 'task_cause_tag'
    __table_args__ = TABLE_ARGS

    id = Column(sqlalchemy.Integer, primary_key=True)
    task_uuid = sqlalchemy.Column(sqlalchemy.String(50), default="")  # Task UUID
    tag_id = sqlalchemy.Column(sqlalchemy.Integer)  # User UUID


def add_cause_to_task(task_uuid=None, tags_id=None):

    session = Session()

    if not isinstance(tags_id, list):
        tags_id = [tags_id]

    try:
        for tag in tags_id:
            new = TaskCauseTag()
            new.task_uuid = str(task_uuid)
            new.tag_id = tag
            session.add(new)
            session.commit()
    except Exception as e:
        print str(e)
        raise e
    finally:
        session.close()


def remove_cause_from_task(task_uuid=None, tags_id=None):

    session = Session()

    if not isinstance(tags_id, list):
        tags_id = [tags_id]

    try:
        session.query(TaskCauseTag).\
            filter(and_(TaskCauseTag.task_uuid == task_uuid,
                        TaskCauseTag.tag_id.in_(tags_id))).delete(synchronize_session=False)
        session.commit()
    except Exception as e:
        print str(e)
        raise e
    finally:
        session.close()


def get_task_cause(task_uuid=None):

    session = Session()

    try:
        resp = session.query(TaskCauseTag.tag_id).filter(TaskCauseTag.task_uuid == task_uuid).all()
    except Exception as e:
        print str(e)
        raise e
    else:
        result = list()
        for i, in resp:
            result.append(i)
        return result
    finally:
        session.close()


class DialogMember(Base):
    __tablename__ = 'dialog_members'
    __table_args__ = TABLE_ARGS

    id = Column(sqlalchemy.Integer, primary_key=True)
    type = Column(sqlalchemy.Integer, default=0)
    uuid = Column(sqlalchemy.String(256), default=uuid.uuid4().__str__())
    name = Column(sqlalchemy.String(256), default="")
    surname = Column(sqlalchemy.String(256), default="")
    emails = Column(sqlalchemy.String(256), default="")
    phone = Column(sqlalchemy.String(256), default="")


def get_dialog_members_list(user_uuid=None, is_admin=False):

    if user_uuid:
        """

        session = Session()
        try:
            if is_admin:
                resp = session.query(WatchMarker).all()
            else:
                resp = session.query(WatchMarker).filter(WatchMarker.user_uuid == user_uuid).all()
        except sqlalchemy.orm.exc.NoResultFound as e:
            print "CPO.get_watch_list(). Ничего не найдено для пользователя %s. %s" % (user_uuid, str(e))
            return list()
        except Exception as e:
            print "CPO.get_watch_list(). Ошибка при поиске для пользователя %s. %s" % (user_uuid, str(e))
            raise e
        else:
            result = list()
            for one in resp:
                result.append(one.client_marker)

            # Убираем дубли
            result = list(set(result))

            return result
        finally:
            session.close()
        """
        pass
    else:
        # возвращаем словарь маркеров и привязанных к ним участников
        session = Session()
        try:
            resp = session.query(DialogMember).all()
        except sqlalchemy.orm.exc.NoResultFound as e:
            print "CPO.get_dialog_members_list(). Список маркеров пуст. %s" % str(e)
            return dict()
        except Exception as e:
            print "CPO.get_dialog_members_list(). Ошибка при поиске. %s" % str(e)
            raise e
        else:
            result = dict()

            for one in resp:
                markers = re.split(",", one.emails) + re.split(",", one.phone)
                for marker in markers:
                    result[marker] = one.uuid

            return result
        finally:
            session.close()


class WarnTaskStatistics(Base):
    __tablename__ = 'warn_task_statistics'
    __table_args__ = TABLE_ARGS

    id = Column(sqlalchemy.Integer, primary_key=True)
    date = Column(sqlalchemy.DATETIME(), default=datetime.datetime.now())
    msg_id = Column(sqlalchemy.String(256), default="")
    member_uuid = Column(sqlalchemy.String(256), default="")


def add_warn_task_stat(msg_id_list=None, start=None, end=None):

    if not isinstance(msg_id_list, list):
        msg_id_list = [msg_id_list]

    start_date = datetime.datetime.strptime("%s-%s-%s 00:00:00" %
                                            (start.year, start.month, start.day),
                                            "%Y-%m-%d %H:%M:%S")
    end_date = datetime.datetime.strptime("%s-%s-%s 23:59:59" % (end.year, end.month, end.day),
                                          "%Y-%m-%d %H:%M:%S")

    session = Session()

    try:
        resp = session.query(Msg.message_id.label("msg_id"), Msg.sender.label("sender"),
                             Msg.recipients.label("to"), Msg.cc_recipients.label("cc"),
                             Msg.create_date.label("date"),
                             TrainAPIRecords.auto_cat.label("auto_cat"),
                             TrainAPIRecords.user_answer.label("user_answer")).\
            join(TrainAPIRecords, TrainAPIRecords.message_id == Msg.message_id).\
            outerjoin(Task, Task.message_id == TrainAPIRecords.message_id).\
            filter(and_(TrainAPIRecords.date >= start_date,
                        TrainAPIRecords.date <= end_date,
                        TrainAPIRecords.auto_cat.in_(WARNING_CATEGORY))).all()
    except Exception as e:
        print str(e)
        raise(e)

    empl_list = get_dialog_members_list()

    for one in resp:
        # print one
        # ищем в полях from, to, cc маркеры которые относятся к сотрудникам, т.е. не входят в CHECK_DOMAINS
        fields = re.split(",", one.sender) + re.split(",", one.to) + re.split(",", one.cc)

        for addr in fields:
            if addr in empl_list.keys():
                print "Fields: ", fields
                # добавляем запись в статистику
                new = WarnTaskStatistics()
                new.msg_id = one.msg_id
                new.date = one.date
                new.member_uuid = empl_list.get(addr)
                new.auto_cat = one.auto_cat
                new.check_cat = one.user_answer
                session.add(new)
                session.commit()


def show_warn_task_stat(start=None, end=None):

    start_date = datetime.datetime.strptime("%s-%s-%s 00:00:00" %
                                            (start.year, start.month, start.day),
                                            "%Y-%m-%d %H:%M:%S")
    end_date = datetime.datetime.strptime("%s-%s-%s 23:59:59" % (end.year, end.month, end.day),
                                          "%Y-%m-%d %H:%M:%S")

    tags = get_tags()

    session = Session()

    """
    try:
        # Количество срабатываний системы у диалогов с участием пользователя
        # Количество подозрительных ситуаций на сотруднике (участнике переписки) за период
        resp = session.query(WarnTaskStatistics.user_uuid.label("user_uuid"),
                             func.count(WarnTaskStatistics.user_uuid).label("count")).\
            filter(and_(WarnTaskStatistics.date >= start_date,
                        WarnTaskStatistics.date <= end_date)).\
            group_by(WarnTaskStatistics.user_uuid).all()

    except Exception as e:
        print str(e)
        raise(e)

    print "Количество подозрительных ситуаций на сотруднике (участнике переписки) за период - %s по %s :" %\
          (start_date, end_date)
    for one in resp:
        print one.user_uuid, " : ", one.count

    try:
        # Кол-во задач из подозрительных ситуаций зафиксированных на сотруднике
        # (где сотрудник участник проблемной ситуации) с разбивкой по причинам, по категориям, по статусу
        my_filter = and_(WarnTaskStatistics.date >= start_date,
                         WarnTaskStatistics.date <= end_date,
                         WarnTaskStatistics.check_cat.in_(WARNING_CATEGORY))

        resp = session.query(WarnTaskStatistics.user_uuid.label("user_uuid"),
                             func.count(WarnTaskStatistics.user_uuid).label("count")).\
            filter(my_filter).\
            group_by(WarnTaskStatistics.user_uuid).all()

        resp_task_status = session.query(WarnTaskStatistics.user_uuid, Task.status, func.count(Task.status)).\
            outerjoin(Task, WarnTaskStatistics.msg_id == Task.message_id).\
            filter(my_filter).\
            group_by(WarnTaskStatistics.user_uuid, Task.status).all()

        # print resp_task_status

        resp_task_cause = session.query(WarnTaskStatistics.user_uuid.label("user_uuid"),
                                        Task.status.label("status"),
                                        TaskCauseTag.tag_id.label("tag_id"),
                                        func.count(TaskCauseTag.task_uuid).label("count")).\
            outerjoin(Task, WarnTaskStatistics.msg_id == Task.message_id).\
            outerjoin(TaskCauseTag, Task.uuid == TaskCauseTag.task_uuid).\
            filter(my_filter).\
            group_by(WarnTaskStatistics.user_uuid, Task.status, TaskCauseTag.tag_id).all()

        print resp_task_cause
        print "\n"

    except Exception as e:
        print str(e)
        raise(e)

    print "Кол-во задач из подозрительных ситуаций зафиксированных на сотруднике за период - %s по %s :" %\
          (start_date, end_date)
    for one in resp:
        print one.user_uuid, " : ", one.count
        print "\tИз них со статусом:"
        for user, status, count in resp_task_status:
            if user == one.user_uuid:
                print "\t\t", TASK_STATUS[status], " : ", count
                print "\t\t Из них с тегом:"
                for row in resp_task_cause:
                    if row.user_uuid == one.user_uuid and row.status == status and row.tag_id:
                        print "\t\t\t", tags.get(row.tag_id).tag, " : ", row.count
                    if not row.tag_id:
                        print "\t\t\tбез тега", " : ", row.count
    """

    users = get_all_users(sort="surname")

    # Количество не проверенных диалогов после срабатывания системы, по ответственным
    try:
        resp = session.query(func.count(TrainAPIRecords.user_action)).\
            filter(and_(TrainAPIRecords.date >= start_date,
                        TrainAPIRecords.date <= end_date,
                        TrainAPIRecords.user_action == 0,
                        TrainAPIRecords.auto_cat.in_(WARNING_CATEGORY))).all()
    except Exception as e:
        print str(e)
        raise(e)
    else:
        non_checked_by_users = resp[0][0]
        print "Подозрительных (не проверенных) :", non_checked_by_users

    # Количество подтвержденных проблем
    try:
        resp = session.query(func.count(TrainAPIRecords.user_action)).\
            filter(and_(TrainAPIRecords.date >= start_date,
                        TrainAPIRecords.date <= end_date,
                        TrainAPIRecords.user_action == 1,
                        TrainAPIRecords.user_answer.in_(WARNING_CATEGORY))).all()
    except Exception as e:
        print str(e)
        raise(e)
    else:
        confirmed_problem = resp[0][0]
        print "Подтвержденных проблем :", confirmed_problem

    # Количество задач с разбивкой по статусу и ответственным
    try:
        resp = session.query(Task.status, Task.responsible, func.count(Task.responsible)).\
            outerjoin(TrainAPIRecords, TrainAPIRecords.message_id == Task.message_id).\
            filter(and_(TrainAPIRecords.date >= start_date,
                        TrainAPIRecords.date <= end_date,
                        TrainAPIRecords.user_action == 1,
                        TrainAPIRecords.user_answer.in_(WARNING_CATEGORY))).\
            group_by(Task.status, Task.responsible).all()
    except Exception as e:
        print str(e)
        raise(e)
    else:
        tasks_by_responsible = resp
        print "Задачи с разбивкой по статусу и ответственным :", tasks_by_responsible

    # Количество задач с разбивкой по статусу и причинам
    try:
        resp = session.query(Task.status, TaskCauseTag.tag_id, func.count(TaskCauseTag.tag_id)).\
            outerjoin(TaskCauseTag, TaskCauseTag.task_uuid == Task.uuid).\
            outerjoin(TrainAPIRecords, TrainAPIRecords.message_id == Task.message_id).\
            filter(and_(TrainAPIRecords.date >= start_date,
                        TrainAPIRecords.date <= end_date,
                        TrainAPIRecords.user_action == 1,
                        TrainAPIRecords.user_answer.in_(WARNING_CATEGORY))).\
            group_by(Task.status, TaskCauseTag.tag_id).all()
    except Exception as e:
        print str(e)
        raise e
    else:
        tasks_by_cause = resp
        print "Задачи с разбивкой по статусу и причинам :", tasks_by_cause

    # Кол-во задач по диалогам с участием сотрудников с разбивкой по статусу
    try:
        resp = session.query(Task.status, WarnTaskStatistics.member_uuid, func.count(WarnTaskStatistics.member_uuid)).\
            outerjoin(TrainAPIRecords, TrainAPIRecords.message_id == Task.message_id).\
            outerjoin(WarnTaskStatistics, WarnTaskStatistics.msg_id == Task.message_id).\
            outerjoin(DialogMember, DialogMember.uuid == WarnTaskStatistics.member_uuid).\
            filter(and_(TrainAPIRecords.date >= start_date,
                        TrainAPIRecords.date <= end_date,
                        TrainAPIRecords.user_action == 1,
                        TrainAPIRecords.user_answer.in_(WARNING_CATEGORY),
                        DialogMember.type == 0)).\
            group_by(Task.status,WarnTaskStatistics.member_uuid).all()
    except Exception as e:
        print str(e)
        raise e
    else:
        tasks_by_empl = resp
        print "Кол-во задач по диалогам с участием сотрудников с разбивкой по статусу :", tasks_by_empl

    # Кол-во задач по диалогам с участием клиентов с разбивкой по статусу
    try:
        resp = session.query(Task.status, WarnTaskStatistics.member_uuid, func.count(WarnTaskStatistics.member_uuid)).\
            outerjoin(TrainAPIRecords, TrainAPIRecords.message_id == Task.message_id).\
            outerjoin(WarnTaskStatistics, WarnTaskStatistics.msg_id == Task.message_id).\
            outerjoin(DialogMember, DialogMember.uuid == WarnTaskStatistics.member_uuid).\
            filter(and_(TrainAPIRecords.date >= start_date,
                        TrainAPIRecords.date <= end_date,
                        TrainAPIRecords.user_action == 1,
                        TrainAPIRecords.user_answer.in_(WARNING_CATEGORY),
                        DialogMember.type == 1)).\
            group_by(Task.status,WarnTaskStatistics.member_uuid).all()
    except Exception as e:
        print str(e)
        raise e
    else:
        tasks_by_client = resp
        print "Кол-во задач по диалогам с участием клиентов с разбивкой по статусу :", tasks_by_client

    return non_checked_by_users, \
           confirmed_problem, \
           tasks_by_responsible, \
           tasks_by_cause, \
           tasks_by_empl, \
           tasks_by_client


def initial_configuration():
    # Фунции которые настраивают константы и глобальные переменные
    global CURRENT_TRAIN_EPOCH
    global CHECK_DOMAINS
    global EXCEPTION_EMAIL

    CHECK_DOMAINS = get_watch_domain_list()

    EXCEPTION_EMAIL = get_exception_list()

    try:
        CURRENT_TRAIN_EPOCH = read_epoch()
    except Exception as e:
        print "Ошибка чтения эпохи. %s" % str(e)
        sys.exit(os.EX_DATAERR)

    print "*" * 30, "\n"
    print "CONFIGURATION INIT"
    print "CHECK_DOMAINS : %s" % CHECK_DOMAINS
    print "EXCEPTION_EMAIL : %s" % EXCEPTION_EMAIL
    print "CURRENT_TRAIN_EPOCH : %s" % CURRENT_TRAIN_EPOCH
    print "*" * 30, "\n"


