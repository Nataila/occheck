#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: cc
# @Date  :2020-09-08

import multiprocessing

bind = '127.0.0.1:8016'
workers = multiprocessing.cpu_count() * 2 + 1

backlog = 2048
worker_class = "gevent"
worker_connections = 1000
daemon = False
debug = True
proc_name = 'gunicorn'
pidfile = './log/gunicorn.pid'
errorlog = './log/gunicorn.log'
