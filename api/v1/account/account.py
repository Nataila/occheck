#!/usr/bin/env python
# coding: utf-8
# cc@2020/08/28


import json
import time
from datetime import datetime

from fastapi import APIRouter, Depends, Body, Request
from werkzeug.security import generate_password_hash, check_password_hash
from bson import json_util, ObjectId

from utils import response_code, tools, depends, wx_pay
from utils.database import db, redis
from utils.mailing import send_code

from schemas import user
from core.config import settings
from extensions import logger
from typing import Optional

from pydantic import BaseModel

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
            {
                'token': token,
                'email': email,
                'id': uid,
                'country': '美国',
                'count': user['query_count'],
                'group': user['group'],
            }
        )
    except Exception:
        return response_code.resp_401()


@router.post('/account/send/mail/code/', name="发送验证码")
def send_mail_code(email: user.SendMail):
    '''发送邮件验证码'''
    code = tools.new_token(3)
    to = email.email
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
def user_list(
    skip: int = 0,
    limit: int = 50,
    search: str = '',
    user: dict = Depends(depends.is_superuser),
):
    spec = {}
    if search:
        spec['$or'] = [{'email': {'$regex': search}}]
    data = list(db.user.find(spec).skip(skip).limit(limit))
    data = json.loads(json_util.dumps(data))
    total = db.user.find().count()
    ctx = {'data': data, 'total': total}
    return response_code.resp_200(ctx)


@router.get('/account/me/', name='个人详情')
def me_detail(user: dict = Depends(depends.token_is_true)):
    user['id'] = str(user['_id'])
    user.pop('_id')
    user.pop('password')
    return response_code.resp_200(user)


@router.get('/account/detail/{uid}/', name='用户详情')
def user_detail(uid: str, user: dict = Depends(depends.is_superuser)):
    data = db.user.find_one({'_id': ObjectId(uid)})
    data = json.loads(json_util.dumps(data))
    return response_code.resp_200(data)


class AccountUpdate(BaseModel):
    group: Optional[int]
    country: Optional[int]
    query_count: Optional[int]


@router.put('/account/update/{uid}/', name='用户更新')
def user_update(
    uid: str, item: AccountUpdate, user: dict = Depends(depends.token_is_true)
):
    if user['group'] != 1 and str(user['_id']) != uid:
        return response_code.resp_403()

    update_data = item.dict()
    for i, j in item.dict().items():
        if j == None:
            update_data.pop(i)
    db.user.find_one_and_update({'_id': ObjectId(uid)}, {'$set': update_data})
    return response_code.resp_200('ok')


@router.post('/account/buy/', name='购买查询次数')
def account_buy(buyitem: user.BuyItem, user: dict = Depends(depends.token_is_true)):
    count = buyitem.count
    price = int(redis.hget('sys:conf', 'price'))
    total_price = count * price
    spec = {
        'uid': user['_id'],
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
        attach=str(dbid),
    )
    spec['nonce_str'] = pay_info['nonce_str']
    qrcode_url = pay_info['code_url']
    db.financial.find_and_modify(
        {"_id": dbid}, {'$set': {'nonce_str': pay_info['nonce_str']}}
    )
    ctx = {
        'qrcode': qrcode_url,
        'price': total_price,
        'fid': str(dbid),
    }
    return response_code.resp_200(ctx)


@router.post('/account/buy/notify/', name='微信支付回调')
async def account_buy_notify(request: Request):
    wp = wx_pay()
    data = await request.body()
    data = wp.to_dict(data.decode('utf-8'))
    dbid = data['attach']
    if not wp.check(data):
        return wp.reply("验证失败", False)
    otn = data['out_trade_no']
    financial = db.financial.find_one({'_id': ObjectId(dbid)})
    db.financial.find_one_and_update(
        {'_id': ObjectId(dbid)},
        {'$set': {'status': 2, 'transaction_id': data['transaction_id']}},
    )
    db.user.find_one_and_update(
        {'_id': financial['uid']}, {'$inc': {'query_count': financial['count']}}
    )
    return wp.reply("OK", True)


@router.get('/account/sysconf/', name='系统配置')
def get_sysconf(user: dict = Depends(depends.token_is_true)):
    conf = redis.hgetall('sys:conf')
    return response_code.resp_200(conf)


class SysConfItem(BaseModel):
    signup_count: str
    price: str
    sem_count: str


@router.post('/account/sysconf/', name='系统配置设置')
def get_sysconf(item: SysConfItem, user: dict = Depends(depends.is_superuser)):
    for i, j in item.dict().items():
        redis.hset('sys:conf', i, j)
    return response_code.resp_200('ok')


@router.post('/account/buy/check/', name='查询是否支付成功')
def account_buy_check(
    payload: dict = Body(...), user: dict = Depends(depends.token_is_true)
):
    fid = payload['fid']
    data = db.financial.find_one({'_id': ObjectId(fid)})
    if data['status'] == 2:
        return response_code.resp_200('ok')
    return response_code.resp_200('failed')
