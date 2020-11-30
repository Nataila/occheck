#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/6/5 17:44
"""

路由汇总

"""

from fastapi import APIRouter
from api.v1.account import account
from api.v1.comments import comments
from api.v1.tasks import tasks

api_v1 = APIRouter()

api_v1.include_router(account.router, tags=["用户管理"])
api_v1.include_router(comments.router, tags=["用户评价"])
api_v1.include_router(tasks.router, tags=["任务"])
