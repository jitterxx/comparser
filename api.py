# -*- coding: utf-8 -*-


"""

"""
import sys
reload(sys)
sys.setdefaultencoding("utf-8")

from configuration import *
import objects as CPO
import cherrypy
from bs4 import BeautifulSoup
from mako.lookup import TemplateLookup
from user_agents import parse
import datetime

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
                status = CPO.set_user_train_data(uuid, category)
            except Exception as e:
                print str(e)
                return ShowNotification().index("Произошла внутренняя ошибка.")

        return ShowNotification().index(error=status[1], url="/")


class API(object):

    def _cp_dispatch(self, vpath):
        """
        Обработка REST URL
        """
        print len(vpath)
        print vpath

        if len(vpath) == 3 and vpath[0] == "message":
            cherrypy.request.params['uuid'] = vpath[1]
            cherrypy.request.params['category'] = vpath[2]
            print "TRUE."
            return UserTrain()
        else:
            print "FALSE. PATH : %s" % (vpath)
            cherrypy.request.params['error'] = "Неверный адрес."
            return ShowNotification().index("Неверный адрес.")

        return []

    @cherrypy.expose
    def index(self):
        return ShowNotification().index("Неверный адрес api.")


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
            # result, train_uuid = CPO.demo_classify(description)
            result, train_uuid = (None, None)
        except Exception as e:
            print "Ошибка. %s" % str(e)
            return ShowNotification().index("Что-то сломалось, будем чинить.")

        raise cherrypy.HTTPRedirect("/demo/train?msg_uuid=%s" % train_uuid)

    @cherrypy.expose
    def train(self, msg_uuid=None):
        tmpl = lookup.get_template("demo.html")
        try:
            result = CPO.get_message_for_train(msg_uuid)
            print result
        except Exception as e:
            print "Ошибка. %s" % str(e)
            return ShowNotification().index("Что-то сломалось, будем чинить.")

        if not result[0]:
            print "Ошибка. %s" % str(result[1])
            return ShowNotification().index(result[1])

        return tmpl.render(action="show_classify", description=result[1], result=result[2], train_uuid=msg_uuid,
                           main_link=main_link)


class MainSite(object):

    @cherrypy.expose
    def index(self):
        tmpl = lookup.get_template("index.html")

        return tmpl.render()


class Test(object):

    @cherrypy.expose
    def index(self, show_msg=None):
        tmpl = lookup.get_template("message_list_page.html")

        if not show_msg:
            show_msg = 0

        try:
            clear_msg_list = CPO.get_clear_message()
            raw_msg_list = CPO.get_raw_message()
            train_rec = CPO.get_train_record()
            category = CPO.GetCategory()
        except Exception as e:
            print "Ошибка. %s" % str(e)
            return ShowNotification.index(str(e), "/")

        # вычисляем результаты и статистику
        count_raw = len(raw_msg_list.keys())
        count_clear = len(clear_msg_list.keys())
        cat_count = dict()
        # список сообщений по категориям по автоматической классификации (с ошибками)
        msg_cat_list = dict()

        for msg in clear_msg_list.values():
            cat1 = msg.category.split(":")[0]
            cat = cat1.split("-")[0]
            if cat in cat_count.keys():
                cat_count[cat] += 1
                msg_cat_list[cat].append(msg.message_id)
            else:
                cat_count[cat] = 1
                msg_cat_list[cat] = list()
                msg_cat_list[cat].append(msg.message_id)

        err_count = dict()
        pos_count = dict()
        err_all = 0
        count_checked = 0
        for one in category.values():
            err_count[one.code] = 0
            pos_count[one.code] = 0

        for key in train_rec.keys():
            # только если есть оценка от пользователя
            if train_rec[key].user_action:
                cat1 = cat = ""
                count_checked += 1
                msg = clear_msg_list.get(key)
                cat1 = msg.category.split(":")[0]
                cat = cat1.split("-")[0]
                # cat категория сообщения с ID key в списке clear_email
                print "MSG ID:", key
                print "Cat in CLEAR DB: ", cat
                print "Cat in USER data: ", train_rec[key].user_answer

                # если категория в clearDB, не совпадает с указанной пользователем в TRAIN_USER.
                # Увеличиваем количество ошибок в ней.
                if cat != train_rec[key].user_answer:
                    err_count[cat] += 1
                    err_all += 1
                # если категория была определена верно, увеличиваем счетчик позитива
                else:
                    pos_count[cat] += 1

        # Составляем списки сообщений помеченных разными категориями в автоматическом и ручном режиме
        for msg in train_rec.values():
            # Автоматический режим классификации
            cat1 = msg.category.split(":")[0]
            cat = cat1.split("-")[0]
            if cat in cat_count.keys():
                msg_cat_list[cat].append(msg.message_id)
            else:
                msg_cat_list[cat] = list()
                msg_cat_list[cat].append(msg.message_id)

            if msg.message_id not in msg_cat_list[cat]:
                msg_cat_list[cat].append(msg.message_id)

            # Ручной режим классификации
            if msg.user_action:
                if msg.message_id not in msg_cat_list[msg.user_answer]:
                    msg_cat_list[msg.user_answer].append(msg.message_id)

        print "Правильные АВТО классификации: ", pos_count
        print "Ошибки АВТО классификации: ", err_count

        return tmpl.render(clear=clear_msg_list, raw=raw_msg_list, train_rec=train_rec, msg_cat_list=msg_cat_list,
                           main_link=main_link, category=category, cat_count=cat_count,
                           count_raw=count_raw, count_clear=count_clear, err_count=err_count, pos_count=pos_count,
                           count_checked=count_checked, err_all=err_all, show_msg=int(show_msg))


