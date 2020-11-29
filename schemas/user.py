import re
from datetime import datetime

from typing import Optional

from pydantic import BaseModel, EmailStr, validator
from werkzeug.security import check_password_hash

from utils.database import db, redis
from core.config import settings


# Shared properties
class UserBase(BaseModel):
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = True
    is_superuser: bool = False
    full_name: Optional[str] = None


class UserSignin(BaseModel):
    email: Optional[EmailStr] = None
    password: str

    @validator('password')
    def user_is_valid(cls, password, values):
        email = values.get('email')
        if email:
            user = db.user.find_one({'email': email})
        if not user:
            raise ValueError('账户或密码错误')
        pwhash = user['password']
        passwd_check = check_password_hash(pwhash, password)
        if not passwd_check:
            raise ValueError('账户或密码错误')
        return password


# Properties to receive via API on creation
class UserCreate(BaseModel):
    email: Optional[EmailStr] = None
    code: str
    nickname: str
    password1: str
    password2: str

    @validator('password2')
    def passwords_match(cls, v, values, **kwargs):
        if 'password1' in values and v != values['password1']:
            raise ValueError('两次密码不一致')
        return v

    @validator('email')
    def email_is_exists(cls, email):
        if not email:
            return email
        is_exists = db.user.find({'email': email}).count()
        if is_exists:
            raise ValueError('该用户已存在')
        return email


    @validator('code')
    def valid_code(cls, code, values):
        email = values.get('email')
        flag = email
        redis_code = redis.get(f'{settings.CODE_KEY}{flag}')
        if redis_code != code:
            raise ValueError('验证码不正确')
        return code


# Properties to receive via API on update
class UserUpdate(UserBase):
    password: Optional[str] = None


class ChangePwd(BaseModel):
    old_password: str
    new_password1: str
    new_password2: str

    @validator('new_password2')
    def valid_password2(cls, pwd2, values):
        if pwd2 != values.get('new_password1'):
            raise ValueError('两次密码不一致')
        return pwd2


class ForgetPwd(BaseModel):
    email: EmailStr
    code: str
    new_password1: str
    new_password2: str

    @validator('email')
    def email_is_exists(cls, email):
        is_exists = db.user.find({'email': email}).count()
        if not is_exists:
            raise ValueError('该用户不存在')
        return email

    @validator('code')
    def valid_code(cls, code, values):
        email = values.get('email')
        redis_code = redis.get(f'{settings.CODE_KEY}{email}')
        if redis_code != code:
            raise ValueError('验证码不正确')
        return code

    @validator('new_password2')
    def valid_password2(cls, pwd2, values):
        if pwd2 != values.get('new_password1'):
            raise ValueError('两次密码不一致')
        return pwd2
