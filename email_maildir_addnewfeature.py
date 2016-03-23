#!/usr/bin/python -t
# coding: utf8

"""
Вспомогательный скрипт заполнения пропущенных данных для форрмирования признаков.
Заполняет пропущенные данные в clear_data и train_data.
"""

import mailbox
import email
import argparse
from configuration import *

# conversation parser object
import objects as CPO

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

parser = argparse.ArgumentParser(description='Debug option')
parser.add_argument('-d', action='store_true', dest='debug', help='print debug info')
args = parser.parse_args()
debug = args.debug

inbox = mailbox.Maildir(maildir_path, factory=None)

session = CPO.Session()


for key in inbox.iterkeys():
    try:
        msg = inbox[key]
    except email.errors.MessageParseError:
        # The message is malformed. Just leave it.
        continue

    if msg.get_subdir() == 'new':
        if debug:
            print '********** Next message **********\n'
            print 'Filename :', key

        try:
            message = CPO.parse_message(msg=msg, debug=debug)

            try:
                clear_msg = session.query(CPO.Msg).filter(CPO.Msg.message_id == message[0]).one_or_none()
            except Exception as e:
                print "EMAIL_MAILDIR_ADDNEW(). Ошибка получения сообщения. MSGID: %s. %s" % (message[0], str(e))
                raise e
            else:
                if clear_msg:
                    # print "Сообщение найдено! Обновляем данные!  MSGID: ", message[0]
                    clear_msg.references = message[9]
                    clear_msg.in_reply_to = message[10]
                    session.commit()
                else:
                    print "Сообщение не найдено! MSGID: ", message[0]

            try:
                train_msg = session.query(CPO.TrainData).filter(CPO.TrainData.message_id == message[0]).one_or_none()
            except Exception as e:
                print "EMAIL_MAILDIR_ADDNEW(). Ошибка получения TRAIN сообщения. MSGID: %s. %s" % (message[0], str(e))
                raise e
            else:
                if train_msg:
                    # print "TRAIN Сообщение найдено! Обновляем данные!  MSGID: ", message[0]
                    # print "REFERENCE: ", message[9]
                    # print "IN-REPLY-TO: ", message[10]

                    train_msg.references = message[9]
                    train_msg.in_reply_to = message[10]
                    train_msg.sender = clear_msg.sender
                    train_msg.sender_name = clear_msg.sender_name
                    train_msg.recipients = clear_msg.recipients
                    train_msg.recipients_name = clear_msg.recipients_name
                    train_msg.cc_recipients = clear_msg.cc_recipients
                    train_msg.cc_recipients_name = clear_msg.cc_recipients_name
                    session.commit()
                else:
                    print "TRAIN Сообщение не найдено! MSGID: ", message[0]

            try:
                raw_msg = session.query(CPO.MsgRaw).filter(CPO.MsgRaw.message_id == message[0]).one_or_none()
            except Exception as e:
                print "EMAIL_MAILDIR_ADDNEW(). Ошибка получения RAW сообщения. MSGID: %s. %s" % (message[0], str(e))
                raise e
            else:
                if raw_msg:
                    # print "Сообщение найдено! Обновляем данные!  MSGID: ", message[0]
                    raw_msg.references = message[9]
                    raw_msg.in_reply_to = message[10]
                    raw_msg.orig_date_str = message[11]
                    session.commit()
                else:
                    print "Сообщение не найдено! MSGID: ", message[0]

        except Exception as e:
            print "Ошибка записи нового сообщения. %s" % str(e)
            print "Message ID: %s" % msg['message-id']
        else:
            # После обработки письма его необходимо пометить как прочитанное и поместитьв папку ~/Maildir/cur
            #msg.set_subdir('cur')
            #msg.add_flag('S')
            #newkey = inbox.add(msg)
            #inbox.remove(key)

            if debug:
                # print 'Перенос в прочитанные...\n'
                print 'Битое: ', message[8]
    else:
        if debug:
            print "Message ID: %s" % msg['message-id']
            print 'Сообщение уже обработано...\n'


session.close()


