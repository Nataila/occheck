#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: cc
# @Date  :2020-11-30


from pydantic import BaseModel
from typing import List

class NewTask(BaseModel):
    file_path: List[str]
    version: int


class Category(BaseModel):
    category: str


class UpdateItem(BaseModel):
    tid: str
    score: str
    repeatScore: str
    repeat: str
    program: str