class Panel(object):

    @cherrypy.expose
    def statistics(self, show_msg=None):
        tmpl = lookup.get_template("panel_statistics_page.html")

        if not show_msg:
            show_msg = 0

        # Данные для общей статистики
        try:
            clear_msg_list = CPO.get_clear_message()
            raw_msg_list = CPO.get_raw_message()
            category = CPO.GetCategory()
        except Exception as e:
            print "Ошибка. %s" % str(e)
            return ShowNotification.index(str(e), "/")

        # вычисляем результаты и статистику
        count_raw = len(raw_msg_list.keys())
        count_clear = len(clear_msg_list.keys())

        cat_count = dict()
        # список сообщений по категориям по автоматической классификации (с ошибками)
        msg_cat_list = dict()

        for msg in clear_msg_list.values():
            cat1 = msg.category.split(":")[0]
            cat = cat1.split("-")[0]
            if cat in cat_count.keys():
                cat_count[cat] += 1
                msg_cat_list[cat].append(msg.message_id)
            else:
                cat_count[cat] = 1
                msg_cat_list[cat] = list()
                msg_cat_list[cat].append(msg.message_id)

        epoch_count = CPO.read_epoch()
        train_rec_epoch = dict()
        cat_count_epoch = dict()
        # список ID сообщений по категориям с автоматической классификацией (с ошибками) разделенные по эпохам
        msg_cat_list_epoch = dict()
        # кол-во негативных ошибок
        neg_err_epoch = dict()
        # кол-во позитивных ошибок
        pos_err_epoch = dict()
        # кол-во всех ошибок
        err_all_epoch = dict()
        # кол-во проверенных в ручном режиме сообщений
        count_checked_epoch = dict()
        # даты эпох: начало и конец
        start_date = dict()
        end_date = dict()

        # получаем все записи классификации по эпохам обучения, проверенные и не проверенные
        for epoch in range(0, epoch_count + 1):
            try:
                train_rec = CPO.get_train_record(for_epoch=epoch)
                train_rec_epoch[epoch] = train_rec
            except Exception as e:
                print "Ошибка. %s" % str(e)
                return ShowNotification.index(str(e), "/")

            # Обнуляем исходные данные
            neg_err_epoch[epoch] = dict()
            pos_err_epoch[epoch] = dict()
            err_all_epoch[epoch] = 0
            count_checked_epoch[epoch] = 0

            cat_count_epoch[epoch] = dict()
            msg_cat_list_epoch[epoch] = dict()
            start_date[epoch] = None
            end_date[epoch] = None

            for one in category.values():
                neg_err_epoch[epoch][one.code] = 0
                pos_err_epoch[epoch][one.code] = 0
                msg_cat_list_epoch[epoch][one.code] = list()
                cat_count_epoch[epoch][one.code] = 0

            for msg in train_rec.values():
                # даты эпохи
                date = clear_msg_list.get(msg.message_id).create_date
                if start_date[epoch]:
                    if start_date[epoch] > date:
                        start_date[epoch] = date
                else:
                    start_date[epoch] = date

                if end_date[epoch]:
                    if end_date[epoch] < date:
                        end_date[epoch] = date
                else:
                    end_date[epoch] = date

                # Считаем по категориям
                cat1 = msg.category.split(":")[0]
                cat = cat1.split("-")[0]
                if cat in cat_count_epoch[epoch].keys():
                    cat_count_epoch[epoch][cat] += 1
                    msg_cat_list_epoch[epoch][cat].append(msg.message_id)
                #else:
                #    cat_count_epoch[epoch][cat] = 1
                #    msg_cat_list_epoch[epoch][cat] = list()
                #    msg_cat_list_epoch[epoch][cat].append(msg.message_id)

                # только если есть оценка от пользователя
                if msg.user_action:
                    cat1 = cat = ""
                    count_checked_epoch[epoch] += 1
                    # msg = clear_msg_list.get(msg.message_id)
                    cat1 = msg.category.split(":")[0]
                    cat = cat1.split("-")[0]
                    # cat категория сообщения с ID key в списке clear_email
                    # print "MSG ID:", msg.message_id
                    # print "Cat in CLEAR DB: ", cat
                    # print "Cat in USER data: ", msg.user_answer

                    # если категория в clearDB, не совпадает с указанной пользователем в TRAIN_USER.
                    # Увеличиваем количество ошибок в ней.
                    if cat != msg.user_answer:
                        neg_err_epoch[epoch][cat] += 1
                        err_all_epoch[epoch] += 1
                    # если категория была определена верно, увеличиваем счетчик позитива
                    else:
                        pos_err_epoch[epoch][cat] += 1

                # Составляем списки сообщений помеченных разными категориями в автоматическом и ручном режиме
                # Автоматический режим классификации
                cat1 = msg.category.split(":")[0]
                cat = cat1.split("-")[0]

                if msg.message_id not in msg_cat_list_epoch[epoch][cat]:
                    msg_cat_list_epoch[epoch][cat].append(msg.message_id)

                # Ручной режим классификации
                if msg.user_action:
                    if msg.message_id not in msg_cat_list_epoch[epoch][msg.user_answer]:
                        msg_cat_list_epoch[epoch][msg.user_answer].append(msg.message_id)

        print "Правильные АВТО классификации: ", pos_err_epoch
        print "Ошибки АВТО классификации: ", neg_err_epoch

        return tmpl.render(train_rec_epoch=train_rec_epoch, msg_cat_list_epoch=msg_cat_list_epoch,
                           main_link=main_link, category=category, cat_count_epoch=cat_count_epoch,
                           count_raw=count_raw, count_clear=count_clear, epoch_count=epoch_count,
                           pos_err_epoch=pos_err_epoch, neg_err_epoch=neg_err_epoch, err_all_epoch=err_all_epoch,
                           count_checked_epoch=count_checked_epoch, start_date=start_date, end_date=end_date,
                           clear=clear_msg_list)

    @cherrypy.expose
    def messages(self, day=None):
        tmpl = lookup.get_template("panel_messages_page.html")

        if not day:
            day = datetime.datetime.now()
        else:
            day = datetime.datetime.strptime(day, "%Y-%m-%d")

        delta = datetime.timedelta(days=1)

        # получаем сообщения для указанного дня
        try:
            clear_msg_list = CPO.get_clear_message(for_day=day)
            category = CPO.GetCategory()
        except Exception as e:
            print "Ошибка. %s" % str(e)
            raise e

        train_rec = dict()
        for msg in clear_msg_list:
            try:
                resp = CPO.get_train_record(msg_id=msg.message_id)
            except Exception as e:
                print "Ошибка. %s" % str(e)
                raise e
            else:
                train_rec[msg.message_id] = resp

        return tmpl.render(clear=clear_msg_list, train_rec=train_rec, day=day, now=datetime.datetime.now(),
                           category=category, main_link=main_link, delta=delta)


class Root(object):

    api = API()
    # demo = Demo()
    connect = MainSite()
    # test = Test()
    panel = Panel()

    @cherrypy.expose
    def index(self):
        tmpl = lookup.get_template("landing.html")

        try:
            user_agent = parse(cherrypy.request.headers['User-Agent'])
        except Exception as e:
            print "Ошибка определения типа клиента. %s" % str(e)
            user_agent = ""

        return tmpl.render(user_agent=user_agent)

    @cherrypy.expose
    def send_contacts(self, customer_email=None, customer_phone=None):
        if not customer_email:
            customer_email = "не указан"
        if not customer_phone or customer_phone == "+7":
            customer_phone = "не указан"

        try:
            CPO.landing_customer_contacts(customer_email, customer_phone, cherrypy.request.headers)
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


cherrypy.config.update("server.config")

if __name__ == '__main__':
    cherrypy.quickstart(Root(), '/', "app.config")
