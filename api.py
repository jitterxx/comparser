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
                return ShowNotification().index("Api.UserTrain(). Произошла внутренняя ошибка. "
                                                "Пожалуйста, сообщите о ней администратору.")
            else:
                # Если категория после проверки в WARNING_CAT и ответ новый, то создаем задачу
                if status[0] and category in WARNING_CATEGORY:
                    session_context = cherrypy.session['session_context']

                    try:
                        api_rec = CPO.get_train_record(uuid=uuid)
                    except Exception as e:
                        print "api.UserTrain(). Ошибка получения записи TrainAPI. %s" % str(e)
                        api_rec = None

                    # создаем задачу
                    try:
                        # ответственный за закрытие задачи - проверяющий
                        responsible = session_context.get("user").uuid
                        if not responsible:
                            responsible = "UNKNOWN-UUID"
                        task_uuid = CPO.create_task(responsible=responsible, message_id=api_rec.message_id)

                        # Формируем сообщение
                        try:
                            text = "Создана автоматически после проверки. Пользователь: %s %s." % \
                                   (session_context["user"].name, session_context["user"].surname)
                        except Exception as e:
                            print "api.UserTrain(). Ошибка формирования комментария. %s" % str(e)
                            text = "Создана автоматически после проверки. Пользователь неизвестен."

                        CPO.add_task_comment(task_uuid=task_uuid, comment=text)
                    except Exception as e:
                        print "api.UserTrain(). Ошибка создания Задачи. %s" % str(e)

                """
                try:
                    api_rec = CPO.get_train_record(uuid=uuid)
                except Exception as e:
                    print "api.UserTrain(). Ошибка получения записи TrainAPI. %s" % str(e)
                    api_rec = None

                # Если ответ пользователя не совпадает с WARNING_CATEGORY,
                # необходимо закрыть таску открытую для этого сообщения
                session_context = cherrypy.session['session_context']
                if category not in WARNING_CATEGORY:
                    # Формируем сообщение
                    try:
                        text = "Закрыто пользователем %s %s после проверки." % \
                               (session_context["user"].name, session_context["user"].surname)
                    except Exception as e:
                        print str(e)
                        text = "Закрыто пользователем после проверки."

                    # Меняем статус задачи на Закрыто
                    try:
                        CPO.change_task_status(api_uuid=uuid, status=2, message=text)
                    except Exception as e:
                        print "api.UserTrain(). Ошибка при смене статуса задачи. %s" % str(e)
                else:
                    # Необходимо проверить, была ли это смена или подтверждение WARNING_CAT. Смотреть TrainAPI.auto_cat
                    if api_rec.auto_cat not in WARNING_CATEGORY:
                        # была смена на WARNING_CAT, создаем задачу
                        try:
                            # вычисляем ответственного за закрытие задачи
                            # Стандартно это ответственный за клиента или менеджера
                            responsible = session_context.get("user").uuid
                            if not responsible:
                                responsible = "UNKNOWN-UUID"
                            task_uuid = CPO.create_task(responsible=responsible, message_id=api_rec.message_id)

                            # Формируем сообщение
                            try:
                                text = "Создана автоматически после проверки. Пользователь: %s %s." % \
                                       (session_context["user"].name, session_context["user"].surname)
                            except Exception as e:
                                print "api.UserTrain(). Ошибка формирования комментария. %s" % str(e)
                                text = "Создана автоматически после проверки. Пользователь неизвестен."

                            CPO.add_task_comment(task_uuid=task_uuid, comment=text)
                        except Exception as e:
                            print "api.UserTrain(). Ошибка создания Задачи. %s" % str(e)
                """

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


