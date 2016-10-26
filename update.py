# -*- coding: utf-8 -*-
"""
Created on Fri Jul 24 17:04:18 2015

@author: sergey
"""
import sys

reload(sys)
sys.setdefaultencoding("utf-8")

import objects as CPO
import datetime
import configuration as CONF

sql = list()
# 0
sql.append("ALTER TABLE email_raw_data ADD COLUMN `message_text_html` MEDIUMTEXT NULL AFTER `message_text`;")
# 1
sql.append("ALTER TABLE `train_api` ADD COLUMN `train_epoch` INT(11) NULL AFTER `user_answer`;")
print "Перед выполнением закомменировать в objects.py CURRENT_TRAIN_EPOCH = read_epoch()."
# 2
sql.append("ALTER TABLE `train_data` ADD COLUMN `train_epoch` INT(11) NULL AFTER `category`;")
# 3
sql.append("ALTER TABLE `user_train_data` ADD COLUMN `train_epoch` INT(11) NULL AFTER `category`;")
# 4
sql.append("")
#sql.append("UPDATE `train_api` SET `train_epoch` = 0 WHERE `id` > 0;")
# 5
# Выполнить один раз
sql.append("")
# sql.append("UPDATE `train_data` SET `train_epoch` = 0 WHERE `id` > 0;")
# 6
# Выполнить один раз
sql.append("")
# sql.append("UPDATE `user_train_data` SET `train_epoch` = 0 WHERE `id` > 0;")

# 7
sql.append("ALTER TABLE `email_raw_data` ADD COLUMN `references` TEXT NULL AFTER `isbroken`,"
           "ADD COLUMN `in_reply_to` VARCHAR(255) NULL AFTER `references`;")

# 8
sql.append("ALTER TABLE `email_cleared_data` ADD COLUMN `references` TEXT NULL AFTER `notified`,"
           "ADD COLUMN `in_reply_to` VARCHAR(255) NULL AFTER `references`;")

# 9
sql.append("ALTER TABLE `email_err_cleared_data` ADD COLUMN `references` TEXT NULL AFTER `create_date`,"
           "ADD COLUMN `in_reply_to` VARCHAR(255) NULL AFTER `references`;")

# 10
sql.append("ALTER TABLE `train_data` ADD COLUMN `references` TEXT NULL AFTER `create_date`,"
           "ADD COLUMN `in_reply_to` VARCHAR(255) NULL AFTER `references`;")

# 11
sql.append("ALTER TABLE `email_raw_data`"
           "ADD COLUMN `orig_date_str` VARCHAR(255) NULL AFTER `in_reply_to`;")

# 12
sql.append("ALTER TABLE `train_api` "
           "ADD COLUMN `auto_cat` VARCHAR(255) NULL DEFAULT NULL AFTER `message_id`;")


def update_12():

    session = CPO.Session()
    try:
        resp = session.query(CPO.TrainAPIRecords).all()
    except Exception as e:
        print "Ошибка в обновлении №12. %s" % str(e)
    else:
        for one in resp:
            try:
                one.auto_cat = str(one.category).split("-", 1)[0]
            except Exception as e:
                print "Ошибка в обновлении №12. Выделение авто категории. Запись: %s. %s" % (one.uuid, str(e))

        session.commit()
        print "Обновление №12 проведено успешно."
    finally:
        session.close()


# 13
sql.append("INSERT INTO `users` (`uuid`, `name`, `surname`, `login`, `password`, `access_groups`, `disabled`, `email`)"
           " VALUES ('uuid-initial', 'admin', '', 'admin', 'Qazcde123', 'admin,users', '0', 'info@conparser.ru');")


# 14 расчет статистики
def update_14():

    print "Рассчитываем статистику за последние 3 месяца."

    today = datetime.datetime.now()
    for i in range(0, 184):
        delta = datetime.timedelta(days=i)
        try:
            day = today - delta
            print "Рассчитываем день: %s" % day.strftime("%d-%m-%Y %H:%M:%S")
            CPO.pred_stat_compute(for_day=day)
            print "*"*30
        except Exception as e:
            print "Ошибка расчета статистики за день %s. " % (today - delta)
            print str(e)

    print "Расчет закончен. Не забудьте добавить в CRON расчет статистики."


# 15
sql_update_15 = "ALTER TABLE `train_api` ADD COLUMN `check_date` DATETIME NULL DEFAULT NULL AFTER `date`;"

# 16
sql_update_16 = "ALTER TABLE `tasks` ADD COLUMN `last_status_change` DATETIME NULL AFTER `status`;"

#17
sql_update_17 = "ALTER TABLE `email_cleared_data` ADD COLUMN `channel_type` INT(11) NULL AFTER `id`;"

