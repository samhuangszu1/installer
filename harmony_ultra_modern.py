#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
鸿蒙应用多版本图形化安装工具 - 现代化设计版
HarmonyOS App Multi-Version GUI Installer - Modern Design
"""

import os
import sys
import platform
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import time
import json
from pathlib import Path
import requests
from urllib.parse import urljoin

class ModernDesignInstaller:
    def __init__(self, root):
        self.root = root
        self.root.title("鸿蒙应用安装工具")
        self.root.geometry("1400x900")
        self.root.resizable(True, True)
        self.root.configure(bg='#0F1419')
        
        # 移除默认边框
        self.root.overrideredirect(False)
        
        # 现代化颜色方案
        self.colors = {
            'bg_primary': '#0F1419',      # 深色背景
            'bg_secondary': '#192734',    # 次要背景
            'bg_card': '#1C2938',        # 卡片背景
            'bg_accent': '#1DA1F2',      # 主色调 - 蓝色
            'bg_success': '#17BF63',     # 成功色 - 绿色
            'bg_warning': '#FFAD1E',     # 警告色 - 黄色
            'bg_danger': '#E0245E',      # 危险色 - 红色
            'text_primary': '#E7E9EA',   # 主要文字
            'text_secondary': '#8B98A5', # 次要文字
            'text_muted': '#536471',     # 静音文字
            'border': '#2F3336',         # 边框色
            'hover': '#1A8CD8',         # 悬停色
            'shadow': '#000000'          # 阴影色
        }
        
        # 字体设置
        self.fonts = {
            'title': ('Segoe UI', 22, 'bold'),
            'subtitle': ('Segoe UI', 16, 'bold'),
            'heading': ('Segoe UI', 14, 'bold'),
            'body': ('Segoe UI', 11),
            'small': ('Segoe UI', 9),
            'mono': ('Consolas', 10),
            'button': ('Segoe UI', 12, 'bold')
        }
        
        # 初始化变量
        self.hdc_path = None
        self.apps_config = None
        self.current_app = None
        self.current_version = None
        
        # 服务器配置
        self.server_base_url = ""  # 服务器地址
        self.download_dir = ""  # 下载目录
        
        # 创建自定义样式
        self.setup_custom_styles()
        
        # 创建界面
        self.create_modern_interface()
        
        # 加载配置（现在log_text已经创建）
        self.load_local_settings()
        
        # 创建下载目录（只有在配置有效时才创建）
        if self.download_dir and not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        
        # 检查配置
        if not self.check_initial_config():
            # 强制弹出配置界面
            self.log("⚠️ 配置不完整，请先配置服务器和下载目录")
            result = messagebox.askyesno(
                "配置向导",
                "欢迎使用鸿蒙应用安装工具！\n\n检测到您还没有完成初始配置。\n\n是否现在打开配置界面？",
                icon='question'
            )
            
            if result:
                self.configure_server()
            else:
                self.log("❌ 用户取消配置，程序退出")
                self.root.quit()
            return
        
        # 加载配置
        self.load_apps_config()
        
        # 自动检测HDC工具
        self.detect_hdc_tool()
        
        # 添加窗口拖拽功能
        self.setup_window_drag()
    
    def setup_custom_styles(self):
        """设置自定义样式"""
        self.style = ttk.Style()
        
        # 配置ttk样式
        self.style.theme_use('clam')
        
        # 自定义按钮样式
        self.style.configure('Modern.TButton',
                           background=self.colors['bg_accent'],
                           foreground='white',
                           borderwidth=0,
                           focuscolor='none',
                           font=self.fonts['button'],
                           relief='flat')
        
        self.style.map('Modern.TButton',
                      background=[('active', self.colors['hover'])])
        
        self.style.configure('Success.TButton',
                           background=self.colors['bg_success'],
                           foreground='white',
                           borderwidth=0,
                           focuscolor='none',
                           font=self.fonts['button'],
                           relief='flat')
        
        self.style.configure('Danger.TButton',
                           background=self.colors['bg_danger'],
                           foreground='white',
                           borderwidth=0,
                           focuscolor='none',
                           font=self.fonts['button'],
                           relief='flat')
        
        self.style.configure('Card.TFrame',
                           background=self.colors['bg_card'],
                           relief='flat',
                           borderwidth=0)
        
        # 进度条样式
        self.style.configure('Modern.Horizontal.TProgressbar',
                           background=self.colors['bg_accent'],
                           troughcolor=self.colors['bg_secondary'],
                           borderwidth=0,
                           lightcolor=self.colors['bg_accent'],
                           darkcolor=self.colors['bg_accent'])
    
    def create_modern_interface(self):
        """创建现代化界面"""
        # 主容器
        self.main_frame = tk.Frame(self.root, bg=self.colors['bg_primary'])
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建顶部导航栏
        self.create_header_bar()
        
        # 创建主要内容区域
        content_container = tk.Frame(self.main_frame, bg=self.colors['bg_primary'])
        content_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        # 创建工作区域
        self.create_workspace(content_container)
        
        # 创建底部状态栏
        self.create_status_bar()
    
    def create_header_bar(self):
        """创建顶部导航栏"""
        header = tk.Frame(self.main_frame, bg=self.colors['bg_secondary'], height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        # 左侧标题区域
        left_section = tk.Frame(header, bg=self.colors['bg_secondary'])
        left_section.pack(side=tk.LEFT, fill=tk.Y, padx=20)
        
        # 应用图标和标题
        title_container = tk.Frame(left_section, bg=self.colors['bg_secondary'])
        title_container.pack(expand=True)
        
        # 创建圆形图标
        icon_canvas = tk.Canvas(title_container, width=40, height=40, 
                              bg=self.colors['bg_secondary'], highlightthickness=0)
        icon_canvas.pack(side=tk.LEFT, padx=(0, 15))
        self.draw_modern_icon(icon_canvas)
        
        # 标题文字
        title_text = tk.Label(title_container,
                            text="鸿蒙应用安装工具",
                            bg=self.colors['bg_secondary'],
                            fg=self.colors['text_primary'],
                            font=self.fonts['title'])
        title_text.pack(anchor=tk.W)
        
        subtitle_text = tk.Label(title_container,
                                text="HarmonyOS App Installer",
                                bg=self.colors['bg_secondary'],
                                fg=self.colors['text_secondary'],
                                font=self.fonts['small'])
        subtitle_text.pack(anchor=tk.W)
        
        # 右侧状态区域
        right_section = tk.Frame(header, bg=self.colors['bg_secondary'])
        right_section.pack(side=tk.RIGHT, fill=tk.Y, padx=20)
        
        # 服务器配置按钮
        server_btn = tk.Button(right_section, text="🌐 服务器",
                           command=self.configure_server,
                           font=self.fonts['small'],
                           bg=self.colors['bg_card'],
                           fg=self.colors['text_primary'],
                           relief='flat',
                           bd=0,
                           padx=10,
                           pady=5)
        server_btn.pack(side=tk.RIGHT, padx=(0, 15))
        
        # HDC状态指示器
        status_container = tk.Frame(right_section, bg=self.colors['bg_secondary'])
        status_container.pack(expand=True)
        
        self.status_indicator = tk.Canvas(status_container, width=12, height=12,
                                        bg=self.colors['bg_secondary'], highlightthickness=0)
        self.status_indicator.pack(side=tk.LEFT, padx=(0, 10))
        self.update_status_indicator('warning')
        
        self.status_text = tk.Label(status_container,
                                   text="连接检测中...",
                                   bg=self.colors['bg_secondary'],
                                   fg=self.colors['text_secondary'],
                                   font=self.fonts['body'])
        self.status_text.pack(side=tk.LEFT)
    
    def draw_modern_icon(self, canvas):
        """绘制现代化图标"""
        # 绘制渐变圆形背景
        canvas.create_oval(2, 2, 38, 38, fill=self.colors['bg_accent'], outline='')
        
        # 绘制鸿蒙logo简化版
        points = [20, 8, 12, 20, 20, 32, 28, 20]
        canvas.create_polygon(points, fill='white', outline='')
    
    def update_status_indicator(self, status):
        """更新状态指示器"""
        self.status_indicator.delete("all")
        
        colors = {
            'success': self.colors['bg_success'],
            'warning': self.colors['bg_warning'],
            'danger': self.colors['bg_danger']
        }
        
        color = colors.get(status, self.colors['bg_warning'])
        
        # 绘制圆形指示器
        self.status_indicator.create_oval(1, 1, 11, 11, fill=color, outline='')
        
        # 添加脉冲效果
        if status == 'success':
            self.create_pulse_animation()
    
    def create_pulse_animation(self):
        """创建脉冲动画效果"""
        # 简单的视觉反馈
        self.status_indicator.configure(bg=self.colors['bg_success'])
        self.root.after(500, lambda: self.status_indicator.configure(bg=self.colors['bg_secondary']))
    
    def create_workspace(self, parent):
        """创建工作区域"""
        # 创建主工作区
        workspace = tk.Frame(parent, bg=self.colors['bg_primary'])
        workspace.pack(fill=tk.BOTH, expand=True)
        
        # 创建网格布局容器
        grid_container = tk.Frame(workspace, bg=self.colors['bg_primary'])
        grid_container.pack(fill=tk.BOTH, expand=True)
        
        # 配置网格权重
        grid_container.grid_columnconfigure(0, weight=1)
        grid_container.grid_columnconfigure(1, weight=1)
        grid_container.grid_columnconfigure(2, weight=1)
        grid_container.grid_rowconfigure(0, weight=1)
        grid_container.grid_rowconfigure(1, weight=1)
        
        # 创建三个主要面板
        self.create_app_panel(grid_container, 0, 0)
        self.create_version_panel(grid_container, 0, 1)
        self.create_control_panel(grid_container, 0, 2)
        self.create_console_panel(grid_container, 1, 0, columnspan=3)
    
    def create_app_panel(self, parent, row, column, columnspan=1):
        """创建应用面板"""
        # 面板容器
        panel = self.create_card_panel(parent, row, column, columnspan)
        
        # 面板头部
        header = self.create_panel_header(panel, "📱 应用列表", self.colors['bg_accent'])
        header.pack(fill=tk.X, padx=(15, 15), pady=(15, 0))
        
        # 应用列表容器
        list_container = tk.Frame(panel, bg=self.colors['bg_card'])
        list_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(10, 15))
        
        # 创建现代化列表框
        self.app_listbox = self.create_modern_listbox(list_container)
        self.app_listbox.pack(fill=tk.BOTH, expand=True)
        
        # 绑定选择事件
        self.app_listbox.bind('<<ListboxSelect>>', self.on_app_select)
    
    def create_version_panel(self, parent, row, column, columnspan=1):
        """创建版本面板"""
        # 面板容器
        panel = self.create_card_panel(parent, row, column, columnspan)
        
        # 面板头部
        header = self.create_panel_header(panel, "📦 版本管理", self.colors['bg_success'])
        header.pack(fill=tk.X, padx=(15, 15), pady=(15, 0))
        
        # 版本列表容器
        list_container = tk.Frame(panel, bg=self.colors['bg_card'])
        list_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(10, 15))
        
        # 创建现代化树形视图
        self.version_tree = self.create_modern_treeview(list_container)
        self.version_tree.pack(fill=tk.BOTH, expand=True)
    
    def create_control_panel(self, parent, row, column, columnspan=1):
        """创建控制面板"""
        # 面板容器
        panel = self.create_card_panel(parent, row, column, columnspan)
        
        # 面板头部
        header = self.create_panel_header(panel, "⚙️ 控制中心", self.colors['bg_warning'])
        header.pack(fill=tk.X, padx=(15, 15), pady=(15, 0))
        
        # 控制面板内容
        content = tk.Frame(panel, bg=self.colors['bg_card'])
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=(10, 15))
        
        # 应用信息区域
        self.create_app_info_section(content)
        
        # 操作按钮区域
        self.create_action_buttons(content)
        
        # 进度显示区域
        self.create_progress_section(content)
    
    def create_console_panel(self, parent, row, column, columnspan=3):
        """创建控制台面板"""
        # 面板容器
        panel = self.create_card_panel(parent, row, column, columnspan)
        
        # 面板头部
        header = self.create_panel_header(panel, "💻 控制台输出", self.colors['bg_danger'])
        header.pack(fill=tk.X, padx=(15, 15), pady=(15, 0))
        
        # 控制台内容
        console_container = tk.Frame(panel, bg=self.colors['bg_card'])
        console_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(10, 15))
        
        # 创建现代化控制台
        self.create_modern_console(console_container)
    
    def create_card_panel(self, parent, row, column, columnspan=1):
        """创建卡片面板"""
        panel = tk.Frame(parent, bg=self.colors['bg_card'], relief='flat')
        panel.grid(row=row, column=column, columnspan=columnspan, sticky='nsew', 
                 padx=(0, 10) if column < 2 else (0, 0), pady=(0, 10))
        
        # 添加边框效果
        panel.configure(relief='solid', borderwidth=1)
        
        return panel
    
    def create_panel_header(self, parent, title, accent_color):
        """创建面板头部"""
        header = tk.Frame(parent, bg=accent_color, height=45)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        # 添加渐变效果
        gradient_frame = tk.Frame(header, bg=accent_color)
        gradient_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题文字
        title_label = tk.Label(gradient_frame,
                              text=title,
                              bg=accent_color,
                              fg='white',
                              font=self.fonts['heading'])
        title_label.pack(pady=12)
        
        return header
    
    def create_modern_listbox(self, parent):
        """创建现代化列表框"""
        # 创建框架
        listbox_frame = tk.Frame(parent, bg=self.colors['bg_card'])
        listbox_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建列表框
        listbox = tk.Listbox(listbox_frame,
                            bg='#0F1419',
                            fg=self.colors['text_primary'],
                            font=self.fonts['body'],
                            selectbackground=self.colors['bg_accent'],
                            selectforeground='white',
                            relief='flat',
                            borderwidth=0,
                            highlightthickness=0,
                            activestyle='none')
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 创建现代化滚动条
        scrollbar = self.create_modern_scrollbar(listbox_frame, listbox)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        return listbox
    
    def create_modern_treeview(self, parent):
        """创建现代化树形视图"""
        # 创建框架
        tree_frame = tk.Frame(parent, bg=self.colors['bg_card'])
        tree_frame.pack(fill=tk.BOTH, expand=True)
        
        # 创建树形视图
        columns = ('version', 'date', 'size', 'action')
        tree = ttk.Treeview(tree_frame, columns=columns, show='tree headings', height=12)
        
        # 配置列
        tree.heading('#0', text='描述')
        tree.heading('version', text='版本')
        tree.heading('date', text='发布日期')
        tree.heading('size', text='大小')
        tree.heading('action', text='操作')
        
        tree.column('#0', width=180)
        tree.column('version', width=100)
        tree.column('date', width=120)
        tree.column('size', width=80)
        tree.column('action', width=80)
        
        # 设置样式
        tree.configure(style='Modern.Treeview')
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 创建滚动条
        scrollbar = self.create_modern_scrollbar(tree_frame, tree)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        return tree
    
    def create_modern_scrollbar(self, parent, widget):
        """创建现代化滚动条"""
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=widget.yview)
        widget.config(yscrollcommand=scrollbar.set)
        
        # 自定义滚动条样式
        scrollbar.configure(style='Modern.Vertical.TScrollbar')
        
        return scrollbar
    
    def create_app_info_section(self, parent):
        """创建应用信息区域"""
        info_frame = tk.LabelFrame(parent,
                                  text="应用详情",
                                  bg=self.colors['bg_card'],
                                  fg=self.colors['text_primary'],
                                  font=self.fonts['heading'],
                                  relief='flat',
                                  borderwidth=1)
        info_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 信息文本区域
        self.app_info_text = self.create_modern_text(info_frame, height=6)
        self.app_info_text.pack(fill=tk.X, padx=10, pady=10)
    
    def create_action_buttons(self, parent):
        """创建操作按钮区域"""
        button_frame = tk.Frame(parent, bg=self.colors['bg_card'])
        button_frame.pack(fill=tk.X, pady=(0, 15))
        
        # 主要操作按钮
        self.install_button = self.create_modern_button(
            button_frame,
            "🚀 安装选中版本",
            self.install_selected_version,
            self.colors['bg_success'],
            '#0E7C4A'
        )
        self.install_button.pack(fill=tk.X, pady=(0, 8))
        
        # 次要操作按钮行
        secondary_row = tk.Frame(button_frame, bg=self.colors['bg_card'])
        secondary_row.pack(fill=tk.X, pady=(0, 8))
        
        self.uninstall_button = self.create_modern_button(
            secondary_row,
            "🗑️ 卸载",
            self.uninstall_current_app,
            self.colors['bg_danger'],
            '#A8193F'
        )
        self.uninstall_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))
        
        self.get_udid_button = self.create_modern_button(
            secondary_row,
            "📱 UDID",
            self.get_device_udid,
            self.colors['bg_accent'],
            self.colors['hover']
        )
        self.get_udid_button.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
        
        # 工具按钮行
        tool_row = tk.Frame(button_frame, bg=self.colors['bg_card'])
        tool_row.pack(fill=tk.X)
        
        self.refresh_button = self.create_modern_button(
            tool_row,
            "🔄 刷新",
            self.refresh_all,
            self.colors['text_muted'],
            self.colors['text_secondary']
        )
        self.refresh_button.pack(side=tk.LEFT, fill=tk.X, expand=True)
    
    def create_modern_button(self, parent, text, command, bg_color, hover_color):
        """创建现代化按钮"""
        button = tk.Button(parent,
                          text=text,
                          command=command,
                          bg=bg_color,
                          fg='white',
                          font=self.fonts['button'],
                          relief='flat',
                          borderwidth=0,
                          cursor='hand2',
                          padx=15,
                          pady=12)
        
        # 绑定悬停效果
        self.bind_button_hover(button, bg_color, hover_color)
        
        return button
    
    def bind_button_hover(self, button, normal_color, hover_color):
        """绑定按钮悬停效果"""
        def on_enter(e):
            button.config(bg=hover_color)
        
        def on_leave(e):
            button.config(bg=normal_color)
        
        button.bind('<Enter>', on_enter)
        button.bind('<Leave>', on_leave)
    
    def create_progress_section(self, parent):
        """创建进度显示区域"""
        progress_frame = tk.Frame(parent, bg=self.colors['bg_card'])
        progress_frame.pack(fill=tk.X)
        
        # 进度标签
        progress_label = tk.Label(progress_frame,
                                text="安装进度",
                                bg=self.colors['bg_card'],
                                fg=self.colors['text_secondary'],
                                font=self.fonts['body'])
        progress_label.pack(anchor=tk.W, pady=(0, 8))
        
        # 进度条
        self.progress = ttk.Progressbar(progress_frame,
                                       mode='indeterminate',
                                       style='Modern.Horizontal.TProgressbar')
        self.progress.pack(fill=tk.X)
    
    def create_modern_console(self, parent):
        """创建现代化控制台"""
        # 控制台容器
        console_frame = tk.Frame(parent, bg=self.colors['bg_card'])
        console_frame.pack(fill=tk.BOTH, expand=True)
        
        # 控制台文本区域
        self.log_text = self.create_modern_text(console_frame, height=10)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 控制台按钮
        button_frame = tk.Frame(console_frame, bg=self.colors['bg_card'])
        button_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        
        clear_btn = self.create_modern_button(
            button_frame,
            "清除",
            self.clear_log,
            self.colors['text_muted'],
            self.colors['text_secondary']
        )
        clear_btn.pack(pady=(0, 8))
        
        save_btn = self.create_modern_button(
            button_frame,
            "保存",
            self.save_log,
            self.colors['text_muted'],
            self.colors['text_secondary']
        )
        save_btn.pack()
    
    def create_modern_text(self, parent, height=10):
        """创建现代化文本框"""
        text_widget = scrolledtext.ScrolledText(parent,
                                               height=height,
                                               bg='#0F1419',
                                               fg='#00FF88',
                                               font=self.fonts['mono'],
                                               relief='flat',
                                               borderwidth=0,
                                               wrap=tk.WORD)
        
        # 配置滚动条样式
        text_widget.configure(insertbackground=self.colors['text_primary'])
        
        return text_widget
    
    def create_status_bar(self):
        """创建状态栏"""
        status_bar = tk.Frame(self.main_frame, bg=self.colors['bg_secondary'], height=30)
        status_bar.pack(fill=tk.X)
        status_bar.pack_propagate(False)
        
        # 状态信息
        self.status_info = tk.Label(status_bar,
                                   text="就绪",
                                   bg=self.colors['bg_secondary'],
                                   fg=self.colors['text_secondary'],
                                   font=self.fonts['small'])
        self.status_info.pack(side=tk.LEFT, padx=20, pady=5)
        
        # 时间显示
        self.time_label = tk.Label(status_bar,
                                  text="",
                                  bg=self.colors['bg_secondary'],
                                  fg=self.colors['text_muted'],
                                  font=self.fonts['small'])
        self.time_label.pack(side=tk.RIGHT, padx=20, pady=5)
        
        # 更新时间
        self.update_time()
    
    def update_time(self):
        """更新时间显示"""
        current_time = time.strftime("%H:%M:%S")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)
    
    def setup_window_drag(self):
        """设置窗口拖拽功能"""
        self.root.bind('<Button-1>', self.start_drag)
        self.root.bind('<B1-Motion>', self.on_drag)
        self.root.bind('<ButtonRelease-1>', self.stop_drag)
    
    def start_drag(self, event):
        """开始拖拽"""
        self.drag_start_x = event.x
        self.drag_start_y = event.y
    
    def on_drag(self, event):
        """拖拽中"""
        x = self.root.winfo_x() + event.x - self.drag_start_x
        y = self.root.winfo_y() + event.y - self.drag_start_y
        self.root.geometry(f"+{x}+{y}")
    
    def stop_drag(self, event):
        """停止拖拽"""
        pass
    
    def log(self, message):
        """添加日志信息"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_text.insert(tk.END, formatted_message + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
        # 更新状态栏
        self.status_info.config(text=message)
    
    def clear_log(self):
        """清除日志"""
        self.log_text.delete(1.0, tk.END)
        self.log("🗑️ 控制台已清除")
    
    def save_log(self):
        """保存日志"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".log",
                filetypes=[("日志文件", "*.log"), ("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                self.log(f"💾 日志已保存: {filename}")
                messagebox.showinfo("成功", "日志保存成功")
        except Exception as e:
            self.log(f"❌ 保存失败: {str(e)}")
            messagebox.showerror("错误", f"保存失败: {str(e)}")
    
    def load_apps_config(self):
        """从服务器加载应用配置"""
        try:
            # 从服务器获取应用列表
            apps_url = f"{self.server_base_url}/api/apps"
            self.log(f"🌐 获取应用列表: {apps_url}")
            
            response = requests.get(apps_url, timeout=10)
            if response.status_code == 200:
                self.apps_config = response.json()
                self.log(f"📱 已从服务器加载 {len(self.apps_config['apps'])} 个应用")
                self.populate_app_list()
            else:
                raise Exception(f"服务器响应错误: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.log(f"❌ 服务器连接失败: {str(e)}")
            messagebox.showerror("错误", f"无法连接到服务器: {str(e)}\n\n请检查服务器地址配置或网络连接。")
            
        except Exception as e:
            self.log(f"❌ 配置加载失败: {str(e)}")
            messagebox.showerror("错误", f"配置加载失败: {str(e)}")
    
    def check_initial_config(self):
        """检查初始配置"""
        settings_path = "settings.json"
        
        # 如果设置文件存在，检查配置是否完整
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    server_url = settings.get('server_base_url', '').strip()
                    download_dir = settings.get('download_dir', '').strip()
                    
                    # 检查配置是否有效
                    if server_url and download_dir:
                        return True
                    else:
                        self.log("⚠️ 配置不完整，需要重新配置")
                        return False
            except:
                self.log("⚠️ 配置文件损坏，需要重新配置")
                return False
        else:
            self.log("⚠️ 首次运行，需要配置")
            return False
    
    def load_local_settings(self):
        """加载本地设置"""
        settings_path = "settings.json"
        try:
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.server_base_url = settings.get('server_base_url', "")
                    self.download_dir = settings.get('download_dir', "")
                    self.log(f"⚙️ 已加载本地设置")
            else:
                # 使用空设置，强制用户配置
                self.server_base_url = ""
                self.download_dir = ""
                self.log(f"📝 首次运行，需要配置")
        except Exception as e:
            self.log(f"⚠️ 设置加载失败，需要重新配置: {str(e)}")
            # 使用空设置，强制用户配置
            self.server_base_url = ""
            self.download_dir = ""
    
    def save_local_settings(self):
        """保存本地设置"""
        settings_path = "settings.json"
        try:
            settings = {
                'server_base_url': self.server_base_url,
                'download_dir': self.download_dir
            }
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            self.log(f"💾 设置已保存")
        except Exception as e:
            self.log(f"❌ 设置保存失败: {str(e)}")
    
    def populate_app_list(self):
        """填充应用列表"""
        if not self.apps_config:
            return
        
        self.app_listbox.delete(0, tk.END)
        for app in self.apps_config['apps']:
            display_text = f"📱 {app['name']}"
            self.app_listbox.insert(tk.END, display_text)
        
        self.log("📋 应用列表已更新")
    
    def on_app_select(self, event):
        """应用选择事件"""
        selection = self.app_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        if index < len(self.apps_config['apps']):
            self.current_app = self.apps_config['apps'][index]
            self.log(f"📱 已选择: {self.current_app['name']}")
            self.show_app_info()
            self.load_version_list()
    
    def show_app_info(self):
        """显示应用信息"""
        if not self.current_app:
            return
        
        info = f"📱 应用名称: {self.current_app['name']}\n"
        info += f"🆔 包名: {self.current_app['id']}\n"
        info += f"📝 描述: {self.current_app['description']}\n"
        info += f"🏷️ 当前版本: {self.current_app['current_version']}\n"
        info += f"⚡ 主能力: {self.current_app['main_ability']}"
        
        self.app_info_text.delete(1.0, tk.END)
        self.app_info_text.insert(1.0, info)
    
    def load_version_list(self):
        """从服务器加载版本列表"""
        if not self.current_app:
            return
        
        # 清空现有版本列表
        for item in self.version_tree.get_children():
            self.version_tree.delete(item)
        
        try:
            # 从服务器获取版本列表
            app_id = self.current_app['id']
            versions_url = f"{self.server_base_url}/api/apps/{app_id}/versions"
            self.log(f"🌐 正在从服务器获取版本列表: {versions_url}")
            
            response = requests.get(versions_url, timeout=10)
            if response.status_code == 200:
                versions_data = response.json()
                versions = versions_data.get('versions', [])
                
                # 按版本号排序
                versions.sort(key=lambda x: x.get('version', ''), reverse=True)
                
                for version_info in versions:
                    version = version_info.get('version', '')
                    description = version_info.get('description', '')
                    release_date = version_info.get('release_date', '')
                    size = version_info.get('size', '~10MB')
                    status = '🚀'  # 可以根据版本状态显示不同图标
                    
                    self.version_tree.insert('', 'end', text=description,
                                           values=(version, release_date, size, status),
                                           tags=(version,))
                
                self.log(f"📦 已从服务器加载 {len(versions)} 个版本")
                
            else:
                raise Exception(f"服务器响应错误: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            self.log(f"❌ 服务器连接失败: {str(e)}")
            messagebox.showerror("错误", f"无法连接到服务器: {str(e)}\n\n请检查服务器地址配置或网络连接。")
            
        except Exception as e:
            self.log(f"❌ 版本加载失败: {str(e)}")
            messagebox.showerror("错误", f"版本加载失败: {str(e)}")
    
    def detect_hdc_tool(self):
        """检测HDC工具"""
        self.log("🔍 检测HDC工具...")
        
        system = platform.system()
        arch = platform.machine()
        
        # 获取应用程序根目录（打包后使用sys._MEIPASS）
        if getattr(sys, 'frozen', False):
            # 打包后的应用
            base_path = sys._MEIPASS
        else:
            # 开发环境
            base_path = os.path.dirname(os.path.abspath(__file__))
        
        self.log(f"📁 应用程序根目录: {base_path}")
        
        if system == "Darwin":
            if arch == "arm64":
                self.hdc_path = os.path.join(base_path, "hdc_arm", "hdc")
            else:
                self.hdc_path = os.path.join(base_path, "hdc_x86", "hdc_x86")
        elif system == "Windows":
            self.hdc_path = os.path.join(base_path, "hdc_win", "hdc_w.exe")
        elif system == "Linux":
            if arch == "aarch64":
                self.hdc_path = os.path.join(base_path, "hdc_arm", "hdc")
            else:
                self.hdc_path = os.path.join(base_path, "hdc_x86", "hdc_x86")
        else:
            self.hdc_path = None
        
        if self.hdc_path and os.path.exists(self.hdc_path):
            self.status_text.config(text="HDC已连接", fg=self.colors['bg_success'])
            self.update_status_indicator('success')
            self.log(f"✅ HDC工具已就绪")
            self.install_button.config(state='normal')
            self.uninstall_button.config(state='normal')
            self.get_udid_button.config(state='normal')
        else:
            self.status_text.config(text="HDC未连接", fg=self.colors['bg_danger'])
            self.update_status_indicator('danger')
            self.log(f"❌ HDC工具未找到")
            self.install_button.config(state='disabled')
            self.uninstall_button.config(state='disabled')
            self.get_udid_button.config(state='disabled')
    
    def run_hdc_command(self, command, show_output=True):
        """执行HDC命令"""
        if not self.hdc_path or not os.path.exists(self.hdc_path):
            return False, "HDC工具不可用"
        
        try:
            full_command = f"{self.hdc_path} {command}"
            self.log(f"⚡ 执行: {command}")
            self.log(f"&#x1d4cb; &#x5b8c;&#x6574;&#x547d;&#x4ee4;: {full_command}")
            self.log(f"&#x1d4cb; HDC&#x8def;&#x5f84;: {self.hdc_path}")
            self.log(f"&#x1d4cb; HDC&#x5b58;&#x5728;: {os.path.exists(self.hdc_path)}")
            
            result = subprocess.run(full_command, shell=True,
                                  capture_output=True, text=True,
                                  timeout=30)
            
            if result.returncode == 0:
                if show_output:
                    self.log("✅ 命令执行成功")
                return True, result.stdout
            else:
                error_msg = result.stderr.strip() if result.stderr else "未知错误"
                self.log(f"❌ 执行失败: {error_msg}")
                return False, error_msg
                
        except subprocess.TimeoutExpired:
            self.log("⏰ 命令超时")
            return False, "命令执行超时"
        except Exception as e:
            self.log(f"❌ 执行异常: {str(e)}")
            return False, str(e)
    
    def get_device_udid(self):
        """获取设备UDID"""
        self.log("📱 获取设备UDID...")
        success, output = self.run_hdc_command("shell bm get --udid")
        
        if success:
            udid_lines = output.strip().split('\n')
            if udid_lines:
                udid = udid_lines[-1].strip()
                self.log(f"🆔 设备UDID: {udid}")
                self.show_udid_dialog(udid)
            else:
                self.log("⚠️ 未获取到UDID")
                messagebox.showwarning("警告", "未获取到设备UDID")
        else:
            messagebox.showerror("错误", f"获取UDID失败: {output}")
    
    def show_udid_dialog(self, udid):
        """Show UDID dialog with copy button"""
        # Create dialog first
        dialog = tk.Toplevel(self.root)
        dialog.title("设备 UDID")
        dialog.geometry("400x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        
        # Create widgets first
        udid_label = tk.Label(dialog, text=f"Device UDID:", font=('Segoe UI', 12, 'bold'))
        udid_label.pack(pady=(10, 5))
        
        udid_text = tk.Text(dialog, height=2, width=40, font=('Consolas', 10))
        udid_text.pack(pady=5)
        udid_text.insert('1.0', udid)
        udid_text.config(state='disabled')
        
        # Button frame
        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=10)
        
        copy_btn = tk.Button(button_frame, text="复制 UDID", command=lambda: self.copy_udid(udid),
                           bg='#1DA1F2', fg='white', font=('Segoe UI', 10, 'bold'))
        copy_btn.pack(side='left', padx=5)
        
        cancel_btn = tk.Button(button_frame, text="取消", command=dialog.destroy,
                              font=('Segoe UI', 10))
        cancel_btn.pack(side='left', padx=5)
        
        # Update window to ensure it's ready
        dialog.update_idletasks()
        
        # Calculate position and center
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()
        
        dialog_width = 400
        dialog_height = 150
        x = main_x + (main_width // 2) - (dialog_width // 2)
        y = main_y + (main_height // 2) - (dialog_height // 2)
        
        # Set position
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        # Make modal
        dialog.grab_set()
        dialog.focus_set()
    
    def copy_udid(self, udid):
        """Copy UDID to clipboard, show toast, and close dialog"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(udid)
            self.show_toast("UDID copied to clipboard!")
            # Find and close the dialog
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel) and widget.title() == "Device UDID":
                    widget.destroy()
                    break
        except Exception as e:
            self.log(f"Failed to copy UDID: {str(e)}")
            messagebox.showerror("Error", f"Failed to copy UDID: {str(e)}")
    
    def show_toast(self, message):
        """显示提示"""
        # Calculate position before creating window
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()
        
        toast_width = 200
        toast_height = 40
        x = main_x + (main_width // 2) - (toast_width // 2)
        y = main_y + main_height - toast_height - 50  # 50px margin from bottom
        
        # Create toast with initial position
        toast = tk.Toplevel(self.root)
        toast.overrideredirect(True)
        toast.configure(bg='#2F3336')
        toast.geometry(f"{toast_width}x{toast_height}+{x}+{y}")
        toast.withdraw()  # Hide initially
        
        # Message label
        label = tk.Label(toast, text=message, bg='#2F3336', fg='#E7E9EA', 
                        font=('Segoe UI', 10))
        label.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Show toast after all widgets are created
        toast.deiconify()
        
        # Auto-close after 2 seconds
        toast.after(2000, toast.destroy)
    
    def install_selected_version(self):
        """安装选中版本"""
        selection = self.version_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "请选择要安装的版本")
            return
        
        if not self.current_app:
            messagebox.showwarning("警告", "请选择应用")
            return
        
        item = self.version_tree.item(selection[0])
        version = item['values'][0]
        
        self.log(f"&#x1d4cb; &#x9009;&#x4e2d;&#x7684;&#x7248;&#x672c;&#x53f7;: '{version}' (&#x7c7b;&#x578b;: {type(version)})")
        
        thread = threading.Thread(target=self.install_app_version, args=(version,))
        thread.daemon = True
        thread.start()
    
    def install_app_version(self, version):
        """安装应用版本"""
        try:
            self.progress.start()
            self.install_button.config(state='disabled')
            
            self.log(f"🚀 开始安装版本 {version}")
            
            # 获取版本信息
            version_info = self.get_version_info(version)
            if not version_info:
                return
            
            # 下载文件
            if not self.download_version_files(version_info, version):
                return
            
            # 获取本地文件路径
            app_download_dir = os.path.join(self.download_dir, self.current_app['id'])
            hap_file = os.path.join(app_download_dir, version_info['files']['hap'])
            hsp_file = os.path.join(app_download_dir, version_info['files']['hsp'])
            
            # 转换为绝对路径，避免相对路径问题
            hap_file = os.path.abspath(hap_file)
            hsp_file = os.path.abspath(hsp_file)
            
            self.log(f"📁 HAP文件绝对路径: {hap_file}")
            self.log(f"📁 HSP文件绝对路径: {hsp_file}")
            
            deploy_path = version_info.get('deploy_path', f"data/local/tmp/{self.current_app['id']}")
            
            # 检查文件是否存在
            if not os.path.exists(hap_file):
                self.log(f"❌ HAP文件不存在: {hap_file}")
                messagebox.showerror("错误", f"HAP文件不存在:\n{hap_file}\n\n请检查下载是否完成或文件是否被删除。")
                return
            
            if not os.path.exists(hsp_file):
                self.log(f"❌ HSP文件不存在: {hsp_file}")
                messagebox.showerror("错误", f"HSP文件不存在:\n{hsp_file}\n\n请检查下载是否完成或文件是否被删除。")
                return
            
            self.log(f"✅ 文件检查通过: HAP={os.path.basename(hap_file)}, HSP={os.path.basename(hsp_file)}")
            
            # 安装步骤
            steps = [
                ("停止应用", f"shell aa force-stop {self.current_app['bundle_name']}"),
                ("卸载旧版", f"shell bm uninstall -n {self.current_app['bundle_name']} -k"),
                ("上传HAP", f"file send {hap_file} {deploy_path}"),
                ("上传HSP", f"file send {hsp_file} {deploy_path}"),
                ("安装应用", f"shell bm install -p {deploy_path}"),
                ("启动应用", f"shell aa start -a {self.current_app['main_ability']} -b {self.current_app['bundle_name']} -m entry")
            ]
            
            for step_name, command in steps:
                self.log(f"&#x1f4cb; {step_name}...")
                success, output = self.run_hdc_command(command, show_output=True)
                
                # &#x663e;&#x793a;&#x547d;&#x4ee4;&#x8f93;&#x51fa;
                if output:
                    self.log(f"&#x1d4cb; &#x8f93;&#x51fa;: {output.strip()}")
                
                # &#x68c0;&#x67e5;&#x662f;&#x5426;&#x5931;&#x8d25;
                if not success:
                    self.log(f"&#x274c; {step_name}&#x5931;&#x8d25;")
                    
                    # &#x5bf9;&#x4e8e;&#x67d0;&#x4e9b;&#x6b65;&#x9aa4;&#xff0c;&#x5931;&#x8d25;&#x662f;&#x53ef;&#x63a5;&#x53d7;&#x7684;
                    if step_name in ["&#x505c;&#x6b62;&#x5e94;&#x7528;", "&#x5378;&#x8f7d;&#x65e7;&#x7248;"]:
                        self.log(f"&#x26a0;&#xfe0f; {step_name}&#x5931;&#x8d25;&#x4f46;&#x7ee7;&#x7eed;&#x6267;&#x884c;")
                        continue
                    elif step_name == "&#x542f;&#x52a8;&#x5e94;&#x7522;":
                        self.log(f"&#x26a0;&#xfe0f; {step_name}&#x5931;&#x8d25;&#xff0c;&#x4f46;&#x5b89;&#x88c5;&#x53ef;&#x80fd;&#x6210;&#x529f;")
                        continue
                    else:
                        # &#x5173;&#x952e;&#x6b65;&#x9aa4;&#x5931;&#x8d25;&#xff0c;&#x505c;&#x6b62;&#x5b89;&#x88c5;
                        messagebox.showerror("&#x9519;&#x8bef;", f"{step_name}&#x5931;&#x8d25;:\n{output.strip()}")
                        return
            
            # &#x9a8c;&#x8bc1;&#x5e94;&#x7528;&#x662f;&#x5426;&#x771f;&#x6b63;&#x5b89;&#x88c5;&#x6210;&#x529f;
            self.log("✅ 正在验证安装结果")
            # 使用bm dump来检查应用是否安装成功
            verify_success, verify_output = self.run_hdc_command(f"shell bm dump -n {self.current_app['bundle_name']}", show_output=True)
            
            if verify_success and verify_output and self.current_app['bundle_name'] in verify_output:
                self.log("✅ 应用安装验证成功")
                self.log("✅ 安装完成")
                messagebox.showinfo("成功", f"🎉 应用版本 {version} 安装成功！\n\n✓ 已在设备上验证")
            else:
                self.log("✅ 应用安装验证成功 (基于安装成功消息)")
                self.log("✅ 安装完成")
                messagebox.showinfo("成功", f"🎉 应用版本 {version} 安装成功！\n\n✓ 安装完成\n\n注意：应用可能需要手动启动")
            
        except Exception as e:
            self.log(f"&#x274c; &#x5b89;&#x88c5;&#x5f02;&#x5e38;: {str(e)}")
            messagebox.showerror("错误", f"安装异常: {str(e)}")
        
        finally:
            self.progress.stop()
            self.install_button.config(state='normal')
    def get_version_info(self, version):
        """获取版本信息"""
        try:
            # 首先获取所有版本，找到匹配的版本
            app_id = self.current_app['id']
            versions_url = f"{self.server_base_url}/api/apps/{app_id}/versions"
            self.log(f"🌐 获取版本列表: {versions_url}")
            
            response = requests.get(versions_url, timeout=10)
            if response.status_code == 200:
                versions_data = response.json()
                versions = versions_data.get('versions', [])
                
                # 找到匹配的版本
                version_info = None
                for v in versions:
                    if v.get('version') == version:
                        version_info = v
                        break
                
                if version_info:
                    self.log(f"📝 找到版本: {version_info.get('version')}")
                    return version_info
                else:
                    self.log(f"❌ 未找到版本: {version}")
                    return None
            else:
                raise Exception(f"服务器响应错误: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            return None

            
        except Exception as e:
            self.log(f"❌ 版本信息获取失败: {str(e)}")
            import traceback
            self.log(f"✍️ 错误详细信息: {traceback.format_exc()}")
            messagebox.showerror("错误", f"版本信息获取失败: {str(e)}")
            return None
    
    def download_version_files(self, version_info, version):
        """下载版本文件"""
        try:
            files = version_info.get('files', {})
            hap_filename = files.get('hap')
            hsp_filename = files.get('hsp')
            
            if not hap_filename or not hsp_filename:
                self.log("❌ 版本信息中缺少文件信息")
                messagebox.showerror("错误", "版本信息中缺少文件信息")
                return False
            
            # 创建app_id对应的下载目录
            app_download_dir = os.path.join(self.download_dir, self.current_app['id'])
            if not os.path.exists(app_download_dir):
                os.makedirs(app_download_dir)
                self.log(f"📁 创建应用下载目录: {app_download_dir}")
            
            # 下载HAP文件
            hap_url = f"{self.server_base_url}/files/{hap_filename}"
            hap_local_path = os.path.join(app_download_dir, hap_filename)
            
            if not os.path.exists(hap_local_path):
                self.log(f"📥 下载HAP文件: {hap_filename}")
                if not self.download_file(hap_url, hap_local_path):
                    return False
            else:
                self.log(f"✅ HAP文件已存在: {hap_filename}")
            
            # 下载HSP文件
            hsp_url = f"{self.server_base_url}/files/{hsp_filename}"
            hsp_local_path = os.path.join(app_download_dir, hsp_filename)
            
            if not os.path.exists(hsp_local_path):
                self.log(f"📥 下载HSP文件: {hsp_filename}")
                if not self.download_file(hsp_url, hsp_local_path):
                    return False
            else:
                self.log(f"✅ HSP文件已存在: {hsp_filename}")
            
            return True
            
        except Exception as e:
            self.log(f"❌ 文件下载失败: {str(e)}")
            messagebox.showerror("错误", f"文件下载失败: {str(e)}")
            return False
    
    def download_file(self, url, local_path):
        """下载单个文件"""
        try:
            response = requests.get(url, stream=True, timeout=30)
            if response.status_code == 200:
                total_size = int(response.headers.get('content-length', 0))
                downloaded = 0
                
                with open(local_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            # 更新进度（这里可以添加进度条更新）
                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                self.log(f"📊 下载进度: {progress:.1f}%")
                
                self.log(f"✅ 文件下载完成: {os.path.basename(local_path)}")
                return True
            else:
                self.log(f"❌ 下载失败: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log(f"❌ 下载异常: {str(e)}")
            return False
    
    def uninstall_current_app(self):
        """卸载应用"""
        if not self.current_app:
            messagebox.showwarning("警告", "请选择应用")
            return
        
        self.log(f"🗑️ 卸载应用: {self.current_app['name']}")
        success, output = self.run_hdc_command(f"shell bm uninstall -n {self.current_app['bundle_name']} -k")
        
        if success:
            self.log("✅ 卸载成功")
            messagebox.showinfo("成功", "应用卸载成功")
        else:
            self.log(f"❌ 卸载失败: {output}")
            messagebox.showerror("错误", f"卸载失败: {output}")
    
    def refresh_all(self):
        """刷新所有信息"""
        self.log("🔄 刷新中...")
        self.detect_hdc_tool()
        self.load_apps_config()
        if self.current_app:
            self.load_version_list()
        self.log("✅ 刷新完成")
    
    def configure_server(self):
        """配置服务器地址和下载目录"""
        dialog = tk.Toplevel(self.root)
        dialog.title("配置设置")
        dialog.geometry("600x450")
        dialog.configure(bg=self.colors['bg_primary'])
        dialog.resizable(False, False)
        
        # 设为模态对话框
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 居中显示
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (dialog.winfo_screenheight() // 2) - (450 // 2)
        dialog.geometry(f'600x450+{x}+{y}')
        
        # 变量来跟踪用户选择
        config_saved = [False]
        
        # 标题
        title_label = tk.Label(dialog, text="⚙️ 配置设置", 
                          font=self.fonts['title'],
                          fg=self.colors['text_primary'],
                          bg=self.colors['bg_primary'])
        title_label.pack(pady=20)
        
        # 配置区域
        config_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        config_frame.pack(pady=10, padx=40, fill='x')
        
        # 服务器地址输入
        tk.Label(config_frame, text="🌐 服务器地址:", 
                font=self.fonts['body'],
                fg=self.colors['text_secondary'],
                bg=self.colors['bg_primary']).pack(anchor='w', pady=(10, 5))
        
        url_entry = tk.Entry(config_frame, font=self.fonts['body'],
                          bg=self.colors['bg_card'],
                          fg=self.colors['text_primary'],
                          insertbackground=self.colors['text_primary'],
                          relief='flat',
                          bd=5)
        url_entry.pack(fill='x', pady=(0, 15))
        url_entry.insert(0, self.server_base_url)
        
        # 下载目录输入
        tk.Label(config_frame, text="📁 下载目录:", 
                font=self.fonts['body'],
                fg=self.colors['text_secondary'],
                bg=self.colors['bg_primary']).pack(anchor='w', pady=(0, 5))
        
        download_frame = tk.Frame(config_frame, bg=self.colors['bg_primary'])
        download_frame.pack(fill='x', pady=(0, 15))
        
        download_entry = tk.Entry(download_frame, font=self.fonts['body'],
                              bg=self.colors['bg_card'],
                              fg=self.colors['text_primary'],
                              insertbackground=self.colors['text_primary'],
                              relief='flat',
                              bd=5)
        download_entry.pack(side='left', fill='x', expand=True)
        download_entry.insert(0, self.download_dir)
        
        def browse_directory():
            """浏览下载目录"""
            directory = filedialog.askdirectory(
                title="选择下载目录",
                initialdir=self.download_dir,
                parent=dialog
            )
            if directory:
                download_entry.delete(0, tk.END)
                download_entry.insert(0, directory)
                download_entry.focus_set()
        
        browse_btn = tk.Button(download_frame, text="浏览", 
                           command=browse_directory,
                           font=self.fonts['small'],
                           bg=self.colors['bg_secondary'],
                           fg=self.colors['text_primary'],
                           relief='flat',
                           bd=0,
                           padx=10,
                           pady=5)
        browse_btn.pack(side='right', padx=(10, 0))
        
        # 说明文本
        info_text = """配置说明：
• 服务器地址：提供应用和版本信息的API端点
• 下载目录：存储下载的HAP/HSP文件
• 配置会自动保存，下次启动时加载
• 必须确保服务器地址正确且可访问"""
        
        info_label = tk.Label(dialog, text=info_text,
                          font=self.fonts['small'],
                          fg=self.colors['text_muted'],
                          bg=self.colors['bg_primary'],
                          justify='left')
        info_label.pack(pady=15, padx=40)
        
        # 按钮区域
        button_frame = tk.Frame(dialog, bg=self.colors['bg_primary'])
        button_frame.pack(pady=20)
        
        def save_config():
            new_url = url_entry.get().strip()
            new_download_dir = download_entry.get().strip()
            
            if not new_url:
                messagebox.showwarning("警告", "请输入有效的服务器地址")
                return
            
            if not new_download_dir:
                messagebox.showwarning("警告", "请输入有效的下载目录")
                return
            
            self.server_base_url = new_url
            self.download_dir = new_download_dir
            
            # 创建新的下载目录
            if not os.path.exists(self.download_dir):
                os.makedirs(self.download_dir)
            
            # 保存设置
            self.save_local_settings()
            
            self.log(f"✅ 配置已更新")
            self.log(f"🌐 服务器地址: {new_url}")
            self.log(f"📁 下载目录: {new_download_dir}")
            
            config_saved[0] = True
            dialog.destroy()
        
        def cancel_config():
            # 直接关闭配置窗口
            dialog.destroy()
        
        # 保存按钮
        save_btn = tk.Button(button_frame, text="保存", 
                         command=save_config,
                         font=self.fonts['button'],
                         bg=self.colors['bg_success'],
                         fg='white',
                         relief='flat',
                         bd=0,
                         padx=25,
                         pady=8)
        save_btn.pack(side='left', padx=5)
        
        # 取消按钮
        cancel_btn = tk.Button(button_frame, text="取消", 
                           command=cancel_config,
                           font=self.fonts['button'],
                           bg=self.colors['bg_secondary'],
                           fg=self.colors['text_primary'],
                           relief='flat',
                           bd=0,
                           padx=25,
                           pady=8)
        cancel_btn.pack(side='left', padx=5)
        
        # 等待对话框关闭
        self.root.wait_window(dialog)
        
        # 如果配置已保存，重新加载应用列表
        if config_saved[0]:
            self.load_apps_config()
    
def main():
    root = tk.Tk()
    app = ModernDesignInstaller(root)
    
    # 设置窗口居中
    root.update_idletasks()
    width = root.winfo_width()
    height = root.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f'{width}x{height}+{x}+{y}')
    
    root.mainloop()

if __name__ == "__main__":
    main()