class Settings(object):

    lookup = TemplateLookup(directories=["./templates/controlcenter"], output_encoding="utf-8",
                            input_encoding="utf-8", encoding_errors="replace")

    @cherrypy.expose
    @require(member_of("users"))
    def index(self):
        # Показываем общие для админов и не админов настройки
        from_url = cherrypy.request.headers.get('Referer')
        tmpl = self.lookup.get_template("control_center_settings.html")
        is_admin = member_of("admin")()

        return tmpl.render(from_url=from_url, session_context=cherrypy.session['session_context'],
                           is_admin=is_admin)

    @cherrypy.expose
    @require(member_of("admin"))
    def administration(self):
        # административные настройки: создание, редактирование пользователей портала(те кто получает уведомления).
        # Настройка списков уведомлений=доступа к сообщениям и событиям
        try:
            # получаем данные о пользователях
            users = CPO.get_all_users(sort="surname", disabled=True)
            # данные для редактирования названия категорий
            categories = CPO.GetCategory()
            # какие категории генерируют уведомления
            cat_warning_list = CPO.WARNING_CATEGORY

            # получаем список уведомлений
            watch_list = CPO.get_watch_list()

        except Exception as e:
            print "ControlCenter.Settings.Administration(). Ошибка: %s." % str(e)
            return ShowNotification().index("Произошла внутренняя ошибка.")
        else:

            print "Watch list: %s" % watch_list

            tmpl = self.lookup.get_template("control_center_settings_administration.html")
            return tmpl.render(session_context=cherrypy.session['session_context'], users=users,
                               categories=categories, user_status=CPO.USER_STATUS, watch_list=watch_list)

    @cherrypy.expose
    @require(member_of("admin"))
    def new_user(self, message=None):
        tmpl = self.lookup.get_template("control_center_new_user.html")
        return tmpl.render(session_context=cherrypy.session['session_context'], message=message,
                           user_status=CPO.USER_STATUS, access_groups=CPO.ACCESS_GROUPS)

    @cherrypy.expose
    @require(member_of("admin"))
    def create_user(self, login=None, name=None, surname=None, email=None, password=None, access_groups=None,
                    status=None):

        if login and email and password and access_groups:
            if not isinstance(access_groups, list):
                access_groups = [access_groups]

            if not name:
                name = email

            if not surname:
                surname = ""

            try:
                result = CPO.create_user(name=name, surname=surname, login=login, password=password,
                                         email=email, access_groups=access_groups, status=status)
            except Exception as e:
                print "API.ControlCenter.Administration.create_user(). Ошибка при создании пользователя. %s" % str(e)
            else:
                raise cherrypy.HTTPRedirect("administration")
        else:
            return self.new_user(message="Не указан логин или емайл или пароль или группа доступа.")

    @cherrypy.expose
    @require(member_of("users"))
    def edit_user(self, user_uuid=None, message=None):
        try:
            user = CPO.get_user_by_uuid(user_uuid=str(user_uuid))
        except Exception as e:
            print "API.ControlCenter.Administration.edit_user(). Ошибка при редактировании пользователя. %s" % str(e)
        else:
            tmpl = self.lookup.get_template("control_center_edit_user.html")
            return tmpl.render(session_context=cherrypy.session['session_context'], message=message,
                               user_status=CPO.USER_STATUS, access_groups=CPO.ACCESS_GROUPS, user=user)


    @cherrypy.expose
    @require(member_of("users"))
    def save_user_data(self, user_uuid=None, login=None, name=None, surname=None, email=None, password=None,
                       access_groups=None, status=None):

        if login and email and password and access_groups and user_uuid:
            if not isinstance(access_groups, list):
                access_groups = [access_groups]

            if not name:
                name = email

            if not surname:
                surname = ""

            try:
                result = CPO.update_user(user_uuid=user_uuid, name=name, surname=surname, login=login, password=password,
                                         email=email, access_groups=access_groups, status=status)
            except Exception as e:
                print "API.ControlCenter.Administration.save_user_data(). Ошибка при редактировании пользователя." \
                      " %s" % str(e)
            else:
                raise cherrypy.HTTPRedirect("administration")
        else:
            return self.edit_user(user_uuid=user_uuid,
                                  message="Не указан логин или емайл или пароль или группа доступа.")


    @cherrypy.expose
    @require(member_of("admin"))
    def change_user_status(self, user_uuid=None):
        if user_uuid:
            try:
                CPO.change_users_status(user_uuid=user_uuid)
            except Exception as e:
                print "ControlCenter.Settings.Administration.change_user_status(). Ошибка: %s." % str(e)
                return ShowNotification().index("Произошла внутренняя ошибка.")

        raise cherrypy.HTTPRedirect("administration")

    @cherrypy.expose
    @require(member_of("admin"))
    def add_watch_rec(self, user_uuid=None, client_marker=None, from_url=None):
        if user_uuid and client_marker:
            # если не список, создаем список с одним элементом
            if not isinstance(user_uuid, list):
                user_uuid = [user_uuid]

            # создаем записи наблюдения
            try:
                status = CPO.create_watch_rec(user_uuid=user_uuid, client_marker=str(client_marker))
            except Exception as e:
                print "ControlCenter.Settings.Administration.create_watch_rec()(). Ошибка: %s." % str(e)
                return ShowNotification().index("Произошла внутренняя ошибка. CPO.create_watch_rec(). ")
            else:
                if not status[0]:
                    return ShowNotification().index(status[1])
                raise cherrypy.HTTPRedirect(from_url or "administration")

        raise cherrypy.HTTPRedirect(from_url or "administration")

    @cherrypy.expose
    @require(member_of("admin"))
    def delete_watch_rec(self, user_uuid=None, client_marker=None, from_url=None):
        if user_uuid and client_marker:
            try:
                status = CPO.delete_watch_rec(user_uuid=str(user_uuid), client_marker=str(client_marker))
            except Exception as e:
                print "ControlCenter.Settings.Administration.delete_watch_rec(). Ошибка: %s." % str(e)
                return ShowNotification().index("Произошла внутренняя ошибка. CPO.delete_watch_rec().")
            else:
                if not status[0]:
                    return ShowNotification().index(status[1])
                raise cherrypy.HTTPRedirect(from_url or "administration")

        raise cherrypy.HTTPRedirect(from_url or "administration")

    @cherrypy.expose
    @require(member_of("admin"))
    def new_watch_rec(self, from_url=None):
        try:
            users = CPO.get_all_users(sort="surname")
        except Exception as e:
            print "ControlCenter.Settings.Administration.new_watch_rec(). Ошибка: %s." % str(e)
            return ShowNotification().index("Произошла внутренняя ошибка. API.new_watch_rec()")
        else:
            tmpl = self.lookup.get_template("control_center_new_watch_rec.html")
            return tmpl.render(session_context=cherrypy.session['session_context'], users=users, from_url=from_url)