#18
sql_update_18 = "UPDATE `email_cleared_data` SET `channel_type` = 0 WHERE `id` > 0 and message_id like 'message%';"


#19
sql_update_19 = "ALTER TABLE `email_raw_data` CHANGE COLUMN `message_text` `message_text` MEDIUMTEXT NULL DEFAULT NULL ," \
                "CHANGE COLUMN `message_text_html` `message_text_html` MEDIUMTEXT NULL DEFAULT NULL;" \
                "ALTER TABLE `email_cleared_data` CHANGE COLUMN `message_text` `message_text` MEDIUMTEXT NULL DEFAULT NULL;" \
                "ALTER TABLE `email_err_cleared_data` CHANGE COLUMN `message_text` `message_text` MEDIUMTEXT NULL DEFAULT NULL;"


# Создаем новые таблицы
print("Создаем новые таблицы в БД.")
CPO.create_tables()

connection = CPO.Engine.connect()
result = None

# Обновляем базу
print("Обновление SQL №1.\n")
try:
    result = connection.execute(sql[0])
except Exception as e:
    print e.message, e.args
else:
    print result

print("Обновление SQL №2.\n")
try:
    result = connection.execute(sql[1])
except Exception as e:
    print e.message, e.args
else:
    print result

print("Обновление SQL №3.\n")
try:
    result = connection.execute(sql[2])
except Exception as e:
    print e.message, e.args
else:
    print result

print("Обновление SQL №4.\n")
try:
    result = connection.execute(sql[3])
except Exception as e:
    print e.message, e.args
else:
    print result

print("Обновление SQL №5.\n")
try:
    result = connection.execute(sql[4])
except Exception as e:
    print e.message, e.args
else:
    print result

print("Обновление SQL №6.\n")
try:
    if CPO.CURRENT_TRAIN_EPOCH == 0:
        result = connection.execute(sql[5])
except Exception as e:
    print e.message, e.args
else:
    print result

print("Обновление SQL №7.\n")
try:
    if CPO.CURRENT_TRAIN_EPOCH == 0:
        result = connection.execute(sql[6])
except Exception as e:
    print e.message, e.args
else:
    print result

print("Обновление SQL №8.\n")
try:
    result = connection.execute(sql[7])
except Exception as e:
    print e.message, e.args
else:
    print result

print("Обновление SQL №9.\n")
try:
    result = connection.execute(sql[8])
except Exception as e:
    print e.message, e.args
else:
    print result

print("Обновление SQL №10.\n")
try:
    result = connection.execute(sql[9])
except Exception as e:
    print e.message, e.args
else:
    print result

print("Обновление SQL №11.\n")
try:
    result = connection.execute(sql[10])
except Exception as e:
    print e.message, e.args
else:
    print result

print("Обновление SQL №12.\n")
try:
    result = connection.execute(sql[11])
except Exception as e:
    print e.message, e.args
else:
    print result

print("Обновление SQL №13.\n")
try:
    result = connection.execute(sql[12])
    update_12()
except Exception as e:
    print e.message, e.args
else:
    print result

print("Обновление SQL №13.\n")
try:
    print "\t#Добавление администратора по умолчанию."
    result = connection.execute("SELECT count(*) FROM `users`;").fetchone()
    if not result:
            result = connection.execute(sql[13])
except Exception as e:
    print e.message, e.args
else:
    print result

try:
    print "Обновление №14. \n\tРасчет статистики по старым данным."
    #   update_14()
except Exception as e:
    print e.message, e.args
else:
    print result

print("Обновление SQL №15.\n")
try:
    result = connection.execute(sql_update_15)
except Exception as e:
    print e.message, e.args
else:
    print result

print("Обновление SQL №16.\n")
try:
    result = connection.execute(sql_update_16)
except Exception as e:
    print e.message, e.args
else:
    print result

print("Обновление SQL №17.\n")
try:
    result = connection.execute(sql_update_17)
except Exception as e:
    print e.message, e.args
else:
    print result

print("Обновление SQL №18.\n")
try:
    result = connection.execute(sql_update_18)
except Exception as e:
    print e.message, e.args
else:
    print result

print("Обновление SQL №19.\n")
try:
    result = connection.execute(sql_update_19)
except Exception as e:
    print e.message, e.args
else:
    print result

