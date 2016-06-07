#!/usr/bin/python -t
# -*- coding: utf-8 -*-


"""

"""
import sys
reload(sys)
sys.setdefaultencoding("utf-8")

# from configuration import *
import web_site_objects as WSO
import cherrypy
from bs4 import BeautifulSoup
from mako.lookup import TemplateLookup
from user_agents import parse


__author__ = 'sergey'

lookup = TemplateLookup(directories=["./templates"], output_encoding="utf-8",
                        input_encoding="utf-8", encoding_errors="replace")

class ShowNotification(object):

    def _cp_dispatch(self, vpath):
        """
        Обработка REST URL
        """
        print "ShowNotification"
        print vpath
        return self

    @cherrypy.expose
    def index(self, error=None, url=None):
        tmpl = lookup.get_template("error.html")
        if not url:
            url = "/demo"
        print str(error)
        return tmpl.render(error=error, url=url)


class UserTrain(object):
    def _cp_dispatch(self, vpath):
        """
        Обработка REST URL
        """
        print "UserTrain"
        print vpath
        return self

    @cherrypy.expose
    def index(self, uuid=None, category=None):
        if uuid and category:
            # 1. записать указанный емайл и категорию в пользовательские тренировочные данные
            # 2. Пометить в таблице train_api ответ.
            try:
                status = WSO.set_user_train_data(uuid, category)
            except Exception as e:
                print str(e)
                return ShowNotification().index("Произошла внутренняя ошибка.")

        return ShowNotification().index(status[1])


class Demo(object):

    @cherrypy.expose
    def index(self):
        tmpl = lookup.get_template("demo.html")
        return tmpl.render(action="show")

    @cherrypy.expose
    def analyze(self, description=None):
        print "Desc: %s" % description
        result = ["", 0]

        try:
            result, train_uuid = WSO.demo_classify(description)
        except Exception as e:
            print "Ошибка. %s" % str(e)
            return ShowNotification().index("Что-то сломалось, будем чинить.")

        raise cherrypy.HTTPRedirect("/demo/train?msg_uuid=%s" % train_uuid)

    @cherrypy.expose
    def train(self, msg_uuid=None):
        tmpl = lookup.get_template("demo.html")
        main_link = "https://"
        try:
            result = WSO.get_message_for_train(msg_uuid)
            print result
        except Exception as e:
            print "Ошибка. %s" % str(e)
            return ShowNotification().index("Что-то сломалось, будем чинить.")

        if not result[0]:
            print "Ошибка. %s" % str(result[1])
            return ShowNotification().index(result[1])

        return tmpl.render(action="show_classify", description=result[1], result=result[2], train_uuid=msg_uuid,
                           main_link=main_link)


class Blog(object):

    @cherrypy.expose
    def post1(self):
        tmpl = lookup.get_template("blog_post1_page.html")
        return tmpl.render()

    @cherrypy.expose
    def post2(self):
        tmpl = lookup.get_template("blog_post2_page.html")
        return tmpl.render()

    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect("/")


class Root(object):

    demo = Demo()
    blog = Blog()

    @cherrypy.expose
    def index(self, ads=None):
        """
        Основная страница лендинга.

        :param ads: код объявления по которому произошел переход.
        :return:
        """

        tmpl = lookup.get_template("landing_ver3.html")

        if not ads:
            ads = "organic"
        print "ads :", ads

        try:
            user_agent = parse(cherrypy.request.headers['User-Agent'])
        except Exception as e:
            print "Ошибка определения типа клиента. %s" % str(e)
            user_agent = ""

        return tmpl.render(user_agent=user_agent, ads_code=ads)

    @cherrypy.expose
    def send_contacts(self, customer_email=None, customer_phone=None):
        if not customer_email:
            customer_email = "не указан"
        if not customer_phone or customer_phone == "+7":
            customer_phone = "не указан"

        try:
            WSO.landing_customer_contacts(customer_email=customer_email, customer_phone=customer_phone,
                                      customer_session=cherrypy.request.headers)
        except Exception as e:
            print "Ошибка при попытке отправить контакты с лендинга. %s " % str(e)

        print customer_email, customer_phone,  cherrypy.request.headers
        text = """
        <br>
        <p class="lead text-left">Мы получили ваши контакты и в ближайшее время с вами свяжемся.</p>
        <br>
        <div class="lead text-left">С уважением,<br> команда Conversation Parser.</div>
        """

        return ShowNotification().index(text, "/")

    @cherrypy.expose
    def promo(self, qr=None):
        if not qr:
            name = ""
            phone = ""
            mail = ""
        else:
            promo_codes = {
                "PROMOXSW": {"name": "Артур Владимирович", "phone": "+78127024242", "email": ""},
                "PROMOZAQ": {"name": "Андреас Василис", "phone": "+78124540506", "email": ""},
                "PROMOCDE": {"name": "Александр Дубовенко", "phone": "+78003331111", "email": ""},
                "PROMOVFR": {"name": "", "phone": "+78123209620", "email": ""},
                "PROMOBGT": {"name": "", "phone": " +78126032688", "email": ""},
                "PROMONHY": {"name": "Владимир Николаевич", "phone": "+78126406021", "email": ""},
                "PROMOMJU": {"name": "Валерий Сергеевич", "phone": "+78553393604 ", "email": ""},
                "PROMOPOI": {"name": "Александр Константинович", "phone": "+78124061395", "email": ""}
            }

            if str(qr).upper() in promo_codes.keys():
                name = promo_codes[str(qr).upper()]["name"]
                phone = promo_codes[str(qr).upper()]["phone"]
                mail = promo_codes[str(qr).upper()]["email"]
            else:
                name = ""
                phone = ""
                mail = ""

        tmpl = lookup.get_template("promo_landing_ver3.html")

        return tmpl.render(mail=mail, name=name, phone=phone)



    @cherrypy.expose
    def send_contacts_demo(self, customer_email=None, customer_name=None, pd=None, ads_code=None):
        if not customer_email:
            customer_email = "не указан"
        if not customer_name:
            customer_name = "не указано"

        try:
            WSO.landing_customer_contacts(customer_email=customer_email, customer_name=customer_name,
                                      customer_session=cherrypy.request.headers, pd=pd, ads_code=ads_code)
        except Exception as e:
            print "Ошибка при попытке отправить контакты с лендинга. %s " % str(e)

        print customer_email, customer_name,  cherrypy.request.headers, pd
        text = """
        <br>
        <p class="lead text-left">%s, мы записали email и в ближайшее время свяжемся с Вами.</p>
        <br>
        <div class="lead text-left">С уважением,<br> команда Conversation Parser.</div>
        """ % customer_name

        return ShowNotification().index(text, "/")

    @cherrypy.expose
    def send_contacts_promo(self, customer_email=None, customer_name=None, customer_phone=None):
        if not customer_email:
            customer_email = "не указан"
        if not customer_name:
            customer_name = "не указано"
        if not customer_phone:
            customer_phone = "не указано"

        try:
            WSO.landing_customer_contacts(customer_email=customer_email, customer_name=customer_name,
                                      customer_session=cherrypy.request.headers, customer_phone=customer_phone)
        except Exception as e:
            print "Ошибка при попытке отправить контакты с лендинга. %s " % str(e)

        print customer_email, customer_name,  cherrypy.request.headers, customer_phone

        tmpl = lookup.get_template("contacts_ok_landing_ver3.html")

        return tmpl.render()


cherrypy.config.update("web_site_server.config")

if __name__ == '__main__':
    cherrypy.quickstart(Root(), '/', "web_site_app.config")
