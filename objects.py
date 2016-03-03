#!/usr/bin/python -t
# coding: utf8

import sqlalchemy
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import and_
from configuration import *
import datetime
import email
from email.header import Header, decode_header
from smtplib import SMTP_SSL
from mod_classifier import fisherclassifier, specfeatures
import uuid
import re
from dateutil.parser import *

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

__author__ = 'sergey'

sql_uri = "mysql://%s:%s@%s:%s/%s?charset=utf8" % (db_user, db_pass, db_host, db_port, db_name)

Base = declarative_base()
Engine = sqlalchemy.create_engine(sql_uri, pool_size=20, pool_recycle=3600)
Session = sqlalchemy.orm.sessionmaker(bind=Engine)


class MsgRaw(Base):

    __tablename__ = "email_raw_data"

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

    subject = msg.get('Subject', 'No subject provided')
    subject = line_decoder(subject)

    date_raw = msg.get('Date')
    p = re.compile('[(]')
    if date_raw:
        date_hdr = p.split(date_raw,1)[0]
    else:
        date_hdr = ""

    msg_datetime = datetime.datetime.now()
    try:
        dt = parse(date_hdr).replace(tzinfo=None)
    except Exception as e:
        print "Ошибка времени из сообщения. %s" % str(e)
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

    return [msg_id, from_, to, cc, subject, text2[0], text2[1], msg_datetime, int(broken_msg)]


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


def get_clear_message(msg_id=None):

    session = Session()

    try:
        resp = session.query(Msg).all()
    except Exception as e:
        raise e
    else:
        result = dict()
        for one in resp:
            result[one.message_id] = one

        return result
    finally:
        session.close()


def get_raw_message(msg_id=None):
    session = Session()

    try:
        resp = session.query(MsgRaw).all()
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

