#!/usr/bin/python -t
# coding: utf8

"""
1. Читаем результаты классификации из базы
2. Если классификация попадает в условия, то формируем уведомление
"""

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

import logging
import os
#from objects import *
import objects as CPO
import re
import email
from email.header import Header
from smtplib import SMTP_SSL
import datetime
import pdfkit
from sqlalchemy import and_, or_
from mako.lookup import TemplateLookup

__author__ = 'sergey'

try:
    sys.argv[1]
except IndexError:
    limit = 1
else:
    limit = int(sys.argv[1])


logging.basicConfig(format='%(asctime)s.%(msecs)d %(levelname)s %(lineno)d : %(message)s',
                    datefmt='%d-%m-%Y %H:%M:%S',
                    level=logging.DEBUG,
                    filename='{}/{}{}.log'.format(os.path.expanduser("~"), CPO.LOG_PATH, os.path.basename(sys.argv[0])))

print("Лог работы находится в {}{}.log".format(os.path.expanduser("~"), CPO.LOG_PATH, os.path.basename(sys.argv[0])))


# Инициализация переменных и констант
try:
    CPO.initial_configuration()
except Exception as e:
    logging.error("Ошибка чтения настроек CPO.initial_configuration(). {}".format(str(e)))
    raise e

lookup = TemplateLookup(directories=["./templates"], output_encoding="utf-8",
                        input_encoding="utf-8", encoding_errors="replace")

CATEGORY = CPO.GetCategory()
code1, code2 = CATEGORY.keys()


