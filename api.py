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

                    try:
                        api_rec = CPO.get_train_record(uuid=uuid)
                    except Exception as e:
                        print "api.UserTrain(). Ошибка получения записи TrainAPI. %s" % str(e)
                        api_rec = None

                    # создаем задачу
                    try:
                        # ответственный за закрытие задачи - проверяющий
                        if cherrypy.session.get('session_context'):
                            responsible = cherrypy.session['session_context'].get("user")
                            task_uuid = CPO.create_task(responsible=responsible.uuid, message_id=api_rec.message_id)
                            text = u"Создана автоматически после проверки. Пользователь: %s %s." % \
                                   (responsible.name, responsible.surname)

                        else:
                            task_uuid = CPO.create_task(responsible=None, message_id=api_rec.message_id)
                            text = "Создана автоматически после проверки. Пользователь неизвестен."

                        # Формируем сообщение
                        try:
                            CPO.add_task_comment(task_uuid=task_uuid, comment=text)
                        except Exception as e:
                            print "api.UserTrain(). Ошибка добавления комментария. %s" % str(e)

                    except Exception as e:
                        print "api.UserTrain(). Ошибка создания Задачи. %s" % str(e)

                    # добавляем адресатов в DialogMembers
                    try:
                        CPO.add_msg_members(msg_id_list=api_rec.message_id)
                    except Exception as e:
                        print "api.UserTrain(). Ошибка добавления адресотов DialogMembers. %s" % str(e)

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


