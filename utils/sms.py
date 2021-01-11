#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: cc
# @Date  :2021-01-07


import json

from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest


@job
def sms(phone, tmp, params):
    client = AcsClient(
        settings.ALI_SMS['accessKeyId'], settings.ALI_SMS['accessSecret'], 'cn-hangzhou'
    )
    params = json.dumps(params)

    request = CommonRequest()
    request.set_accept_format('json')
    request.set_domain('dysmsapi.aliyuncs.com')
    request.set_method('POST')
    request.set_protocol_type('https')  # https | http
    request.set_version('2017-05-25')
    request.set_action_name('SendSms')

    request.add_query_param('RegionId', "cn-hangzhou")
    request.add_query_param('PhoneNumbers', phone)
    request.add_query_param('SignName', "得控飞行基地")
    request.add_query_param('TemplateCode', tmp)
    request.add_query_param('TemplateParam', params)

    response = client.do_action(request)
    return str(response, encoding='utf-8')
