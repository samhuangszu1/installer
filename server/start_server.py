#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鸿蒙应用安装工具服务端启动脚本
"""

import sys
import os
import subprocess

def check_python_version():
    """检查Python版本"""
    if sys.version_info < (3, 6):
        print("错误: 需要Python 3.6或更高版本")
        print(f"当前版本: {sys.version}")
        sys.exit(1)

def install_dependencies():
    """安装依赖"""
    print("正在安装依赖包...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ 依赖安装完成")
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖安装失败: {e}")
        sys.exit(1)

def start_server():
    """启动服务器"""
    print("正在启动服务器...")
    print("📡 服务器地址: http://localhost:5000")
    print("📋 API文档: http://localhost:5000")
    print("🔍 健康检查: http://localhost:5000/api/health")
    print("按 Ctrl+C 停止服务器")
    print()
    
    try:
        from app import app
        app.run(
            host='0.0.0.0',
            port=5000,
            debug=False
        )
    except KeyboardInterrupt:
        print("\n🛑 服务器已停止")
    except Exception as e:
        print(f"❌ 服务器启动失败: {e}")
        sys.exit(1)

def main():
    """主函数"""
    print("🚀 鸿蒙应用安装工具服务端")
    print("=" * 40)
    
    # 检查Python版本
    check_python_version()
    
    # 检查并安装依赖
    if not os.path.exists('venv'):
        print("💡 提示: 建议使用虚拟环境")
        print("   python -m venv venv")
        print("   venv\\Scripts\\activate  # Windows")
        print("   source venv/bin/activate  # Linux/Mac")
        print()
    
    # 检查requirements.txt
    if os.path.exists('requirements.txt'):
        install_dependencies()
    else:
        print("⚠️  未找到requirements.txt文件")
    
    # 启动服务器
    start_server()

if __name__ == '__main__':
    main()
