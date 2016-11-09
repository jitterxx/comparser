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
import json
from auth import AuthController, require, member_of, name_is, all_of, any_of
from sklearn.externals import joblib

__author__ = 'sergey'

lookup = TemplateLookup(directories=["./templates"], output_encoding="utf-8",
                        input_encoding="utf-8", encoding_errors="replace")


class ShowNotification(object):

    """
    def _cp_dispatch(self, vpath):

        # Обработка REST URL

        print "ShowNotification"
        print vpath
        return self
    """

    @cherrypy.expose
    def index(self, error=None, url=None):
        tmpl = lookup.get_template("message.html")
        if not url:
            url = "/"
        print("ShowNotification.index(). {}".format(str(error)))
        return tmpl.render(text=error, url=url)

    @cherrypy.expose
    def error(self, text=None, url=None):
        tmpl = lookup.get_template("error.html")
        if not url:
            url = "/"
        print("ShowNotification.error(). {}".format(str(text)))
        return tmpl.render(error=text, url=url)


class API_V2(object):
    # WWW API

    @cherrypy.expose
    def default(self):
        print("WWW/default - req")

    @cherrypy.expose
    def problem_create(self, msg_uuid=None, responsible=None, new_problem_title=None):
        print("WWW/Problem/Create - req")
        print("MSG_UUID: {}, RESP: {}, Title: {}".format(msg_uuid, responsible, new_problem_title))
        if new_problem_title and msg_uuid and responsible:
            try:
                result = Problem().create(msg_uuid=msg_uuid, responsible=responsible, title=new_problem_title)
            except Exception as e:
                print("API.WWW.Problem_create(). Ошибка создания новой проблемы. {}".format(str(e)))
                err_text = "API.WWW.Problem_create(). Произошла внутренняя ошибка. \nПожалуйста, сообщите о " \
                           "ней администратору.\n {}".format(str(e))
                return ShowNotification().error(text=err_text)
            else:
                if result['return_data'][0]:
                    return ShowNotification().index(error=result['message'])
                else:
                    return ShowNotification().error(text=result['message'])


    @cherrypy.expose
    def problem_link(self, problem_uuid=None, msg_uuid=None):
        print("WWW/Problem/Link - req")
        print("Problem_UUID: {}, MSG_UUID: {}".format(problem_uuid, msg_uuid))
        if problem_uuid and msg_uuid:
            try:
                result = Problem().link(msg_uuid=msg_uuid, problem_uuid=problem_uuid)
            except Exception as e:
                print("API.WWW.Problem_link(). Ошибка линковки. {}".format(str(e)))
                err_text = "API.JS.Problem_link(). Произошла внутренняя ошибка. Пожалуйста, сообщите о " \
                           "ней администратору. {}".format(str(e))
                return ShowNotification().error(text=err_text)
            else:
                if result['return_data'][0]:
                    return ShowNotification().index(error=result['message'])
                else:
                    return ShowNotification().error(text=result['message'])

    @cherrypy.expose
    def message_train(self, uuid=None, category=None):
        print("WWW/Message/Train - req")
        print("MSG_UUID: {}, CAT: {}".format(uuid, category))
        if uuid and category:
            try:
                result = Message().train(uuid=uuid, category=category)
            except Exception as e:
                print("API.WWW.Message.train(). Ошибка записи проверочного ответа пользователя. {}".format(str(e)))
                err_text = "API.WWW.Message.train(). Произошла внутренняя ошибка. \n Пожалуйста, сообщите о " \
                           "ней администратору. \n{}".format(str(e))
                return ShowNotification().error(text=err_text)
            else:
                if not result.get('status'):
                    # Сообщение не существует или уже проверено
                    return ShowNotification().index(error=result['message'])

                if result.get('status') and category in CPO.WARNING_CATEGORY:
                    # [cur_user, responsible_list, problem_list, uuid, user_list]
                    print "Выводим страницу создания проблемы..."
                    # ответ через уведомление, надо запросить к какой проблеме отнести сообщение или создать новую
                    tmpl = lookup.get_template("warning_cat_create_problem.html")
                    return tmpl.render(status=result['message'], cur_user=result['return_data'][0],
                                       responsible_list=result['return_data'][1],
                                       problem_list=result['return_data'][2],
                                       api_uuid=result['return_data'][3], user_list=result['return_data'][4])
                else:
                    return ShowNotification().index(error=result['message'])

    """
    @cherrypy.expose
    def problem(self, action=None, problem_uuid=None, msg_uuid=None, request_type=None, new_problem_title=None,
                responsible=None):
        print "Problem API v2 :", action, problem_uuid, msg_uuid, request_type
        print("{} {}".format(new_problem_title, responsible))
        if action == 'link' and problem_uuid and msg_uuid:
            print "Линкуем"
            try:
                # status = CPO.link_problem_to_message(problem_uuid=problem_uuid, msg_uuid=msg_uuid)
                status = [True, "test"]
            except Exception as e:
                err_text = "Api.Problem(). Произошла внутренняя ошибка. Пожалуйста, сообщите о ней администратору."
                print err_text, str(e)
                if request_type == "js":
                    cherrypy.response.status = 500
                    cherrypy.response.body = [err_text]
                    return err_text
                else:
                    return ShowNotification().error(text=err_text)
            else:
                if request_type == "js":
                    if status[0]:
                        cherrypy.response.status = 200
                    else:
                        cherrypy.response.status = 500
                    cherrypy.response.body = [status[1]]
                    return status[1]
                else:
                    if status[0]:
                        return ShowNotification().index(error=status[1])
                    else:
                        return ShowNotification().error(text=status[1])

        elif action == 'create' and new_problem_title and msg_uuid and responsible:
            print "Создаем новую проблему"

            try:
                check = CPO.problem_api_check(msg_uuid=msg_uuid)

            except Exception as e:
                err_text = "Api.Problem(). Произошла внутренняя ошибка. Пожалуйста, сообщите о ней администратору."
                print err_text, str(e)
                if request_type == "js":
                    cherrypy.response.status = 500
                    cherrypy.response.body = [err_text]
                    return err_text
                else:
                    return ShowNotification().error(text=err_text)
            else:
                if check[0]:
                    status = CPO.create_problem(responsible=responsible, title=new_problem_title, message_uuid=msg_uuid)

                    if request_type == "js":
                        if status[0]:
                            cherrypy.response.status = 200
                        else:
                            cherrypy.response.status = 500
                        cherrypy.response.body = [status[1]]
                        return status[1]
                    else:
                        if status[0]:
                            return ShowNotification().index(error=status[1])
                        else:
                            return ShowNotification().error(text=status[1])
                else:
                    if request_type == "js":
                        cherrypy.response.status = 500
                        cherrypy.response.body = [check[1]]
                        return check[1]
                    else:
                        return ShowNotification().error(text=check[1])

        else:
            print "API_v2(). Incorrect REST URL.", cherrypy.request
            if request_type == "js":
                cherrypy.response.status = 500
                cherrypy.response.body = "API_v2(). Incorrect REST URL."
                return "error"
            else:
                return ShowNotification().error(text="Указан неверный адрес. Обратитесь к администратору.")


    @cherrypy.expose
    def message(self, uuid=None, category=None, request_type=None):
        print "Message API v2 :", uuid, category, request_type

        if uuid and category:

            # 1. записать указанный емайл и категорию в пользовательские тренировочные данные
            # 2. Пометить в таблице train_api ответ.

            try:
                #status = CPO.set_user_train_data(uuid, category)
                status = [True, "Test"]

            except Exception as e:
                err_text = "Api.UserTrain(). Произошла внутренняя ошибка. Пожалуйста, сообщите о ней администратору."
                print err_text, str(e)
                if request_type == "js":
                    cherrypy.response.status = 500
                    cherrypy.response.body = [err_text]
                    return err_text
                else:
                    return ShowNotification().error(text=err_text)
            else:
                print("Req type: {}. {}. {}".format(request_type, status[0], status[1]))

                # Сообщени уже проверено или его не существует
                if not status[0]:
                    if request_type == "js":
                        cherrypy.response.status = 200
                        cherrypy.response.body = [status[1]]
                        return status[1]
                    else:
                        return ShowNotification().index(error=status[1])

                # Если категория после проверки в WARNING_CAT и ответ новый, то создаем проблему
                if status[0] and category in WARNING_CATEGORY:

                    try:
                        api_rec = CPO.get_train_record(uuid=uuid)
                    except Exception as e:
                        print "api.UserTrain(). Ошибка получения записи TrainAPI UUID = {}. {}".format(uuid, str(e))
                        api_rec = None

                    # добавляем адресатов в DialogMembers
                    try:
                        CPO.add_msg_members(msg_id_list=api_rec.message_id)
                    except Exception as e:
                        print "api.UserTrain(). Ошибка добавления адресатов DialogMembers для MSG_ID = {}.  {}".\
                            format(api_rec.message_id, str(e))

                    # Создание задачи автоматически не нужно. СУщность Задача выводится из использования.
                    # Оставлено в коде для совместимости.

                    # Все действия будут производится с новой сущностью - Проблема.
                    # Сотрудник нажавший "красную кнопку", должен в ручную привязать инцидент (сообщение) к проблеме.
                    # Выбрать из списка или создать новую.

    """
    """
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
                            print "api.UserTrain(). Ошибка добавления комментария TASK_UUID = {}. {}".\
                                format(task_uuid, str(e))

                    except Exception as e:
                        print "api.UserTrain(). Ошибка создания Задачи для MSG_ID = {}. {}".\
                            format(api_rec.message_id, str(e))
    """
    """

                    # Связывание или создание проблемы
                    print "Собираем данные для связывания или создания проблемы..."
                    cur_user = ""
                    responsible_list = list()
                    problem_list = tuple()
                    user_list = list()
                    try:
                        if cherrypy.session.get('session_context'):
                            cur_user = cherrypy.session['session_context'].get("user")
                        responsible_list = CPO.get_watchers_uuid_for_email(message_id=api_rec.message_id)
                        user_list = CPO.get_all_users_dict()
                        problem_list = CPO.get_problems_api(status='not closed', sort='frequency')

                    except Exception as e:
                        print "api.UserTrain(). Ошибка получения данных создания/связывания проблемы для MSG_ID = {}. {}".\
                            format(api_rec.message_id, str(e))

                    print cur_user
                    print responsible_list
                    print problem_list
                    print user_list

                    # в js надо запросить к какой проблеме отнести сообщение или создать новую
                    if request_type == "js":
                        cherrypy.response.status = 200
                        cherrypy.response.body = ['ok']

                        response = list()
                        response.append(cur_user.uuid)
                        response.append(list())
                        for one in responsible_list:
                            if one not in CPO.HIDDEN_USERS:
                                response[1].append({'uuid': one, 'name': user_list.get(one).name,
                                                    'surname': user_list.get(one).surname})

                        response.append(api_rec.uuid)
                        response.append(list())
                        for one, count in problem_list:
                            response[3].append({'uuid': one.uuid, 'title': one.title, 'count': count})


                        return json.dumps(response)
                    else:

                        print "Выводим страницу создания проблемы..."
                        # ответ через уведомление, надо запросить к какой проблеме отнести сообщение или создать новую
                        tmpl = lookup.get_template("warning_cat_create_problem.html")
                        return tmpl.render(status=status, cur_user=cur_user, responsible_list=responsible_list,
                                           problem_list=problem_list, api_uuid=api_rec.uuid, user_list=user_list)
                        # return ShowNotification().index(error=status[1])

                else:
                    if request_type == "js":
                        cherrypy.response.status = 200
                        cherrypy.response.body = ['ok']
                        return 'ok'
                    else:
                        # tmpl = lookup.get_template("usertrain_page.html")
                        # return tmpl.render(status=status)
                        return ShowNotification().index(error=status[1])

        else:
            print "API_v2(). Incorrect REST URL.", cherrypy.request
            if request_type == "js":
                cherrypy.response.status = 500
                cherrypy.response.body = "API_v2(). Incorrect REST URL."
                return "error"
            else:
                return ShowNotification().error(text="Указан неверный адрес. Обратитесь к администратору.")
    """


