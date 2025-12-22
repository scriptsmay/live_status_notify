# -*- encoding: utf-8 -*-
import asyncio
import configparser
import datetime
import os
import sys
import re
import shutil
from typing import Any, Dict, List, Optional, Tuple, Set
from src import spider, stream
from src.utils import logger
from src import utils
from msg_push import (
    dingtalk, xizhi, tg_bot, send_email, bark, ntfy, pushplus, gotify, feishubot
)

# --- 常量定义 ---
CONFIG_FILE = 'config/config.ini'
URL_CONFIG_FILE = 'config/URL_config.ini'
TEXT_ENCODING = 'utf-8-sig'
RSTR = r"[\/\\\:\*\？?\"\<\>\|&#.。,， ~！· ]"

# 备份目录
BACKUP_DIR = 'backup_config'
# 最多保留n个备份
BACKUP_LIMIT = 6

DEFAULT_VIDEO_QUALITY = 'LD'

# --- 配置管理类 ---
class ConfigManager:
    """配置管理器，统一处理配置读取和验证"""
    
    def __init__(self):
        self.cfg = configparser.RawConfigParser()
        self._ensure_sections()
        
    def _ensure_sections(self):
        """确保必要的配置段存在"""
        required_sections = ['推送配置', 'Cookie', 'Authorization', '账号密码', '全局设置']
        for section in required_sections:
            if not self.cfg.has_section(section):
                self.cfg.add_section(section)
    
    def read(self, section: str, option: str, default: Any = None, 
             value_type: str = 'str') -> Any:
        """读取配置值，支持不同类型"""
        try:
            self.cfg.read(CONFIG_FILE, encoding=TEXT_ENCODING)
            value = self.cfg.get(section, option)
            
            if value_type == 'bool':
                return str(value).strip().lower() in ('是', 'true', 'yes', '1', 'on')
            elif value_type == 'int':
                try:
                    return int(str(value).strip())
                except ValueError:
                    return default if default is not None else 0
            elif value_type == 'str':
                return str(value).strip()
            else:
                return value
        except (configparser.NoSectionError, configparser.NoOptionError):
            if default is not None:
                self.cfg.set(section, option, str(default))
                self._save_config()
            return default
    
    def read_boolean(self, section: str, option: str, default: bool) -> bool:
        """读取布尔值配置"""
        return self.read(section, option, default, 'bool')
    
    def read_int(self, section: str, option: str, default: int) -> int:
        """读取整型配置"""
        return self.read(section, option, default, 'int')
    
    def read_str(self, section: str, option: str, default: str = '') -> str:
        """读取字符串配置"""
        return self.read(section, option, default, 'str')
    
    def _save_config(self):
        """保存配置到文件"""
        with open(CONFIG_FILE, 'w', encoding=TEXT_ENCODING) as f:
            self.cfg.write(f)

