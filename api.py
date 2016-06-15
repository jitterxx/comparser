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
from auth import AuthController, require, member_of, name_is, all_of, any_of


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
            else:
                # Если ответ пользователя не совпадает с WARNING_CATEGORY,
                # необходимо закрыть таску открытую для этого сообщения
                if category not in WARNING_CATEGORY:
                    # Формируем сообщение
                    session_context = cherrypy.session['session_context']
                    try:
                        text = "Закрыто пользователем %s %s после проверки." % (session_context["user"].name,
                                                                                session_context["user"].surname)
                    except Exception as e:
                        print str(e)
                        text = "Закрыто пользователем после проверки."

                    # Меняем статус задачи на Закрыто
                    try:
                        CPO.change_task_status(api_uuid=uuid, status=2, message=text)
                    except Exception as e:
                        print "api.message(). Ошибка при смене статуса задачи. %s" % str(e)

                tmpl = lookup.get_template("usertrain_page.html")
                return tmpl.render(status=status)


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

"""
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
"""


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


class ControlCenter(object):

    """
        Центр управления для сотрудников. Вся информация и функции для работы с системой.
        Уведомления, статистика, результаты.
    """
    lookup = TemplateLookup(directories=["./templates/controlcenter"], output_encoding="utf-8",
                            input_encoding="utf-8", encoding_errors="replace")

    auth = AuthController()

    @cherrypy.expose
    @require(member_of("users"))
    def index(self, day=None):
        """
        Основная страница центра управления.
        """

        tmpl = self.lookup.get_template("control_center_main.html")
        context = cherrypy.session['session_context']

        today = datetime.datetime.now()
        delta_1 = datetime.timedelta(days=1)
        if day:
            print day
            cur_day = datetime.datetime.strptime(str(day), "%d-%m-%Y")
        else:
            cur_day = today

        print delta_1
        print cur_day
        print today

        # Загружаем сообщения требующие внимания в указанную дату cur_day
        # Указываем кто запрашивает сообщения (доступ по спискам доступа)

        cat = "conflict"
        # список емайл адресов сотрудников или доменов, к которым у этого пользователя есть доступ
        empl_access_list = list()
        # список емайл адресов и доменов клиентов к которым у этого пользователя есть доступ
        client_access_list = list()
        # список данных из API
        actions_train_api = list()

        try:
            actions, actions_msg_id = CPO.get_only_cat_message(for_day=cur_day, cat=cat,
                                                               empl_access_list=empl_access_list,
                                                               client_access_list=client_access_list)
        except Exception as e:
            print "Ошибка. %s" % str(e)
            actions = None
        else:
            if actions:
                pass
                # print actions
            else:
                print "Actions is empty."

            # Запрашиваем данные API для создания ссылок на проверку и результатов проверки, если она уже была
            try:
                actions_train_api = CPO.get_cat_train_api_records(for_day=cur_day,
                                                                  empl_access_list=empl_access_list,
                                                                  client_access_list=client_access_list,
                                                                  actions_msg_id=actions_msg_id)
            except Exception as e:
                print "Ошибка. %s" % str(e)
                actions_train_api = None
            else:
                if actions_train_api:
                    pass
                    # print actions_train_api
                else:
                    print "Actions_train_api is empty."

            # Запрашиваем данные тредов. Треды выводятся в попапе и подгружаются по запросу через JS
            # Запрашиваем данные по действиям предпринятым для разрешения ситуаций
            try:
                # TODO: Таски добавляются когда для сообщений определяется категория из WARNING_CATEGORY
                # TODO: Таска добавляется при ручной категории (после проверки) из из WARNING_CATEGORY

                tasks = CPO.get_tasks(msg_id_list=actions_msg_id)
            except Exception as e:
                print "ControlCenter.index(). Ошибка. %s" % str(e)
                tasks = None
            else:
                print tasks
                pass


        return tmpl.render(session_context=context, today=today, cur_day=cur_day,
                           delta=delta_1, actions=actions, main_link=main_link,
                           category=CPO.GetCategory(), actions_train_api=actions_train_api,
                           tasks=tasks, task_status=CPO.TASK_STATUS)



    @cherrypy.expose
    @require(member_of("users"))
    def show_full_thread(self, msg_id=None):
        """
        Фунция возвращает  HTML документ. Если ошибка, код - 500, если ничего не найдено, код - 404, если
        что-то найдено, код - 200.

        :param msg_id: идентификтор сообщения
        :return: документ с тредом переписки с указанным сообщением
        """
        full_thread = ""

        try:
            full_thread = CPO.control_center_full_thread_html_document(msg_id=msg_id)
        except Exception as e:
            print "ControlCenter.show_full_thread(). Ошибка. %s" % str(e)
            cherrypy.response.status = 500
            full_thread = None
        else:
            if full_thread:
                cherrypy.response.status = 200
            else:
                cherrypy.response.status = 404

        finally:
            return full_thread


    @cherrypy.expose
    @require(member_of("users"))
    def create_task(self, msg_id=None):
        """
        Создание задачи для сообщения.
        :param msg_id:
        :return:
        """

        if msg_id:
            try:
                session_context = cherrypy.session['session_context']
                task_uuid = CPO.create_task(responsible=session_context["user"].login,
                                            message_id=msg_id, comment="", status=0)
            except Exception as e:
                print "ControlCenter.create_task(). Ошибка: %s" % str(e)
                return ShowNotification().index("Произошла внутренняя ошибка.")
            else:
                raise cherrypy.HTTPRedirect("/control_center/task?uuid=%s" % task_uuid)
        else:
            print "ControlCenter.create_task(). Ошибка: не указан MSG_ID сообщения."
            return ShowNotification().index("Произошла внутренняя ошибка. Не указан ID сообщения.")


    @cherrypy.expose
    @require(member_of("users"))
    def task(self, uuid=None):
        """
        Функция показа задачи.
        :param uuid:
        :return:
        """

        if uuid:
            try:
                # получаем задачу и сообщение
                task = CPO.get_task_by_uuid(task_uuid=uuid)
                message = CPO.get_clear_message(msg_id=task.message_id)
                api_data = CPO.get_train_record(msg_id=task.message_id)
                responsible = CPO.get_user_by_login(task.responsible)
                users = CPO.get_all_users(sort="surname")
            except Exception as e:
                print "ControlCenter.task(). Ошибка: %s." % str(e)
                return ShowNotification().index("Произошла внутренняя ошибка.")
            else:
                tmpl = self.lookup.get_template("control_center_task_show.html")
                return tmpl.render(task=task, message=message, responsible=responsible,
                                   session_context=cherrypy.session['session_context'],
                                   task_status=CPO.TASK_STATUS, api_data=api_data,
                                   category=CPO.GetCategory(), users=users)

        else:
            print "ControlCenter.task(). Ошибка: не указан UUID задачи."
            return ShowNotification().index("Произошла внутренняя ошибка. Не указан UUID задачи.")

    @cherrypy.expose
    @require(member_of("users"))
    def change_task_status(self, task_uuid=None, status=None, from_url=None):
        pass

    @cherrypy.expose
    @require(member_of("users"))
    def change_task_reponsible(self, task_uuid=None, responsible=None, from_url=None):
        pass

    @cherrypy.expose
    @require(member_of("users"))
    def add_task_comment(self, task_uuid=None, comment=None, from_url=None):
        pass


class Root(object):
    """
        Основой сервис для запуска API и центров управления
    """

    api = API()
    control_center = ControlCenter()
    # demo = Demo()
    # connect = MainSite()
    # test = Test()
    panel = Panel()

    @cherrypy.expose
    def index(self, ads=None):
        """
        Основная страница лендинга.

        :param ads: код объявления по которому произошел переход.
        :return:
        """

        tmpl = lookup.get_template("index.html")

        if not ads:
            ads = "organic"
        print "ads :", ads

        try:
            user_agent = parse(cherrypy.request.headers['User-Agent'])
        except Exception as e:
            print "Ошибка определения типа клиента. %s" % str(e)
            user_agent = ""

        return tmpl.render(user_agent=user_agent, ads_code=ads)


cherrypy.config.update("server.config")

if __name__ == '__main__':
    cherrypy.quickstart(Root(), '/', "app.config")
