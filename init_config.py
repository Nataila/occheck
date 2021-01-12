#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: cc
# @Date  :2020-11-29

import json

from utils.database import redis


def system_config():
    '''
    初始化系统配置
    '''
    conf = {
        # 注册赠送的次数
        'signup_count': 3,
        # 购买次数的单件 ?/次
        'price': 35,
        # 推广赠送的次数
        'sem_count': 3,
        # 通知的手机号
        'phone': '15965347737',
    }

    for i, j in conf.items():
        redis.hset('sys:conf', i, j)

    print('DONE')

if __name__ == "__main__":
    system_config()