class Dialogs(object):

    lookup = TemplateLookup(directories=["./templates/controlcenter"], output_encoding="utf-8",
                            input_encoding="utf-8", encoding_errors="replace")

    @cherrypy.expose
    @require(member_of("users"))
    def all(self,day=None):
        print "day", day

        # Формируем сегодняшнее число или получаем указанную дату
        today = datetime.datetime.now()
        delta_1 = datetime.timedelta(days=1)
        if day:
            print day
            try:
                cur_day = datetime.datetime.strptime(str(day), "%d-%m-%Y")
            except Exception as e:
                print "Dialogs.index(). Ошибка получения даты. %s" % str(e)
                cur_day = today
        else:
            cur_day = today

        session_context = cherrypy.session['session_context']

        # Выводим все диалоги за указанный день. Если день не указан, то за текущий
        # Считаем число из WARNING_CAT общее = проверенные + непроверенные

        # список емайл адресов сотрудников или доменов, к которым у этого пользователя есть доступ
        empl_access_list = list()
        is_admin = member_of("admin")()

        # список емайл адресов и доменов клиентов к которым у этого пользователя есть доступ
        client_access_list = CPO.get_watch_list(user_uuid=session_context.get("user").uuid, is_admin=is_admin)
        print "User UUID: %s" % session_context.get("user").uuid

        try:
            api_list, message_list, message_id_list, unchecked, checked = \
                CPO.get_dialogs(for_day=cur_day, cat=CPO.GetCategory().keys(),
                                empl_access_list=empl_access_list,
                                client_access_list=client_access_list)

        except Exception as e:
            print "Ошибка. %s" % str(e)
            message_id_list = list()
            checked = list()
            api_list = list()
            message_list = list()
            unchecked = list()

        else:
            pass
            # print "API list: %s" % api_list
            # print "Msg list: %s" % message_list
            # print "MSG_ID list: %s" % message_id_list
            # print "Unchecked list: %s" % unchecked
            # print "Сhecked list: %s" % checked

        try:
            # Получаем задачи для всех и задачи со статусом "не закрыто" для проверенных
            task_list = CPO.get_tasks(msg_id_list=message_id_list)
            task_list2 = CPO.get_tasks(msg_id_list=checked, task_status="not closed")
        except Exception as e:
            print "ControlCenter.index(). Ошибка get_tasks(). %s" % str(e)
            task_list = dict()
            task_list2 = dict()
        else:
            # print "Task list: %s" % task_list
            # print "Not closed task list: %s" % task_list2
            pass

        try:
            # Получаем списки сообщений из WARNING_CAT проверенных и не проверенных
            checked_warn, unchecked_warn = CPO.get_dialogs_warn(for_msg_id=message_id_list,
                                                                for_cat=CPO.WARNING_CATEGORY)
        except Exception as e:
            print "ControlCenter.index(). Ошибка get_dialogs_warn(). %s" % str(e)
            checked_warn = unchecked_warn = list()
        else:
            # print "Checked WARNING_CAT msg: %s" % checked_warn
            # print "UnChecked WARNING_CAT msg: %s" % unchecked_warn
            pass

        text = "Все сообщения за этот день."

        tmpl = self.lookup.get_template("control_center_dialogs_all.html")
        return tmpl.render(session_context=session_context, dialog=text,
                           active_cat="all", warn_cat=CPO.WARNING_CATEGORY,
                           today=today, cur_day=cur_day, delta=delta_1, main_link=main_link,
                           category=CPO.GetCategory(), task_status=CPO.TASK_STATUS,
                           task_list=task_list, message_list=message_list, unchecked=unchecked,
                           api_list=api_list, checked_with_task=task_list2, message_id_list=message_id_list,
                           unchecked_warn=unchecked_warn, checked_warn=checked_warn)
    """
            elif cat in cats.keys():
                # Выводим диалоги указанной категории за указанные день. Если день не указан, то за текущий
                # Диалоги с указанной категорией выводятся проверенные и не проверенные.
                # Если категория из WARNING_CAT:
                # - считаем число НЕ проверенных
                # - считаем число проверенных с НЕ закрытыми задачами

                tmpl = self.lookup.get_template("control_center_dialogs_default.html")
                return tmpl.render(session_context=cherrypy.session['session_context'], dialog="show %s" % str(cat),
                                   active_cat=cat)
    """

    @cherrypy.expose
    @require(member_of("users"))
    def warning(self, day=None):
        print "day", day

        # Формируем сегодняшнее число или получаем указанную дату
        today = datetime.datetime.now()
        delta_1 = datetime.timedelta(days=1)
        if day:
            print day
            try:
                cur_day = datetime.datetime.strptime(str(day), "%d-%m-%Y")
            except Exception as e:
                print "Dialogs.index(). Ошибка получения даты. %s" % str(e)
                cur_day = today
        else:
            cur_day = today

        print "Dialog default page"
        session_context = cherrypy.session['session_context']
        # Выводим диалоги (проверенные и не проверенные) с категорией из WARNING_CAT за указанные день.
        # Если день не указан, то выводим за текущий
        # - считаем число НЕ проверенных
        # - считаем чило проверенных с НЕ закрытыми задачами

        # Загружаем диалоги из WARNING_CAT в указанную дату cur_day
        # Указываем кто запрашивает (доступ по спискам доступа)

        # список емайл адресов сотрудников или доменов, к которым у этого пользователя есть доступ
        empl_access_list = list()

        is_admin = member_of("admin")()
        # список емайл адресов и доменов клиентов к которым у этого пользователя есть доступ
        client_access_list = CPO.get_watch_list(user_uuid=session_context.get("user").uuid, is_admin=is_admin)
        # print "User UUID: %s" % session_context.get("user").uuid

        try:
            api_list, message_list, message_id_list, unchecked, checked = \
                CPO.get_dialogs(for_day=cur_day, cat=CPO.WARNING_CATEGORY,
                                empl_access_list=empl_access_list,
                                client_access_list=client_access_list)
        except Exception as e:
            print "Ошибка. %s" % str(e)
            message_id_list = list()
            checked = list()
            api_list = dict()
            message_list = dict()
            unchecked = list()

        else:
            pass
            # print "API list: %s" % api_list
            # print "Msg list: %s" % message_list
            # print "MSG_ID list: %s" % message_id_list
            # print "Unchecked list: %s" % unchecked
            # print "Сhecked list: %s" % checked

        try:
            task_list = CPO.get_tasks(msg_id_list=message_id_list)
            task_list2 = CPO.get_tasks(msg_id_list=checked, task_status="not closed")
        except Exception as e:
            print "ControlCenter.index(). Ошибка. %s" % str(e)
            task_list = dict()
            task_list2 = dict()
        else:
            # print "Task list: %s" % task_list
            # print "Not closed task list: %s" % task_list2
            # print "Cats: %s" % CPO.GetCategory()
            pass
        cat_dict = CPO.GetCategory()
        text = "Проверенные и не проверенные сообщения на которые надо обратить внимание."

        tmpl = self.lookup.get_template("control_center_dialogs_default.html")
        return tmpl.render(session_context=session_context, dialog=text, active_cat=None,
                           today=today, cur_day=cur_day, delta=delta_1, main_link=main_link,
                           category=cat_dict, task_status=CPO.TASK_STATUS,
                           task_list=task_list, message_list=message_list, unchecked=unchecked,
                           api_list=api_list, checked_with_task=task_list2, message_id_list=message_id_list)


