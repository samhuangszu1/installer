#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鸿蒙应用安装工具服务端
提供应用管理、版本管理和文件下载功能
"""

from flask import Flask, jsonify, request, send_file, abort
from flask_cors import CORS
import os
import json
import logging
from datetime import datetime
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 配置
class Config:
    DEBUG = True
    APPS_FILE = 'apps.json'
    FILES_DIR = 'files'
    
    @staticmethod
    def init():
        """初始化配置"""
        # 确保files目录存在
        os.makedirs(Config.FILES_DIR, exist_ok=True)

# 初始化配置
Config.init()

def load_apps_config():
    """加载应用配置"""
    try:
        if os.path.exists(Config.APPS_FILE):
            with open(Config.APPS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # 返回默认配置
            return {
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
    except Exception as e:
        logger.error(f"加载应用配置失败: {e}")
        return {"apps": []}

def save_apps_config(config):
    """保存应用配置"""
    try:
        with open(Config.APPS_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"保存应用配置失败: {e}")
        return False

@app.route('/apps', methods=['GET'])
def get_apps():
    """获取应用列表"""
    try:
        config = load_apps_config()
        logger.info(f"返回应用列表: {len(config.get('apps', []))} 个应用")
        return jsonify(config)
    except Exception as e:
        logger.error(f"获取应用列表失败: {e}")
        return jsonify({"error": "获取应用列表失败", "code": "GET_APPS_ERROR"}), 500

@app.route('/apps/<app_id>/versions', methods=['GET'])
def get_app_versions(app_id):
    """获取应用版本列表"""
    try:
        config = load_apps_config()
        apps = config.get('apps', [])
        
        # 查找对应的应用
        target_app = None
        for app in apps:
            if app.get('id') == app_id:
                target_app = app
                break
        
        if not target_app:
            return jsonify({"error": "应用不存在", "code": "APP_NOT_FOUND"}), 404
        
        # 模拟版本数据（实际应该从文件系统或数据库读取）
        versions_dir = target_app.get('versions_dir', f'versions/{app_id}')
        versions = []
        
        if os.path.exists(versions_dir):
            for item in os.listdir(versions_dir):
                version_path = os.path.join(versions_dir, item)
                if os.path.isdir(version_path):
                    version_info_path = os.path.join(version_path, 'version_info.json')
                    if os.path.exists(version_info_path):
                        try:
                            with open(version_info_path, 'r', encoding='utf-8') as f:
                                version_info = json.load(f)
                                versions.append(version_info)
                        except Exception as e:
                            logger.warning(f"读取版本信息失败 {version_info_path}: {e}")
        
        # 按版本号排序
        versions.sort(key=lambda x: x.get('version', ''), reverse=True)
        
        logger.info(f"返回应用 {app_id} 的版本列表: {len(versions)} 个版本")
        return jsonify({"versions": versions})
        
    except Exception as e:
        logger.error(f"获取版本列表失败: {e}")
        return jsonify({"error": "获取版本列表失败", "code": "GET_VERSIONS_ERROR"}), 500

@app.route('/apps/<app_id>/versions/<version>', methods=['GET'])
def get_version_info(app_id, version):
    """获取版本详细信息"""
    try:
        config = load_apps_config()
        apps = config.get('apps', [])
        
        # 查找对应的应用
        target_app = None
        for app in apps:
            if app.get('id') == app_id:
                target_app = app
                break
        
        if not target_app:
            return jsonify({"error": "应用不存在", "code": "APP_NOT_FOUND"}), 404
        
        # 查找版本信息
        versions_dir = target_app.get('versions_dir', f'versions/{app_id}')
        version_info_path = os.path.join(versions_dir, version, 'version_info.json')
        
        if not os.path.exists(version_info_path):
            return jsonify({"error": "版本不存在", "code": "VERSION_NOT_FOUND"}), 404
        
        with open(version_info_path, 'r', encoding='utf-8') as f:
            version_info = json.load(f)
        
        logger.info(f"返回版本信息: {app_id} {version}")
        return jsonify(version_info)
        
    except Exception as e:
        logger.error(f"获取版本信息失败: {e}")
        return jsonify({"error": "获取版本信息失败", "code": "GET_VERSION_INFO_ERROR"}), 500

@app.route('/files/<filename>', methods=['GET'])
def download_file(filename):
    """下载文件"""
    try:
        file_path = os.path.join(Config.FILES_DIR, filename)
        
        if not os.path.exists(file_path):
            logger.warning(f"文件不存在: {file_path}")
            return jsonify({"error": "文件不存在", "code": "FILE_NOT_FOUND"}), 404
        
        # 检查文件大小
        file_size = os.path.getsize(file_path)
        logger.info(f"下载文件: {filename} ({file_size} bytes)")
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"文件下载失败: {e}")
        return jsonify({"error": "文件下载失败", "code": "DOWNLOAD_ERROR"}), 500

@app.route('/api/files', methods=['GET'])
def list_files():
    """列出所有可用文件"""
    try:
        files = []
        if os.path.exists(Config.FILES_DIR):
            for filename in os.listdir(Config.FILES_DIR):
                file_path = os.path.join(Config.FILES_DIR, filename)
                if os.path.isfile(file_path):
                    stat = os.stat(file_path)
                    files.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    })
        
        logger.info(f"返回文件列表: {len(files)} 个文件")
        return jsonify({"files": files})
        
    except Exception as e:
        logger.error(f"获取文件列表失败: {e}")
        return jsonify({"error": "获取文件列表失败", "code": "GET_FILES_ERROR"}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })

@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return jsonify({"error": "资源不存在", "code": "NOT_FOUND"}), 404

@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    logger.error(f"内部服务器错误: {error}")
    return jsonify({"error": "内部服务器错误", "code": "INTERNAL_ERROR"}), 500

@app.route('/')
def index():
    """Index page"""
    return jsonify({
        "name": "HarmonyOS Installer Server",
        "version": "1.0.0",
        "description": "Server for HarmonyOS application management",
        "endpoints": {
            "apps": "/apps",
            "versions": "/apps/{app_id}/versions",
            "version_info": "/apps/{app_id}/versions/{version}",
            "download": "/files/{filename}",
            "files_list": "/files",
            "health": "/health"
        }
    })

if __name__ == '__main__':
    logger.info("启动鸿蒙应用安装工具服务端...")
    logger.info(f"应用配置文件: {Config.APPS_FILE}")
    logger.info(f"文件存储目录: {Config.FILES_DIR}")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=Config.DEBUG
    )
