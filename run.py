#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
大富翁棋盘游戏 - 启动脚本
"""

import os
import sys
import importlib.util

def import_app():
    """导入Flask应用"""
    spec = importlib.util.spec_from_file_location("app", os.path.join("web", "app.py"))
    app_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_module)
    return app_module.app, app_module.socketio

if __name__ == "__main__":
    # 导入Flask应用
    app, socketio = import_app()
    
    # 从环境变量或命令行参数获取配置
    debug = os.environ.get('DEBUG', 'True').lower() == 'true'
    
    # 默认只允许本地访问
    # 如需允许公共访问，设置host='0.0.0.0'或环境变量HOST=0.0.0.0
    host = os.environ.get('HOST', '127.0.0.1')
    
    # 默认端口
    port = int(os.environ.get('PORT', 5000))
    
    print(f"启动服务器: {'开发模式' if debug else '生产模式'}")
    print(f"监听地址: {host}:{port}")
    print("访问URL: http://{0}:{1}".format(
        'localhost' if host == '0.0.0.0' else host, 
        port
    ))
    
    # 启动服务器
    socketio.run(app, debug=debug, host=host, port=port) 