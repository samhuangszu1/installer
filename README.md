# HarmonyOS 应用安装工具（Modern GUI）

一个用于华为 HarmonyOS 应用安装的现代化图形客户端，支持多应用、多版本、多租户（多公司隔离）、基于服务端的统一管理，界面中文化。

## 功能特性

- **现代化 GUI**：深色主题、交互友好
- **多应用管理**：集中管理多个 HarmonyOS 应用
- **多版本管理**：每个应用支持多版本选择与安装
- **多租户隔离**：支持多公司独立管理，数据隔离，API Key 鉴权
- **客户端-服务端架构**：服务端统一管理应用/版本/文件
- **跨平台**：Windows、macOS、Linux
- **中文界面**：完整中文界面与提示
- **HDC 自动检测**：自动选择合适的 HDC 工具
- **实时日志**：完整的执行过程与错误信息
- **一键安装**：自动化安装流程与错误处理
- **Web 管理后台**：浏览器管理应用与版本
- **用户认证**：Admin / Company Manager 登录，JWT 鉴权

## 架构说明

### 客户端-服务端结构
- **客户端**：`harmony_ultra_modern.py`（图形安装器）
- **服务端**：`server/`（Flask REST API）
- **管理后台**：`server/admin.html`

### 关键组件

#### 客户端能力
- Tkinter 深色主题 GUI
- 应用列表/版本选择
- 安装进度与日志
- 设备状态监控（HDC）

#### 服务端能力
- 应用/版本管理 REST API
- 文件上传与版本文件管理
- SQLite 元数据存储
- Web 管理后台（Admin / Company Manager 分离入口）
- 文件下载服务
- 多租户公司隔离与 API Key 管理
- 用户认证（JWT + API Key）

## 安装与运行

### 前置条件
- Python 3.7+
- HDC 工具（项目已包含）
- 用于管理后台的现代浏览器

### 启动服务端
```bash
cd server
pip install -r requirements.txt
python app.py
```

### 配置环境变量（必须）

复制 `server/.env.example` 为 `server/.env`，并设置 `ADMIN_API_KEY`：
```bash
cp server/.env.example server/.env
# 编辑 .env，设置 ADMIN_API_KEY 为一个安全的随机字符串
```

> ⚠️ `ADMIN_API_KEY` 是 Admin 登录后自动存储到浏览器 localStorage 的关键凭证，未设置将导致 Admin 登录后后续接口报 401。

不要提交真实的 `server/.env` 文件。

### 创建 Admin 用户

首次使用前需创建 Admin 用户：
```bash
cd server
python create_admin.py <email> <password> [name]
# 示例：python create_admin.py admin@test.com admin123 Administrator
```

> 只能在数据库无用户时执行，密码至少 8 位。

服务端默认监听：`http://localhost:5000`

### 启动客户端

#### 方式 1：直接运行 Python 脚本
```bash
python harmony_ultra_modern.py
```

#### 方式 2：使用 PyInstaller 构建可执行文件（推荐）
```bash
pip install pyinstaller
pyinstaller harmony_app_installer.spec
```

可执行文件输出在：`dist/HarmonyOSInstaller.exe`

#### 方式 3：生成 Windows 安装包（Setup.exe）

项目提供了 Inno Setup 脚本 `installer.iss`，用于把 onefile 的 `HarmonyOSInstaller.exe` 封装为标准 Windows 安装程序（支持自定义安装目录、开始菜单、卸载）。

前置条件：
- Inno Setup 6

步骤：
1. 构建 onefile 可执行文件：
   ```bash
   pyinstaller harmony_app_installer.spec
   ```
2. 将预先配置好的 `settings.json` 放到 `dist/settings.json`（后续要打不同安装包，只需替换该文件即可）。
3. 编译安装包：
   - GUI：打开 Inno Setup Compiler，打开 `installer.iss`，点击 **Compile**
   - 命令行（PowerShell）：
     ```powershell
     & "C:\Users\huangkr\AppData\Local\Programs\Inno Setup 6\ISCC.exe" "C:\Users\huangkr\Desktop\harmony_test_pkg\installer.iss"
     ```

输出：
- `installer_out/HarmonyOSInstaller_Setup.exe`

配置文件位置：
- 客户端配置读写位置为 `%APPDATA%\HarmonyOSInstaller\settings.json`
- 安装程序会把 `dist/settings.json` 复制到上述位置（脚本使用 `onlyifdoesntexist`，避免覆盖已有用户配置）

默认下载目录：
- `%LOCALAPPDATA%\HarmonyOSInstaller\downloads`

## 使用方法