# --- 推送处理器 ---
class PushHandler:
    """推送处理器，统一管理所有推送渠道"""
    
    def __init__(self, config: dict):
        self.config = config
        self.channels = self._parse_channels(config.get('channels', ''))
        self.push_start = config.get('push_start', True)
        self.push_stop = config.get('push_stop', True)
        self.custom_start_msg = config.get('custom_start_msg', '[直播间名称] 已开播！ \n [时间]')
        self.custom_stop_msg = config.get('custom_stop_msg', '[直播间名称] 已结束直播。 \n [时间]')
    
    def _parse_channels(self, channels_str: str) -> Set[str]:
        """解析推送渠道字符串"""
        channels = set()
        if not channels_str:
            return channels
            
        # 支持多种分隔符
        for sep in ['|', ',', '，', '、']:
            if sep in channels_str:
                channels = set(ch.strip().upper() for ch in channels_str.split(sep) if ch.strip())
                break
        else:
            channels = {channels_str.strip().upper()}
        
        # 映射可能的别名
        channel_mapping = {
            'TG': 'TG',
            'TELEGRAM': 'TG',
            '微信': '微信',
            'WECHAT': '微信',
            '钉钉': '钉钉',
            'DINGTALK': '钉钉',
            '邮箱': '邮箱',
            'EMAIL': '邮箱',
            'BARK': 'BARK',
            'NTFY': 'NTFY',
            'PUSHPLUS': 'PUSHPLUS',
            '飞书': '飞书',
            'FEISHU': '飞书',
            'GOTIFY': 'GOTIFY'
        }
        
        return {channel_mapping.get(ch, ch) for ch in channels if ch in channel_mapping}
    
    def _parse_template(self, template: str, anchor: str, url: str, now_time: str) -> str:
        """解析模板，替换变量和换行符"""
        if not template:
            return f"主播：{anchor}\n时间：{now_time}\n链接：{url}"
        
        # 替换变量
        content = template.replace('[直播间名称]', anchor) \
                         .replace('[时间]', now_time) \
                         .replace('[链接]', url) \
                         .replace('[URL]', url)
        
        # 处理换行符 - 将字符串中的 \n 转换为实际的换行符
        # 注意：配置文件中可能是 "\\n" 或 "\n"，这里统一处理
        content = content.replace('\\n', '\n').replace(r'\n', '\n')
        
        # 确保包含完整信息
        if url not in content:
            content += f"\n链接：{url}"
        
        return content
    
    def _build_content(self, anchor: str, url: str, status: str) -> Tuple[str, str]:
        """构建推送标题和内容"""
        now_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        title = self.config.get('title', '直播间通知')
        
        if status == "开播啦":
            template = self.custom_start_msg
        else:
            template = self.custom_stop_msg
        
        # 解析模板
        content = self._parse_template(template, anchor, url, now_time)
        
        return title, content
    
    async def push(self, anchor: str, url: str, status: str) -> None:
        """执行推送操作"""
        if (status == "开播啦" and not self.push_start) or \
           (status == "直播结束" and not self.push_stop):
            return
        
        title, content = self._build_content(anchor, url, status)
        
        logger.info(f"推送消息: {anchor} -> {status}")
        
        push_tasks = []
        channels = self.channels
        
        # 微信推送
        if '微信' in channels and self.config.get('wx_url'):
            push_tasks.append(asyncio.to_thread(xizhi, self.config['wx_url'], title, content))
        
        # 钉钉推送
        if '钉钉' in channels and self.config.get('dd_url'):
            push_tasks.append(asyncio.to_thread(
                dingtalk, self.config['dd_url'], content, 
                self.config.get('dd_at', ''), 
                self.config.get('dd_all', False)
            ))
        
        # Telegram推送
        if 'TG' in channels and self.config.get('tg_token') and self.config.get('tg_chat_id'):
            push_tasks.append(asyncio.to_thread(
                tg_bot, self.config['tg_chat_id'], self.config['tg_token'], content
            ))
        
        # Bark推送
        if 'BARK' in channels and self.config.get('bark_url'):
            push_tasks.append(asyncio.to_thread(
                bark, self.config['bark_url'], title, content,
                self.config.get('bark_lv', 'active'),
                self.config.get('bark_ring', '')
            ))
        
        # Ntfy推送
        if 'NTFY' in channels and self.config.get('ntfy_url'):
            push_tasks.append(asyncio.to_thread(
                ntfy, self.config['ntfy_url'], title, content,
                self.config.get('ntfy_tag', 'tada'),
                url, self.config.get('ntfy_email', '')
            ))
        
        # Pushplus推送
        if 'PUSHPLUS' in channels and self.config.get('pp_token'):
            push_tasks.append(asyncio.to_thread(
                pushplus, self.config['pp_token'], title, content
            ))
        
        # 飞书推送
        if '飞书' in channels and self.config.get('fs_url'):
            push_tasks.append(asyncio.to_thread(
                feishubot, self.config['fs_url'], title, content,
                self.config.get('fs_at', '')
            ))
        
        # Gotify推送
        if 'GOTIFY' in channels and self.config.get('gt_url') and self.config.get('gt_token'):
            push_tasks.append(asyncio.to_thread(
                gotify, self.config['gt_url'], self.config['gt_token'], 
                title, content, self.config.get('gt_prio', 5)
            ))
        
        # 邮箱推送
        if '邮箱' in channels and all(self.config.get(k) for k in [
            'email_srv', 'email_acc', 'email_pwd', 'email_from', 'email_to'
        ]):
            push_tasks.append(asyncio.to_thread(
                send_email, self.config['email_srv'], 
                self.config['email_acc'], self.config['email_pwd'],
                self.config['email_from'], self.config.get('email_nick', ''),
                self.config['email_to'], title, content,
                self.config.get('email_port', 465),
                self.config.get('email_ssl', True)
            ))
        
        if push_tasks:
            results = await asyncio.gather(*push_tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"推送失败: {result}")

