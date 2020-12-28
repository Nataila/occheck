#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: cc
# @Date  :2020-11-29

import json
from datetime import datetime

from fastapi import APIRouter, Depends, Header
from bson import json_util, ObjectId
from typing import Optional
import pymongo

from schemas import comment
from utils.database import db, redis
from utils import response_code, depends

router = APIRouter()

@router.post('/comments/new/', name='添加评价')
def comment_create(comment: comment.AddComment, user: dict = Depends(depends.token_is_true)):
    comment = comment.dict()
    comment.update({
        # 状态 0 未审核|1 已通过
        'status': 1,
        'created_at': datetime.now(),
        'uid': user['_id'],
    })
    doc = db.comments.insert(comment)
    return response_code.resp_200('ok')


@router.get('/comments/list/', name='评价列表')
def comment_list(skip: int = 0, limit: int = 50, token: Optional[str] = Header(None)):
    spec = {'status': 1}
    if token:
        uid = redis.get(token)
        user = db.user.find_one({'_id': ObjectId(uid)})
        if user['group'] == 1:
            spec['status'] = 0
    data = db.comments.find(spec).sort('created_at', pymongo.DESCENDING).skip(skip).limit(limit)
    data = json.loads(json_util.dumps(data))
    return response_code.resp_200(data)
