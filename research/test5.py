#!/usr/bin/python -t
# coding: utf8

import sys
reload(sys)
sys.setdefaultencoding("utf-8")
sys.path.extend(['/Users/sergey/PycharmProjects/comparser/'])

import datetime
from configuration import *
import objects as CPO


import uuid

CPO.CURRENT_TRAIN_EPOCH = 2

causes = CPO.get_task_cause(task_uuid="031e6830-6265-4524-b884-fe0ae4ae7a6b")

print causes



