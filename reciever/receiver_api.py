# -*- coding: utf-8 -*-


"""

"""
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['/home/sergey/dev/conflict analyser'])

import objects as CPO
import cherrypy
import dateutil.parser
import dateutil.tz
import datetime
import json

__author__ = 'sergey'

class Root(object):

    @cherrypy.expose
    def post(self, json_data=None):

        try:
            message = json.loads(json_data)

            #for key in message:
            #    print "\t", key

        except Exception as e:
            cherrypy.response.status = 500
            return "Error: %s" % str(e)
        else:
            session = CPO.Session()

            # проверяем было ли сообщение с таких MSG-ID записано в базу. Возможно идет повторная передача после сбоя
            # на сборщике
            try:
                resp = session.query(CPO.MsgRaw).filter(CPO.MsgRaw.message_id == message[0]).one_or_none()
            except Exception as e:
                print "receiver_api(). Ошибка при получении MSG-ID. %s" % str(e)
                cherrypy.response.status = 500
                return "Error: %s" % str(e)
            else:
                if resp:
                    # Если существует, значит передача уже состоялась
                    # print "Message already writed."
                    cherrypy.response.status = 200
                    return "Message already writed."
                else:
                    # записываем
                    pass

            try:
                new = CPO.MsgRaw()
                new.message_id = message[0]  # msg_id
                new.sender = message[1]  # from_
                new.recipient = message[2]  # to
                new.cc_recipient = message[3]  # cc
                new.message_title = message[4]  # subject
                new.message_text = message[5]  # text2[0]
                new.message_text_html = message[6]  # text2[1]
                # парсим строку со временем

                msg_datetime = datetime.datetime.now()
                # Вычисляем время создания сообщения в UTC
                try:
                    dt = dateutil.parser.parse(message[7]).replace(tzinfo=None)
                except Exception as e:
                    print "receiver_api(). Ошибка считывания времени. %s" % str(e)
                else:
                    msg_datetime = dt

                new.orig_date = msg_datetime  # msg_datetime
                new.isbroken = message[8]  # int(broken_msg)
                new.references = message[9]  # references (str)
                new.in_reply_to = message[10]  # in_reply_to (str)
                new.orig_date_str = message[11]  # orig_date_str (str)

                session.add(new)
                session.commit()
            except Exception as e:
                print "receiver_api(). Ошибка записи нового сообщения. %s" % str(e)
                print "receiver_api(). Message ID: %s" % message[0]
                cherrypy.response.status = 500
                return "Error: %s" % str(e)
            else:
                cherrypy.response.status = 200
                return "ok"
            finally:
                session.close()


cherrypy.config.update("receiver_server.config")

if __name__ == '__main__':
    cherrypy.quickstart(Root(), '/', "receiver_app.config")