class Problem(object):

    def create(self, msg_uuid=None, responsible=None, title=None):
        print("Создаем новую проблему...")
        result = {'status': True, 'message': '', 'return_data': None}
        try:
            # Проверяем наличие у сообщения связанной проблемы
            check = CPO.problem_api_check(msg_uuid=msg_uuid)
        except Exception as e:
            err_text = "Problem().create(). Произошла внутренняя ошибка. Пожалуйста, сообщите о ней администратору."
            print err_text, str(e)
            raise e
        else:
            if check[0]:
                result['message'] = check[1]
                result['return_data'] = check
            else:
                try:
                    # Создаем новую проблему и линкуем с сообщением
                    status = CPO.create_problem(responsible=responsible, title=title, message_uuid=msg_uuid)
                except Exception as e:
                    err_text = "Problem().create(). Произошла внутренняя ошибка. Пожалуйста, сообщите о ней администратору."
                    print err_text, str(e)
                    raise e
                else:
                    result['message'] = status[1]
                    result['return_data'] = status

            return result

    def link(self, problem_uuid=None, msg_uuid=None):
        print("Линкуем...")
        result = {'status': True, 'message': '', 'return_data': None}
        try:
            status = CPO.link_problem_to_message(problem_uuid=problem_uuid, msg_uuid=msg_uuid)
            # status = [True, "test"]
        except Exception as e:
            print("Problem().link(). Ошибка при линковке проблемы и сообщения. {}".format(str(e)))
            raise e
        else:
            result['message'] = status[1]
            result['return_data'] = status
            return result


