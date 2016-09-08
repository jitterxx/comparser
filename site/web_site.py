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
            url = "/"
        print str(error)
        return tmpl.render(error=error, url=url)


class Blog(object):

    lookup = TemplateLookup(directories=["./templates/blog"], output_encoding="utf-8",
                            input_encoding="utf-8", encoding_errors="replace")

    @cherrypy.expose
    def index(self, post=None, ads=None, utm_source=None, utm_medium=None, utm_campaign=None, utm_term=None):
        if post:
            try:
                tmpl = self.lookup.get_template("blog_post_{}.html".format(post))
            except Exception as e:
                print("Ошибка при получении поста для блога. {}".format(str(e)))
                tmpl = lookup.get_template("error.html")
                return tmpl.render(error="Статья не найдена.", url="/")
            else:
                return tmpl.render()
        else:
            tmpl = self.lookup.get_template("blog_index.html")
            return tmpl.render()


class Root(object):

    # demo = Demo()
    blog = Blog()

    @cherrypy.expose
    def index(self, ads=None, utm_source=None, utm_medium=None, utm_campaign=None, utm_term=None):
        """
        Основная страница лендинга.

        :param ads: код объявления по которому произошел переход.
        :return:
        """

        tmpl = lookup.get_template("landing_ver3.html")

        if not ads:
            ads = "organic"
        try:
            print "Параметры перехода: \n \t ADS: {0}\n\t UTM_SOURCE: {1}\n\t UTM_MEDIUM: {2}\n" \
                  "\t UTM_CAMPAIGN: {3}\n\t UTM_TERM: {4}\n".format(ads, str(utm_source), str(utm_medium),
                                                                    str(utm_campaign), str(utm_term))
        except Exception as e:
            print "Ошибка при выводе параметров запроса. {}".format(str(e))

        try:
            user_agent = parse(cherrypy.request.headers['User-Agent'])
        except Exception as e:
            print "Ошибка определения типа клиента. %s" % str(e)
            user_agent = ""

        return tmpl.render(user_agent=user_agent, ads_code=ads)

    @cherrypy.expose
    def test(self, ads=None, utm_source=None, utm_medium=None, utm_campaign=None, utm_term=None):

        tmpl = lookup.get_template("landing_ver72.html")

        if not ads:
            ads = "organic"
        try:
            print "Параметры перехода: \n \t ADS: {0}\n\t UTM_SOURCE: {1}\n\t UTM_MEDIUM: {2}\n" \
                  "\t UTM_CAMPAIGN: {3}\n\t UTM_TERM: {4}\n".format(ads, str(utm_source), str(utm_medium),
                                                                    str(utm_campaign), str(utm_term))
        except Exception as e:
            print "Ошибка при выводе параметров запроса. {}".format(str(e))

        try:
            user_agent = parse(cherrypy.request.headers['User-Agent'])
        except Exception as e:
            print "Ошибка определения типа клиента. %s" % str(e)
            user_agent = ""

        return tmpl.render(user_agent=user_agent, ads_code=ads)

    @cherrypy.expose
    def yandex_6e3971fd399cf7fd_html(self):
        return lookup.get_template("yandex_6e3971fd399cf7fd.html").render()

    @cherrypy.expose
    def robots_txt(self):
        return lookup.get_template("robots.txt").render()

    @cherrypy.expose
    def sitemap_xml(self):
        return lookup.get_template("sitemap.xml").render()

    @cherrypy.expose
    def demo_request(self, customer_email=None, customer_name=None, customer_phone=None, ads_code=None):

        if not customer_email and not customer_phone:
            text = "К сожалению, вы не указали ни email, ни телефон. <br>" \
                   "Сейчас я верну вас обратно, укажите пожалуйста ваши контакты."
            return ShowNotification().index(error=text, url="/#price")

        if not customer_email:
            customer_email = "не указан"
        if not customer_name:
            customer_name = "не указано"
        if not customer_phone:
            customer_phone = "не указано"
        if not ads_code:
            ads_code = "Запрос подробностей с сайта"

        try:
            WSO.landing_customer_contacts(customer_email=customer_email, customer_name=customer_name,
                                          customer_session=cherrypy.request.headers, customer_phone=customer_phone,
                                          ads_code=ads_code)
        except Exception as e:
            print "Ошибка при попытке отправить контакты с лендинга. %s " % str(e)

        print customer_email, customer_name,  customer_phone, cherrypy.request.headers

        return ShowNotification().index(error="Спасибо! Мы с вами свяжемся в ближайшее время.", url="/")

cherrypy.config.update("web_site_server.config")

if __name__ == '__main__':
    cherrypy.quickstart(Root(), '/', "web_site_app.config")
