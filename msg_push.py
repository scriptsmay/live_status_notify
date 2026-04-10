# -*- coding: utf-8 -*-

"""
Author: Hmily
GitHub: https://github.com/ihmily
Date: 2023-09-03 19:18:36
Update: 2025-01-23 17:16:12
Copyright (c) 2023-2024 by Hmily, All Rights Reserved.
"""
from typing import Dict, Any
import json
import base64
import os
import urllib.request
import urllib.error
import smtplib
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from src.utils import logger

# 支持系统代理配置
proxy_env = {
    'http': os.environ.get('http_proxy') or os.environ.get('HTTP_PROXY'),
    'https': os.environ.get('https_proxy') or os.environ.get('HTTPS_PROXY'),
    'no': os.environ.get('no_proxy') or os.environ.get('NO_PROXY'),
}
proxy_config = {k: v for k, v in proxy_env.items() if v}
proxy_handler = urllib.request.ProxyHandler(proxy_config) if proxy_config else urllib.request.ProxyHandler({})
opener = urllib.request.build_opener(proxy_handler)
headers: Dict[str, str] = {'Content-Type': 'application/json'}


def dingtalk(url: str, content: str, number: str = None, is_atall: bool = False) -> Dict[str, Any]:
    success = []
    error = []
    api_list = url.replace('，', ',').split(',') if url.strip() else []
    for api in api_list:
        json_data = {
            'msgtype': 'text',
            'text': {
                'content': content,
            },
            "at": {
                "atMobiles": [number] if number else [],
                "isAtAll": is_atall
            },
        }
        try:
            data = json.dumps(json_data).encode('utf-8')
            req = urllib.request.Request(api, data=data, headers=headers)
            response = opener.open(req, timeout=10)
            json_str = response.read().decode('utf-8')
            json_data = json.loads(json_str)
            if json_data['errcode'] == 0:
                success.append(api)
            else:
                error.append(api)
                logger.error(f'钉钉推送失败, 推送地址：{api}, {json_data["errmsg"]}')
        except Exception as e:
            error.append(api)
            logger.error(f'钉钉推送失败, 推送地址：{api}, 错误信息:{e}')
    return {"success": success, "error": error}


def xizhi(url: str, title: str, content: str) -> Dict[str, Any]:
    success = []
    error = []
    api_list = url.replace('，', ',').split(',') if url.strip() else []
    for api in api_list:
        json_data = {
            'title': title,
            'content': content
        }
        try:
            data = json.dumps(json_data).encode('utf-8')
            req = urllib.request.Request(api, data=data, headers=headers)
            response = opener.open(req, timeout=10)
            json_str = response.read().decode('utf-8')
            json_data = json.loads(json_str)
            if json_data['code'] == 200:
                success.append(api)
            else:
                error.append(api)
                logger.error(f'微信推送失败, 推送地址：{api}, 失败信息：{json_data["msg"]}')
        except Exception as e:
            error.append(api)
            logger.error(f'微信推送失败, 推送地址：{api}, 错误信息:{e}')
    return {"success": success, "error": error}


def send_email(email_host: str, login_email: str, email_pass: str, sender_email: str, sender_name: str,
               to_email: str, title: str, content: str, smtp_port: int = None, open_ssl: bool = True) -> Dict[str, Any]:
    receivers = to_email.replace('，', ',').split(',') if to_email.strip() else []

    try:
        message = MIMEMultipart()
        send_name = base64.b64encode(sender_name.encode("utf-8")).decode()
        message['From'] = f'=?UTF-8?B?{send_name}?= <{sender_email}>'
        message['Subject'] = Header(title, 'utf-8')
        if len(receivers) == 1:
            message['To'] = receivers[0]

        t_apart = MIMEText(content, 'plain', 'utf-8')
        message.attach(t_apart)

        if open_ssl:
            smtp_port = int(smtp_port) or 465
            smtp_obj = smtplib.SMTP_SSL(email_host, smtp_port)
        else:
            smtp_port = int(smtp_port) or 25
            smtp_obj = smtplib.SMTP(email_host, smtp_port)
        smtp_obj.login(login_email, email_pass)
        smtp_obj.sendmail(sender_email, receivers, message.as_string())
        return {"success": receivers, "error": []}
    except smtplib.SMTPException as e:
        logger.error(f'邮件推送失败, 推送邮箱：{to_email}, 错误信息:{e}')
        return {"success": [], "error": receivers}


def tg_bot(chat_id: str, token: str, content: str) -> Dict[str, Any]:
    try:
        json_data = {
            "chat_id": chat_id,
            'text': content
        }
        url = f'https://api.telegram.org/bot{token}/sendMessage'
        data = json.dumps(json_data).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers=headers)
        response = urllib.request.urlopen(req, timeout=15)
        response.read().decode('utf-8')
        return {"success": [1], "error": []}
    except Exception as e:
        logger.error(f'tg推送失败, 聊天ID：{chat_id}, 错误信息:{e}')
        return {"success": [], "error": [1]}