# --- 平台检测器 ---
class PlatformDetector:
    """平台检测器，统一管理各平台的检测逻辑"""
    
    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.cookies = {}
        self._load_cookies(config)
    
    def _load_cookies(self, config: Dict[str, str]):
        """加载所有平台的cookies"""
        cookie_mapping = {
            'douyin': '抖音cookie',
            'kuaishou': '快手cookie',
            'huya': '虎牙cookie',
            'douyu': '斗鱼cookie',
            'bilibili': 'b站cookie',
            'tiktok': 'tiktok_cookie',
            'yy': 'yy_cookie',
            'xiaohongshu': '小红书cookie',
            'bigo': 'bigo_cookie',
            'blued': 'blued_cookie',
            'sooplive': 'sooplive_cookie',
            'netease': 'netease_cookie',
            'qianbaidu': '千度热播_cookie',
            'pandatv': 'pandatv_cookie',
            'maoer': '猫耳fm_cookie',
            'winktv': 'winktv_cookie',
            'flextv': 'flextv_cookie',
            'look': 'look_cookie',
            'twitcasting': 'twitcasting_cookie',
            'baidu': 'baidu_cookie',
            'weibo': 'weibo_cookie',
            'kugou': 'kugou_cookie',
            'twitch': 'twitch_cookie',
            'liveme': 'liveme_cookie',
            'huajiao': 'huajiao_cookie',
            'liuxing': 'liuxing_cookie',
            'showroom': 'showroom_cookie',
            'acfun': 'acfun_cookie',
            'changliao': 'changliao_cookie',
            'yinbo': 'yinbo_cookie',
            'yingke': 'yingke_cookie',
            'zhihu': 'zhihu_cookie',
            'chzzk': 'chzzk_cookie',
            'haixiu': 'haixiu_cookie',
            'vvxqiu': 'vvxqiu_cookie',
            '17live': '17live_cookie',
            'langlive': 'langlive_cookie',
            'pplive': 'pplive_cookie',
            '6room': '6room_cookie',
            'lehaitv': 'lehaitv_cookie',
            'huamao': 'huamao_cookie',
            'shopee': 'shopee_cookie',
            'youtube': 'youtube_cookie',
            'taobao': 'taobao_cookie',
            'jd': 'jd_cookie',
            'faceit': 'faceit_cookie',
            'migu': 'migu_cookie',
            'lianjie': 'lianjie_cookie',
            'laixiu': 'laixiu_cookie',
            'picarto': 'picarto_cookie'
        }
        
        for platform, config_key in cookie_mapping.items():
            if config_key in config and config[config_key]:
                self.cookies[platform] = config[config_key]
    
    def clean_name(self, input_text: str):
        if not input_text:
            return '空白昵称'
        
        cleaned_name = re.sub(RSTR, "_", input_text.strip()).strip('_')
        cleaned_name = cleaned_name.replace("（", "(").replace("）", ")")

        if self.config.get('clean_emoji', True):
            cleaned_name = utils.remove_emojis(cleaned_name, '_').strip('_')
            
        return cleaned_name or '空白昵称'
    async def check_status(self, url: str) -> Tuple[Optional[bool], str]:
        """检测直播状态"""
        
        try:
            port_info = []

            # 抖音平台
            if "douyin.com" in url or "iesdouyin.com" in url:
                cookie = self.cookies.get('douyin', '')
                data = await spider.get_douyin_web_stream_data(url, cookies=cookie)

                anchor_name = data.get('anchor_name') or data.get('nickname') or "抖音主播"

                return data.get('is_live', False), anchor_name
            
            # B站平台
            elif "bilibili.com" in url:
                cookie = self.cookies.get('bilibili', '')
                data = await spider.get_bilibili_room_info(url, cookies=cookie)
                # B站可能使用uname作为主播名
                anchor_name = data.get('uname', 'B站主播')

                return data.get('live_status') == 1, anchor_name
            
            # 虎牙平台
            elif "huya.com" in url:
                cookie = self.cookies.get('huya', '')
                data = await spider.get_huya_stream_data(url, cookies=cookie)
                port_info = await stream.get_huya_stream_url(data, DEFAULT_VIDEO_QUALITY)

                # 从port_info中获取主播名
                anchor_name = port_info.get("anchor_name", "虎牙主播")

                return data.get('is_live', False), anchor_name
            
            # 斗鱼平台
            elif "douyu.com" in url:
                cookie = self.cookies.get('douyu', '')
                data = await spider.get_douyu_info_data(url, cookies=cookie)
                anchor_name = data.get('anchor_name', '斗鱼主播')
                return data.get('is_live', False), anchor_name
            
            # 快手平台
            elif "kuaishou.com" in url or "gifshow.com" in url:
                cookie = self.cookies.get('kuaishou', '')
                data = await spider.get_kuaishou_stream_data(url, cookies=cookie)
                return data.get('is_live', False), data.get('anchor_name', '快手主播')
            
            # TikTok平台
            elif "tiktok.com" in url:
                cookie = self.cookies.get('tiktok', '')
                data = await spider.get_tiktok_stream_data(url, cookies=cookie)
                return data.get('is_live', False), data.get('anchor_name', 'TikTok主播')

            # 小红书平台
            elif "xhslink.com" in url or "xiaohongshu.com" in url or "redelight.cn" in url:
                cookie = self.cookies.get('xiaohongshu', '')
                
                # 调用小红书的爬虫
                port_info = await spider.get_xhs_stream_url(url, cookies=cookie)
                
                if port_info:
                    is_live = port_info.get('is_live', False)
                    anchor_name = port_info.get("anchor_name", "小红书主播")
                    
                    # 清理主播名
                    if anchor_name:
                        anchor_name = self.clean_name(anchor_name)
                    
                    return is_live, anchor_name
                else:
                    return False, "小红书主播"
            
            # 添加其他平台的检测逻辑...
            # 可以根据需要添加更多平台
            
            else:
                logger.warning(f"不支持的平台: {url}")
                return False, "未知平台"
                
        except Exception as e:
            logger.debug(f"检测出错 [{url}]: {e}")
            return None, "检测失败"