def notify():
    session = CPO.Session()

    try:
        resp = session.query(CPO.Msg, CPO.TrainAPIRecords.uuid, CPO.TrainAPIRecords.auto_cat).\
            join(CPO.TrainAPIRecords, CPO.Msg.message_id == CPO.TrainAPIRecords.message_id).\
            filter(and_(CPO.Msg.isclassified == 1, CPO.Msg.notified == 0)).limit(limit)
    except Exception as e:
        logging.error("Ошибка доступа к БД с результатами классификации. {}".format(str(e)))
        raise e
    else:
        for msg, msg_uuid, msg_auto_cat in resp:

            # Если нужно оповещать только при конфликте
            if CPO.SEND_ONLY_WARNING and msg_auto_cat in CPO.WARNING_CATEGORY:
                logging.debug("{}. Отправляем уведомление.".format(msg_auto_cat))

                try:
                    #  получаем список для уведомления
                    notify_list = CPO.get_watchers_for_email(message=msg)
                    logging.debug("Адресаты уведомления: {}".format(notify_list))

                    # отправляем уведомления
                    if CPO.PRODUCTION_MODE:
                        send_email(category=msg_auto_cat, orig_msg=msg, msg_uuid=msg_uuid, notify_list=notify_list)
                except Exception as e:
                    logging.error("Ошибка отправки сообщения. Ошибка: {}".format(str(e)))
                    raise e
                else:
                    try:
                        msg.notified = 1
                        session.commit()
                    except Exception as e:
                        logging.error("Ошибка при отметке уведомления как отправленного. Ошибка: {}".format(str(e)))
                        raise e

                logging.debug("{}".format("*"*30))

            elif not CPO.SEND_ONLY_WARNING:
                # Если нужно оповещать об всех сообщениях
                logging.debug("{}. Отправляем уведомление.".format(msg_auto_cat))

                try:
                    #  получаем список для уведомления
                    notify_list = CPO.get_watchers_for_email(message=msg)
                    logging.debug("Адресаты уведомления: {}".format(notify_list))

                    # отправляем уведомления
                    if CPO.PRODUCTION_MODE:
                        send_email(category=msg_auto_cat, orig_msg=msg, msg_uuid=msg_uuid, notify_list=notify_list)
                except Exception as e:
                    logging.error("Ошибка отправки сообщения. Ошибка: {}".format(str(e)))
                    raise e
                else:
                    try:
                        msg.notified = 1
                        session.commit()
                    except Exception as e:
                        logging.error("Ошибка при отметке уведомления для сообщения. Ошибка: {}".format(str(e)))
                        raise e

                logging.debug("{}".format("#"*30))
            else:
                # Сообщение не из WARNING_CATEGORY помечаем как с отправленным уведомлением
                try:
                    msg.notified = 1
                    session.commit()
                except Exception as e:
                    logging.debug("Ошибка при отметке уведомления как отправленного. Ошибка: {}".format(str(e)))
                    raise e

                logging.debug("Уведомление не отправлено.")
                logging.debug("{}".format("#"*30))

    finally:
        session.close()

    """
        try:
            resp = session.query(CPO.Msg).filter(and_(CPO.Msg.isclassified == 1, CPO.Msg.notified == 0)).all()
        except Exception as e:
            logging.error("Ошибка доступа к БД с результатами классификации. {}".format(str(e)))
            raise e

        for msg in resp:
            try:
                query1 = session.query(TrainAPIRecords).filter(TrainAPIRecords.message_id == msg.message_id).one()
            except Exception as e:
                print "Ошибка получения uuid для сообщения %s." % msg.message_id
                msg_uuid = ""
            else:
                msg_uuid = query1.uuid

            cats = re.split(":", msg.category)
            # l = dict()
            ll = list()
            for cat in cats:
                m = re.split("-", cat)
                # print m
                if m[1] == "unknown":
                    m[1] = 0
                # l[m[0]] = float(m[1])
                ll.append((m[0], float(m[1])))

            # category = sorted(l.items(), key=lambda (k, v): v, reverse=True)
            categoryll = sorted(ll, key=lambda (k, v): v, reverse=True)

            print "Дата запуска: ", datetime.datetime.now()
            print "MSGID: %s " % msg.message_id
            print "От: %s (%s)" % (msg.sender, msg.sender_name)
            print "\n%s\n" % msg.message_text

            # print category
            print categoryll

            cat, val = categoryll[0]
            # Если нужно оповещать только при конфликте
            if SEND_ONLY_WARNING and cat in WARNING_CATEGORY:
                print "Notificater(). Это %s. Отправляем уведомление." % cat

                try:
                    #  получаем список для уведомления
                    notify_list = get_watchers_for_email(message=msg)
                    print "Notificater(). Адресаты уведомления: ", notify_list

                    # отправляем уведомления
                    if PRODUCTION_MODE:
                        send_email(category=categoryll, orig_msg=msg, msg_uuid=msg_uuid, notify_list=notify_list)
                except Exception as e:
                    print "Notificater(). Ошибка отправки сообщения. Ошибка: ", str(e)
                    raise e
                else:
                    try:
                        msg.notified = 1
                        session.commit()
                    except Exception as e:
                        print "Ошибка при отметке уведомления как отправленного. Ошибка: ", str(e)
                        raise e

                print "#" * 30
            elif not SEND_ONLY_WARNING:
                # Если нужно оповещать об всех сообщениях
                print "Notificater(). Это %s. Отправляем уведомление." % cat

                try:
                    #  получаем список для уведомления
                    notify_list = get_watchers_for_email(message=msg)
                    print "Notificater(). Адресаты уведомления: ", notify_list

                    # отправляем уведомления
                    if PRODUCTION_MODE:
                        send_email(category=categoryll, orig_msg=msg, msg_uuid=msg_uuid, notify_list=notify_list)
                except Exception as e:
                    print "Notificater(). Ошибка отправки сообщения. Ошибка: ", str(e)
                    raise e
                else:
                    try:
                        msg.notified = 1
                        session.commit()
                    except Exception as e:
                        print "Notificater(). Ошибка при отметке уведомления для сообщения. Ошибка: ", str(e)
                        raise e

                print "#" * 30
            else:
                # Сообщение не из WARNING_CATEGORY помечаем как с отправленным уведомлением
                try:
                    msg.notified = 1
                    session.commit()
                except Exception as e:
                    print "Notificater(). Ошибка при отметке уведомления как отправленного. Ошибка: ", str(e)
                    raise e

                print "Notificater(). Уведомление не отправлено."
                print "#" * 30

            # Чистые сообщения используются для переобучения системы, если была совершена ошибка и пользователь об этом
            # сообщил. При отправке результатов не чистим.
            # session.delete(msg)
            # session.commit()
    """


