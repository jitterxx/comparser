#!/usr/bin/python -t
# coding: utf8

#import smtpd, smtplib, asyncore
from __future__ import print_function
import re, sys, os, socket, threading, signal
from select import select
import pdb
# conversation parser object
import objects as CPO
import argparse
import email

reload(sys)
sys.setdefaultencoding("utf-8")

CRLF="\r\n"

class Server:
    def __init__(self, listen_addr, remote_addr):
        self.local_addr = listen_addr
        self.remote_addr = remote_addr
        self.srv_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.srv_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.srv_socket.bind(listen_addr)
        self.srv_socket.setblocking(0)

        self.please_die = False

        self.accepted = {}

    def start(self):
        self.srv_socket.listen(10)
        while not self.please_die:
            try:
                ready_to_read, ready_to_write, in_error = select([self.srv_socket], [], [], 0.1)
            except Exception as err:
                pass
            if len(ready_to_read) > 0:
                try:
                    client_socket, client_addr = self.srv_socket.accept()
                except Exception as err:
                    print("Problem:", err)
                else:
                    print("Connection from {0}:{1}".format(client_addr[0], client_addr[1]))
                    tclient = ThreadClient(self, client_socket, self.remote_addr)
                    tclient.start()
                    self.accepted[tclient.getName()] = tclient

    def die(self):
        """Used to kill the server (joining threads, etc...)
        """
        print("Killing all client threads...")
        self.please_die = True
        for tc in self.accepted.values():
            tc.die()
            tc.join()