# --- URL 配置读取器 ---
def load_url_config() -> List[Dict[str, str]]:
    """加载URL配置"""
    urls = []
    
    if not os.path.exists(URL_CONFIG_FILE):
        logger.warning(f"URL配置文件不存在: {URL_CONFIG_FILE}")
        return urls
    
    with open(URL_CONFIG_FILE, 'r', encoding=TEXT_ENCODING) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 尝试多种格式解析
            if line.count(',') >= 2:
                # 格式: 序号,URL,名称
                parts = line.split(',', 2)
                if len(parts) >= 3:
                    url = parts[1].strip()
                    name = parts[2].strip()
                    urls.append({'url': url, 'name': name})
            elif 'http' in line:
                # 格式: URL
                urls.append({'url': line.strip(), 'name': "未知主播"})
            else:
                logger.warning(f"第{line_num}行格式无法识别: {line}")
    
    logger.info(f"加载了 {len(urls)} 个直播间")
    return urls

# --- 状态追踪器 ---
class StatusTracker:
    """状态追踪器，管理主播状态变化"""
    
    def __init__(self, push_handler: PushHandler):
        self.push_handler = push_handler
        self.status_map: Dict[str, bool] = {}
    
    async def process(self, url: str, custom_name: str, is_live: bool, anchor_name: str) -> None:
        """处理状态变化"""
        if is_live is None:
            logger.debug(f"检测失败，跳过: {url}")
            return
        
        display_name = custom_name if custom_name != "未知主播" else anchor_name
        prev_status = self.status_map.get(url, False)
        
        # 状态变化判断
        if is_live and not prev_status:
            self.status_map[url] = True
            await self.push_handler.push(display_name, url, "开播啦")
            logger.info(f"状态变化: {display_name} 开播")
            
        elif not is_live and prev_status:
            self.status_map[url] = False
            await self.push_handler.push(display_name, url, "直播结束")
            logger.info(f"状态变化: {display_name} 关播")
        
        elif is_live == prev_status:
            # 状态未变化，记录日志
            status_str = "直播中" if is_live else "未开播"
            logger.debug(f"状态未变: {display_name} {status_str}")


# --- 配置文件备份功能 ---
def backup_config_file(file_path: str, backup_dir_path: str, limit_counts: int = BACKUP_LIMIT) -> None:
    """备份配置文件"""
    try:
        if not os.path.exists(file_path):
            logger.warning(f"配置文件不存在: {file_path}")
            return
            
        if not os.path.exists(backup_dir_path):
            os.makedirs(backup_dir_path)
            logger.info(f"创建备份目录: {backup_dir_path}")

        # 生成带时间戳的备份文件名
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        file_name = os.path.basename(file_path)
        backup_file_name = f"{file_name}_{timestamp}.bak"
        backup_file_path = os.path.join(backup_dir_path, backup_file_name).replace("\\", "/")
        
        # 复制文件
        shutil.copy2(file_path, backup_file_path)
        logger.info(f"备份配置文件: {file_path} -> {backup_file_path}")
        
        # 清理旧的备份文件
        clean_old_backups(backup_dir_path, file_name, limit_counts)
        
    except Exception as e:
        logger.error(f'备份配置文件 {file_path} 失败：{str(e)}')

