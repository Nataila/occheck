#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: cc
# @Date  :2020-12-01


from pydantic import BaseModel

class TaskDone(BaseModel):
    tid: str
    grammarFile: str
    grammarScore: int
    repeatFile: str
    repeatScore: str


class CommentStatus(BaseModel):
    cid: str
    status: int
