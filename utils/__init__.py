#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/6/5 17:37
# @Author  : CoderCharm
# @File    : __init__.py.py
# @Software: PyCharm
# @Desc    :
"""

"""
from core.config import settings
from weixin.pay import WeixinPay

def wx_pay(key=None, cert=None, notify_uri=None):
    wp = settings.WX_PAY
    app_id = wp['app_id']
    if not notify_uri:
        notify_uri = wp['notify_url']
    if not notify_uri.startswith('http'):
        notify_uri = '{}{}'.format(settings.SITE_URL, notify_uri)
    pay = WeixinPay(
        app_id=app_id,
        mch_id=wp['mch_id'],
        mch_key=wp['mch_key'],
        notify_url=notify_uri,
        key=key,
        cert=cert,
    )
    return pay