def send_email(category=None, orig_msg=None, msg_uuid=None, notify_list=None):

    """
    Отправка оповещений на адрес отправителя с результатами классификации.

    :return:
    """

    msg = email.MIMEMultipart.MIMEMultipart()
    from_addr = CPO.smtp_email

    # Получаем список адресов для отправки уведомления
    # to_addr = re.split("\\s", to_address)
    to_addr = notify_list

    # Формируем текст сообщения в plain
    orig_text = "\n\n---------------- Исходное сообщение -------------------\n"
    orig_text += "Дата: %s \n" % orig_msg.orig_date
    orig_text += "От кого: %s (%s)\n" % (orig_msg.sender_name, orig_msg.sender)
    orig_text += "Кому: %s (%s) \n" % (orig_msg.recipients_name, orig_msg.recipients)
    orig_text += "Тема: %s" % orig_msg.message_title
    orig_text += "%s" % orig_msg.message_text
    orig_text += "\n------------------------------------------------------\n"

    text = "Результат: {}\n".format(category)

    links_block = """\n
    Независимо от результата укажите, пожалуйста, правильный вариант.
    Для этого перейдите по одной из ссылок: \n
        %s - %s
        %s - %s
    \n
    Ваш ответ будет использован для повышения точности анализа.
    \n
    Спасибо за участие,
    команда Conversation Parser.
    \n""" % (CATEGORY[code1].category, CPO.main_link + "%s/%s" % (msg_uuid, CATEGORY[code1].code),
             CATEGORY[code2].category, CPO.main_link + "%s/%s" % (msg_uuid, CATEGORY[code2].code))

    plain_body = "Письмо было проанализовано. \n" + text + links_block + orig_text

    msg.preamble = "This is a multi-part message in MIME format."
    msg.epilogue = "End of message"

    # Генерация приложения
    try:
        attach_in_html = CPO.create_full_thread_html_document(msg_id=orig_msg.message_id)

        if CPO.FILE_ATTACH_TYPE == "html" and attach_in_html:
            part = email.MIMEBase.MIMEBase('application', "octet-stream")
            part.set_payload(attach_in_html)
            email.Encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename="full thread.html"')
            msg.attach(part)
        elif CPO.FILE_ATTACH_TYPE == "pdf" and attach_in_html:
            # без X сервера, нужно делать хак от поставщика. Меняется путь к исполняемому файлу
            # https://github.com/JazzCore/python-pdfkit/wiki/Using-wkhtmltopdf-without-X-server
            config = pdfkit.configuration(wkhtmltopdf=CPO.WK_HTML_TO_PDF_PATH)
            pdf = pdfkit.from_string(attach_in_html, False, configuration=config)
            part = email.MIMEBase.MIMEBase('application', "octet-stream")
            part.set_payload(pdf)
            email.Encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename="full thread.pdf"')
            msg.attach(part)
    except Exception as e:
        logging.error("Ошибка при создании приложения. Ошибка: {}".format(str(e)))
        attach_in_html = None
        pass
    else:
        logging.debug("*** Приложение с тредом добавлено к уведомлению. ***")

    # HTML сообщение
    tmpl = lookup.get_template("email_notification.html")
    try:
        body_in_html = tmpl.render(main_link=CPO.main_link, cat_list=CATEGORY, orig_msg=orig_msg,
                                   msg_uuid=msg_uuid, code1=code1, code2=code2, attach=attach_in_html)

        msg.attach(email.MIMEText.MIMEText(body_in_html, "html", "UTF-8"))
    except Exception as e:
        logging.error("Ошибка создания html сообщения. {}".format(str(e)))
        try:
            msg.attach(email.MIMEText.MIMEText(plain_body, "plain", "UTF-8"))
        except Exception as e:
            logging.error("Ошибка создания plain сообщения. {}".format(str(e)))
            logging.error("Ошибка создания всего сообщения. {}".format(str(e)))
            raise e
        else:
            logging.debug("Plain - сообщение сформировано.")
    else:
        logging.debug("HTML - Сообщение сформировано.")


    smtp = SMTP_SSL()
    logging.debug("*** Отправка сообщений ***")
    try:
        smtp.connect(CPO.smtp_server)
        smtp.login(from_addr, CPO.smtp_pass)
    except Exception as e:
        logging.error("Ошибка подключения к серверу {} с логином {}.".format(CPO.smtp_server, from_addr))
        logging.error("Ошибка: {}".format(str(e)))
        raise e
    else:
        msg['From'] = from_addr
        msg['To'] = ""
        msg['Subject'] = Header("Уведомление от Conversation parser", "utf8")
        for addr in to_addr:
            msg.replace_header("To", addr)
            text = msg.as_string()
            try:
                smtp.sendmail(from_addr, addr, text)
            except Exception as e:
                logging.error("Ошибка отправки сообщения на адрес: {} ",format(addr))
                logging.error("Ошибка: {}".format(str(e)))
            else:
                logging.debug("Отправленно на адрес: {}".format(addr))
        logging.debug("*** Отправка завершена ***")
    finally:
        smtp.quit()

if __name__ == '__main__':
    if not CPO.PRODUCTION_MODE:
        print "*** Система находится в режиме обучения ***"
        print "*** Уведомления не отправляются ***"
        print "PRODUCTION_MODE: ", CPO.PRODUCTION_MODE
    notify()