def clean_old_backups(backup_dir_path: str, base_name: str, limit_counts: int) -> None:
    """清理旧的备份文件"""
    try:
        if not os.path.exists(backup_dir_path):
            return
            
        files = os.listdir(backup_dir_path)
        # 筛选出相同基础文件名的备份文件
        backup_files = [f for f in files if f.startswith(base_name + '_') and f.endswith('.bak')]
        
        if len(backup_files) > limit_counts:
            # 按时间排序（旧的在前面）
            backup_files.sort(key=lambda x: os.path.getmtime(os.path.join(backup_dir_path, x)))
            
            # 删除超出的旧备份
            for i in range(len(backup_files) - limit_counts):
                old_file = backup_files[i]
                old_file_path = os.path.join(backup_dir_path, old_file)
                os.remove(old_file_path)
                logger.debug(f"清理旧备份: {old_file}")
                
    except Exception as e:
        logger.error(f'清理旧备份失败：{str(e)}')

def backup_config_files_at_startup() -> None:
    """程序启动时备份配置文件"""
    logger.info("=== 启动配置文件备份 ===")
    
    # 备份主配置文件
    if os.path.exists(CONFIG_FILE):
        backup_config_file(CONFIG_FILE, BACKUP_DIR, BACKUP_LIMIT)
    else:
        logger.warning(f"主配置文件不存在: {CONFIG_FILE}")
    
    # 备份URL配置文件
    if os.path.exists(URL_CONFIG_FILE):
        backup_config_file(URL_CONFIG_FILE, BACKUP_DIR, BACKUP_LIMIT)
    else:
        logger.warning(f"URL配置文件不存在: {URL_CONFIG_FILE}")
    
    logger.info("=== 配置文件备份完成 ===")
