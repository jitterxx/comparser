#!/usr/bin/python -t
# coding: utf8


# import email.parser, email.utils
# import chardet
# import base64
# import html2text
# import MySQLdb
# import datetime

import mailbox

import poplib, email
import re
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
            print 'Filename :',key

        try:
            message = CPO.parse_message(msg=msg, debug=debug)

            new = CPO.MsgRaw()
            new.message_id = message[0]  # msg_id
            new.sender = message[1]  # from_
            new.recipient = message[2]  # to
            new.cc_recipient = message[3]  # cc
            new.message_title = message[4]  # subject
            new.message_text = message[5]  # text2[0]
            new.message_text_html = message[6]  # text2[1]
            new.orig_date = message[7]  # msg_datetime
            new.isbroken = message[8]  # int(broken_msg)
            new.references = message[9]
            new.in_reply_to = message[10]
            new.orig_date_str = message[11]

            session.add(new)
            session.commit()
        except Exception as e:
            print "Ошибка записи нового сообщения. %s" % str(e)
            print "Message ID: %s" % msg['message-id']
        else:
            # После обработки письма его необходимо пометить как прочитанное и поместитьв папку ~/Maildir/cur
            msg.set_subdir('cur')
            msg.add_flag('S')
            newkey = inbox.add(msg)
            inbox.remove(key)
            if debug:
                print 'Перенос в прочитанные...\n'
                print 'Битое: ', message[8]
    else:
        if debug:
            print "Message ID: %s" % msg['message-id']
            print 'Сообщение уже обработано...\n'

session.close()


