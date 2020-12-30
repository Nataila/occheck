#!/usr/bin/env python
# coding: utf-8
# cc@2020/08/28


import json
import time
from datetime import datetime

from fastapi import APIRouter, Depends
from werkzeug.security import generate_password_hash, check_password_hash
from bson import json_util

from utils import response_code, tools, depends, wx_pay
from utils.database import db, redis
from utils.mailing import send_code

from schemas import user
from core.config import settings
from extensions import logger

router = APIRouter()


@router.post("/account/signin/", name='登录')
def signin(user: user.UserSignin):
    '''登录'''
    email = user.dict().get('email')
    user = db.user.find_one({'email': email})
    try:
        token = tools.new_token(20)
        uid = str(user['_id'])
        redis.set(token, uid)
        return response_code.resp_200(
            {'token': token, 'email': email, 'id': uid, 'country': '美国', 'count': user['query_count'], 'group': user['group']}
        )
    except Exception:
        return response_code.resp_401()


@router.post('/account/send/mail/code/', name="发送验证码")
def send_mail_code(to: str):
    '''发送邮件验证码'''
    code = tools.new_token(3)
    logger.info(f'send {code} to {to}')
    redis.set(f'{settings.CODE_KEY}{to}', code, settings.CODE_KEY_EXPIRE)
    send_code(to, code)
    return response_code.resp_200('ok')


@router.post('/account/signup/', name='注册')
def signup(user: user.UserCreate):
    '''注册'''
    signup_count = int(redis.hget('sys:conf', 'signup_count'))
    [email, password, country] = map(user.dict().get, ['email', 'password', 'country'])
    encrypt_passwd = generate_password_hash(password)
    insert_data = {
        'email': email,
        'password': encrypt_passwd,
        'group': 0,  #  0: 普通用户，1: 管理员
        'country': country,  # 0: 美国，1: 英国，2: 澳洲，3: 加拿大
        'query_count': signup_count,
        'created_at': datetime.now(),
    }
    _id = db.user.insert(insert_data)
    ctx = {'email': email, 'id': str(_id)}
    return response_code.resp_200(ctx)


@router.post('/account/changepwd/', name='修改密码')
def change_pwd(passwd: user.ChangePwd, user: dict = Depends(depends.token_is_true)):
    '''修改密码'''
    pwhash = user['password']
    old_password = passwd.old_password
    passwd_check = check_password_hash(pwhash, old_password)
    if not passwd_check:
        return response_code.resp_422('密码不正确')
    db.user.find_one_and_update(
        user, {'$set': {'password': generate_password_hash(passwd.new_password2)}}
    )
    return response_code.resp_200('ok')


@router.post('/account/forget/', name='忘记密码')
def forget_passwd(passwd: user.ForgetPwd):
    email = passwd.email
    db.user.find_one_and_update(
        {'email': email},
        {'$set': {'password': generate_password_hash(passwd.new_password2)}},
    )
    return response_code.resp_200('ok')


@router.get('/account/list/', name='用户列表')
def user_list(skip: int = 0, limit: int = 50, user: dict = Depends(depends.is_superuser)):
    data = list(db.user.find().skip(skip).limit(limit))
    data = json.loads(json_util.dumps(data))
    return response_code.resp_200(data)


@router.get('/account/me/', name='用户详情')
def user_detail(user: dict = Depends(depends.token_is_true)):
    user['id'] = str(user['_id'])
    user.pop('_id')
    user.pop('password')
    return response_code.resp_200(user)


@router.post('/account/buy/', name='购买查询次数')
def account_buy(buyitem: user.BuyItem, user: dict = Depends(depends.token_is_true)):
    count = buyitem.count
    price = int(redis.hget('sys:conf', 'price'))
    total_price = count * price
    spec = {
        'count': count,
        'unit_price': price,
        'total': total_price,
        # 0:未付款 1:付款中 2: 已付款 3:付款失败
        'status': 0,
        'created_at': datetime.now(),
    }
    out_trade_no = f'{int(time.time())}{tools.new_token(8)}'
    spec['out_trade_no'] = out_trade_no
    dbid = db.financial.insert(spec)
    pay_info = wx_pay().unified_order(
        trade_type="NATIVE",
        product_id=str(dbid),
        body=f'购买查询次数',
        out_trade_no=out_trade_no,
        total_fee=str(int(total_price * 100)),
        attach='',
    )
    spec['nonce_str'] = pay_info['nonce_str']
    qrcode_url = pay_info['code_url']
    db.financial.find_and_modify({"_id": dbid}, {'$set': {'nonce_str': pay_info['nonce_str']}})
    ctx = {
        'qrcode': qrcode_url,
        'price': total_price,
    }
    return response_code.resp_200(ctx)

@router.post('/account/group/{uid}/', name='更改用户组')
def user_modify_group(user: dict = Depends(depends.is_superuser)):
    return response_code.resp_200('ok')
