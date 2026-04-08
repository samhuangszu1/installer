# 服务器API文档

## 概述

鸿蒙应用安装工具服务器API提供应用和版本管理功能。

## 基础URL

```
https://your-server.com/api
```

## API端点

### 1. 获取应用列表

**请求：**
```
GET /apps
```

**响应：**
```json
{
  "apps": [
    {
      "id": "com.example.app",
      "name": "示例应用",
      "description": "这是一个示例应用",
      "current_version": "1.0.0",
      "bundle_name": "com.example.app",
      "main_ability": "EntryAbility"
    }
  ]
}
```

### 2. 获取应用版本列表

**请求：**
```
GET /apps/{app_id}/versions
```

**响应：**
```json
{
  "versions": [
    {
      "version": "1.0.0",
      "release_date": "2024-04-07",
      "description": "初始版本发布",
      "files": {
        "hap": "debug.hap",
        "hsp": "tztzfnetwork-signed.hsp"
      },
      "requirements": "鸿蒙系统 3.0+",
      "changelog": [
        "初始版本发布",
        "基础功能实现"
      ],
      "deploy_path": "data/local/tmp/test123",
      "size": "~15MB"
    },
    {
      "version": "1.1.0",
      "release_date": "2024-04-10",
      "description": "功能更新版本",
      "files": {
        "hap": "debug-v1.1.0.hap",
        "hsp": "tztzfnetwork-signed-v1.1.0.hsp"
      },
      "requirements": "鸿蒙系统 3.0+",
      "changelog": [
        "新增功能A",
        "修复bug",
        "性能优化"
      ],
      "deploy_path": "data/local/tmp/test123",
      "size": "~18MB"
    }
  ]
}
```

### 3. 获取特定版本信息

**请求：**
```
GET /apps/{app_id}/versions/{version}
```

**响应：**
```json
{
  "version": "1.0.0",
  "release_date": "2024-04-07",
  "description": "初始版本发布",
  "files": {
    "hap": "debug.hap",
    "hsp": "tztzfnetwork-signed.hsp"
  },
  "requirements": "鸿蒙系统 3.0+",
  "changelog": [
    "初始版本发布",
    "基础功能实现"
  ],
  "deploy_path": "data/local/tmp/test123",
  "size": "~15MB"
}
```

### 4. 下载文件

**请求：**
```
GET /files/{filename}
```

**响应：**
文件二进制数据

## 错误处理

所有API端点都应返回适当的HTTP状态码：

- `200 OK` - 请求成功
- `404 Not Found` - 资源不存在
- `500 Internal Server Error` - 服务器内部错误

错误响应格式：
```json
{
  "error": "错误描述",
  "code": "ERROR_CODE"
}
```

## 文件存储结构

建议的服务器文件存储结构：

```
/
├── api/
│   ├── apps.py          # 应用列表API
│   ├── versions.py      # 版本列表API
│   └── files.py         # 文件下载API
├── files/
│   ├── debug.hap
│   ├── tztzfnetwork-signed.hsp
│   ├── debug-v1.1.0.hap
│   └── tztzfnetwork-signed-v1.1.0.hsp
└── static/
    └── ...
```

## 示例实现 (Flask)

```python
from flask import Flask, jsonify, send_file
import os

app = Flask(__name__)

# 示例应用数据
APPS_DATA = {
    "apps": [
        {
            "id": "com.example.app",
            "name": "示例应用",
            "description": "这是一个示例应用",
            "versions_dir": "versions/com_example_app",
            "current_version": "1.0.0",
            "bundle_name": "com.example.app",
            "main_ability": "EntryAbility"
        }
    ]
}

# 示例版本数据
VERSIONS_DATA = {
    "com.example.app": {
        "versions": [
            {
                "version": "1.0.0",
                "release_date": "2024-04-07",
                "description": "初始版本发布",
                "files": {
                    "hap": "debug.hap",
                    "hsp": "tztzfnetwork-signed.hsp"
                },
                "requirements": "鸿蒙系统 3.0+",
                "changelog": ["初始版本发布", "基础功能实现"],
                "deploy_path": "data/local/tmp/test123",
                "size": "~15MB"
            }
        ]
    }
}

@app.route('/api/apps', methods=['GET'])
def get_apps():
    return jsonify(APPS_DATA)

@app.route('/api/apps/<app_id>/versions', methods=['GET'])
def get_versions(app_id):
    if app_id in VERSIONS_DATA:
        return jsonify(VERSIONS_DATA[app_id])
    return jsonify({"error": "应用不存在"}), 404

@app.route('/api/apps/<app_id>/versions/<version>', methods=['GET'])
def get_version(app_id, version):
    if app_id in VERSIONS_DATA:
        for v in VERSIONS_DATA[app_id]["versions"]:
            if v["version"] == version:
                return jsonify(v)
    return jsonify({"error": "版本不存在"}), 404

@app.route('/api/files/<filename>', methods=['GET'])
def download_file(filename):
    file_path = os.path.join('files', filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    return jsonify({"error": "文件不存在"}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## 部署说明

1. 将HAP和HSP文件放在服务器的`files/`目录下
2. 配置应用和版本数据
3. 启动API服务
4. 在客户端配置服务器地址

## 安全考虑

- 实现文件访问权限控制
- 添加API认证机制
- 限制文件下载速度
- 记录下载日志
- 防止恶意文件访问
