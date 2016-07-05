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



# Создаем новые таблицы
CPO.create_tables()

connection = CPO.Engine.connect()
result = None

# Обновляем базу
try:
    result = connection.execute(sql[0])
except Exception as e:
    print e.message, e.args
else:
    print result

try:
    result = connection.execute(sql[1])
except Exception as e:
    print e.message, e.args
else:
    print result

try:
    result = connection.execute(sql[2])
except Exception as e:
    print e.message, e.args
else:
    print result

try:
    result = connection.execute(sql[3])
except Exception as e:
    print e.message, e.args
else:
    print result

try:
    result = connection.execute(sql[4])
except Exception as e:
    print e.message, e.args
else:
    print result

try:
    if CPO.CURRENT_TRAIN_EPOCH == 0:
        result = connection.execute(sql[5])
except Exception as e:
    print e.message, e.args
else:
    print result

try:
    if CPO.CURRENT_TRAIN_EPOCH == 0:
        result = connection.execute(sql[6])
except Exception as e:
    print e.message, e.args
else:
    print result


try:
    result = connection.execute(sql[7])
except Exception as e:
    print e.message, e.args
else:
    print result

try:
    result = connection.execute(sql[8])
except Exception as e:
    print e.message, e.args
else:
    print result

try:
    result = connection.execute(sql[9])
except Exception as e:
    print e.message, e.args
else:
    print result


try:
    result = connection.execute(sql[10])
except Exception as e:
    print e.message, e.args
else:
    print result

try:
    result = connection.execute(sql[11])
except Exception as e:
    print e.message, e.args
else:
    print result


try:
    result = connection.execute(sql[12])
    update_12()
except Exception as e:
    print e.message, e.args
else:
    print result

try:
    print "# Обновление №13. Добавление администратора по умолчанию."
    result = connection.execute("SELECT count(*) FROM `users`;").fetchone()
    if not result:
            result = connection.execute(sql[13])
except Exception as e:
    print e.message, e.args
else:
    print result

try:
    print "# Обновление №14. Расчет статистики по старым данным."
    update_14()
except Exception as e:
    print e.message, e.args
else:
    print result

connection.close()


