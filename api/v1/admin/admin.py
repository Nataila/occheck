#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: cc
# @Date  :2020-12-01


import json
from datetime import datetime

from fastapi import APIRouter, Depends
from werkzeug.security import generate_password_hash, check_password_hash
from bson import json_util, ObjectId

from utils import response_code, tools, depends
from utils.database import db, redis
from utils.mailing import send_code

from schemas import admin
from core.config import settings
from extensions import logger

router = APIRouter()


@router.post('/admin/task/done/', name="完成查询上传结果")
def task_done(task: admin.TaskDone, user: dict = Depends(depends.is_superuser)):
    task = task.dict()
    tid = task.pop('tid')
    task['status'] = 1
    db.tasks.update({'_id': ObjectId(tid)}, {'$set': task})
    return response_code.resp_200('ok')


@router.post('/admin/comment/', name="审核评价")
def comment(comment: admin.CommentStatus, user: dict = Depends(depends.is_superuser)):
    [cid, status] = map(comment.dict().get, ['cid', 'status'])
    db.comments.update({'_id': ObjectId(cid)}, {'$set': {'status': status}})
    return response_code.resp_200('ok')
