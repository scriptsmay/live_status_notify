# 配置文件迁移指南：从 INI 到 YAML

## 概述

项目已从 INI 配置文件迁移到 YAML 格式，以获得更好的可读性和结构化配置支持。

## 主要变更

### 1. 文件名称变更

| 旧文件 | 新文件 |
|--------|--------|
| `config/config.ini` | `config/config.yml` |
| `config/URL_config.ini` | `config/urls.yml` |

### 2. 配置结构变更

#### 全局设置

**INI 格式：**
```ini
[全局设置]
language(zh_cn/en) = zh_cn
是否跳过代理检测 = 否
循环时间(秒) = 300
```

**YAML 格式：**
```yaml
global:
  language: zh_cn
  skip_proxy_check: false
  loop_time: 300
```

#### 推送配置

**INI 格式：**
```ini
[推送配置]
直播状态推送渠道 = 微信|钉钉
微信推送接口链接 = https://xxx
开播推送开启(是/否) = 是
```

**YAML 格式：**
```yaml
push:
  channels: ["wechat", "dingtalk"]
  wechat:
    url: "https://xxx"
  push_start: true
```

#### Cookie 配置

**INI 格式：**
```ini
[Cookie]
抖音cookie = xxxxx
快手cookie = xxxxx
```

**YAML 格式：**
```yaml
cookies:
  douyin: "xxxxx"
  kuaishou: "xxxxx"
```

#### 账号密码配置

**INI 格式：**
```ini
[账号密码]
sooplive账号 = xxx
sooplive密码 = xxx
```

**YAML 格式：**
```yaml
accounts:
  sooplive:
    username: "xxx"
    password: "xxx"
```

#### URL 配置

**旧格式（每行一个）：**
```
1,https://live.douyin.com/123456,主播A
2,https://live.bilibili.com/789,主播B
```

**新格式（YAML 列表）：**
```yaml
urls:
  - url: "https://live.douyin.com/123456"
    name: "主播A"
  - url: "https://live.bilibili.com/789"
    name: "主播B"
```

## 迁移步骤

### 步骤 1：安装新依赖

```bash
pip install -r requirements.txt
```

新增的依赖：
- `PyYAML>=6.0` - YAML 文件解析

### 步骤 2：创建新的配置文件

```bash
# 下载示例配置文件
wget https://raw.githubusercontent.com/scriptsmay/live_status_notify/main/config/config.example.yml -O ./config/config.yml
wget https://raw.githubusercontent.com/scriptsmay/live_status_notify/main/config/urls.example.yml -O ./config/urls.yml
```

### 步骤 3：迁移你的配置

#### 方案 A：手动迁移（推荐）

1. 打开 `config/config.example.yml`
2. 根据你的旧 `config.ini` 配置，逐项填写到新文件
3. 打开 `config/urls.example.yml`
4. 根据你的旧 `URL_config.ini`，将直播间列表转换为 YAML 格式

#### 方案 B：使用转换脚本

你可以编写一个简单的 Python 脚本来自动转换配置：

```python
import configparser
import yaml

# 读取旧配置
config = configparser.RawConfigParser()
config.read('config/config.ini', encoding='utf-8-sig')

# 转换为新格式
new_config = {
    'global': {
        'language': config.get('全局设置', 'language(zh_cn/en)', fallback='zh_cn'),
        'skip_proxy_check': config.get('全局设置', '是否跳过代理检测', fallback='否') in ('是', 'true'),
        # ... 其他配置
    },
    'push': {
        'channels': config.get('推送配置', '直播状态推送渠道', fallback='').split('|'),
        # ... 其他配置
    },
    'cookies': dict(config.items('Cookie')) if config.has_section('Cookie') else {},
    # ...
}

# 写入新配置
with open('config/config.yml', 'w', encoding='utf-8-sig') as f:
    yaml.dump(new_config, f, allow_unicode=True, default_flow_style=False)
```

### 步骤 4：测试新配置

```bash
# 运行程序测试
python main.py
```

### 步骤 5：备份旧配置文件（可选）

```bash
mkdir -p config/old_backup
mv config/config.ini config/old_backup/
mv config/URL_config.ini config/old_backup/
```

## 注意事项

1. **布尔值**：YAML 支持原生布尔值（`true`/`false`），不再使用 `是`/`否`
2. **列表**：推送渠道现在是 YAML 列表类型，如 `["wechat", "dingtalk"]`
3. **嵌套结构**：配置按功能模块组织为嵌套结构，更清晰
4. **注释**：YAML 注释使用 `#`，与 INI 不同
5. **缩进**：YAML 使用 2 个空格缩进，不使用 Tab

## 优势

- ✅ 更好的可读性
- ✅ 支持注释和复杂数据结构
- ✅ 原生支持布尔值、整数、列表等类型
- ✅ 嵌套结构更清晰
- ✅ 减少配置解析错误

## 回滚方案

如果遇到问题，可以临时回滚到 INI 配置：

1. 修改 `main.py` 中的 `CONFIG_FILE` 和 `URL_CONFIG_FILE` 常量
2. 恢复旧的 ConfigManager 类代码
3. 使用旧的配置文件

但建议优先排查 YAML 配置格式问题。

## 常见问题

### Q: YAML 配置文件解析失败

A: 检查以下几点：
- 缩进是否正确使用空格（不是 Tab）
- 字符串是否包含特殊字符时需要引号
- 列表格式是否正确

### Q: 如何配置多个推送渠道？

A: 使用 YAML 列表：
```yaml
push:
  channels:
    - wechat
    - dingtalk
    - telegram
```

或简写：
```yaml
push:
  channels: ["wechat", "dingtalk", "telegram"]
```

### Q: URL 配置格式错误

A: 确保格式正确：
```yaml
urls:
  - url: "https://..."
    name: "主播名称"
```

每个配置项必须包含 `url` 和 `name` 两个字段。