class Tasks(object):

    lookup = TemplateLookup(directories=["./templates/controlcenter"], output_encoding="utf-8",
                            input_encoding="utf-8", encoding_errors="replace")

    """
    @cherrypy.expose
    @require(member_of("users"))
    def create_task(self, msg_id=None):

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
    """

    @cherrypy.expose
    @require(member_of("users"))
    def index(self):

        try:
            # получаем задачу и сообщение
            # task = CPO.get_task_by_uuid(task_uuid=uuid)
            # message = CPO.get_clear_message(msg_id=task.message_id)
            # api_data = CPO.get_train_record(msg_id=task.message_id)
            # responsible = CPO.get_user_by_uuid(user_uuid=task.responsible)
            users = CPO.get_all_users_dict(disabled=True)
            tasks, task_msgid_list = CPO.get_tasks_grouped(grouped="status", sort="create_time",
                                                          user_uuid=cherrypy.session['session_context']["user"].uuid)
            msg_list = CPO.get_clear_message(msg_id_list=task_msgid_list)

        except Exception as e:
            print "ControlCenter.tasks(). Ошибка: %s." % str(e)
            return ShowNotification().index("Произошла внутренняя ошибка.")
            users = dict()
            tasks = dict()
            task_msgid_list = list()
            msg_list = list()
        else:

            print "Users: %s" % users
            print "Tasks: %s" % tasks
            print "Msg: %s" % msg_list

            tmpl = self.lookup.get_template("control_center_tasks_all.html")
            return tmpl.render(session_context=cherrypy.session['session_context'], task_list=tasks,
                               task_status=CPO.TASK_STATUS, task_closed_status=CPO.TASK_CLOSED_STATUS,
                               users=users, msg_list=msg_list)

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
                responsible = CPO.get_user_by_uuid(user_uuid=task.responsible)
                users = CPO.get_all_users(sort="surname")
                task_cause = CPO.get_task_cause(task_uuid=uuid)
                cause_tags = CPO.get_tags()
            except Exception as e:
                print "ControlCenter.task(). Ошибка: %s." % str(e)
                return ShowNotification().index("Произошла внутренняя ошибка.")
            else:
                tmpl = self.lookup.get_template("control_center_task_show.html")
                return tmpl.render(task=task, message=message, responsible=responsible,
                                   session_context=cherrypy.session['session_context'],
                                   close_task_status=CPO.TASK_CLOSED_STATUS,
                                   task_status=CPO.TASK_STATUS, api_data=api_data, category=CPO.GetCategory(),
                                   users=users, task_cause=task_cause, cause_tags=cause_tags)

        else:
            print "ControlCenter.task(). Ошибка: не указан UUID задачи."
            return ShowNotification().index("Произошла внутренняя ошибка. Не указан UUID задачи.")

    @cherrypy.expose
    def change_task_status(self, task_uuid=None, status=None, from_url=None):
        if task_uuid:
            try:
                CPO.change_task_status(task_uuid=task_uuid, status=status)
            except Exception as e:
                print "change_task_status(). Ошибка при смене статуса. %s" % str(e)
                return ShowNotification().index("Произошла внутренняя ошибка.")
        else:
            raise cherrypy.HTTPRedirect(from_url or "/control_center")
        raise cherrypy.HTTPRedirect(from_url or "/control_center/tasks/task?uuid=%s" % task_uuid)

    @cherrypy.expose
    @require(member_of("users"))
    def change_task_responsible(self, task_uuid=None, responsible=None, from_url=None):
        if task_uuid:
            try:
                CPO.change_task_responsible(task_uuid=task_uuid, responsible=responsible)
            except Exception as e:
                print "change_task_responsible(). Ошибка при смене ответственного. %s" % str(e)
                return ShowNotification().index("Произошла внутренняя ошибка.")
        else:
            raise cherrypy.HTTPRedirect(from_url or "/control_center/tasks")
        raise cherrypy.HTTPRedirect(from_url or "/control_center/tasks/task?uuid=%s" % task_uuid)

    @cherrypy.expose
    @require(member_of("users"))
    def add_task_comment(self, task_uuid=None, comment=None, from_url=None):
        if task_uuid:
            try:
                CPO.add_task_comment(task_uuid=task_uuid, comment=comment)
            except Exception as e:
                print "add_task_comment(). Ошибка при добавлении комментария. %s" % str(e)
                return ShowNotification().index("Произошла внутренняя ошибка.")
        else:
            raise cherrypy.HTTPRedirect(from_url or "/control_center/tasks")
        raise cherrypy.HTTPRedirect(from_url or "/control_center/tasks/task?uuid=%s" % task_uuid)

    @cherrypy.expose
    @require(member_of("users"))
    def add_tag(self, task_uuid=None, tag_id=None, from_url=None):
        if task_uuid and tag_id:
            try:
                CPO.add_cause_to_task(task_uuid=task_uuid, tags_id=tag_id)
            except Exception as e:
                print "Tasks().add_tag(). Ошибка при добавлении тега. %s" % str(e)
                return ShowNotification().index("Произошла внутренняя ошибка.")
        else:
            raise cherrypy.HTTPRedirect(from_url or "/control_center/tasks")
        raise cherrypy.HTTPRedirect(from_url or "/control_center/tasks/task?uuid=%s" % task_uuid)

    @cherrypy.expose
    @require(member_of("users"))
    def remove_tag(self, task_uuid=None, tag_id=None, from_url=None):
        if task_uuid and tag_id:
            try:
                CPO.remove_cause_from_task(task_uuid=task_uuid, tags_id=tag_id)
            except Exception as e:
                print "Tasks().remove_tag(). Ошибка при удалении тега. %s" % str(e)
                return ShowNotification().index("Произошла внутренняя ошибка.")
        else:
            raise cherrypy.HTTPRedirect(from_url or "/control_center/tasks")
        raise cherrypy.HTTPRedirect(from_url or "/control_center/tasks/task?uuid=%s" % task_uuid)

    @cherrypy.expose
    @require(member_of("users"))
    def new_tag(self, task_uuid=None, tag="", from_url=None):
        if task_uuid and tag:
            try:
                tag_id = CPO.create_tag(tag=tag)
            except Exception as e:
                print "Tasks().new_tag(). Ошибка при создании тега. %s" % str(e)
                return ShowNotification().index("Произошла внутренняя ошибка.")
            else:
                try:
                    CPO.add_cause_to_task(task_uuid=task_uuid, tags_id=tag_id)
                except Exception as e:
                    print "Tasks().new_tag(). Ошибка при добавлении тега. %s" % str(e)
                    return ShowNotification().index("Произошла внутренняя ошибка.")
                else:
                    raise cherrypy.HTTPRedirect(from_url or "/control_center/tasks/task?uuid=%s" % task_uuid)

        else:
            raise cherrypy.HTTPRedirect(from_url or "/control_center/tasks")