### 使用 GUI 客户端
1. **启动客户端**：运行 `HarmonyOSInstaller.exe` 或 `harmony_ultra_modern.py`
2. **配置服务端地址**：在配置界面填写 server URL
3. **连接设备**：USB 连接 HarmonyOS 设备并开启开发者模式
4. **选择应用**：从应用列表选择目标应用
5. **选择版本**：选择要安装的版本
6. **执行安装**：点击安装按钮
7. **查看日志**：观察实时日志与错误提示

### 使用 Web 管理后台

系统提供两个独立的登录入口：

| 入口 | URL | 说明 |
|------|-----|------|
| Admin | `http://localhost:5000/admin` | 管理员登录，可切换到 Company Manager |
| Company Manager | `http://localhost:5000/company/admin` | 公司管理员专用入口，仅显示 Company 登录 |

1. **打开后台**：根据角色访问对应 URL
2. **Admin 功能**：管理公司、创建 API Key、创建公司管理员、管理所有应用/版本
3. **Company Manager 功能**：管理本公司应用/版本、上传 HAP/HSP 文件
4. **配置与维护**：进行相关配置管理

## 项目结构

```
installer/
|   harmony_ultra_modern.py      # Main GUI client
|   harmony_app_installer.spec   # PyInstaller specification
|   installer.iss                # Inno Setup script
|   .example.settings.json       # Example client settings
|   logo.ico / logo.png          # App icon
|   README.md                    # This file
|   .gitignore                   # Git ignore file
|   
+---server/                      # Server directory
|   |   app.py                   # Flask server application
|   |   admin.html               # Web admin panel (Admin + Company Manager)
|   |   create_admin.py          # Admin user creation script
|   |   requirements.txt         # Server dependencies
|   |   .env.example             # Environment variable template
|   |   .env                     # Environment variables (not committed)
|   |   .gitignore               # Server git ignore
|   
|   +---api/                     # API endpoints
|   |   |   apps.py               # Application management API
|   |   |   files.py              # File upload/download API
|   |   |   versions.py           # Version management API
|   |   |   auth.py               # Authentication & API key management API
|   |   |   __init__.py           # API initialization
|   
|   +---database/                # Database components
|   |   |   models.py             # Database models
|   |   |   database.py           # Database initialization
|   |   |   __init__.py           # Database initialization
|   
|   +---uploads/                  # Upload directory (uploads/apps/<app_id>/<version_id>/...)

+---hdc_arm/                     # ARM architecture HDC tools
+---hdc_win/                     # Windows HDC tools  
+---hdc_x86/                     # x86 architecture HDC tools
```

## API 接口

### 认证
- `POST /api/auth/login` - 登录（Admin / Company Manager），返回 JWT token + api_key
- `POST /api/auth/logout` - 登出
- `GET /api/auth/me` - 获取当前用户信息（需 JWT）
- `POST /api/auth/setup` - 创建初始 Admin 用户（仅在无用户时可用，需 ADMIN_API_KEY）

### 应用管理
- `GET /api/apps` - 获取应用列表（按公司隔离）
- `POST /api/apps` - 创建应用
- `PUT /api/apps/{id}` - 更新应用
- `DELETE /api/apps/{id}` - 删除应用

### 版本管理
- `GET /api/apps/{app_id}/versions` - 获取应用版本列表
- `POST /api/apps/{app_id}/versions` - 创建版本
- `PUT /api/versions/{id}` - 更新版本
- `DELETE /api/versions/{id}` - 删除版本
- `GET /api/versions/{id}/info` - 获取版本信息（兼容格式）
- `DELETE /api/versions/{version_id}/files/{file_type}` - 删除指定类型文件（hap/hsp）

#### 一次性创建/覆盖版本并上传文件（字段 + 文件）

在一个请求中创建（或覆盖）版本，并上传 HAP/HSP 文件。

- **Method/URL**: `POST /api/versions/create-with-files`
- **Content-Type**: `multipart/form-data`

鉴权说明：
- 所有受保护接口需要 header `X-API-Key: <your_api_key>`
- Admin 使用 `ADMIN_API_KEY`（环境变量），Company Manager 使用公司分配的 API Key
- 登录后 API Key 会自动存储到浏览器 localStorage
- JWT token 通过 `Authorization: Bearer <token>` 传递

表单字段：
- `app_id` (required, int)
- `version` (required, string)
- `description` (optional)
- `release_date` (optional, e.g. `2026-04-10`)
- `deploy_path` (optional, default: `/data/local/tmp`)
- `set_as_current` (optional, `true/false` or `1/0`)

Files:
- `hap_file` (required, `.hap`)
- `hsp_file` (required, `.hsp`)

覆盖规则：
- 版本去重规则为 `(app_id, version)`
- 若版本已存在，会覆盖旧版本的 `hap/hsp` 记录（每种类型仅保留 1 个文件）

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

示例（Python）：
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

