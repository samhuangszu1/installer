# 鸿蒙应用多版本图形化安装工具

这是一个为华为鸿蒙系统应用安装而设计的多版本图形化工具，解决了原始shell脚本在Windows系统上不便使用的问题，并支持多个应用和版本的管理。

## 特性

- **多应用支持**: 支持管理多个鸿蒙应用
- **版本管理**: 每个应用支持多个版本，可选择安装
- **跨平台支持**: 支持Windows、macOS、Linux系统
- **图形化界面**: 用户友好的GUI界面，一键操作
- **自动检测**: 自动检测并选择合适的HDC工具
- **实时日志**: 显示详细的操作过程和错误信息
- **配置管理**: 支持编辑应用和版本配置
- **多种功能**: 安装、卸载、获取设备UDID等

## 功能说明

### 主要功能
1. **应用管理**: 管理多个鸿蒙应用，显示应用列表和详细信息
2. **版本选择**: 每个应用显示可用版本列表，支持选择安装特定版本
3. **安装应用**: 一键安装选定版本的鸿蒙应用到设备
4. **卸载应用**: 安全卸载已安装的应用
5. **获取UDID**: 获取连接设备的唯一标识符
6. **状态检测**: 实时显示HDC工具状态
7. **配置管理**: 编辑应用配置和版本信息

### 界面布局
- **左侧**: 应用列表，显示所有可用的应用
- **中间**: 版本列表，显示选中应用的所有可用版本
- **右侧**: 控制面板，显示应用信息和操作按钮
- **底部**: 操作日志，显示详细的操作过程和错误信息

### 自动化流程
安装过程包含以下步骤：
- 停止现有应用
- 卸载旧版本
- 清理部署路径
- 上传HAP和HSP文件
- 安装应用
- 启动应用

## 使用方法

### 方法一：直接运行Python脚本
```bash
# Windows
python harmony_multi_installer.py

# macOS/Linux
python3 harmony_multi_installer.py
```

### 方法二：使用启动脚本
```bash
# Windows
双击运行 run_multi_installer.bat

# macOS/Linux
chmod +x run_multi_installer.sh
./run_multi_installer.sh
```

### 方法三：打包成可执行文件（推荐）
```bash
# 安装PyInstaller
pip install pyinstaller

# 打包成单个可执行文件
pyinstaller --onefile --windowed --name="鸿蒙应用多版本安装工具" harmony_multi_installer.py

# 打包完成后，在dist目录下找到可执行文件
```

## 配置文件结构

### 应用配置 (config/apps.json)
```json
{
  "apps": [
    {
      "id": "com.ytzq.hmos",
      "name": "天通智联网络应用",
      "description": "天通智联网络鸿蒙应用",
      "versions_dir": "versions/com_ytzq_hmos",
      "current_version": "1.0.0",
      "bundle_name": "com.ytzq.hmos",
      "main_ability": "EntryAbility"
    }
  ]
}
```

### 版本配置 (versions/{app_id}/{version}/version_info.json)
```json
{
  "version": "1.0.0",
  "release_date": "2024-04-03",
  "description": "初始版本发布",
  "files": {
    "hap": "debug.hap",
    "hsp": "tztzfnetwork-signed.hsp"
  },
  "requirements": "鸿蒙系统 3.0+",
  "changelog": ["初始版本发布"],
  "deploy_path": "data/local/tmp/test123"
}
```

## 系统要求

- Python 3.6 或更高版本
- tkinter模块（通常随Python一起安装）
- HDC工具（已包含在项目中）

## 文件结构

