#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: cc
# @Date  :2020-11-30

import json
from datetime import datetime

from fastapi import APIRouter, Depends
from werkzeug.security import generate_password_hash, check_password_hash
from bson import json_util, ObjectId

from utils import response_code, tools, depends
from utils.database import db, redis
from utils.mailing import send_code

from schemas import task
from core.config import settings
from extensions import logger

router = APIRouter()


@router.post('/tasks/new/', name = '添加任务')
def new_task(task: task.NewTask, user: dict = Depends(depends.token_is_true)):
    if user['query_count'] <= 0:
        return response_code.resp_200('查询次数不足', message="failed")
    task = task.dict()
    task.update({
        # 状态:
        # 0 已上传查询文件
        # 1 已上传结果文件
        # 2 已生成评分PDF
        # 3 已合并PDF
        # 4 已发送邮件
        'status': 0,
        'created_at': datetime.now(),
        'uid': user['_id'],
    })
    doc = db.tasks.insert(task)
    db.user.update({'_id': user['_id']}, {'$inc': {'query_count': -1}})
    return response_code.resp_200('ok')


@router.get('/tasks/list/', name = '任务列表')
def task_list(status: int = None, skip: int = 0, limit: int = 50, user: dict = Depends(depends.token_is_true)):
    spec = {}
    if user['group'] == 0:
        spec['uid'] = user['_id']
    if status is not None:
        spec['status'] = status
    data = db.tasks.find(spec).skip(skip).limit(limit)
    data = json.loads(json_util.dumps(data))
    return response_code.resp_200(data)
