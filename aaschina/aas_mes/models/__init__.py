# -*-  coding: utf-8 -*-

"""
@version: 1.0
@author: luforn
@license: LGPL V3
@time: 2017-7-15 17:57
"""

"""
 *                    _ooOoo_
 *                   o8888888o
 *                   88" . "88
 *                   (| -_- |)
 *                    O\ = /O
 *                ____/`---'\____
 *              .   ' \\| |// `.
 *               / \\||| : |||// \
 *             / _||||| -:- |||||- \
 *               | | \\\ - /// | |
 *             | \_| ''\---/'' | |
 *              \ .-\__ `-` ___/-. /
 *           ___`. .' /--.--\ `. . __
 *        ."" '< `.___\_<|>_/___.' >'"".
 *       | | : `- \`.;`\ _ /`;.`/ - ` : | |
 *         \ \ `-. \_ __\ /__ _/ .-` / /
 * ======`-.____`-.___\_____/___.-`____.-'======
 *                    `=---='
 *
 * .............................................
 *
"""


MESLINETYPE = [('station', u'工位式生产'), ('flowing', u'流水线生产')]

import aas_mes_models
import aas_mes_line
import aas_mes_working
import aas_mes_badmode
import aas_mes_routing
import aas_mes_bom
import aas_mes_wires
import aas_mes_workstation
import aas_mes_mainorder
import aas_mes_workorder
import aas_mes_workticket
import aas_mes_tracing
import aas_mes_feedmaterial
import aas_mes_stockadjust
import aas_mes_lineusers
import aas_mes_serialnumber
import aas_mes_operation
import aas_mes_rework
import aas_mes_scrap
import aas_mes_allocation
import aas_mes_attendance
import aas_mes_settings
import aas_mes_container
import aas_mes_production
import aas_mes_producttest