def bark(api: str, title: str = "message", content: str = 'test', level: str = "active",
         badge: int = 1, auto_copy: int = 1, sound: str = "", icon: str = "", group: str = "",
         is_archive: int = 1, url: str = "") -> Dict[str, Any]:
    success = []
    error = []
    api_list = api.replace('，', ',').split(',') if api.strip() else []
    for _api in api_list:
        json_data = {
            "title": title,
            "body": content,
            "level": level,
            "badge": badge,
            "autoCopy": auto_copy,
            "sound": sound,
            "icon": icon,
            "group": group,
            "isArchive": is_archive,
            "url": url
        }
        try:
            data = json.dumps(json_data).encode('utf-8')
            req = urllib.request.Request(_api, data=data, headers=headers)
            response = opener.open(req, timeout=10)
            json_str = response.read().decode("utf-8")
            json_data = json.loads(json_str)
            if json_data['code'] == 200:
                success.append(_api)
            else:
                error.append(_api)
                logger.error(f'Bark推送失败, 推送地址：{_api}, 失败信息：{json_data["message"]}')
        except Exception as e:
            error.append(_api)
            logger.error(f'Bark推送失败, 推送地址：{_api}, 错误信息:{e}')
    return {"success": success, "error": error}


def ntfy(api: str, title: str = "message", content: str = 'test', tags: str = 'tada', priority: int = 3,
         action_url: str = "", attach: str = "", filename: str = "", click: str = "", icon: str = "",
         delay: str = "", email: str = "", call: str = "") -> Dict[str, Any]:
    success = []
    error = []
    api_list = api.replace('，', ',').split(',') if api.strip() else []
    tags = tags.replace('，', ',').split(',') if tags else ['partying_face']
    actions = [{"action": "view", "label": "view live", "url": action_url}] if action_url else []
    for _api in api_list:
        server, topic = _api.rsplit('/', maxsplit=1)
        json_data = {
            "topic": topic,
            "title": title,
            "message": content,
            "tags": tags,
            "priority": priority,
            "attach": attach,
            "filename": filename,
            "click": click,
            "actions": actions,
            "markdown": False,
            "icon": icon,
            "delay": delay,
            "email": email,
            "call": call
        }

        try:
            data = json.dumps(json_data, ensure_ascii=False).encode('utf-8')
            req = urllib.request.Request(server, data=data, headers=headers)
            response = opener.open(req, timeout=10)
            json_str = response.read().decode("utf-8")
            json_data = json.loads(json_str)
            if "error" not in json_data:
                success.append(_api)
            else:
                error.append(_api)
                logger.error(f'ntfy推送失败, 推送地址：{_api}, 失败信息：{json_data["error"]}')
        except urllib.error.HTTPError as e:
            error.append(_api)
            error_msg = e.read().decode("utf-8")
            logger.error(f'ntfy推送失败, 推送地址：{_api}, 错误信息:{json.loads(error_msg)["error"]}')
        except Exception as e:
            error.append(_api)
            logger.error(f'ntfy推送失败, 推送地址：{_api}, 错误信息:{e}')
    return {"success": success, "error": error}


def pushplus(token: str, title: str, content: str) -> Dict[str, Any]:
    """
    PushPlus推送通知
    API文档: https://www.pushplus.plus/doc/
    """
    success = []
    error = []
    token_list = token.replace('，', ',').split(',') if token.strip() else []

    for _token in token_list:
        json_data = {
            'token': _token,
            'title': title,
            'content': content
        }

        try:
            url = 'https://www.pushplus.plus/send'
            data = json.dumps(json_data).encode('utf-8')
            req = urllib.request.Request(url, data=data, headers=headers)
            response = opener.open(req, timeout=10)
            json_str = response.read().decode('utf-8')
            json_data = json.loads(json_str)

            if json_data.get('code') == 200:
                success.append(_token)
            else:
                error.append(_token)
                logger.error(f'PushPlus推送失败, Token：{_token}, 失败信息：{json_data.get("msg", "未知错误")}')
        except Exception as e:
            error.append(_token)
            logger.error(f'PushPlus推送失败, Token：{_token}, 错误信息:{e}')

    return {"success": success, "error": error}