class Message(object):

    def train(self, uuid=None, category=None):
        print("Запись ответа для обучения...")
        result = {'status': True, 'message': '', 'return_data': None}

        # 1. записать указанный емайл и категорию в пользовательские тренировочные данные
        # 2. Пометить в таблице train_api ответ.
        try:
            status = CPO.set_user_train_data(uuid, category)
            #status = [True, "Test"]

        except Exception as e:
            err_text = "Message.Train(). Произошла внутренняя ошибка. Пожалуйста, сообщите о ней администратору."
            print err_text, str(e)
            raise e
        else:
            print("UserTrain data result: {}. {}".format(status[0], status[1]))
            result['message'] = status[1]
            result['status'] = status[0]

            # Сообщени уже проверено или его не существует
            if not status[0]:
                return result

            # Если категория после проверки в WARNING_CAT и ответ новый, то создаем проблему
            if status[0] and category in WARNING_CATEGORY:

                try:
                    api_rec = CPO.get_train_record(uuid=uuid)
                except Exception as e:
                    print "Message.Train(). Ошибка получения записи TrainAPI UUID = {}. {}".format(uuid, str(e))
                    raise e

                # добавляем адресатов в DialogMembers
                try:
                    CPO.add_msg_members(msg_id_list=api_rec.message_id)
                except Exception as e:
                    print "Message.Train(). Ошибка добавления адресатов DialogMembers для MSG_ID = {}.  {}".\
                        format(api_rec.message_id, str(e))
                    raise e

                # Создание задачи автоматически не нужно. СУщность Задача выводится из использования.
                # Оставлено в коде для совместимости.

                # Все действия будут производится с новой сущностью - Проблема.
                # Сотрудник нажавший "красную кнопку", должен в ручную привязать инцидент (сообщение) к проблеме.
                # Выбрать из списка или создать новую.

                # Связывание или создание проблемы
                print "Собираем данные для связывания или создания проблемы..."
                cur_user = None
                responsible_list = list()
                problem_list = tuple()
                user_list = list()
                try:
                    if cherrypy.session.get('session_context'):
                        cur_user = cherrypy.session['session_context'].get("user")
                    responsible_list = CPO.get_watchers_uuid_for_email(message_id=api_rec.message_id)
                    user_list = CPO.get_all_users_dict()
                    problem_list = CPO.get_problems_api(status='not closed', sort='frequency')

                except Exception as e:
                    print "Message.Train(). Ошибка получения данных создания/связывания проблемы для MSG_ID = {}. {}".\
                        format(api_rec.message_id, str(e))

                print cur_user
                print responsible_list
                print problem_list
                print user_list

                result['return_data'] = [cur_user, responsible_list, problem_list, uuid, user_list]

            return result

    """
    def problem(self, action=None, problem_uuid=None, msg_uuid=None, request_type=None, new_problem_title=None,
                responsible=None):
        print "Problem API v2 :", action, problem_uuid, msg_uuid, request_type
        print("{} {}".format(new_problem_title, responsible))
        if action == 'link' and problem_uuid and msg_uuid:
            print "Линкуем"
            try:
                # status = CPO.link_problem_to_message(problem_uuid=problem_uuid, msg_uuid=msg_uuid)
                status = [True, "test"]
            except Exception as e:
                err_text = "Api.Problem(). Произошла внутренняя ошибка. Пожалуйста, сообщите о ней администратору."
                print err_text, str(e)
                if request_type == "js":
                    cherrypy.response.status = 500
                    cherrypy.response.body = [err_text]
                    return err_text
                else:
                    return ShowNotification().error(text=err_text)
            else:
                if request_type == "js":
                    if status[0]:
                        cherrypy.response.status = 200
                    else:
                        cherrypy.response.status = 500
                    cherrypy.response.body = [status[1]]
                    return status[1]
                else:
                    if status[0]:
                        return ShowNotification().index(error=status[1])
                    else:
                        return ShowNotification().error(text=status[1])

        elif action == 'create' and new_problem_title and msg_uuid and responsible:
            print "Создаем новую проблему"

            try:
                check = CPO.problem_api_check(msg_uuid=msg_uuid)

            except Exception as e:
                err_text = "Api.Problem(). Произошла внутренняя ошибка. Пожалуйста, сообщите о ней администратору."
                print err_text, str(e)
                if request_type == "js":
                    cherrypy.response.status = 500
                    cherrypy.response.body = [err_text]
                    return err_text
                else:
                    return ShowNotification().error(text=err_text)
            else:
                if check[0]:
                    status = CPO.create_problem(responsible=responsible, title=new_problem_title, message_uuid=msg_uuid)

                    if request_type == "js":
                        if status[0]:
                            cherrypy.response.status = 200
                        else:
                            cherrypy.response.status = 500
                        cherrypy.response.body = [status[1]]
                        return status[1]
                    else:
                        if status[0]:
                            return ShowNotification().index(error=status[1])
                        else:
                            return ShowNotification().error(text=status[1])
                else:
                    if request_type == "js":
                        cherrypy.response.status = 500
                        cherrypy.response.body = [check[1]]
                        return check[1]
                    else:
                        return ShowNotification().error(text=check[1])

        else:
            print "API_v2(). Incorrect REST URL.", cherrypy.request
            if request_type == "js":
                cherrypy.response.status = 500
                cherrypy.response.body = "API_v2(). Incorrect REST URL."
                return "error"
            else:
                return ShowNotification().error(text="Указан неверный адрес. Обратитесь к администратору.")

    def message(self, uuid=None, category=None, request_type=None):
        print "Message API v2 :", uuid, category, request_type

        if uuid and category:

            # 1. записать указанный емайл и категорию в пользовательские тренировочные данные
            # 2. Пометить в таблице train_api ответ.

            try:
                #status = CPO.set_user_train_data(uuid, category)
                status = [True, "Test"]

            except Exception as e:
                err_text = "Api.UserTrain(). Произошла внутренняя ошибка. Пожалуйста, сообщите о ней администратору."
                print err_text, str(e)
                if request_type == "js":
                    cherrypy.response.status = 500
                    cherrypy.response.body = [err_text]
                    return err_text
                else:
                    return ShowNotification().error(text=err_text)
            else:
                print("Req type: {}. {}. {}".format(request_type, status[0], status[1]))

                # Сообщени уже проверено или его не существует
                if not status[0]:
                    if request_type == "js":
                        cherrypy.response.status = 200
                        cherrypy.response.body = [status[1]]
                        return status[1]
                    else:
                        return ShowNotification().index(error=status[1])

                # Если категория после проверки в WARNING_CAT и ответ новый, то создаем проблему
                if status[0] and category in WARNING_CATEGORY:

                    try:
                        api_rec = CPO.get_train_record(uuid=uuid)
                    except Exception as e:
                        print "api.UserTrain(). Ошибка получения записи TrainAPI UUID = {}. {}".format(uuid, str(e))
                        api_rec = None

                    # добавляем адресатов в DialogMembers
                    try:
                        CPO.add_msg_members(msg_id_list=api_rec.message_id)
                    except Exception as e:
                        print "api.UserTrain(). Ошибка добавления адресатов DialogMembers для MSG_ID = {}.  {}".\
                            format(api_rec.message_id, str(e))

                    # Создание задачи автоматически не нужно. СУщность Задача выводится из использования.
                    # Оставлено в коде для совместимости.

                    # Все действия будут производится с новой сущностью - Проблема.
                    # Сотрудник нажавший "красную кнопку", должен в ручную привязать инцидент (сообщение) к проблеме.
                    # Выбрать из списка или создать новую.
    """

    """
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
                            print "api.UserTrain(). Ошибка добавления комментария TASK_UUID = {}. {}".\
                                format(task_uuid, str(e))

                    except Exception as e:
                        print "api.UserTrain(). Ошибка создания Задачи для MSG_ID = {}. {}".\
                            format(api_rec.message_id, str(e))
    """
    """
                    # Связывание или создание проблемы
                    print "Собираем данные для связывания или создания проблемы..."
                    cur_user = ""
                    responsible_list = list()
                    problem_list = tuple()
                    user_list = list()
                    try:
                        if cherrypy.session.get('session_context'):
                            cur_user = cherrypy.session['session_context'].get("user")
                        responsible_list = CPO.get_watchers_uuid_for_email(message_id=api_rec.message_id)
                        user_list = CPO.get_all_users_dict()
                        problem_list = CPO.get_problems_api(status='not closed', sort='frequency')

                    except Exception as e:
                        print "api.UserTrain(). Ошибка получения данных создания/связывания проблемы для MSG_ID = {}. {}".\
                            format(api_rec.message_id, str(e))

                    print cur_user
                    print responsible_list
                    print problem_list
                    print user_list

                    # в js надо запросить к какой проблеме отнести сообщение или создать новую
                    if request_type == "js":
                        cherrypy.response.status = 200
                        cherrypy.response.body = ['ok']

                        response = list()
                        response.append(cur_user.uuid)
                        response.append(list())
                        for one in responsible_list:
                            if one not in CPO.HIDDEN_USERS:
                                response[1].append({'uuid': one, 'name': user_list.get(one).name,
                                                    'surname': user_list.get(one).surname})

                        response.append(api_rec.uuid)
                        response.append(list())
                        for one, count in problem_list:
                            response[3].append({'uuid': one.uuid, 'title': one.title, 'count': count})


                        return json.dumps(response)
                    else:

                        print "Выводим страницу создания проблемы..."
                        # ответ через уведомление, надо запросить к какой проблеме отнести сообщение или создать новую
                        tmpl = lookup.get_template("warning_cat_create_problem.html")
                        return tmpl.render(status=status, cur_user=cur_user, responsible_list=responsible_list,
                                           problem_list=problem_list, api_uuid=api_rec.uuid, user_list=user_list)
                        # return ShowNotification().index(error=status[1])

                else:
                    if request_type == "js":
                        cherrypy.response.status = 200
                        cherrypy.response.body = ['ok']
                        return 'ok'
                    else:
                        # tmpl = lookup.get_template("usertrain_page.html")
                        # return tmpl.render(status=status)
                        return ShowNotification().index(error=status[1])

        else:
            print "API_v2(). Incorrect REST URL.", cherrypy.request
            if request_type == "js":
                cherrypy.response.status = 500
                cherrypy.response.body = "API_v2(). Incorrect REST URL."
                return "error"
            else:
                return ShowNotification().error(text="Указан неверный адрес. Обратитесь к администратору.")
    """

