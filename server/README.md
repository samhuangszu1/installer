# 鸿蒙应用安装工具服务端

提供应用管理、版本管理和文件下载功能的Flask服务端。

## 🚀 快速开始

### 1. 安装依赖

```bash
# 方式1: 使用启动脚本（推荐）
python start_server.py

# 方式2: 手动安装
pip install -r requirements.txt
python app.py
```

### 2. 启动服务器

```bash
# 使用启动脚本
python start_server.py

# 或直接运行
python app.py
```

服务器将在 `http://localhost:5000` 启动

## 📋 API端点

### API endpoints
- `GET /apps` - Get application list
- `GET /apps/{app_id}/versions` - Get application version list
- `GET /apps/{app_id}/versions/{version}` - Get version details
- `GET /files/{filename}` - Download file
- `GET /files` - List files
- `GET /health` - Health check
- `GET /` - 服务信息

## 📁 目录结构

```
server/
├── app.py              # 主应用文件
├── start_server.py      # 启动脚本
├── requirements.txt     # 依赖包
├── apps.json          # 应用配置
├── files/             # 文件存储
│   ├── debug.hap
│   └── tztzfnetwork-signed.hsp
└── versions/          # 版本信息存储
    └── com_ytzq_hmos/
        └── 1.0.0/
            └── version_info.json
```

## ⚙️ 配置说明

### 应用配置 (apps.json)
```json
{
  "apps": [
    {
      "id": "com.ytzq.hmos",
      "name": "YTZQ鸿蒙应用",
      "description": "YTZQ公司开发的鸿蒙应用",
      "current_version": "1.0.0",
      "main_ability": "com.ytzq.hmos.MainAbility",
      "versions_dir": "versions/com_ytzq_hmos"
    }
  ]
}
```

### 版本信息 (version_info.json)
```json
{
  "version": "1.0.0",
  "description": "YTZQ鸿蒙应用 v1.0.0",
  "release_date": "2024-01-01",
  "size": "~10MB",
  "files": {
    "hap": "debug.hap",
    "hsp": "tztzfnetwork-signed.hsp"
  },
  "changelog": [
    "初始版本发布",
    "支持鸿蒙OS 4.0+"
  ]
}
```

## 🔧 开发说明

### 添加新应用
1. 在 `apps.json` 中添加应用信息
2. 在 `versions/` 中创建对应的版本目录
3. 添加版本信息和文件

### 添加新版本
1. 在对应应用的版本目录中创建新版本目录
2. 添加 `version_info.json` 文件
3. 将HAP/HSP文件复制到 `files/` 目录

### 文件上传
将HAP、HSP等文件上传到 `files/` 目录，然后通过API提供下载。

## 🌐 客户端配置

在客户端配置服务器地址：
```
服务器地址: http://127.0.0.1:5000
```

**重要提示**：不要添加 `/api` 前缀，客户端直接使用基地址。

## 🛡️ 安全说明

- 当前版本未启用身份验证
- 建议在生产环境中添加API密钥验证
- 文件下载建议添加访问控制

## 📝 日志

服务器运行时会输出详细的日志信息，包括：
- API请求记录
- 文件下载记录
- 错误信息

## 🔄 部署建议

### 开发环境
```bash
python start_server.py
```

### 生产环境
```bash
# 使用WSGI服务器
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app

# 或使用Docker
docker build -t harmony-server .
docker run -p 5000:5000 harmony-server
```

## 🐛 故障排除

### 常见问题

1. **端口被占用**
   - 修改 `app.py` 中的端口号
   - 或停止占用5000端口的其他服务

2. **文件不存在**
   - 检查 `files/` 目录中是否有对应文件
   - 确认文件名拼写正确

3. **跨域问题**
   - 已启用CORS支持
   - 检查客户端请求地址是否正确

### 调试模式

修改 `app.py` 中的 `Config.DEBUG` 为 `True` 启用调试模式。