# --- 主程序 ---
async def main():
    """主程序入口"""
    # 程序启动时备份配置文件
    backup_config_files_at_startup()

    logger.info("=== 直播监测模式启动 ===")
    
    # 初始化配置管理器
    config_mgr = ConfigManager()
    
    # 读取基础配置
    logger.info("正在读取配置...")

    # 全局配置
    # [全局设置]
    # language(zh_cn/en) = zh_cn
    # 是否跳过代理检测 = 否
    # 是否去除名称中的表情符号 = True
    # 是否使用代理ip = True
    # 代理地址 = 
    # 同一时间访问网络的线程数 = 3
    # 循环时间(秒) = 300
    # 排队读取网址时间(秒) = 0
    global_config = {
        'language': config_mgr.read_str('全局设置', 'language(zh_cn/en)', 'zh-cn'),
        'skip_proxy_check': config_mgr.read_boolean('全局设置', '是否跳过代理检测', False),
        'proxy_ip': config_mgr.read_str('全局设置', '是否使用代理ip', True),
        'proxy_address': config_mgr.read_str('全局设置', '代理地址', ''),
        'thread_count': config_mgr.read_int('全局设置', '同一时间访问网络的线程数', 3),
        'loop_time': config_mgr.read_int('全局设置', '循环时间(秒)', 300),
        'queue_time': config_mgr.read_int('全局设置', '排队读取网址时间(秒)', 0),
        'clean_emoji': config_mgr.read_int('全局设置', '是否去除名称中的表情符号', True),
    }
    
    # 推送配置
    push_config = {
        'channels': config_mgr.read_str('推送配置', '直播状态推送渠道', ''),
        'title': config_mgr.read_str('推送配置', '自定义推送标题', '直播间通知'),
        'custom_start_msg': config_mgr.read_str('推送配置', '自定义开播推送内容', '[直播间名称] 已开播！ \n [时间]'),
        'custom_stop_msg': config_mgr.read_str('推送配置', '自定义关播推送内容', '[直播间名称] 已结束直播。 \n [时间]'),
        'push_start': config_mgr.read_boolean('推送配置', '开播推送开启(是/否)', True),
        'push_stop': config_mgr.read_boolean('推送配置', '关播推送开启(是/否)', True),
        
        # 各渠道配置
        'wx_url': config_mgr.read_str('推送配置', '微信推送接口链接', ''),
        'dd_url': config_mgr.read_str('推送配置', '钉钉推送接口链接', ''),
        'dd_at': config_mgr.read_str('推送配置', '钉钉通知@对象(填手机号)', ''),
        'dd_all': config_mgr.read_boolean('推送配置', '钉钉通知@全体(是/否)', False),
        'tg_token': config_mgr.read_str('推送配置', 'tgapi令牌', ''),
        'tg_chat_id': config_mgr.read_str('推送配置', 'tg聊天id(个人或者群组id)', ''),
        'bark_url': config_mgr.read_str('推送配置', 'bark推送接口链接', ''),
        'bark_lv': config_mgr.read_str('推送配置', 'bark推送中断级别', 'active'),
        'bark_ring': config_mgr.read_str('推送配置', 'bark推送铃声', ''),
        'ntfy_url': config_mgr.read_str('推送配置', 'ntfy推送地址', ''),
        'ntfy_tag': config_mgr.read_str('推送配置', 'ntfy推送标签', 'tada'),
        'ntfy_email': config_mgr.read_str('推送配置', 'ntfy推送邮箱', ''),
        'pp_token': config_mgr.read_str('推送配置', 'pushplus推送token', ''),
        'fs_url': config_mgr.read_str('推送配置', '飞书推送接口链接', ''),
        'fs_at': config_mgr.read_str('推送配置', '飞书通知@对象', ''),
        'gt_url': config_mgr.read_str('推送配置', 'gotify推送地址', ''),
        'gt_token': config_mgr.read_str('推送配置', 'gotify推送token', ''),
        'gt_prio': config_mgr.read_int('推送配置', 'gotify推送优先级', 5),
        'email_srv': config_mgr.read_str('推送配置', 'smtp邮件服务器', ''),
        'email_acc': config_mgr.read_str('推送配置', '邮箱登录账号', ''),
        'email_pwd': config_mgr.read_str('推送配置', '发件人密码(授权码)', ''),
        'email_from': config_mgr.read_str('推送配置', '发件人邮箱', ''),
        'email_nick': config_mgr.read_str('推送配置', '发件人显示昵称', ''),
        'email_to': config_mgr.read_str('推送配置', '收件人邮箱', ''),
        'email_port': config_mgr.read_int('推送配置', 'SMTP邮件服务器端口', 465),
        'email_ssl': config_mgr.read_boolean('推送配置', '是否使用SMTP服务SSL加密(是/否)', True)
    }
    
    # 读取Cookie配置
    cookie_config = {}
    if config_mgr.cfg.has_section('Cookie'):
        for option in config_mgr.cfg.options('Cookie'):
            cookie_config[option] = config_mgr.read_str('Cookie', option, '')
    
    # 合并配置
    push_config.update(cookie_config)
    push_config.update(global_config)
    
    # 读取检测间隔
    check_interval = config_mgr.read_int('推送配置', '直播推送检测频率(秒)', global_config['loop_time'])
    if check_interval < 10:  # 最小间隔保护
        check_interval = 10
        logger.warning(f"检测间隔过小，调整为{check_interval}秒")
    
    logger.info(f"检测间隔: {check_interval}秒")
    logger.info(f"开播推送: {'开启' if push_config['push_start'] else '关闭'}")
    logger.info(f"关播推送: {'开启' if push_config['push_stop'] else '关闭'}")
    
    # 初始化各个组件
    push_handler = PushHandler(push_config)
    detector = PlatformDetector(push_config)
    tracker = StatusTracker(push_handler)
    
    cycle_count = 0
    
    # 主循环
    while True:
        cycle_count += 1
        logger.info(f"=== 第{cycle_count}轮检测开始 ===")
        
        urls = load_url_config()
        
        if not urls:
            logger.warning("未找到有效的直播间配置")
        else:
            tasks = []
            for item in urls:
                task = asyncio.create_task(
                    _process_single_url(item, detector, tracker)
                )
                tasks.append(task)
            
            # 并发处理所有直播间
            await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info(f"第{cycle_count}轮检测完成，等待{check_interval}秒后继续...")
        await asyncio.sleep(check_interval)

async def _process_single_url(item: Dict[str, str], detector: PlatformDetector, tracker: StatusTracker) -> None:
    """处理单个直播间"""
    try:
        is_live, anchor_name = await detector.check_status(item['url'])
        await tracker.process(item['url'], item['name'], is_live, anchor_name)
    except Exception as e:
        logger.error(f"处理直播间失败 [{item.get('name', '未知')}]: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n程序已手动退出")
    except Exception as e:
        logger.error(f"程序异常退出: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)