class API_JS_V2(object):

    @cherrypy.expose
    def default(self):
        print("JS/default - req")

    @cherrypy.expose
    def problem_create(self, msg_uuid=None, responsible=None, new_problem_title=None):
        print("JS/Problem/Create - req")
        print("MSG_UUID: {}, RESP: {}, Title: {}".format(msg_uuid, responsible, new_problem_title))
        if new_problem_title and msg_uuid and responsible:
            try:
                result = Problem().create(msg_uuid=msg_uuid, responsible=responsible, title=new_problem_title)
            except Exception as e:
                err_text = "API.JS.Problem_create(). Произошла внутренняя ошибка. Пожалуйста, сообщите о " \
                           "ней администратору. {}".format(str(e))
                cherrypy.response.status = 500
                cherrypy.response.body = [err_text]
                return err_text
            else:
                cherrypy.response.status = 200
                cherrypy.response.body = [result.get('message')]
                return json.dumps(result.get('return_data'))

    @cherrypy.expose
    def problem_link(self, problem_uuid=None, msg_uuid=None):
        print("JS/Problem/Link - req")
        print("Problem_UUID: {}, MSG_UUID: {}".format(problem_uuid, msg_uuid))
        if problem_uuid and msg_uuid:
            try:
                result = Problem().link(msg_uuid=msg_uuid, problem_uuid=problem_uuid)
            except Exception as e:
                print("API.JS.Problem_link(). Ошибка линковки. {}".format(str(e)))
                err_text = "API.JS.Problem_link(). Произошла внутренняя ошибка. Пожалуйста, сообщите о " \
                           "ней администратору. {}".format(str(e))
                cherrypy.response.status = 500
                cherrypy.response.body = [err_text]
                return err_text
            else:
                cherrypy.response.status = 200
                cherrypy.response.body = [result.get('message')]
                return json.dumps(result.get('return_data'))

    @cherrypy.expose
    def message_train(self, uuid=None, category=None):
        print("JS/Message/Train - req")
        print("MSG_UUID: {}, CAT: {}".format(uuid, category))
        if uuid and category:
            try:
                result = Message().train(uuid=uuid, category=category)
            except Exception as e:
                err_text = "API.JS.Message.train(). Произошла внутренняя ошибка. Пожалуйста, сообщите о " \
                           "ней администратору. {}".format(str(e))
                cherrypy.response.status = 500
                cherrypy.response.body = [err_text]
                return err_text
            else:
                if not result.get('status'):
                    cherrypy.response.status = 200
                    cherrypy.response.body = [result.get('message')]
                    return result.get('message')

                if result.get('status') and category in CPO.WARNING_CATEGORY:

                    print("RESULT 1: {}".format(result.get('return_data')[0]))
                    print("RESULT 2: {}".format(result.get('return_data')[1]))
                    print("RESULT 3: {}".format(result.get('return_data')[2]))
                    print("RESULT 4: {}".format(result.get('return_data')[3]))
                    print("RESULT 5: {}".format(result.get('return_data')[4]))

                    try:
                        response = list()
                        # [cur_user, responsible_list, problem_list, uuid, user_list]
                        if result.get('return_data')[0]:
                            response.append(result.get('return_data')[0].uuid)
                        else:
                            response.append(None)

                        response.append(list())
                        for one in result.get('return_data')[1]:
                            if one not in CPO.HIDDEN_USERS:
                                response[1].append({'uuid': one, 'name': result.get('return_data')[4].get(one).name,
                                                    'surname': result.get('return_data')[4].get(one).surname})

                        response.append(result.get('return_data')[3])

                        response.append(list())
                        for one, count in result.get('return_data')[2]:
                            response[3].append({'uuid': one.uuid, 'title': one.title, 'count': count})

                    except Exception as e:
                        print("API.JS.Message.train(). Ошибка подготовки данных для возврата. {}".format(str(e)))
                        err_text = "API.JS.Message.train(). Произошла внутренняя ошибка. Пожалуйста, сообщите о " \
                                   "ней администратору. {}".format(str(e))
                        cherrypy.response.status = 500
                        cherrypy.response.body = [err_text]
                        return err_text
                    else:
                        cherrypy.response.status = 200
                        cherrypy.response.body = [result.get('message')]
                        return json.dumps(response)
                else:
                    cherrypy.response.status = 200
                    cherrypy.response.body = [result.get('message')]
                    return result.get('message')


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

        try:
            problem_list = CPO.get_problems_api()
        except Exception as e:
            print("Dialogs().warning(). Ошибка получения списка проблем. {}".format(str(e)))
            problem_list = []

        tmpl = self.lookup.get_template("control_center_dialogs_default.html")
        return tmpl.render(session_context=session_context, dialog=text, active_cat=None,
                           today=today, cur_day=cur_day, delta=delta_1, main_link=main_link,
                           category=cat_dict, task_status=CPO.TASK_STATUS, warn_cat=CPO.WARNING_CATEGORY,
                           task_list=task_list, message_list=message_list, unchecked=unchecked,
                           api_list=api_list, checked_with_task=task_list2, message_id_list=message_id_list,
                           problem_list=problem_list)


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