class Settings(object):

    lookup = TemplateLookup(directories=["./templates/controlcenter"], output_encoding="utf-8",
                            input_encoding="utf-8", encoding_errors="replace")

    @cherrypy.expose
    @require(member_of("users"))
    def index(self, message=None):
        # Показываем общие для админов и не админов настройки
        from_url = cherrypy.request.headers.get('Referer')
        tmpl = self.lookup.get_template("control_center_settings.html")
        is_admin = member_of("admin")()

        return tmpl.render(from_url=from_url, session_context=cherrypy.session['session_context'],
                           is_admin=is_admin, access_groups=CPO.ACCESS_GROUPS, message=message)

    @cherrypy.expose
    @require(member_of("users"))
    def save_user_self_data(self, user_uuid=None, login=None, name=None, surname=None, email=None, password=None):
        cur_user = cherrypy.session['session_context']["user"]
        print "CUR user uuid:", cur_user.uuid
        print "Reg user uuid:", user_uuid
        if login and email and password and user_uuid == cur_user.uuid:
            if not name:
                name = email

            if not surname:
                surname = ""

            try:
                result = CPO.update_user(user_uuid=user_uuid, name=name, surname=surname, login=login, password=password,
                                         email=email, self_update=True)
            except Exception as e:
                print "API.ControlCenter.Administration.save_user_self_data(). Ошибка при редактировании пользователя." \
                      " %s" % str(e)
            else:
                return self.index(message="Чтобы изменения вступили в силу перелогиньтесь.")
        else:
            return self.index(message="Не указан логин, емайл или пароль.")

    @cherrypy.expose
    @require(member_of("admin"))
    def administration(self, message=None):
        from_url = cherrypy.request.headers.get('Referer') or "/"
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

            # Список участников даилогов
            members = CPO.get_all_dialog_members(disabled=True)

            # Исключения
            exceptions = CPO.get_address_exceptions()

        except Exception as e:
            print "ControlCenter.Settings.Administration(). Ошибка: %s." % str(e)
            return ShowNotification().index("Произошла внутренняя ошибка.")
        else:

            # print "Watch list: %s" % watch_list

            tmpl = self.lookup.get_template("control_center_settings_administration.html")
            return tmpl.render(session_context=cherrypy.session['session_context'], users=users,
                               categories=categories, user_status=CPO.USER_STATUS, watch_list=watch_list,
                               members=members, exceptions=exceptions, from_url=from_url)

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
    @require(member_of("admin"))
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

    @cherrypy.expose
    @require(member_of("admin"))
    def new_dialog_member(self, message=None, from_url=None):
        tmpl = self.lookup.get_template("control_center_new_dialog_member.html")
        return tmpl.render(session_context=cherrypy.session['session_context'], message=message,
                           dialog_member_type=CPO.DIALOG_MEMBER_TYPE)

    @cherrypy.expose
    @require(member_of("admin"))
    def create_dialog_member(self, m_type=None, name=None, surname=None, emails=None, phone=None):

        if m_type and (emails or phone):
            if not name:
                name = str(CPO.DIALOG_MEMBER_TYPE.get(int(m_type))) + "-" + CPO.uuid.uuid4().__str__()[0:3]

            if not surname:
                surname = ""

            try:
                result = CPO.create_dialog_member(name=str(name), surname=str(surname),
                                                  m_type=int(m_type), emails=str(emails), phone=str(phone))
            except Exception as e:
                print "API.ControlCenter.Settings.create_dialog_member(). Ошибка при создании участника. %s" % str(e)
            else:
                raise cherrypy.HTTPRedirect("administration")
        else:
            return self.new_dialog_member(message="Не указан тип, хотя бы один емайл или телефон.")

    @cherrypy.expose
    @require(member_of("users"))
    def edit_dialog_member(self, member_uuid=None, message=None):
        try:
            member = CPO.get_dialog_members_list(member_uuid=str(member_uuid))
        except Exception as e:
            print "API.ControlCenter.Administration.%s. Ошибка при редактировании участника диалога. %s" % \
                  (self.__name__, str(e))
        else:
            tmpl = self.lookup.get_template("control_center_edit_dialog_member.html")
            return tmpl.render(session_context=cherrypy.session['session_context'], message=message,
                               dialog_member_type=CPO.DIALOG_MEMBER_TYPE, member=member)

    @cherrypy.expose
    @require(member_of("users"))
    def save_dialog_member_data(self, member_uuid=None, m_type=None, name=None, surname=None, emails=None, phone=None):

        if member_uuid and (emails or phone):

            if not name:
                name = str(CPO.DIALOG_MEMBER_TYPE.get(int(m_type))) + CPO.uuid.uuid4().__str__()[2]

            try:
                result = CPO.update_dialog_member(member_uuid=str(member_uuid), name=str(name), surname=str(surname),
                                                  m_type=int(m_type), emails=str(emails), phone=str(phone))
            except Exception as e:
                print "API.ControlCenter.Settings.save_dialog_member_data(). Ошибка при изменении участника." \
                      " %s" % str(e)
            else:
                raise cherrypy.HTTPRedirect("administration")
        else:
            return self.edit_dialog_member(member_uuid=member_uuid,
                                           message="Не указан тип, емайл или телефон.")

    @cherrypy.expose
    @require(member_of("admin"))
    def change_dialog_member_status(self, member_uuid=None):
        if member_uuid:
            try:
                CPO.change_dialog_member_type(member_uuid=member_uuid)
            except Exception as e:
                print "ControlCenter.Settings.Administration.change_dialog_member_status(). Ошибка: %s." % str(e)
                return ShowNotification().index("Произошла внутренняя ошибка.")

        raise cherrypy.HTTPRedirect("administration")

    @cherrypy.expose
    @require(member_of("admin"))
    def new_exception(self, from_url=None, message=None):
        tmpl = self.lookup.get_template("control_center_new_exception.html")
        return tmpl.render(session_context=cherrypy.session['session_context'], message=message)

    @cherrypy.expose
    @require(member_of("admin"))
    def create_exception(self, address=None):
        if address:

            try:
                result = CPO.create_exception(address=address)
            except Exception as e:
                print "API.ControlCenter.Administration.create_exception(). Ошибка при создании исключения. %s" % str(e)
            else:
                raise cherrypy.HTTPRedirect("administration")
        else:
            return self.new_exception(message="Не указана строка адреса для проверки.")

    @cherrypy.expose
    @require(member_of("admin"))
    def delete_exception(self, uuid=None):
        from_url = None
        if uuid:
            try:
                CPO.delete_exception(uuid=int(uuid))
            except Exception as e:
                print "ControlCenter.Settings.Administration.delete_exception(). Ошибка: %s." % str(e)
                return self.administration(message="Ошибка удаления исключения.")
            else:
                raise cherrypy.HTTPRedirect(from_url or "administration")

        raise cherrypy.HTTPRedirect(from_url or "administration")


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
    def index(self, message=None):

        users = dict()
        tasks = dict()
        task_msgid_list = list()
        msg_list = list()

        is_admin = member_of("admin")()

        try:
            session_context = cherrypy.session['session_context']
            users = CPO.get_all_users_dict(disabled=True)
            if is_admin:
                tasks, task_msgid_list = CPO.get_tasks_grouped(grouped="status", sort="create_time")
            else:
                tasks, task_msgid_list = CPO.get_tasks_grouped(grouped="status", sort="create_time",
                                                               user_uuid=session_context["user"].uuid)
            msg_list = CPO.get_clear_message(msg_id_list=task_msgid_list)

        except Exception as e:
            print "ControlCenter.tasks(). Ошибка: %s." % str(e)
            # return ShowNotification().index("Произошла внутренняя ошибка.")
        else:

            print "Users: %s" % users
            print "Tasks: %s" % tasks
            print "Msg: %s" % msg_list

            tmpl = self.lookup.get_template("control_center_tasks_all.html")
            return tmpl.render(session_context=session_context, task_list=tasks,
                               task_status=CPO.TASK_STATUS, task_closed_status=CPO.TASK_CLOSED_STATUS,
                               users=users, msg_list=msg_list, cur_day=datetime.datetime.now(), message=message)

    @cherrypy.expose
    @require(member_of("users"))
    def task(self, uuid=None, message=None):
        """
        Функция показа задачи.
        :param uuid:
        :return:
        """

        if uuid:
            try:
                # получаем задачу и сообщение
                task = CPO.get_task_by_uuid(task_uuid=uuid)
                msg = CPO.get_clear_message(msg_id=task.message_id)
                api_data = CPO.get_train_record(msg_id=task.message_id)
                responsible = CPO.get_user_by_uuid(user_uuid=task.responsible)
                users = CPO.get_all_users_dict(disabled=True)
                task_cause = CPO.get_task_cause(task_uuid=uuid)
                cause_tags = CPO.get_tags()
                session_context=cherrypy.session['session_context']
                is_admin = member_of("admin")()
            except Exception as e:
                print "ControlCenter.task(). Ошибка: %s." % str(e)
                return ShowNotification().index("Произошла внутренняя ошибка.")
            else:
                # Если запрошен доступ к задаче других пользователей и текущий пользователь не администратор
                if responsible.uuid != session_context["user"].uuid and not is_admin:
                    print "ControlCenter.task(). Пользователь не имеет доступа к этой задаче. " \
                          "Ответственный - %s. Текущий пользователь: %s" % (responsible.uuid, session_context["user"].uuid)
                    return self.index(message="У вас нет доступа задачам других пользователей.")

                tmpl = self.lookup.get_template("control_center_task_show.html")
                return tmpl.render(task=task, message=message, responsible=responsible, msg=msg,
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

        # print dbd_data

        return tmpl.render(session_context=context, dbd=dbd_data, agr=agr_data, cat=CPO.GetCategory(),
                           now=datetime.datetime.now(), delta1=datetime.timedelta)

    @cherrypy.expose
    @require(member_of("users"))
    def management(self, start_date=None, end_date=None):
        tmpl = self.lookup.get_template("control_center_stat_management2.html")
        context = cherrypy.session['session_context']

        is_admin = member_of("admin")()

        if start_date:
            start_date = datetime.datetime.strptime(start_date, "%d-%m-%Y")
        else:
            start_date = None

        if end_date:
            end_date = datetime.datetime.strptime(end_date, "%d-%m-%Y")
        else:
            end_date = datetime.datetime.now()

        try:
            cur_day = datetime.datetime.now()
            users = CPO.get_all_users_dict()
            members = CPO.get_all_dialog_members()
            tags = CPO.get_tags()
            stat_data = CPO.get_stat_for_management(start=start_date, end=end_date,
                                                    tags=tags, members=members, users=users)
        except Exception as e:
            print str(e)
            raise e

        return tmpl.render(session_context=context, stat=stat_data, cat=CPO.GetCategory(),
                           users=users, members=members, tags=tags, cur_day=cur_day,
                           start_date=start_date, end_date=end_date, is_admin=is_admin)

    @cherrypy.expose
    @require(member_of("admin"))
    def get_chart_data(self, chart_id=None, start_date=None, end_date=None, days=0):

        now = datetime.datetime.now()

        if chart_id != "violation_stats":
            if start_date == "None" or not start_date:
                start_date = now
            else:
                start_date = datetime.datetime.strptime(start_date, "%d-%m-%Y")

            if not end_date or end_date == "None":
                end_date = now
            else:
                end_date = datetime.datetime.strptime(end_date, "%d-%m-%Y")

            try:
                users = CPO.get_all_users_dict()
                members = CPO.get_all_dialog_members()
                tags = CPO.get_tags()
                stat = CPO.get_stat_for_management(start=start_date, end=start_date,
                                                   tags=tags, members=members, users=users)
                non_checked_by_users = stat[0]
                confirmed_problem = stat[1]
                tasks_by_responsible = stat[2]
                tasks_by_cause = stat[3]
                tasks_by_empl = stat[4]
                tasks_by_client = stat[5]
            except Exception as e:
                print str(e)
                raise e

        colors = [
            ["#CC0033", "#FFCCCC"],
            ["#996600", "#FFCC66"],
            ["#CCCC00", "#FFFFCC"],
            ["#990066", "#FF66CC"],
            ["#660066", "#CC66FF"],
            ["#663366", "#CC99FF"],
            ["#003366", "#0066FF"],
            ["#006699", "#99CCFF"],
            ["#009999", "#99FFCC"],
            ["#009933", "#66FF99"]
        ]

        data = list()
        if chart_id == "problem_by_cause":
            i = 0
            print "tasks_by_cause: ",tasks_by_cause
            for one in tasks_by_cause[0]:
                part = {
                    "value": one[1],
                    "color": colors[i][0],
                    "highlight": colors[i][1],
                    "label": tags.get(one[0]).tag
                }
                data.append(part)
                i += 1
                if i == len(colors):
                    i = 0

        elif chart_id == "problem_by_employee":
            i = 0
            for one in tasks_by_empl[0]:
                part = {
                    "value": one[1],
                    "color": colors[i][0],
                    "highlight": colors[i][1],
                    "label": members.get(one[0]).name
                }
                data.append(part)
                i += 1
                if i == len(colors):
                    i = 0

        elif chart_id == "problem_by_client":
            i = 0
            for one in tasks_by_client[0]:
                part = {
                    "value": one[1],
                    "color": colors[i][0],
                    "highlight": colors[i][1],
                    "label": members.get(one[0]).name
                }
                data.append(part)
                i += 1
                if i == len(colors):
                    i = 0
        elif chart_id == "violation_stats":
            if not start_date or start_date == "None":
                start_date = 7
            else:
                start_date = datetime.datetime.strptime(start_date, "%d-%m-%Y")

            if not end_date or end_date == "None":
                end_date = now
            else:
                end_date = datetime.datetime.strptime(end_date, "%d-%m-%Y")

            try:
                print "JS date: ", start_date, end_date
                viol_stat = CPO.get_violation_stat(start_date=start_date, end_date=end_date)

            except Exception as e:
                print "Statistics.get_chart_data(). Ошибка получения данных для графика violation_stats.", str(e)
                raise e

            # Формируем датасет
            part1 = {
                "label": "",
                "fillColor": "rgba(255,204,153,0.2)",
                "strokeColor": "#ffb53e",
                "pointColor": "#ffb53e",
                "pointStrokeColor": "#fff",
                "pointHighlightFill": "#fff",
                "pointHighlightStroke" : "rgba(220,220,220,1)",
                "data": list()
            }
            part2 = {
                "label": "",
                "fillColor": "rgba(255,204,204,0.2)",
                "strokeColor": "#f9243f",
                "pointColor": "#f9243f",
                "pointStrokeColor": "#fff",
                "pointHighlightFill": "#fff",
                "pointHighlightStroke" : "rgba(220,220,220,1)",
                "data": list()
            }
            part3 = {
                "label": "",
                "fillColor": "rgba(204,255,204,0.2)",
                "strokeColor": "#1ebfae",
                "pointColor": "#1ebfae",
                "pointStrokeColor": "#fff",
                "pointHighlightFill": "#fff",
                "pointHighlightStroke" : "rgba(220,220,220,1)",
                "data": list()
            }
            data = {"labels": list(), "datasets": [part1, part2, part3]}
            data["datasets"][0]["label"] = u"на проверку"
            data["datasets"][1]["label"] = u"подтверждено"
            data["datasets"][2]["label"] = u"закрыто"

            to_check = list()
            confirmed = list()
            closed = list()

            for one in viol_stat:
                data["labels"].append(one.start_date.strftime("%d-%m-%Y"))
                to_check.append(one.to_check)
                confirmed.append(one.confirmed)
                closed.append(one.closed)

            data["datasets"][0]["data"] = to_check
            data["datasets"][1]["data"] = confirmed
            data["datasets"][2]["data"] = closed

            # print "Line data:", data

        import json

        return json.dumps(data)


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
        try:
            is_admin = member_of("admin")()
        except Exception as e:
            print "Control_center.index(). Ошибка определения привилегий пользователя. %s" % str(e)
            raise cherrypy.HTTPRedirect("dialogs/warning")
        else:
            if is_admin:
                raise cherrypy.HTTPRedirect("/control_center/statistics/management")
            else:
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

        session_context = cherrypy.session['session_context']
        is_admin = member_of("admin")()
        # список емайл адресов и доменов клиентов к которым у этого пользователя есть доступ
        client_access_list = CPO.get_watch_list(user_uuid=session_context.get("user").uuid, is_admin=is_admin)

        for_day = datetime.datetime.now()
        # for_day = datetime.datetime.strptime("%s-%s-%s 00:00:00" % (2016, 4, 4), "%Y-%m-%d %H:%M:%S")

        try:
            api_list, message_list, message_id_list, unchecked, checked = \
                CPO.get_dialogs(for_day=for_day, cat=CPO.WARNING_CATEGORY,
                                empl_access_list=[],
                                client_access_list=client_access_list)
        except Exception as e:
            print "Control_center. Get_notify(). Ошибка. %s" % str(e)
            show = False
            count = 0
        else:

            #  считаем количество уведомлений
            if len(unchecked) == 0:
                count = len(unchecked)
                cherrypy.session['session_context']["notifications"] = len(unchecked)
                show = False
            elif cherrypy.session['session_context']["notifications"] == len(unchecked):
                # количество с прошлого запроса не изменилось
                show = False
                count = 0
            else:
                # количество изменилось
                count = len(unchecked)
                cherrypy.session['session_context']["notifications"] = len(unchecked)
                show = True

        if count > 4:
            text = "У вас %s новых непроверенных уведомлений." % int(count)
        elif count == 1:
            text = "У вас %s новое непроверенное уведомление." % int(count)
        else:
            text = "У вас %s новых непроверенных уведомления." % int(count)

        url = "http://localhost:8585/control_center"

        import json

        data = {"title": "Conversation parser",
                "count": count,
                "text": text,
                "url": url,
                "show": show
                }

        return json.dumps(data)


class Root(object):
    """
        Основой сервис для запуска API и центров управления
    """

    api = API()
    control_center = ControlCenter()

    @cherrypy.expose
    @require(member_of("users"))
    def index(self, ads=None):

       raise cherrypy.HTTPRedirect("control_center/dialogs/warning")


cherrypy.config.update("server.config")

if __name__ == '__main__':
    CPO.initial_configuration()
    cherrypy.quickstart(Root(), '/', "app.config")
