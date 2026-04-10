# HarmonyOS Installer - Database Version

## Overview

这是数据库版本的HarmonyOS安装工具服务器，替代了原来的JSON文件存储方式。

## Features

- **SQLite数据库存储**：应用、版本和文件的统一管理
- **RESTful API**：完整的CRUD操作
- **Web管理界面**：直观的管理面板
- **文件上传下载**：安全的文件管理
- **向后兼容**：支持现有客户端

## Quick Start

### 1. 启动服务器
```bash
pip install -r requirements.txt
python app.py
```

如果需要使用 API Key 鉴权（保护上传接口），推荐通过 `.env` 配置：
1. 复制 `server/.env.example` 为 `server/.env`
2. 修改 `ADMIN_API_KEY=...`
3. 重启服务器

注意：不要提交真实的 `server/.env` 到仓库。

### 2. 访问管理界面
打开浏览器访问：`http://localhost:5000/admin`

### 3. 客户端使用
客户端会自动适配新的API端点，无需修改配置。

## API Endpoints

### 应用管理
- `GET /api/apps` - 获取所有应用
- `POST /api/apps` - 创建新应用
- `PUT /api/apps/{id}` - 更新应用
- `DELETE /api/apps/{id}` - 删除应用

### 版本管理
- `GET /api/apps/{app_id}/versions` - 获取应用版本
- `POST /api/apps/{app_id}/versions` - 创建新版本
- `PUT /api/versions/{id}` - 更新版本
- `DELETE /api/versions/{id}` - 删除版本

#### 创建版本并上传文件（字段+文件一次提交）

创建（或覆盖）某个应用的版本，并在同一次请求中同时上传 HAP/HSP 文件。

- **Method/URL**: `POST /api/versions/create-with-files`
- **Content-Type**: `multipart/form-data`

安全（API Key）：
- 如果启动 server 时设置了环境变量 `ADMIN_API_KEY`，则以下接口必须带请求头 `X-API-Key: <ADMIN_API_KEY>` 才能访问：
  - `POST /api/versions/create-with-files`
  - `POST /api/upload`
  - `PUT /api/apps/{id}`
  - `PUT /api/versions/{id}`

表单字段（form fields）：
- `app_id`（必填，int）
- `version`（必填，string）
- `description`（可选）
- `release_date`（可选，例如 `2026-04-10`）
- `deploy_path`（可选，默认 `/data/local/tmp`）
- `set_as_current`（可选，`true/false` 或 `1/0`）

文件字段（form files）：
- `hap_file`（必填，`.hap`）
- `hsp_file`（必填，`.hsp`）

覆盖规则：
- 以 `(app_id, version)` 判断是否为重复版本。
- 若已存在，则覆盖该版本的 `hap/hsp` 文件记录（同类型只保留一份）。

示例（Windows PowerShell curl）：
```powershell
curl -X POST "http://127.0.0.1:5000/api/versions/create-with-files" `
  -H "X-API-Key: YOUR_ADMIN_API_KEY" `
  -F "app_id=1" `
  -F "version=1.0.2" `
  -F "description=second release" `
  -F "release_date=2026-04-10" `
  -F "deploy_path=/data/local/tmp" `
  -F "set_as_current=true" `
  -F "hap_file=@C:\path\to\debug1.hap" `
  -F "hsp_file=@C:\path\to\tztzfnetwork-signed1.hsp"
```

示例（Python requests）：
```python
import requests

url = "http://127.0.0.1:5000/api/versions/create-with-files"
data = {
    "app_id": "1",
    "version": "1.0.2",
    "description": "second release",
    "release_date": "2026-04-10",
    "deploy_path": "/data/local/tmp",
    "set_as_current": "true",
}
files = {
    "hap_file": open(r"C:\path\to\debug1.hap", "rb"),
    "hsp_file": open(r"C:\path\to\tztzfnetwork-signed1.hsp", "rb"),
}
resp = requests.post(url, data=data, files=files, timeout=300)
print(resp.status_code)
print(resp.text)
```

返回：
- 成功：HTTP `201`，返回版本对象和 `files` 字段（成功时不包含 `error` 字段）。
- 失败：HTTP `400/404/500`，返回 `{ "error": "..." }`。

### 文件管理
- `POST /api/upload` - 上传文件
- `GET /api/files/{id}` - 下载文件
- `DELETE /api/files/{id}` - 删除文件
- `GET /api/versions/{version_id}/files/{file_type}/download` - 下载指定版本的指定文件（hap/hsp）
- `GET /files/{filename}` - 通过文件名下载（兼容接口）

### 系统端点
- `GET /health` - 健康检查
- `GET /admin` - 管理界面
- `GET /` - API文档

## Project Structure

```
server/
├── app.py              # 主应用文件
├── database/           # 数据库模块
│   ├── __init__.py
│   ├── database.py    # 数据库连接
│   └── models.py      # 数据模型
├── api/               # API接口
│   ├── __init__.py
│   ├── apps.py        # 应用API
│   ├── versions.py    # 版本API
│   └── files.py       # 文件API
├── uploads/           # 文件存储
├── database/          # 数据库文件
├── admin.html         # 管理界面
└── requirements.txt    # 依赖包
```

## Database Schema

数据库包含三个主要表：
- **apps** - 应用基本信息
- **versions** - 版本信息
- **files** - 文件管理

详细的表结构请参考 `database/database.py`。

## Admin Panel

访问 `http://localhost:5000/admin` 可以：
- 查看统计信息（应用、版本、文件数量）
- 管理应用（创建、编辑、删除）
- 管理版本（创建、编辑、删除）
- 上传文件（HAP、HSP）
- 实时数据更新

## Migration from JSON Version

如果从JSON版本升级：

1. 运行数据迁移（如果需要）：
```bash
python migrate.py
```

2. 数据库会自动创建并导入现有数据

## Requirements

```bash
pip install -r requirements.txt
```

## Development

### 添加新功能
1. 在 `database/models.py` 中定义数据模型
2. 在相应的 `api/*.py` 文件中添加API端点
3. 更新 `admin.html` 添加管理界面

### 数据库位置
默认数据库文件：`server/database/harmony_installer.db`

### 文件存储位置
默认上传目录：`server/uploads/apps/<app_id>/<version_id>/`

## Troubleshooting

### 数据库连接问题
1. 确保Python有写入权限
2. 检查数据库文件是否存在
3. 重新启动服务器

### 文件上传问题
1. 检查uploads目录权限
2. 验证文件大小限制
3. 查看磁盘空间

## License

与原项目保持相同的许可证。
