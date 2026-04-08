# 服务器API文档

## 概述

这是数据库版本的HarmonyOS安装工具服务器API文档。

## 基础URL

```
http://localhost:5000/api
```

## 认证

目前版本不需要认证，所有端点都是公开的。

## API端点

### 应用管理

#### 获取所有应用
```http
GET /api/apps
```

**响应：**
```json
{
  "apps": [
    {
      "id": 1,
      "name": "YTZQ",
      "description": "YTZQ",
      "bundle_name": "com.ytzq.hmos",
      "main_ability": "EntryAbility",
      "current_version": "1.0.0",
      "created_at": "2026-04-08T06:17:06",
      "updated_at": "2026-04-08T06:17:06"
    }
  ]
}
```

#### 创建应用
```http
POST /api/apps
Content-Type: application/json
```

**请求体：**
```json
{
  "name": "App Name",
  "description": "App Description",
  "bundle_name": "com.example.app",
  "main_ability": "EntryAbility",
  "current_version": "1.0.0"
}
```

#### 更新应用
```http
PUT /api/apps/{id}
Content-Type: application/json
```

#### 删除应用
```http
DELETE /api/apps/{id}
```

### 版本管理

#### 获取应用版本
```http
GET /api/apps/{app_id}/versions
```

**响应：**
```json
{
  "versions": [
    {
      "id": 1,
      "app_id": 1,
      "version": "1.0.0",
      "description": "初始版本发布",
      "release_date": "2024-04-03",
      "size": null,
      "hap_filename": "debug.hap",
      "hsp_filename": "tztzfnetwork-signed.hsp",
      "deploy_path": "/data/local/tmp",
      "created_at": "2026-04-08T06:17:06",
      "files": [
        {
          "id": 1,
          "version_id": 1,
          "file_type": "hap",
          "filename": "debug.hap",
          "file_path": "C:\\path\\to\\debug.hap",
          "file_size": 109920232,
          "upload_time": "2026-04-08T06:17:06"
        },
        {
          "id": 2,
          "version_id": 1,
          "file_type": "hsp",
          "filename": "tztzfnetwork-signed.hsp",
          "file_path": "C:\\path\\to\\tztzfnetwork-signed.hsp",
          "file_size": 11010581,
          "upload_time": "2026-04-08T06:17:06"
        }
      ]
    }
  ]
}
```

#### 创建版本
```http
POST /api/apps/{app_id}/versions
Content-Type: application/json
```

**请求体：**
```json
{
  "version": "1.0.1",
  "description": "New version description",
  "release_date": "2024-04-10",
  "size": 15728640,
  "deploy_path": "/data/local/tmp",
  "set_as_current": true
}
```

#### 获取版本信息（旧格式）
```http
GET /api/versions/{version_id}/info
```

**响应：**
```json
{
  "version": "1.0.0",
  "description": "初始版本发布",
  "release_date": "2024-04-03",
  "size": null,
  "deploy_path": "/data/local/tmp",
  "files": {
    "hap": "debug.hap",
    "hsp": "tztzfnetwork-signed.hsp"
  },
  "bundle_name": "com.ytzq.hmos",
  "main_ability": "EntryAbility"
}
```

### 文件管理

#### 上传文件
```http
POST /api/upload
Content-Type: multipart/form-data
```

**表单数据：**
- `file`: 二进制文件数据
- `version_id`: 目标版本ID
- `file_type`: "hap" 或 "hsp"

**响应：**
```json
{
  "message": "File uploaded successfully",
  "filename": "debug.hap",
  "file_size": 109920232,
  "file_id": 1
}
```

#### 下载文件
```http
GET /api/files/{id}
```

#### 下载版本文件
```http
GET /api/versions/{version_id}/files/{file_type}/download
```

**参数：**
- `version_id`: 版本ID
- `file_type`: "hap" 或 "hsp"

#### 删除文件
```http
DELETE /api/files/{id}
```

### 系统端点

#### 健康检查
```http
GET /health
```

**响应：**
```json
{
  "status": "healthy",
  "database": "connected",
  "apps": 1,
  "versions": 1,
  "files": 2
}
```

#### API文档
```http
GET /
```

#### 管理面板
```http
GET /admin
```

返回Web管理界面。

## 错误处理

所有端点返回适当的HTTP状态码：

- `200 OK` - 成功
- `201 Created` - 资源创建成功
- `400 Bad Request` - 无效输入数据
- `404 Not Found` - 资源不存在
- `500 Internal Server Error` - 服务器错误

**错误响应格式：**
```json
{
  "error": "错误描述"
}
```

## 数据库架构

### 应用表
```sql
CREATE TABLE apps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    bundle_name VARCHAR(255) NOT NULL,
    main_ability VARCHAR(255) NOT NULL,
    current_version VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 版本表
```sql
CREATE TABLE versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id INTEGER NOT NULL,
    version VARCHAR(50) NOT NULL,
    description TEXT,
    release_date DATE,
    size INTEGER,
    hap_filename VARCHAR(255),
    hsp_filename VARCHAR(255),
    deploy_path VARCHAR(500) DEFAULT '/data/local/tmp',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (app_id) REFERENCES apps(id) ON DELETE CASCADE
);
```

### 文件表
```sql
CREATE TABLE files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version_id INTEGER NOT NULL,
    file_type VARCHAR(20) NOT NULL CHECK (file_type IN ('hap', 'hsp')),
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size INTEGER,
    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (version_id) REFERENCES versions(id) ON DELETE CASCADE
);
```

## 文件存储

文件存储在`uploads/apps/{app_id}/{version_id}/`目录结构中。

## 管理界面

访问Web管理面板`http://localhost:5000/admin`以：

- 查看统计数据（应用、版本、文件数量）
- 管理应用（创建、编辑、删除）
- 管理版本（创建、编辑、删除）
- 上传文件（支持拖放）
- 实时数据更新

## 从JSON版本迁移

如果从旧的JSON版本升级：

1. 运行迁移脚本：
```bash
python migrate.py
```

2. 脚本将：
   - 读取现有的`apps.json`和版本文件
   - 将它们转换为数据库格式
   - 保留文件位置
   - 显示迁移统计数据

## 客户端兼容性

数据库版本通过以下方式保持与现有客户端的兼容性：

1. **相同的响应格式**用于核心功能
2. **向后兼容的端点**在需要时
3. **无缝迁移**无需客户端更改

## 开发

### 项目结构
```
server/
├── app.py              # 主Flask应用
├── database/           # 数据库模块
│   ├── __init__.py
│   ├── database.py    # 数据库连接
│   └── models.py      # 数据模型
├── api/               # API端点
│   ├── __init__.py
│   ├── apps.py        # 应用API
│   ├── versions.py    # 版本API
│   └── files.py       # 文件API
├── uploads/           # 文件存储目录
├── admin.html         # Web管理界面
└── requirements.txt    # 依赖项
```

### 添加新功能

1. 在`database/models.py`中定义数据模型
2. 在相应的`api/*.py`文件中添加API端点
3. 更新`admin.html`以进行UI更改
4. 使用提供的示例进行测试

## 安全性

- **SQL注入防护**：所有查询使用参数化语句
- **文件上传验证**：文件经过验证并存储安全
- **输入验证**：所有输入在处理前经过验证
- **文件访问控制**：文件通过安全端点提供

## 性能

- **数据库索引**：主键和外键已索引
- **连接池**：SQLite高效处理连接
- **文件存储**：考虑大型部署时使用云存储
