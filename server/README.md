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
python app.py
```

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

### 文件管理
- `POST /api/upload` - 上传文件
- `GET /api/files/{id}` - 下载文件
- `DELETE /api/files/{id}` - 删除文件

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
默认上传目录：`server/uploads/apps/`

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