class ThreadClient(threading.Thread):
    """This class is used to manage a 'client to final SMTP server' connection.
    It is the 'Proxy' part of the program
    """

    (MAIL_DIALOG, MSG_HEADER, MSG_BODY) = range(3)
    message = ""

    def __init__(self, serv, conn, remote_addr):
        threading.Thread.__init__(self)
        self.server = serv
        self.local = conn
        # self.remote_addr = remote_addr
        # self.remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.please_die = False
        self.mbuffer = []
        self.msg_state = ThreadClient.MAIL_DIALOG

    def recv_body_line(self, line):
        """Each line of the body is received here and can be processed, one by one.
        A typical behaviour should be to send it immediatly... or keep all the
        body until it reaches the end of it, and then process it and finally,
        send it.

        Body example:
            Hello foo !
            blabla
        """
        mline = "{0}{1}".format(line, CRLF)
        print("B>", line)
        self.mbuffer.append(line)

    def flush_body(self):
        """This method is called when the end of body (matched with a single
        dot (.) on en empty line is encountered. This method is useful if you
        want to process the whole body.
        """
        for line in self.mbuffer:
            mline = "{0}{1}".format(line, CRLF)
            print("~B>", mline)
            self.message += mline.encode()
            # self.remote.send(mline.encode())

        # Append example:
        #toto = "---{0}{0}Un peu de pub{0}".format(CRLF)
        #self.remote.send(toto.encode())

    def recv_header_line(self, line):
        """All header lines (subject, date, mailer, ...) are processed here.
        """
        mline = "{0}{1}".format(line, CRLF)
        print("H>", line)
        self.message += mline.encode()
        # self.remote.send(mline.encode())

    def recv_server_dialog_line(self, line):
        """All 'dialog' lines (which are mail commands send by the mail client
        to the MTA) are processed here.

        Dialog example:
            MAIL FROM: foo@bar.tld
        """
        mline = "{0}{1}".format(line, CRLF)
        print(">>", line)
        # self.remote.send(mline.encode())

    def run(self):
        """
        Here is the core of the proxy side of this script:
        For each line sent by the Mail client to the MTA, split it on the CRLF
        character, and then:
            If it is a DOT on an empty line, call the 'flush_body()' method
            else, if it matches 'DATA' begin to process the body of the message,
            else:
                if we're processing the header, give each line to the
                   'recv_header_line()' method,
                else if we're processing the 'MAIL DIALOG' give the line to the
                     'recv_server_dialog_line()' method.
                else, consider that we're processing the body and give each line
                      to the 'recv_body_line()' method,
        """
        # self.remote.connect(self.remote_addr)
        # self.remote.setblocking(0)
        mline = "{0}{1}".format("220 Conparser filter", CRLF)
        self.local.send(mline.encode())
        while not self.please_die:

            # Check if the client side has something to say:
            ready_to_read, ready_to_write, in_error = select([self.local], [], [], 0.1)

            if len(ready_to_read) > 0:
                try:
                    msg = self.local.recv(1024)
                except Exception as err:
                    print(str(self.getName()) + " > " + str(err))
                    break
                else:
                    dmsg = msg.decode()
                    if dmsg != "":

                        dmsg = dmsg.strip(CRLF)
                        for line in dmsg.split(CRLF):
                            mline = "{0}{1}".format(line,CRLF)
                            if line != "":
                                if line == "DATA":
                                    # the 'DATA' string means: 'BEGINNING of the # MESSAGE { HEADER + BODY }
                                    self.msg_state = ThreadClient.MSG_HEADER
                                    mline = "{0}{1}".format("354 End data with <CR><LF>.<CR><LF>", CRLF)
                                    self.local.send(mline.encode())
                                    # self.remote.send(mline.encode())
                                elif line == ".":
                                    # a signle dot means 'END OF MESSAGE { HEADER+BODY }'
                                    self.msg_state = ThreadClient.MAIL_DIALOG
                                    self.flush_body()
                                    self.please_die = True
                                    # self.remote.send(mline.encode())
                                else:
                                    # else, the line can be anything and its
                                    # signification depend on the part of the
                                    # whole dialog we're processing.
                                    if self.msg_state == ThreadClient.MSG_HEADER:
                                        self.recv_header_line(line)
                                    elif self.msg_state == ThreadClient.MAIL_DIALOG:
                                        self.recv_server_dialog_line(line)
                                        mline = "{0}{1}".format("250 filter answer", CRLF)
                                        self.local.send(mline.encode())
                                    else:
                                        self.recv_body_line(line)
                            else:
                                # Probably the most important: An empty line
                                # inside the { HEADER + BODY } part of the
                                # message means we're done with the 'HEADER'
                                # part and we're beginning the BODY part.
                                self.msg_state = ThreadClient.MSG_BODY
                    else:
                        break

            # Check if the server side has something to say:
            # ready_to_read, ready_to_write, in_error = select([self.remote], [], [], 0.1)

            """
            if len(ready_to_read) > 0:
                try:
                    msg = self.remote.recv(1024)
                except Exception as err:
                    print(str(self.getName()) + " > " + str(err))
                    break
                else:
                    dmsg = msg.decode()
                    if dmsg != "":
                        print("<< {0}".format(repr(msg.decode())))
                        self.local.send(dmsg.encode())
                    else:
                        break
            """
        # self.remote.close()

        print("SMTP daemon. Message :")
        print(self.message, "-" * 30, "\n")

        if not eater(data=self.message):
            # Вернуть код ошибки, чтобы сообщение попало в deffered очередь postfix
            mline = "{0}{1}".format("421 Message not writed to MsgRaw. Close transmission channel.", CRLF)
            self.local.send(mline.encode())

        else:
            # Все нормально сообщение записано
            mline = "{0}{1}".format("250 ok terminate", CRLF)
            self.local.send(mline.encode())

        self.local.close()
        self.server.accepted.pop(self.getName())

    def die(self):
        self.please_die = True


def eater(data=None):

    parser = argparse.ArgumentParser(description='Debug option')
    parser.add_argument('-d', action='store_true', dest='debug', help='print debug info')
    args = parser.parse_args()
    debug = args.debug

    # собираем объект email для парсинга
    msg = email.message_from_string(data)

    if msg:
        try:
            session = CPO.Session()

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
            new.references = message[9]  # references
            new.in_reply_to = message[10]  # in-reply-to header
            new.orig_date_str = message[11]  # original date header string with timezone info

            session.add(new)
            session.commit()
        except Exception as e:
            print("Ошибка записи нового сообщения. {0}".format(str(e)))
            return False
        else:
            if debug:
                print('Перенос в прочитанные...\n')
                print('Битое: ', message[8])
            return True
        finally:
            session.close()

    print("Eater. Message :")
    print(msg)
    print("-" * 30)

srv = Server(("127.0.0.1", 10025), ("127.0.0.1", 10026))


def die(signum, frame):
    global srv
    srv.die()

signal.signal(signal.SIGINT, die)
signal.signal(signal.SIGTERM, die)

srv.start()