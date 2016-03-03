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

def get_decoded_email_body(message_body):
    """ Decode email body.

    Detect character set if the header is not set.

    We try to get text/plain, but if there is not one then fallback to text/html.

    :param message_body: Raw 7-bit message body input e.g. from imaplib. Double encoded in quoted-printable and latin-1

    :return: Message body as unicode string
    """

    msg = email.message_from_string(message_body)

    text = ""
    if msg.is_multipart():
        html = None
        for part in msg.get_payload():

            print "%s, %s" % (part.get_content_type(), part.get_content_charset())

            if part.get_content_charset() is None:
                # We cannot know the character set, so return decoded "something"
                text = part.get_payload(decode=True)
                continue

            charset = part.get_content_charset()

            if part.get_content_type() == 'text/plain':
                text = unicode(part.get_payload(decode=True), str(charset), "ignore").encode('utf8', 'replace')

            if part.get_content_type() == 'text/html':
                html = unicode(part.get_payload(decode=True), str(charset), "ignore").encode('utf8', 'replace')

        if text is not None:
            return text.strip()
        else:
            return html.strip()
    else:
        text = unicode(msg.get_payload(decode=True), msg.get_content_charset(), 'ignore').encode('utf8', 'replace')
        return text.strip()

# note that if you want to get text content (body) and the email contains
# multiple payloads (plaintext/ html), you must parse each message separately.
# use something like the following: (taken from a stackoverflow post)
def get_first_text_block(email_message_instance):
    maintype = email_message_instance.get_content_maintype()
    if maintype == 'multipart':
        for part in email_message_instance.get_payload():
            if part.get_content_maintype() == 'text':
                return part.get_payload()
    elif maintype == 'text':
            return email_message_instance.get_payload()

parser = argparse.ArgumentParser(description='Debug option')
parser.add_argument('-d', action='store_true', dest='debug', help='print debug info')
args = parser.parse_args()
debug = args.debug

inbox = mailbox.Maildir(maildir_path, factory=None)
"""
db = MySQLdb.connect(host=db_host, port=db_port, user=db_user, passwd=db_pass, db=db_name, use_unicode=True,
                     charset="utf8")
db.set_character_set('utf8')
cur = db.cursor() 
cur.execute('SET NAMES utf8;')
cur.close()
db.commit()
"""


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
# db.close()


