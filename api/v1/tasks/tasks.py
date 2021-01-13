#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: cc
# @Date  :2020-11-30

import os
import time
import json
from datetime import datetime
import pymongo

from fastapi import APIRouter, Depends, File, UploadFile, Form
from bson import json_util, ObjectId
from starlette.responses import FileResponse

from utils import response_code, depends, sms
from utils.database import db

from schemas import task
from core.config import settings
from extensions import logger

router = APIRouter()


@router.post('/tasks/new/', name='添加任务')
def new_task(task: task.NewTask, user: dict = Depends(depends.token_is_true)):
    if user['query_count'] <= 0:
        return response_code.resp_200('查询次数不足', message="failed")
    task = task.dict()
    task.update(
        {
            # 状态:
            # 0 已上传查询文件
            # 1 已上传结果文件
            # 2 已生成评分PDF
            # 3 已合并PDF
            # 4 已发送邮件
            'status': 0,
            'created_at': datetime.now(),
            'uid': user['_id'],
            'username': user['email'],
        }
    )
    db.tasks.insert(task)
    db.user.update({'_id': user['_id']}, {'$inc': {'query_count': -1}})
    sms.send_notify()
    return response_code.resp_200('ok')


@router.get('/tasks/detail/{fid}/', name='任务详情')
def task_detail(fid: str, user: dict = Depends(depends.is_superuser)):
    data = db.tasks.find_one({'_id': ObjectId(fid)})
    data = json.loads(json_util.dumps(data))
    return response_code.resp_200(data)


def get_level(t, g, x):
    """
    t: 重复率
    g: 语法评分
    x: 综合评分
    """
    if t > 20 or g < 80:
        return 2
    if x < 65:
        return 2
    elif 65 <= x < 85:
        return 1
    else:
        return 0


@router.post('/tasks/update/', name='修改任务')
def task_update(item: task.UpdateItem, user: dict = Depends(depends.is_superuser)):
    task = item.dict()
    task['program'] = ObjectId(task['program'])
    task['repeat'] = ObjectId(task['repeat'])
    task['status'] = 1
    # 重复率
    rs = item.repeatScore
    # 语法评分
    score = item.score
    # 综合得分
    x = int((100 - float(rs)) * float(score) / 100)
    # 登机
    level = get_level(float(rs), float(score), float(x))
    task['composite'] = x
    # ['优秀', '合格', '不合格']
    task['level'] = level
    tid = task.pop('tid')
    res = db.tasks.find_one_and_update({'_id': ObjectId(tid)}, {'$set': task})
    if res:
        return response_code.resp_200('ok')


@router.get('/tasks/list/', name='任务列表')
def task_list(
    status: int = None,
    skip: int = 0,
    limit: int = 50,
    search: str = '',
    user: dict = Depends(depends.token_is_true),
):
    spec = {}
    if search:
        spec['$or'] = [{'username': {'$regex': search}}]
    if user['group'] == 0:
        spec['uid'] = ObjectId(user['_id'])
    if status is not None:
        spec['status'] = status
    data = (
        db.tasks.find(spec)
        .sort('created_at', pymongo.DESCENDING)
        .skip(skip)
        .limit(limit)
    )
    res_data = []
    for item in data:
        month = item['created_at'].strftime('%B')
        day = item['created_at'].strftime('%d')
        fids = [ObjectId(fid) for fid in item['file_path']]
        files = db.files.find({'_id': {'$in': fids}})
        file_names = [{'name': f['old_name'], 'fid': str(f['_id'])} for f in files]
        res_data.append(
            {
                'id': str(item['_id']),
                'key': str(item['_id']),
                'month': month,
                'version': item['version'],
                'score': item.get('score'),
                'repeatScore': item.get('repeatScore'),
                'level': item.get('level'),
                'composite': item.get('composite'),
                'day': day,
                'username': item.get('username', ''),
                'status': item['status'],
                'files': file_names,
            }
        )
    ctx = {
        'data': res_data,
        'total': db.tasks.find().count(),
    }
    return response_code.resp_200(ctx)


@router.post("/tasks/upload/")
async def file_upload(
    file: UploadFile = File(...),
    category: int = Form(...),
    tuid: str = Form(...),
    user: dict = Depends(depends.token_is_true),
):
    uid = user['_id']
    if category != 0 and user['group'] == 1:
        uid = ObjectId(tuid)
    f = await file.read()
    ext = os.path.splitext(file.filename)[-1]
    user_dir = f'{settings.UPLOAD_DIR}/{str(uid)}'
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    new_file_name = "%d%s" % (int(time.time() * 1000), ext)
    os_path = os.path.join(user_dir, new_file_name)

    with open(os_path, "wb") as n:
        n.write(f)
    _id = db.files.insert(
        {
            'uid': uid,
            'category': category,  # 0: 查询文件 1: 查重文件 2: 语法文件
            'filename': new_file_name,
            'old_name': file.filename,
            'created_time': datetime.now(),
        }
    )
    return response_code.resp_200(
        {
            'filename': file.filename,
            'id': str(_id),
            'category': category,
            'path': f"{uid}/{new_file_name}",
        }
    )


@router.get("/download/{fid}/", name='文件下载')
def download(fid: str, user: dict = Depends(depends.token_is_true)):
    if user['group'] != 1:
        return response_code.resp_401()
    file = db.files.find_one({'_id': ObjectId(fid)})
    uid = file['uid']
    name = file['filename']
    user_dir = f'{settings.UPLOAD_DIR}/{str(uid)}'
    file_path = f'{user_dir}/{name}'
    return FileResponse(file_path, filename=file['old_name'])


@router.get("/result/download/{uid}/{fid}/", name="结果文件下载")
def result_download(uid: str, fid: str):
    user_dir = f'{settings.UPLOAD_DIR}/{str(uid)}'
    file_path = f'{user_dir}/occheck_result_{fid}.pdf'
    return FileResponse(file_path, filename=f'occheck查询结果_{fid}.pdf')
