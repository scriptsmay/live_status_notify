# -*- encoding: utf-8 -*-

"""
Date: 2026-02-04 23:15:00
Update: 2026-02-05 18:28:00
Function: Get kuaishou live stream data.
"""

import os
import traceback
import asyncio
from typing import Optional
from playwright.async_api import async_playwright
from .utils import trace_error_decorator, logger
from playwright_stealth import Stealth


@trace_error_decorator
async def get_kuaishou_stream_data(url: str, proxy_addr: Optional[str] = None, cookies: Optional[str] = None) -> dict:
    result = {"type": 2, "is_live": False, "anchor_name": "未知"}

    # 检测是否在 Docker 容器中（无 GUI 环境）
    in_docker = os.path.exists('/.dockerenv') or os.environ.get('CONTAINER') == '1'
    
    async with async_playwright() as p:
        # 指定一个文件夹路径来存储用户数据（Cookies、缓存等）
        user_data_dir = os.path.join(os.getcwd(), "kuaishou_user_data")
        os.makedirs(user_data_dir, exist_ok=True)

        # Docker 环境中必须使用 headless 模式
        launch_args = {
            'user_data_dir': user_data_dir,
            'headless': True,  # 容器内必须为 True
            'viewport': {'width': 1920, 'height': 1080},
            'proxy': {"server": proxy_addr} if proxy_addr else None,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            # Docker 环境优化参数
            'args': [
                '--no-sandbox',  # 容器内必须
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',  # 避免 /dev/shm 内存不足
                '--disable-gpu',  # 无 GPU 环境
                '--single-process',  # 单进程模式节省资源
                '--no-first-run',
                '--no-zygote',
            ] if in_docker else []
        }

        context = await p.chromium.launch_persistent_context(**launch_args)

        try:
            # 注入 Cookies
            if cookies:
                try:
                    cookie_list = []
                    for item in cookies.split(';'):
                        if '=' in item:
                            k, v = item.strip().split('=', 1)
                            cookie_list.append({"name": k, "value": v, "domain": ".kuaishou.com", "path": "/"})
                    await context.add_cookies(cookie_list)
                except Exception as e:
                    logger.error(f"Cookie 注入失败: {e}")


            page = await context.new_page()
            await Stealth().apply_stealth_async(page)

            # 核心逻辑：拦截 API 响应 (这种方式比解析 HTML 稳定 10 倍)
            api_data = {"raw": None}
            async def handle_response(response):
                # 快手直播的关键 API 路径
                if "live_api/profile/public" in response.url:
                    try:
                        res_json = await response.json()
                        if res_json.get('data'):
                            api_data["raw"] = res_json['data']
                    except:
                        pass

            page.on("response", handle_response)

            # 设置较短的超时，避免任务堆积
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            
            # 等待一小会儿确保 API 触发或初始状态挂载
            await asyncio.sleep(1) 

            content = await page.content()

            if "请求过快" in content:
                logger.warning(f"触发反爬虫提示！当前页面内容检测到：'请求过快'。")
                # headless 模式下无法暂停，等待后重试
                await asyncio.sleep(3)

            if "captcha" in content or "验证码" in page.url or "拖动下方滑块" in content:
                logger.warning("检测到验证码！headless 模式下无法自动处理验证码，请考虑："
                               "1. 在本地运行（非 Docker）并手动过验证码；"
                               "2. 更新 Cookie 以绕过验证；"
                               "3. 降低检测频率避免触发反爬")
                return result  # 直接返回，不继续处理

            # 方案 A: 检查 API 拦截到的数据
            source_data = None
            if api_data["raw"]:
                source_data = api_data["raw"]
            else:
                # 方案 B: 兜底 evaluate 获取
                source_data = await page.evaluate("() => window.__INITIAL_STATE__")

            if not source_data or not isinstance(source_data, dict):
                logger.error(f"无法定位数据源: {url}")
                return result

            # 7. 统一解析字段
            author = source_data.get('author') or source_data.get('user', {})
            result["anchor_name"] = author.get('name') or author.get('user_name', '未知主播')

            live_stream = source_data.get('liveStream')
            
            # 如果 live_stream 为 None，说明当前没有直播信息（未开播或数据异常）
            if not live_stream:
                # 检查是否是因为被封禁导致没数据
                if 'errorType' in source_data:
                    logger.warning(f"访问受限或页面异常: {source_data.get('errorType')}")
                return result

            # 既然 live_stream 不为 None，现在可以安全地调用 .get()
            is_living = live_stream.get('isLive') or live_stream.get('living')

            if is_living:
                play_urls = live_stream.get('playUrls', {})
                # 快手 H264 标准路径解析
                h264_info = play_urls.get('h264', {}) if isinstance(play_urls, dict) else {}
                
                # 提取 representation 列表
                reps = h264_info.get('adaptationSet', {}).get('representation', [])
                if reps:
                    result.update({
                        "is_live": True,
                        "flv_url_list": reps
                    })
                elif isinstance(play_urls, list) and len(play_urls) > 0:
                    # 兼容部分 API 返回的数组结构
                    result.update({
                        "is_live": True,
                        "flv_url_list": play_urls[0].get('adaptationSet', {}).get('representation', [])
                    })

        except Exception as e:
            logger.error(f"检测出错 [{url}]: {e}")
            logger.debug(f"详细错误日志:\n{traceback.format_exc()}")
        finally:
            await context.close()
            
    return result