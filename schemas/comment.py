#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: cc
# @Date  :2020-11-29

from datetime import datetime

from pydantic import BaseModel

from typing import Optional

class AddComment(BaseModel):
    name: str
    content: str
    location: str
