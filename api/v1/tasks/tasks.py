#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: cc
# @Date  :2020-11-30

import os
import time
import json
from datetime import datetime

from fastapi import APIRouter, Depends, File, UploadFile
from bson import json_util, ObjectId

from utils import response_code, depends
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
        }
    )
    db.tasks.insert(task)
    db.user.update({'_id': user['_id']}, {'$inc': {'query_count': -1}})
    return response_code.resp_200('ok')


@router.get('/tasks/list/', name='任务列表')
def task_list(
    status: int = None,
    skip: int = 0,
    limit: int = 50,
    user: dict = Depends(depends.token_is_true),
):
    spec = {}
    if user['group'] == 0:
        spec['uid'] = ObjectId(user['_id'])
    if status is not None:
        spec['status'] = status
    data = db.tasks.find(spec).skip(skip).limit(limit)
    res_data = []
    for item in data:
        month = item['created_at'].strftime('%B')
        day = item['created_at'].strftime('%d')
        fids = [ObjectId(fid) for fid in item['file_path']]
        files = db.files.find({'_id': {'$in': fids}})
        file_names = ', '.join([f['old_name'] for f in files])
        res_data.append({
            'id': str(item['_id']),
            'month': month,
            'day': day,
            'status': item['status'],
            'files': file_names,
        })
    return response_code.resp_200(res_data)


@router.post("/tasks/upload/")
async def file_upload(
    file: UploadFile = File(...), user: dict = Depends(depends.token_is_true)
):
    uid = user['_id']
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
            'filename': new_file_name,
            'old_name': file.filename,
            'created_time': datetime.now(),
        }
    )
    return response_code.resp_200(
        {'filename': file.filename, 'id': str(_id), 'path': f"{uid}/{new_file_name}"}
    )
