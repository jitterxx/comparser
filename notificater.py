#!/usr/bin/python -t
# coding: utf8

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

from configuration import *
from objects import *
import re
import email
from email.header import Header
from smtplib import SMTP_SSL
import datetime
import pdfkit
from sqlalchemy import and_, or_

from mako.lookup import TemplateLookup
lookup = TemplateLookup(directories=["./templates"], output_encoding="utf-8",
                        input_encoding="utf-8", encoding_errors="replace")

__author__ = 'sergey'

"""
1. Читаем результаты классификации из базы
2. Если классификация попадает в условия, то формируем сообщение в адрес менеджера
"""

CATEGORY = GetCategory()
code1, code2 = CATEGORY.keys()


def notify():
    session = Session()

    query = session.query(Msg).filter(and_(Msg.isclassified == 1, Msg.notified == 0)).all()

    for msg in query:
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
                send_email(category=categoryll, orig_msg=msg, msg_uuid=msg_uuid, notify_list=notify_list)
            except Exception as e:
                print "Notificater(). Ошибка отправки сообщения. Ошибка: ", str(e)
                raise e
            else:
                try:
                    msg.notified = 1
                    session.commit()
                except Exception as e:
                    print "Ошибка при отметке уведомления для сообщения. Ошибка: ", str(e)
                    raise e

            print "#" * 30
        else:
            print "Notificater(). Уведомление не отправлено."
            print "#" * 30

        # Чистые сообщения используются для переобучения системы, если была совершена ошибка и пользователь об этом
        # сообщил. При отправке результатов не чистим.
        # session.delete(msg)
        # session.commit()

    session.close()


def send_email(category=None, orig_msg=None, msg_uuid=None, notify_list=None):
    """
    Отправка оповещений на адрес отправителя с результатами классификации.

    :return:
    """

    msg = email.MIMEMultipart.MIMEMultipart()
    from_addr = smtp_email

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

    text = "Результат: \n"
    cat, val = category[0]
    if val != 0:
        text += "\t %s - %.2f%% \n" % (CATEGORY[cat].category, val*100)
    else:
        text += "\t Затрудняюсь определить. \n"

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
    \n""" % (CATEGORY[code1].category, main_link + "%s/%s" % (msg_uuid, CATEGORY[code1].code),
             CATEGORY[code2].category, main_link + "%s/%s" % (msg_uuid, CATEGORY[code2].code))

    body = "Письмо было проанализовано. \n" + text + links_block + orig_text

    msg.preamble = "This is a multi-part message in MIME format."
    msg.epilogue = "End of message"

    # Генерация приложения
    try:
        attach_in_html = create_full_thread_html_document(msg_id=orig_msg.message_id)

        if FILE_ATTACH_TYPE == "html" and attach_in_html:
            part = email.MIMEBase.MIMEBase('application', "octet-stream")
            part.set_payload(attach_in_html)
            email.Encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename="full thread.html"')
            msg.attach(part)
        elif FILE_ATTACH_TYPE == "pdf" and attach_in_html:
            # без X сервера, нужно делать хак от поставщика. Меняется путь к исполняемому файлу
            # https://github.com/JazzCore/python-pdfkit/wiki/Using-wkhtmltopdf-without-X-server
            config = pdfkit.configuration(wkhtmltopdf=WK_HTML_TO_PDF_PATH)
            pdf = pdfkit.from_string(attach_in_html, False, configuration=config)
            part = email.MIMEBase.MIMEBase('application', "octet-stream")
            part.set_payload(pdf)
            email.Encoders.encode_base64(part)
            part.add_header('Content-Disposition', 'attachment; filename="full thread.pdf"')
            msg.attach(part)
    except Exception as e:
        print "notificater. Ошибка при создании приложения. Ошибка: ", str(e)
        attach_in_html = None
        pass
    else:
        print "notificater. Приложение с тредом добавлено к уведомлению."

    # HTML сообщение
    tmpl = lookup.get_template("email_notification.html")
    body_in_html = tmpl.render(main_link=main_link, cat_list=CATEGORY, cat=cat, orig_msg=orig_msg,
                               msg_uuid=msg_uuid, code1=code1, code2=code2, attach=attach_in_html)

    msg.attach(email.MIMEText.MIMEText(body_in_html, "html", "UTF-8"))
    print "Сообщение сформировано."

    # PLAIN text сообщение
    # msg.attach(email.MIMEText.MIMEText(body, "plain", "UTF-8"))

    smtp = SMTP_SSL()

    try:
        smtp.connect(smtp_server)
        smtp.login(from_addr, smtp_pass)
    except Exception as e:
        print "Ошибка подключения к серверу %s с логином %s."  % (smtp_server, from_addr)
        print "Ошибка: ", str(e)
    else:
        msg['From'] = from_addr
        msg['To'] = ""
        msg['Subject'] = Header("Сообщение от Conversation parser", "utf8")
        for addr in to_addr:
            msg.replace_header("To", addr)
            text = msg.as_string()
            try:
                smtp.sendmail(from_addr, addr, text)
            except Exception as e:
                print "Ошибка отправки сообщения на адрес: %s " % addr
                print str(e)
            else:
                print "Отправленно на адрес: %s" % addr
    finally:
        smtp.quit()


notify()