```
harmony_test_pkg/
├── harmony_multi_installer.py    # 主程序文件
├── run_multi_installer.bat      # Windows启动脚本
├── run_multi_installer.sh       # macOS/Linux启动脚本
├── requirements.txt              # 依赖文件
├── config/                      # 配置文件目录
│   └── apps.json               # 应用配置文件
├── versions/                    # 版本文件目录
│   ├── com_ytzq_hmos/         # 应用版本目录
│   │   ├── 1.0.0/             # 版本1.0.0
│   │   │   ├── version_info.json
│   │   │   ├── debug.hap
│   │   │   └── tztzfnetwork-signed.hsp
│   │   └── 1.1.0/             # 版本1.1.0
│   │       └── version_info.json
│   ├── com_example_demo/       # 另一个应用
│   │   └── 1.0.0/
│   │       └── version_info.json
│   └── com_test_app/           # 第三个应用
│       └── 1.0.0/
│           └── version_info.json
├── install.sh                   # 原始shell脚本
├── debug.hap                    # 原始HAP文件
├── tztzfnetwork-signed.hsp     # 原始HSP文件
├── hdc_arm/                     # ARM架构HDC工具
├── hdc_win/                     # Windows HDC工具
└── hdc_x86/                     # x86架构HDC工具
```

## 使用说明

1. **确保设备连接**: 使用USB连接鸿蒙设备，并开启开发者模式
2. **启动工具**: 运行多版本安装工具
3. **检查状态**: 确认HDC工具状态显示为"已找到"
4. **选择应用**: 在左侧应用列表中选择要安装的应用
5. **选择版本**: 在中间版本列表中选择要安装的版本
6. **点击安装**: 点击"安装选中版本"按钮开始安装
7. **查看日志**: 在底部日志区域查看详细安装过程

## 添加新应用

### 1. 编辑应用配置
打开 `config/apps.json`，添加新的应用信息：

```json
{
  "id": "com.newapp.example",
  "name": "新应用名称",
  "description": "新应用描述",
  "versions_dir": "versions/com_newapp_example",
  "current_version": "1.0.0",
  "bundle_name": "com.newapp.example",
  "main_ability": "EntryAbility"
}
```

### 2. 创建版本目录和文件
```bash
# 创建版本目录
mkdir -p versions/com_newapp_example/1.0.0

# 复制HAP和HSP文件
cp your_app.hap versions/com_newapp_example/1.0.0/
cp your_shared.hsp versions/com_newapp_example/1.0.0/

# 创建版本信息文件
```

### 3. 创建版本信息文件
在 `versions/com_newapp_example/1.0.0/version_info.json` 中添加：

```json
{
  "version": "1.0.0",
  "release_date": "2024-04-03",
  "description": "新应用初始版本",
  "files": {
    "hap": "your_app.hap",
    "hsp": "your_shared.hsp"
  },
  "requirements": "鸿蒙系统 3.0+",
  "changelog": ["新应用发布"],
  "deploy_path": "data/local/tmp/newapp"
}
```

## 故障排除

### HDC工具未找到
- 确保在包含HDC工具的目录中运行此工具
- 检查hdc_arm、hdc_win、hdc_x86目录是否存在

### 设备连接问题
- 确保USB线缆连接正常
- 检查设备是否开启开发者模式和USB调试
- 尝试重新连接设备

### 安装失败
- 查看日志区域的错误信息
- 确保debug.hap和tztzfnetwork-signed.hsp文件存在
- 检查设备存储空间是否充足

## 技术细节

### HDC工具选择逻辑
- **macOS ARM64**: 使用hdc_arm/hdc
- **macOS x86**: 使用hdc_x86/hdc_x86
- **Windows**: 使用hdc_win/hdc_w.exe
- **Linux ARM64**: 使用hdc_arm/hdc
- **Linux x86**: 使用hdc_x86/hdc_x86

### 应用配置
- **包名**: com.ytzq.hmos
- **主能力**: EntryAbility
- **部署路径**: data/local/tmp/test123

## 更新日志

### v2.0 (2024-04-03)
- 新增多应用支持
- 新增版本管理功能
- 重新设计界面布局
- 添加配置文件管理
- 支持应用列表和版本列表显示
- 改进用户体验

### v1.0 (2024-04-03)
- 初始版本发布
- 支持图形化安装
- 跨平台HDC工具检测
- 实时日志显示
- 错误处理机制

## 许可证

本工具基于MIT许可证开源，可自由使用和修改。

## 联系方式

如有问题或建议，请联系开发团队。