def gotify(api: str, token: str, title: str = "message", content: str = 'test', priority: int = 5,
           action_url: str = "") -> Dict[str, Any]:
    """
    通过 Gotify API 推送通知消息。

    :param api: Gotify 服务器地址
    :param token: Gotify 应用令牌
    :param title: 通知标题
    :param content: 通知内容 (message)
    :param priority: 消息优先级 (1-10, 默认为 5)
    :param action_url: 点击通知后跳转的 URL (将被设置为 Gotify 的 client::display::url extra)
    :return: 包含成功和失败推送列表的字典
    """
    success: List[str] = []
    error: List[str] = []
    
        
    try:
        # 1. 解析 Base URL 和 Token (BaseURL;Token)
        base_url = api.strip().rstrip('/')
        app_token = token.strip()
        
    except ValueError:
        error.append(api)
        print(f'Gotify推送失败, 推送地址：{api}, 错误信息: API 格式错误')
        
    # 2. 构造请求 URL 和 Headers
    request_url = f"{base_url}/message"

    # 复制全局 headers 并添加 Gotify Token 认证头部
    request_headers = headers.copy()
    request_headers['X-Gotify-Key'] = app_token
    request_headers['User-Agent'] = 'python-requests/2.31.0'
    request_headers['Accept'] = '*/*'

    # 3. 构造 JSON Payload
    extras = {}
    if action_url:
        # Gotify 使用 client::display::url extra 来实现点击跳转
        extras['client::display::url'] = action_url
    
    json_data = {
        "title": title,
        "message": content,
        "priority": priority,
        "extras": extras,
        "multipart": False  
    }

    try:
        data = json.dumps(json_data, ensure_ascii=False).encode('utf-8')
        
        # 4. 发送请求
        req = urllib.request.Request(request_url, data=data, headers=request_headers, method='POST')
        response = opener.open(req, timeout=10)
        
        # 5. 处理响应
        json_str = response.read().decode("utf-8")
        json_data = json.loads(json_str)
        
        # Gotify 成功返回包含 'id', 'appid' 等字段的对象
        if "id" in json_data:
            success.append(api)
        else:
            error.append(api)
            print(f'Gotify推送失败, 推送地址：{request_url}, 失败信息：未知响应: {json_data}')
            
    except urllib.error.HTTPError as e:
        error.append(api)
        try:
            error_msg = e.read().decode("utf-8")
            error_details = json.loads(error_msg).get("error", "无法解析错误")
            logger.error(f'Gotify推送失败, 推送地址：{api}, HTTP错误码: {e.code}, 错误信息: {error_details}')
        except Exception:
            logger.error(f'Gotify推送失败, 推送地址：{api}, HTTP错误码: {e.code}, 无法解析错误响应。')

    except Exception as e:
        error.append(api)
        logger.error(f'Gotify推送失败, 推送地址：{api}, 错误信息:{e}')

    return {"success": success, "error": error}

def feishubot(webhook_url: str, title: str, content: str, user_id: str = "") -> Dict[str, Any]:
    """
    通过飞书机器人 Webhook 推送通知消息 (仅支持文本)。
    """
    success = []
    error = []
    
    if not webhook_url:
        logger.error('飞书推送失败, 错误信息: Webhook URL 为空。')
        return {"success": [], "error": [1]}

    # 1. 构建内容块
    content_blocks = []

    # 1.1 文字消息块
    text_block = [{"tag": "text", "text": content}]
    if user_id:
        # 添加 @ 某人的逻辑
        text_block.append({"tag": "at", "user_id": user_id})
        
    content_blocks.append(text_block)

    # 2. 构建消息体 (使用 Post 消息类型)
    message_data = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": title,
                    "content": content_blocks,
                }
            }
        },
    }

    try:
        data = json.dumps(message_data, ensure_ascii=False).encode('utf-8')
        
        # 3. 构造请求头
        # 飞书通常要求特定的 Content-Type
        feishu_headers = {"Content-Type": "application/json; charset=utf-8"}
        
        # 4. 发送请求
        req = urllib.request.Request(webhook_url, data=data, headers=feishu_headers, method='POST')
        response = opener.open(req, timeout=10)
        
        # 5. 处理响应
        json_str = response.read().decode("utf-8")
        json_data = json.loads(json_str)
        
        # 飞书成功返回 code=0
        if json_data.get("code") == 0:
            success.append(1)
        else:
            error.append(1)
            err_msg = json_data.get("msg", "未知错误")
            logger.error(f'飞书推送失败, 推送地址：{webhook_url}, 失败信息：{err_msg}')

    except urllib.error.HTTPError as e:
        error.append(1)
        try:
            error_msg = e.read().decode("utf-8")
            error_details = json.loads(error_msg).get("msg", f"HTTP 错误码: {e.code}")
            logger.error(f'飞书推送失败, 推送地址：{webhook_url}, 错误信息: {error_details}')
        except Exception:
             logger.error(f'飞书推送失败, 推送地址：{webhook_url}, HTTP错误码: {e.code}, 无法解析错误响应。')

    except Exception as e:
        error.append(1)
        logger.error(f'飞书推送失败, 推送地址：{webhook_url}, 错误信息:{e}')

    return {"success": success, "error": error}
