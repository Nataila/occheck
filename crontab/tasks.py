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

from utils import mailing

MONGODB = {
    'host': '127.0.0.1',
    'port': 27017,
}

client = MongoClient(**MONGODB)
db = client['occheck']

env = Environment(loader=FileSystemLoader('./score_template'))
template = env.get_template('index.html')

upload_dir = '/data/occheck/server/uploads'

def score():
    '''评分html to pdf'''
    data = db.tasks.find({'status': 1})
    for i in data:
        tid = str(i['_id'])
        uid = str(i['uid'])
        score_html_path = f'{upload_dir}/{uid}/{tid}_result.html'
        score_out_pdf_path = f'{upload_dir}/{uid}/{tid}_score.pdf'
        level_map = ['优秀', '合格', '不合格']
        data = {
            'score': int(i.get('score', 0)),
            'repeatScore': int(i.get('repeatScore', 0)),
            'composite': int(i.get('composite', 0)),
            'level': level_map[i.get('level', 0)],
        }
        html_content = template.render(**data)
        pdfkit.from_string(html_content, score_out_pdf_path)
        # with open(score_html_path, 'w') as fout:
        #     html_content = template.render(**{'num': int(i['score'])})
        #     fout.write(html_content)
        #     # pdfkit.from_string(html_content, score_out_pdf_path)
        # pdfkit.from_file(score_html_path, score_out_pdf_path)
        db.tasks.find_one_and_update({'_id': i['_id']}, {'$set': {'status': 2}})


def merge_pdf():
    '''合并PDF'''
    data = db.tasks.find({'status': 2})
    for i in data:
        tid = str(i['_id'])
        uid = str(i['uid'])
        score_out_pdf_path = f'{upload_dir}/{uid}/{tid}_score.pdf'
        repeat_data = db.files.find_one({'_id': i['repeat']})
        repeat_file = repeat_data['filename']

        program_data = db.files.find_one({'_id': i['program']})
        program_file = program_data['filename']

        repeat_file_path = f'{upload_dir}/{uid}/{repeat_file}'
        program_file_path = f'{upload_dir}/{uid}/{program_file}'

        pdf_files = (score_out_pdf_path, repeat_file_path, program_file_path)

        last_file_name = f'occheck_result_{tid}.pdf'
        last_file_path = f'{upload_dir}/{uid}/{last_file_name}'

        result_pdf = PdfFileMerger()
        for pdf in pdf_files:
            with open(pdf, 'rb') as fp:
                pdf_reader = PdfFileReader(fp)
                result_pdf.append(pdf_reader, import_bookmarks=False)
        result_pdf.write(last_file_path)
        result_pdf.close()
        db.tasks.find_one_and_update({'_id': i['_id']}, {'$set': {'status': 3, 'last_file': last_file_name}})


def send_mail():
    '''发送邮件'''
    data = db.tasks.find({'status': 3})
    for i in data:
        uid = str(i['uid'])
        tid = str(i['_id'])
        # file_name = i['last_file']
        # last_file_path = f'{upload_dir}/{uid}/{file_name}'
        mailing.send_attach(i['username'], uid, tid)
        db.tasks.find_one_and_update({'_id': i['_id']}, {'$set': {'status': 4}})


def every1m():
    '''每一分钟运行的任务'''
    score()
    merge_pdf()
    send_mail()

scheduler = BlockingScheduler()

# 每隔 1分钟 运行
scheduler.add_job(every1m, 'interval', minutes=1)

scheduler.start()

# score()
# merge_pdf()
# send_mail()
