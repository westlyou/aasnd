# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-10-7 16:13
"""

import datetime

def get_china_time(timestr):
    temp_time = datetime.datetime.strptime(timestr, '%Y-%m-%d %H:%M:%S')
    temp_time = temp_time + datetime.timedelta(hours=8)
    return temp_time.strftime('%Y-%m-%d %H:%M:%S')

import aas_mesindex
import aas_feedmaterial
import aas_workorder