返回说明：
- **Success**: HTTP `201`，返回版本对象与 `files` 字段，不包含 `error`
- **Failure**: HTTP `400/404/500`，返回 JSON `{ "error": "..." }`

### 文件管理
- `POST /api/upload` - 向已存在的版本上传文件（multipart）
- `GET /api/files/{id}` - 根据 file id 下载文件
- `DELETE /api/files/{id}` - 根据 file id 删除文件
- `GET /api/versions/{version_id}/files/{file_type}/download` - 下载版本的指定文件（hap/hsp）

### 公司与 API Key 管理（Admin）
- `GET /api/admin/companies` - 获取公司列表
- `POST /api/admin/companies` - 创建公司（自动生成 API Key）
- `PUT /api/admin/companies/{id}` - 更新公司信息
- `DELETE /api/admin/companies/{id}` - 删除公司及关联 API Key
- `GET /api/admin/companies/{id}/api-keys` - 获取公司 API Key 列表
- `POST /api/admin/companies/{id}/api-keys` - 为公司创建新 API Key
- `DELETE /api/admin/api-keys/{id}` - 撤销 API Key
- `POST /api/admin/api-keys/{id}/toggle` - 启用/禁用 API Key
- `POST /api/admin/companies/{id}/managers` - 创建公司管理员用户

## 安装流程

自动化安装步骤包括：
1. **停止应用**：`shell aa force-stop {bundle_name}`
2. **卸载旧版本**：`shell bm uninstall -n {bundle_name} -k`
3. **上传 HSP**：`file send {hsp_file} {deploy_path}`
4. **上传 HAP**：`file send {hap_file} {deploy_path}`
5. **安装 HSP**：`shell bm install -p {deploy_path}/{hsp_file}`
6. **安装 HAP**：`shell bm install -p {deploy_path}/{hap_file}`
7. **启动应用**：`shell aa start -a {main_ability} -b {bundle_name} -m entry`

## 配置说明

### 客户端配置
- 服务端 URL（参考 `.example.settings.json`）
- 下载目录
- API Key（用于访问受保护接口）
- HDC 工具检测

### 服务端配置
- `ADMIN_API_KEY`：Admin API 密钥（环境变量，**必须设置**）
- `JWT_SECRET_KEY`：JWT 签名密钥（环境变量，可选，未设置则自动生成）
- 数据库：SQLite（`server/database/harmony_installer.db`）
- 文件存储路径：`uploads/apps/<app_id>/<version_id>/`
- 上传限制
- API 接口

## 常见问题排查

### HDC 相关问题
- 确认 HDC 工具目录是否完整
- 检查设备连接与 USB 调试
- 确认设备已开启开发者选项

### 服务端相关问题
- 确认 Flask 服务已启动
- 检查数据库权限
- 确认上传/下载目录存在

### 安装失败问题
- 检查设备存储空间
- 检查 HAP/HSP 文件是否正确
- 查看客户端日志定位错误

## 更新记录

### v4.0（最新）
- **多租户隔离**：多公司独立管理，数据隔离
- **用户认证**：Admin / Company Manager 登录，JWT + API Key 鉴权
- **分离入口**：`/admin`（Admin）与 `/company/admin`（Company Manager）独立登录页
- **API Key 管理**：公司 API Key 的创建、撤销、启用/禁用
- **公司管理员**：Admin 可为公司创建管理员用户
- **登录持久化**：API Key 自动存储到 localStorage
- **现代 GUI**：深色主题界面
- **中文化**：中文界面与提示
- **客户端-服务端架构**：REST API 管理
- **Web 管理后台**：浏览器管理
- **版本选择**：动态版本详情展示
- **错误处理**：更清晰的错误反馈
- **安装优化**：优化安装步骤与路径

### v3.0
- 现代 GUI 深色主题界面
- 中文化界面与提示
- 客户端-服务端架构：REST API 管理
- Web 管理后台
- 版本选择：动态版本详情展示

### v2.0
- 多应用支持
- 版本管理
- 界面优化
- 配置管理

### v1.0
- 初始版本
- 跨平台 HDC 检测
- 实时日志
- 基础安装能力

## 依赖与环境

### 系统要求
- Python 3.7+
- 4GB+ 内存
- 100MB+ 磁盘空间
- USB 连接设备

### 依赖
- **客户端**：tkinter, requests, subprocess
- **服务端**：Flask, SQLite3, Werkzeug, PyJWT, python-dotenv

## 许可证

MIT License

## 支持与反馈

遇到问题时建议：
1. 查看“常见问题排查”
2. 查看客户端日志
3. 确认服务端连接
4. 检查设备兼容性

---

**说明**：该工具用于 HarmonyOS 应用开发/测试环境，请确保设备与开发环境配置正确。
