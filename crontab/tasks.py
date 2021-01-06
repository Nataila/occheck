#!/usr/bin/env python
# coding: utf-8
# cc@2020/11/27

import time
import json
import pdfkit

from apscheduler.schedulers.blocking import BlockingScheduler

from pymongo import MongoClient

from jinja2 import Environment, FileSystemLoader

from PyPDF2 import PdfFileReader, PdfFileMerger

MONGODB = {
    'host': '127.0.0.1',
    'port': 27017,
}

client = MongoClient(**MONGODB)
db = client['occheck']

env = Environment(loader=FileSystemLoader('./'))
template = env.get_template('index.html')

upload_dir = '/opt/outsource/occheck/server/uploads'

def score():
    data = db.tasks.find({'status': 1})
    for i in data:
        tid = str(i['_id'])
        uid = str(i['uid'])
        score_html_path = f'{upload_dir}/{uid}/{tid}_result.html'
        score_out_pdf_path = f'{upload_dir}/{uid}/{tid}_score.pdf'
        with open(score_html_path, 'w') as fout:
            html_content = template.render(**{'num': i['score']})
            print(html_content)
            pdfkit.from_string(html_content, score_out_pdf_path)

def every1m():
    '''每一分钟运行的任务'''
    score()

# scheduler = BlockingScheduler()
# 
# # 每隔 1分钟 运行
# scheduler.add_job(every1m, 'interval', minutes=1)
# 
# scheduler.start()

score()
