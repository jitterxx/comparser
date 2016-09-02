#!/usr/bin/python -t
# coding: utf8

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])
import re
import objects as CPO
import datetime


if __name__ == '__main__':

    session = CPO.Session()
    try:

        for_day1 = str(sys.argv[1]).split("-")
        for_day2 = str(sys.argv[2]).split("-")

        CPO.initial_configuration()

        CURRENT_TRAIN_EPOCH = CPO.read_epoch()


        # правильные даты
        start_date = datetime.datetime.strptime("%s-%s-%s 00:00:00" %
                                                (for_day1[2], for_day1[1], for_day1[0]),
                                                "%Y-%m-%d %H:%M:%S")
        end_date = datetime.datetime.strptime("%s-%s-%s 23:59:59" % (for_day2[2], for_day2[1], for_day2[0]),
                                              "%Y-%m-%d %H:%M:%S")

        print "Start_date: ", start_date
        print "End_date: ", end_date

        # Общее количество классифицированных сообщений
        session = CPO.Session()

        try:
            resp = session.query(CPO.Msg).filter(CPO.and_(CPO.Msg.create_date >= start_date,
                                                          CPO.Msg.create_date <= end_date,
                                                          CPO.Msg.isclassified == 1)).count()
        except Exception as e:
            print str(e)
            session.close()
            raise e
        else:
            msg_all = int(resp)
            print "общее количество классифицированных сообщений: %s" % resp

        cat = CPO.GetCategory().keys()
        msg_cat = dict()
        msg_cat_check = dict()
        msg_in_cat_wrong = dict()
        error_in_cat = dict()
        accuracy_in_cat = dict()

        # Количество сообщений, определенных системой, во всех категориях
        for c in cat:
            msg_cat[c] = 0
            msg_cat_check[c] = 0
            msg_in_cat_wrong[c] = 0
            error_in_cat[c] = 0.0
            accuracy_in_cat[c] = 0.0

        try:
            resp = session.query(CPO.TrainAPIRecords.auto_cat, CPO.func.count(CPO.TrainAPIRecords.auto_cat)).\
                filter(CPO.and_(CPO.TrainAPIRecords.date >= start_date, CPO.TrainAPIRecords.date <= end_date,
                                CPO.TrainAPIRecords.train_epoch == CURRENT_TRAIN_EPOCH)).\
                group_by(CPO.TrainAPIRecords.auto_cat).all()
        except Exception as e:
            print str(e)
            raise e
        else:

            for n, c in resp:
                msg_cat[n] = c

            print "Количество сообщений, определенных системой, во всех категориях: %s" % resp

        # Количество сообщений, проверенных пользователями, во всех категориях
        try:
            resp = session.query(CPO.TrainAPIRecords.auto_cat, CPO.func.count(CPO.TrainAPIRecords.auto_cat)).\
                filter(CPO.and_(CPO.TrainAPIRecords.date >= start_date, CPO.TrainAPIRecords.date <= end_date,
                                CPO.TrainAPIRecords.train_epoch == CURRENT_TRAIN_EPOCH,
                                CPO.TrainAPIRecords.user_action == 1)).\
                group_by(CPO.TrainAPIRecords.auto_cat).all()
        except Exception as e:
            print str(e)
            session.close()
            raise e
        else:
            for n,c in resp:
                msg_cat_check[n] = c
            print "Количество сообщений, проверенных пользователями, во всех категориях: %s" % resp

        # Количество сообщений во всех категориях, где авто-категория не совпадает с проверочной
        try:
            resp = session.query(CPO.TrainAPIRecords.auto_cat, CPO.func.count(CPO.TrainAPIRecords.auto_cat)).\
                filter(CPO.and_(CPO.TrainAPIRecords.date >= start_date, CPO.TrainAPIRecords.date <= end_date,
                                CPO.TrainAPIRecords.train_epoch == CURRENT_TRAIN_EPOCH,
                                CPO.TrainAPIRecords.user_action == 1,
                                CPO.TrainAPIRecords.user_answer != CPO.TrainAPIRecords.auto_cat)).\
                group_by(CPO.TrainAPIRecords.auto_cat).all()
        except Exception as e:
            print str(e)
            session.close()
            raise e
        else:
            for n,c in resp:
                msg_in_cat_wrong[n] = c
            print "Количество сообщений во всех категориях, где авто-категория не совпадает с проверочной: %s" % resp

        try:
            try:
                full_accuracy = 1.0 - float(sum([t for t in msg_in_cat_wrong.values()]))/sum([t for t in msg_cat_check.values()])
            except ZeroDivisionError as e:
                print "Full accuracy. Деление на 0."
                full_accuracy = 0.0
            else:
                print "Общая точность системы: ", full_accuracy


            """
            # Удаляем старую статистику за этот день
            try:
                resp = session.query(CPO.PredictionStatistics).filter(CPO.and_(CPO.PredictionStatistics.date >= start_date,
                                                                               CPO.PredictionStatistics.date <= end_date)).delete()
                session.commit()
            except Exception as e:
                print str(e)
            else:
                print "Старые данные удалены. for_day = %s" % for_day
                # raw_input()
            """

            for c in cat:

                try:
                    error_in_cat[c] = float(msg_in_cat_wrong[c])/msg_cat_check[c]
                except ZeroDivisionError as e:
                    print "Erron_in_cat. Деление на 0."
                    pass

                try:
                    accuracy_in_cat[c] = 1.0 - error_in_cat[c]
                except ZeroDivisionError as e:
                    print "accuracy_in_cat. Деление на 0."
                    pass

                """
                new_stat = PredictionStatistics()
                new_stat.date = for_day
                new_stat.msg_all = msg_all
                new_stat.category = str(c)
                new_stat.msg_in_cat = msg_cat[c]
                new_stat.msg_in_cat_check = msg_cat_check[c]
                new_stat.msg_in_cat_wrong = msg_in_cat_wrong[c]
                new_stat.error_in_cat = error_in_cat[c]
                new_stat.accuracy_in_cat = accuracy_in_cat[c]
                new_stat.full_accuracy = full_accuracy
                new_stat.train_epoch = CURRENT_TRAIN_EPOCH
                """

                print "Процент ошибок определения системой категории %s: " % c, error_in_cat[c]
                print "Точность системы в категории %s: " % c, accuracy_in_cat[c]
                print "\n"

                # session.add(new_stat)
                # session.commit()

        except Exception as e:
            print str(e)
            pass

    except Exception as e:
        print str(e)
        raise e

    finally:
        session.close()