print("Обновление №20.\n")
try:
    with open('configuration.py', 'a') as file:
        if not hasattr(CONF, 'CLIENT_NAME'):
            temp = raw_input("Input CLIENT_NAME for prediction services: ")
            if not temp:
                temp = CONF.db_name
            file.writelines("CLIENT_NAME = '{}'\n".format(temp))
            print "CONF.CLIENT_NAME - added to configuration"

        if not hasattr(CONF, 'PREDICT_SERVICE_HOSTNAME'):
            file.writelines("PREDICT_SERVICE_HOSTNAME = 'localhost'\n")
            print "CONF.PREDICT_SERVICE_HOSTNAME - added to configuration"

        if not hasattr(CONF, 'PREDICT_SERVICE_PORT'):
            file.writelines("PREDICT_SERVICE_PORT = '11111'\n")
            print "CONF.PREDICT_SERVICE_PORT - added to configuration"

        if not hasattr(CONF, 'PREDICT_SERVICE_NAME'):
            file.writelines("PREDICT_SERVICE_NAME = ['default']\n")
            print "CONF.PREDICT_SERVICE_NAME - added to configuration"

        if not hasattr(CONF, 'PREDICT_SERVICE_NAME_DEFAULT'):
            file.writelines("PREDICT_SERVICE_NAME_DEFAULT = 'default'\n")
            print "CONF.PREDICT_SERVICE_NAME_DEFAULT - added to configuration"

        if not hasattr(CONF, 'PREDICT_SERVICE_MODEL_REPO'):
            file.writelines("PREDICT_SERVICE_MODEL_REPO = '/home/deepdetect/service/models'\n")
            print "CONF.PREDICT_SERVICE_MODEL_REPO - added to configuration"

except Exception as e:
    print e.message, e.args
else:
    print result
finally:
    file.close()

print("Обновление №21.\n")
try:
    with open('configuration.py', 'a') as file:
        if not hasattr(CONF, 'LOG_PATH'):
            file.writelines("LOG_PATH = ''\n")
            print "CONF.LOG_PATH - added to configuration"

except Exception as e:
    print e.message, e.args
else:
    print result
finally:
    file.close()

#20
sql_update_22 = "ALTER TABLE `train_api`" \
                "ADD COLUMN `problem_uuid` VARCHAR(50) NULL DEFAULT NULL AFTER `train_epoch`;"
print("Обновление SQL №22.\n Добавляем столбец problem_uuid к train_api...")
try:
    result = connection.execute(sql_update_22)
except Exception as e:
    print e.message, e.args
else:
    print result
    print("Обновление SQL №20 - SUCCESS.\n")

print("Обновление №23.\n\tНовые переменные в конфигурации.")
try:
    with open('configuration.py', 'a') as file:
        if not hasattr(CONF, 'PROBLEM_STATUS'):
            file.writelines('PROBLEM_STATUS = ["Новая", "В работе", "Закрыта"]\n')
            print "\tCONF.PROBLEM_STATUS - added to configuration\n"
        if not hasattr(CONF, 'PROBLEM_CLOSED_STATUS'):
            file.writelines('PROBLEM_CLOSED_STATUS = 2\n')
            print "\tCONF.PROBLEM_CLOSED_STATUS - added to configuration\n"

except Exception as e:
    print("Обновление №23 - ERROR.\n")
    print e.message, e.args
else:
    print("Обновление №23 - SUCCESS.\n")
finally:
    file.close()

print("Обновление №24.\n\tНовые переменные в конфигурации.")
try:
    with open('configuration.py', 'a') as file:
        if not hasattr(CONF, 'HIDDEN_USERS'):
            file.writelines('# Пользователи не выводящиеся при взаимодействии с пользователями. '
                            'Технические пользователи.')
            file.writelines('HIDDEN_USERS = ["admin-uuid"]\n')
            print "\tCONF.HIDDEN_USERS - added to configuration\n"

            PREDICT_SERVICE_PARAMS_UPDATE = {
                'default':
                    {'sequence': 50,
                     'alphabet': u'!\“#%&’*+,-./0123456789:;<=>?@^_abcdefghijklmnopqrstuvwxyz«»'
                                 u'абвгдежзийклмнопрстуфхцчшщъыьэюяёєі“”',
                     'characters': True,
                     'nclasses': 2,
                     'finetuning': True,
                     'weights': 'model_iter_50000.caffemodel'}
            }

        if not hasattr(CONF, 'PREDICT_SERVICE_PARAMS'):
            file.writelines('# Параметры для создания сервисов классификации. '
                            'Ключ - название сервиса, далее настройки.\n')
            file.writelines('PREDICT_SERVICE_PARAMS = {}\n\n'.format(PREDICT_SERVICE_PARAMS_UPDATE))
            print "\tCONF.PREDICT_SERVICE_PARAMS - added to configuration\n"

        if not hasattr(CONF, 'LOG_PATH'):
            file.writelines('# LOG_PATH - каталог расположения логов. По умолчанию в каталоге пользователя. \n')
            file.writelines('LOG_PATH = ""\n\n')
            print "\tCONF.LOG_PATH - added to configuration\n"

except Exception as e:
    print("Обновление №24 - ERROR.\n")
    print e.message, e.args
else:
    print("Обновление №24 - SUCCESS.\n")
finally:
    file.close()


connection.close()