class Problems(object):

    lookup = TemplateLookup(directories=["./templates/controlcenter"], output_encoding="utf-8",
                            input_encoding="utf-8", encoding_errors="replace")

    """
    @cherrypy.expose
    @require(member_of("users"))
    def create_problem(self, msg_id=None):

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
        problem_msgid_list = list()
        msg_list = list()

        is_admin = member_of("admin")()
        #is_admin = True

        try:

            users = CPO.get_all_users_dict(disabled=True)
            session_context = cherrypy.session['session_context']

            if is_admin:
                user_uuid = None
            else:
                user_uuid = session_context["user"].uuid

            print user_uuid
            print session_context

            problems, msg_list = CPO.get_problems_messages_grouped(grouped="status", sort="create_time",
                                                                   user_uuid=user_uuid)

        except Exception as e:
            print "ControlCenter.problems(). Ошибка: %s." % str(e)
            # return ShowNotification().index("Произошла внутренняя ошибка.")
        else:

            print "Users: %s" % users
            print "problems: %s" % problems
            print "MSG list: %s" % msg_list

            tmpl = self.lookup.get_template("control_center_problems_all.html")
            return tmpl.render(session_context=session_context, problem_list=problems,
                               problem_status=CPO.PROBLEM_STATUS, problem_closed_status=CPO.PROBLEM_CLOSED_STATUS,
                               users=users, msg_list=msg_list, cur_day=datetime.datetime.now(), message=message)

    @cherrypy.expose
    @require(member_of("users"))
    def problem(self, uuid=None, message=None):
        """
        Функция показа problem.
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
    def change_problem_status(self, problem_uuid=None, status=None, from_url=None):
        if problem_uuid:
            try:
                CPO.change_task_status(task_uuid=problem_uuid, status=status)
            except Exception as e:
                print "change_problem_status(). Ошибка при смене статуса. %s" % str(e)
                return ShowNotification().index("Произошла внутренняя ошибка.")
        else:
            raise cherrypy.HTTPRedirect(from_url or "/control_center")
        raise cherrypy.HTTPRedirect(from_url or "/control_center/tasks/task?uuid=%s" % problem_uuid)

    @cherrypy.expose
    @require(member_of("users"))
    def change_problem_responsible(self, problem_uuid=None, responsible=None, from_url=None):
        if problem_uuid:
            try:
                CPO.change_task_responsible(task_uuid=problem_uuid, responsible=responsible)
            except Exception as e:
                print "change_task_responsible(). Ошибка при смене ответственного. %s" % str(e)
                return ShowNotification().index("Произошла внутренняя ошибка.")
        else:
            raise cherrypy.HTTPRedirect(from_url or "/control_center/tasks")
        raise cherrypy.HTTPRedirect(from_url or "/control_center/tasks/task?uuid=%s" % problem_uuid)

    @cherrypy.expose
    @require(member_of("users"))
    def add_problem_comment(self, problem_uuid=None, comment=None, from_url=None):
        if problem_uuid:
            try:
                CPO.add_task_comment(task_uuid=problem_uuid, comment=comment)
            except Exception as e:
                print "add_task_comment(). Ошибка при добавлении комментария. %s" % str(e)
                return ShowNotification().index("Произошла внутренняя ошибка.")
        else:
            raise cherrypy.HTTPRedirect(from_url or "/control_center/tasks")
        raise cherrypy.HTTPRedirect(from_url or "/control_center/tasks/task?uuid=%s" % problem_uuid)

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
                stat = CPO.get_stat_for_management(start=start_date, end=end_date,
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
            ["#FF9933", "#FFCC66"],
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
            tasks_by_cause[0] = sorted(tasks_by_cause[0], key=lambda x: x[1], reverse=True)
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
            tasks_by_empl[0] = sorted(tasks_by_empl[0], key=lambda x: x[1], reverse=True)
            for one in tasks_by_empl[0]:
                part = {
                    "value": one[1],
                    "color": colors[i][0],
                    "highlight": colors[i][1],
                    "label": " ".join([members.get(one[0]).name, members.get(one[0]).surname])
                }
                data.append(part)
                i += 1
                if i == len(colors):
                    i = 0

        elif chart_id == "problem_by_client":
            i = 0
            tasks_by_client[0] = sorted(tasks_by_client[0], key=lambda x: x[1], reverse=True)
            for one in tasks_by_client[0]:
                part = {
                    "value": one[1],
                    "color": colors[i][0],
                    "highlight": colors[i][1],
                    "label": " ".join([members.get(one[0]).name, members.get(one[0]).surname])
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

    auth = AuthController()
    settings = Settings()
    dialogs = Dialogs()
    tasks = Tasks()
    statistics = Statistics()
    problems = Problems()

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



SERVICES = dict()
service_root_dir = CPO.PREDICT_SERVICE_MODEL_REPO
from deep_learning.mod_classifier_test import specfeatures_new2, mytoken, features_extractor2

class Predict(object):

    exposed = True

    def POST(self, service=None, data=None):

        print service
        print data

        if not service:
            cherrypy.response.status = 500
            cherrypy.response.body = 'error'
            return json.dumps({'status': 500, 'message': 'Service name MUST be in request.'})

        if not data:
            cherrypy.response.status = 500
            cherrypy.response.body = 'error'
            return json.dumps({'status': 500, 'message': 'Data MUST be send in request.'})

        if not SERVICES.get(service) and not SERVICES.get(service):
            print("Predict(). Service: {}. Service NOT created.".format(service))
            cherrypy.response.status = 404
            cherrypy.response.body = 'error'
            return json.dumps({'status': 404, 'message': "Service NOT created."})


        # готовим данные
        class msg_data(object):
            message_text = ''
            message_title = ''
            category = ''
            in_reply_to = ''
            references = ''
            recipients = ''
            cc_recipients = ''

        try:
            data = json.loads(data)

            new = msg_data()
            new.message_text = data['message_text']
            new.message_title = data['message_title']
            new.category = data['category']
            new.in_reply_to = data['in_reply_to']
            new.references = data['references']
            new.recipients = data['recipients']
            new.cc_recipients = data['cc_recipients']

            X_test = SERVICES.get(service)[0].transform([new])
            pred = SERVICES.get(service)[1].predict_proba(X_test)
            # print SERVICES.get(service)[1].predict(X_test)
            result = [SERVICES.get(service)[1].classes_.tolist(), pred.tolist()[0]]

        except Exception as e:
            print("2218. Predict(). Service: {}. Error. {}".format(service, str(e)))
            cherrypy.response.status = 500
            cherrypy.response.body = 'error'
            return json.dumps({'status': 500, 'message': str(e)})
        else:
            print("Predict(). Service: {}. Answer. {}".format(service, result))
            cherrypy.response.status = 200
            cherrypy.response.body = ''
            return json.dumps({'status': 200, 'message': '{}'.format(result)})


class Create(object):

    exposed = True

    def POST(self, service=None):

        if not service:
            cherrypy.response.status = 500
            cherrypy.response.body = 'error'
            return json.dumps({'status': 500, 'message': 'Service name MUST be in request.'})

        if service in SERVICES.keys():
            cherrypy.response.status = 200
            cherrypy.response.body = ''
            return json.dumps({'status': 200, 'message': 'Service with this name exists.'})

        # ищем и загружаем сохраненный сервис
        service_dir = service_root_dir + '/' + service + '/'
        try:
            print 'Loading {}{}_vectorizer.pkl'.format(service_dir, service)
            # print joblib.load('{}{}_vectorizer.pkl'.format(service_dir, service))
            vectorizer = joblib.load('{}{}_vectorizer.pkl'.format(service_dir, service))
        except Exception as e:
            print("Create(). Service: {}. Vectorizer load error. {}".format(service, str(e)))
            cherrypy.response.status = 500
            cherrypy.response.body = 'error'
            return json.dumps({'status': 500, 'message': str(e)})

        try:
            print 'Loading {}{}_clf.pkl'.format(service_dir, service)
            # print joblib.load('{}{}_clf.pkl'.format(service_dir, service))
            clf = joblib.load('{}{}_clf.pkl'.format(service_dir, service))
        except Exception as e:
            print("Create(). Service: {}. Clf load error. {}".format(service, str(e)))
            cherrypy.response.status = 500
            cherrypy.response.body = 'error'
            return json.dumps({'status': 500, 'message': str(e)})
        else:
            print("Create(). Service: {}. All loaded successfully.".format(service))
            SERVICES[service] = [vectorizer, clf]
            cherrypy.response.status = 200
            cherrypy.response.body = ''
            return json.dumps({'status': 200, 'message': 'Service {} created'.format(service)})


class Info(object):

    exposed = True

    def GET(self, service=None):

        if not service:
            resp = list()
            for one in SERVICES.keys():
                resp.append({'name': one, 'status': 'ok'})

            cherrypy.response.status = 200
            cherrypy.response.body = ''
            return json.dumps({'status': 200, 'message': 'Service list.', 'services': resp})

        # ищем и загружаем сохраненный сервис
        if not SERVICES.get(service) and not SERVICES.get(service):
            print("Predict(). Service: {}. Service NOT created.".format(service))
            cherrypy.response.status = 404
            cherrypy.response.body = 'error'
            return json.dumps({'status': 404, 'message': "Service NOT created."})
        else:
            print("Predict(). Service: {}. Service created.".format(service))
            cherrypy.response.status = 200
            cherrypy.response.body = ''
            return json.dumps({'status': 200, 'message': "Service {} created.".format(service)})


class Root(object):
    """
        Основой сервис для запуска API и центров управления
    """

    # api = API()
    api = API_V2()
    api.problem = API_V2()
    api.problem.create = API_V2().problem_create
    api.problem.link = API_V2().problem_link
    api.message = API_V2().message_train

    api.js = API_JS_V2()
    api.js.problem = API_JS_V2()
    api.js.problem.create = API_JS_V2().problem_create
    api.js.problem.link = API_JS_V2().problem_link
    api.js.message = API_JS_V2().message_train

    control_center = ControlCenter()

    api.detect = API_V2()
    api.detect.predict = Predict()
    api.detect.create = Create()
    api.detect.info = Info()

    @cherrypy.expose
    @require(member_of("users"))
    def index(self, ads=None):

       raise cherrypy.HTTPRedirect("control_center/dialogs/warning")


cherrypy.config.update("server.config")

if __name__ == '__main__':
    CPO.initial_configuration()
    cherrypy.quickstart(Root(), '/', "app.config")
