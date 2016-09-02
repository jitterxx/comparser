#!/usr/bin/python -t
# coding: utf8

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['..'])
import re
import objects as CPO
import datetime

session = CPO.Session()

empl_access_list = list()


# список емайл адресов и доменов клиентов к которым у этого пользователя есть доступ
client_access_list = CPO.get_watch_list(user_uuid="admin-uuid", is_admin=True)

api_list, message_list, message_id_list, unchecked, checked = \
                CPO.get_dialogs(for_day=datetime.datetime.now(), cat=CPO.WARNING_CATEGORY,
                                empl_access_list=empl_access_list,
                                client_access_list=client_access_list)

for id in message_id_list:
    print(id)
    print(message_list[id].orig_date)
    print("\n")

for_day = datetime.datetime.now()
start = datetime.datetime.strptime("%s-%s-%s 00:00:00" % (for_day.year, for_day.month, for_day.day),
                                   "%Y-%m-%d %H:%M:%S")
end = datetime.datetime.strptime("%s-%s-%s 23:59:59" % (for_day.year, for_day.month, for_day.day),
                                 "%Y-%m-%d %H:%M:%S")

cat = CPO.WARNING_CATEGORY

resp = session.query(CPO.Msg).\
    filter(CPO.and_(CPO.Msg.create_date >= start, CPO.Msg.create_date <= end), CPO.Msg.isclassified == 1,
           CPO.or_(*[CPO.Msg.category.like(c + "%") for c in cat])).\
    order_by(CPO.Msg.create_date.desc()).all()

ll = list()

for one in resp:
    print(one.message_id)
    print(one.orig_date)
    print("\n")
    ll.append(one.message_id)

print api_list.keys()
print ll

i = len(ll)
while i > 0:
    if ll[i] not in ll:
        ll.pop[i]
    i = i - 1

print ll