class Statistics(object):

    lookup = TemplateLookup(directories=["./templates/controlcenter"], output_encoding="utf-8",
                            input_encoding="utf-8", encoding_errors="replace")

    @cherrypy.expose
    @require(member_of("admin"))
    def system(self, start_date=None, end_date=None):
        tmpl = self.lookup.get_template("control_center_stat_system.html")
        context = cherrypy.session['session_context']

        if start_date and end_date:
            start_date = datetime.datetime.strptime(start_date, "%d-%m-%Y")
            end_date = datetime.datetime.strptime(end_date, "%d-%m-%Y")
        else:
            end_date = datetime.datetime.now()
            start_date = datetime.datetime.strptime("01-01-%s" % end_date.year, "%d-%m-%Y")

        dbd_data = CPO.pred_stat_get_data(start_date=start_date, end_date=end_date)
        agr_data = CPO.pred_stat_get_data_agr(start_date=start_date, end_date=end_date)

        print dbd_data

        return tmpl.render(session_context=context, dbd=dbd_data, agr=agr_data, cat=CPO.GetCategory(),
                           now=datetime.datetime.now(), delta1=datetime.timedelta)


class ControlCenter(object):

    """
        Центр управления для сотрудников. Вся информация и функции для работы с системой.
        Уведомления, статистика, результаты.
    """
    lookup = TemplateLookup(directories=["./templates/controlcenter"], output_encoding="utf-8",
                            input_encoding="utf-8", encoding_errors="replace")


    # Не показывать нейтральные закрытые события
    # Список сообщений должен отражать количество проверенных и не проверенных, чтобы было просто
    #       найти непроверенные сообщения
    # Если я ставлю задачу, то где мне смотреть все задачи которые я назначил кому-то или оставил себе
    # TODO: Уведомление при переводе задачи на другосо сотрудника
    # TODO: Раздел помощи. Написать.
    # TODO: Пользователи не являющиеся пользователями системы при назначении задачи, получают уведомление.
    #       Контроль исполнения лежит на пользователе системы.
    # Статистику простую (кол-во по дням, классам и тд)
    # TODO: Календарь при выборе дня показа событий

    auth = AuthController()
    settings = Settings()
    dialogs = Dialogs()
    tasks = Tasks()
    statistics = Statistics()

    @cherrypy.expose
    @require(member_of("users"))
    def index(self, day=None):
        raise cherrypy.HTTPRedirect("dialogs/warning")

    """
    @cherrypy.expose
    @require(member_of("users"))
    def index(self, day=None):

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
        """

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
    def get_notify(self, user_uuid=None):
        import json
        return json.dump({"text": "Ответ от get_notify()"})


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

       raise cherrypy.HTTPRedirect("control_center/dialogs/warning")


cherrypy.config.update("server.config")

if __name__ == '__main__':
    CPO.initial_configuration()
    cherrypy.quickstart(Root(), '/', "app.config")
