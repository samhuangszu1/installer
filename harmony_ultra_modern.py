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
from tkinter import ttk, filedialog
import tkinter.font as tkfont
import time
import json
import requests


class ModernDesignInstaller:
    def __init__(self, root):
        self.root = root
        # Don't set title or configure here - it's already set in main()
        # This prevents white screen flash during UI creation

        self.ui_scale = 1.0
        try:
            dpi = getattr(self.root, '_system_dpi', None)
            if dpi:
                self.ui_scale = float(dpi) / 96.0
        except Exception:
            self.ui_scale = 1.0

        self.system_dpi = 96.0
        try:
            self.system_dpi = float(getattr(self.root, '_system_dpi', None) or 0) or float(
                self.root.winfo_fpixels('1i'))
        except Exception:
            self.system_dpi = 96.0

        def _px(pt):
            try:
                px = float(pt) * (float(self.system_dpi) / 72.0)
                return -max(9, int(round(px)))
            except Exception:
                return -int(pt)

        # 现代化颜色方案
        self.colors = {
            'bg_primary': '#0B0F13',     # 更深邃的主背景
            'bg_secondary': '#15191C',   # 导航栏背景
            'bg_card': '#1C2126',        # 卡片背景
            'bg_accent': '#3A86B8',      # 统一强调/选中蓝（更偏灰、更低饱和）
            'bg_selection': '#2A2F33',   # 选中背景（中性浅灰，统一全客户端选中态）
            'bg_success': '#00BA7C',     # 成功绿 (更清爽)
            'bg_warning': '#F7931A',     # 警告橙
            'bg_danger': '#F4212E',      # 错误红 (高饱和)
            'text_primary': '#E7E9EA',   # 主要文字
            'text_secondary': '#71767B',  # 次要文字
            'text_muted': '#536471',     # 静音文字
            'border': '#2F3336',         # 边框色
            'hover': '#2F6F98',          # 悬停色（与蓝灰主色匹配）
            'shadow': '#000000'          # 阴影色
        }

        # 字体设置
        self.fonts = {
            'title': ('Segoe UI', _px(22), 'bold'),
            'subtitle': ('Segoe UI', _px(16), 'bold'),
            'heading': ('Segoe UI', _px(14), 'bold'),
            'body': ('Segoe UI', _px(11)),
            'small': ('Segoe UI', _px(9)),
            'mono': ('Consolas', _px(10)),
            'button': ('Segoe UI', _px(12), 'bold')
        }

        # 初始化变量
        self.hdc_path = None
        self.apps_config = None
        self.current_app = None
        self.current_version = None
        self.current_versions = []
        self._version_item_map = {}

        # 版本列表分页状态
        self._ver_page = 1
        self._ver_page_size = 20
        self._ver_has_more = True
        self._ver_loading = False
        self._ver_app_id = None

        self.control_panel_content = None
        self.header_segment_container = None
        self.header_frame = None
        self.header_status_container = None
        self.header_left_section = None
        self._header_align_after_id = None

        # 服务器配置
        self.server_base_url = ""  # 服务器地址
        self.download_dir = ""  # 下载目录
        self.api_key = ""  # API Key for SaaS authentication

        self._install_spinner_after_id = None
        self._install_spinner_idx = 0
        self._install_button_base_text = None

        # 创建自定义样式
        self.setup_custom_styles()

        # 创建界面
        self.create_modern_interface()

        try:
            self.log(
                f"UI: dpi={getattr(self.root, '_system_dpi', 'N/A')} "
                f"tk_scaling={self.root.tk.call('tk', 'scaling')} "
                f"ui_scale={getattr(self, 'ui_scale', 'N/A')}"
            )
        except Exception:
            pass

        # 延迟检测HDC工具（确保UI完全加载）
        self.root.after(100, self.detect_hdc_tool)

        # 加载配置（现在log_text已经创建）
        self.load_local_settings()

        # 创建下载目录（只有在配置有效时才创建）
        if self.download_dir and not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

        # 检查配置
        if not self.check_initial_config():
            # 强制弹出配置界面
            self.log("⚠️ 配置不完整，请先配置服务器和下载目录")
            # Delay the dialog to avoid white screen flicker
            self.root.after(200, self.show_initial_config_dialog)
            return

        # 加载配置（异步，避免在启动阶段阻塞 UI 导致停留在启动页）
        self.root.after(200, self.load_apps_list_async)

        # 设置窗口图标
        self._set_window_icon()

        # 添加窗口拖拽功能
        self.setup_window_drag()

    def _set_window_icon(self):
        try:
            if getattr(sys, 'frozen', False):
                # PyInstaller 打包环境
                base_path = sys._MEIPASS
            else:
                # 开发环境
                base_path = os.path.dirname(os.path.abspath(__file__))

            # 优先尝试PNG格式
            png_path = os.path.join(base_path, 'logo.png')

            # 尝试使用PNG图标（需要PIL库）
            if os.path.exists(png_path):
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(png_path)

                    # 确保图像有透明通道（RGBA）
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')

                    # 创建透明背景的PhotoImage
                    photo = ImageTk.PhotoImage(img)
                    self.root.iconphoto(True, photo)
                    # 保持引用防止垃圾回收
                    self.root._icon_photo = photo
                    return
                except Exception:
                    pass

        except Exception:
            pass

    def load_apps_list_async(self):
        """异步从服务器加载应用配置，避免阻塞 Tk 主线程"""
        try:
            apps_url = f"{self.server_base_url}/api/apps"
        except Exception:
            apps_url = None

        self.log(f"🌐 获取应用列表: {apps_url}")
        try:
            self.show_toast("应用加载中...")
        except Exception:
            pass

        def _worker():
            try:
                if not apps_url:
                    raise Exception("服务器地址无效")
                response = requests.get(apps_url, headers=self._get_api_headers(), timeout=10)
                if response.status_code == 401:
                    error_msg = 'API Key 无效或已过期'
                    try:
                        error_data = response.json()
                        if error_data.get('error'):
                            error_msg = error_data.get('error')
                    except Exception:
                        pass
                    return False, f"认证失败: {error_msg}\n\n请在设置中更新有效的 API Key。"
                if response.status_code != 200:
                    raise Exception(f"服务器响应错误: {response.status_code}")
                data = response.json()
                return True, data
            except requests.exceptions.RequestException as e:
                return False, f"无法连接到服务器: {str(e)}\n\n请检查服务器地址配置或网络连接。"
            except Exception as e:
                return False, f"配置加载失败: {str(e)}"

        def _on_done(ok, payload):
            if ok:
                try:
                    self.apps_config = payload
                    apps = (self.apps_config or {}).get('apps', [])
                    self.log(f"📱 已从服务器加载 {len(apps)} 个应用")
                    try:
                        self.show_toast("应用加载完成")
                    except Exception:
                        pass
                    self.populate_app_list()
                except Exception as e:
                    self.log(f"❌ 配置加载失败: {str(e)}")
                    self.show_error("错误", f"配置加载失败: {str(e)}")
            else:
                self.log(f"❌ 服务器连接失败: {payload}")
                try:
                    self.show_toast("应用加载失败")
                except Exception:
                    pass
                self.show_error("错误", str(payload))

        def _run():
            ok, payload = _worker()
            try:
                self.root.after(0, lambda: _on_done(ok, payload))
            except Exception:
                pass

        t = threading.Thread(target=_run, daemon=True)
        t.start()

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

        # Treeview 样式优化
        self.style.configure('Modern.Treeview',
                             background=self.colors['bg_card'],
                             foreground=self.colors['text_primary'],
                             fieldbackground=self.colors['bg_card'],
                             rowheight=40,
                             font=self.fonts['body'],
                             borderwidth=0,
                             relief='flat')
        self.style.map('Modern.Treeview',
                       background=[('selected', self.colors['bg_selection'])],
                       foreground=[('selected', self.colors['text_primary'])])

        heading_font = ('Segoe UI', 11, 'bold')
        pad_y = 4
        try:
            row_h = int(self.style.lookup(
                'Modern.Treeview', 'rowheight') or 40)
        except Exception:
            row_h = 40

        try:
            f = tkfont.Font(self.root, font=heading_font)
            linespace = int(f.metrics('linespace') or 0)
            if linespace > 0:
                # Heading height is affected by theme internals; using floor here often makes it slightly smaller.
                # Use rounding and then correct upwards to guarantee heading height >= rowheight.
                pad_y = max(0, int(round((row_h - linespace) / 2.0)))
                total_h = linespace + pad_y * 2
                if total_h < row_h:
                    # bump padding to eliminate off-by-1/-2 differences across DPI/theme
                    pad_y += int((row_h - total_h + 1) / 2)
        except Exception:
            pad_y = 4

        self.style.configure('Modern.Treeview.Heading',
                             background=self.colors['bg_secondary'],
                             foreground=self.colors['text_primary'],
                             font=heading_font,
                             padding=(6, pad_y),
                             borderwidth=0,
                             relief='flat')

        # 进一步降低原生边框/分隔线存在感
        self.style.configure('Modern.Treeview',
                             bordercolor=self.colors['bg_card'],
                             lightcolor=self.colors['bg_card'],
                             darkcolor=self.colors['bg_card'])
        self.style.map('Modern.Treeview.Heading',
                       background=[('active', self.colors['bg_secondary'])],
                       foreground=[('active', self.colors['text_primary'])])

        # 滚动条样式
        self.style.configure('Modern.Vertical.TScrollbar',
                             background=self.colors['border'],
                             troughcolor=self.colors['bg_card'],
                             bordercolor=self.colors['bg_card'],
                             lightcolor=self.colors['border'],
                             darkcolor=self.colors['border'],
                             arrowcolor=self.colors['text_secondary'],
                             borderwidth=0,
                             arrowsize=12)
        self.style.map('Modern.Vertical.TScrollbar',
                       background=[('active', self.colors['border']),
                                   ('pressed', self.colors['border'])],
                       arrowcolor=[('active', self.colors['text_secondary']), ('pressed', self.colors['text_secondary'])])

    def create_modern_interface(self):
        """创建现代化界面"""
        # 主容器
        self.main_frame = tk.Frame(self.root, bg=self.colors['bg_primary'])
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 创建顶部导航栏
        self.create_header_bar()

        # 创建主要内容区域
        content_container = tk.Frame(
            self.main_frame, bg=self.colors['bg_primary'])
        content_container.pack(fill=tk.BOTH, expand=True,
                               padx=20, pady=(20, 20))

        # 创建工作区域
        self.create_workspace(content_container)

        # 创建底部状态栏
        self.create_status_bar()

    def create_header_bar(self):
        """创建顶部导航栏"""
        header_h = 70
        try:
            header_h = int(round(70 * float(getattr(self, 'ui_scale', 1.0))))
        except Exception:
            header_h = 70

        header = tk.Frame(
            self.main_frame, bg=self.colors['bg_secondary'], height=header_h)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        self.header_frame = header

        # 左侧标题区域
        left_section = tk.Frame(header, bg=self.colors['bg_secondary'])
        left_section.pack(side=tk.LEFT, fill=tk.Y, padx=20)
        self.header_left_section = left_section

        # 应用图标和标题
        title_container = tk.Frame(
            left_section, bg=self.colors['bg_secondary'])
        title_container.pack(expand=True)
        title_container.grid_columnconfigure(1, weight=1)

        # 创建圆形图标
        icon_sz = 40
        try:
            icon_sz = int(round(40 * float(getattr(self, 'ui_scale', 1.0))))
        except Exception:
            icon_sz = 40

        icon_canvas = tk.Canvas(title_container, width=icon_sz, height=icon_sz,
                                bg=self.colors['bg_secondary'], highlightthickness=0)
        icon_canvas.grid(row=0, column=0, padx=(0, 15), sticky='w')
        self.draw_modern_icon(icon_canvas)

        # 标题文字
        title_text = tk.Label(title_container,
                              text="鸿蒙应用安装助手",
                              bg=self.colors['bg_secondary'],
                              fg=self.colors['text_primary'],
                              font=self.fonts['title'])
        title_text.grid(row=0, column=1, sticky='w')

        segment_container = tk.Frame(header, bg=self.colors['bg_secondary'])
        self.header_segment_container = segment_container

        # Create rounded segment background using Canvas
        try:
            seg_total_w = int(
                round(240 * float(getattr(self, 'ui_scale', 1.0))))
        except Exception:
            seg_total_w = 240
        try:
            seg_h = int(round(32 * float(getattr(self, 'ui_scale', 1.0))))
        except Exception:
            seg_h = 32

        try:
            seg_y = max(0, int((header_h - seg_h) / 2))
        except Exception:
            seg_y = 19

        # segment_container 初始放在屏幕外(x=-1000)，但 y 坐标提前定死防止跳动
        segment_container.place(x=-1000, y=seg_y)

        segment_canvas = tk.Canvas(segment_container, bg=self.colors['bg_secondary'],
                                   highlightthickness=0, width=seg_total_w, height=seg_h)
        segment_canvas.pack()

        segment_bg_color = self.colors['bg_selection']
        segment_border = self.colors['border']
        segment_active_bg = self.colors['hover']
        segment_active_fg = self.colors['bg_accent']
        segment_sep = '#4B5258'

        # Draw rounded rectangle background using arcs and rectangle
        # 关键：不留左右边距，否则会露出 Canvas 背景（表现为左右黑块）
        bg_y0 = 0
        bg_y1 = seg_h
        bg_r = max(8, int(round(12 * float(getattr(self, 'ui_scale', 1.0)))))
        segment_canvas.create_oval(
            0, bg_y0, bg_r * 2, bg_y1, fill=segment_bg_color, outline='')
        segment_canvas.create_oval(
            seg_total_w - bg_r * 2, bg_y0, seg_total_w, bg_y1, fill=segment_bg_color, outline='')
        segment_canvas.create_rectangle(
            bg_r, bg_y0, seg_total_w - bg_r, bg_y1, fill=segment_bg_color, outline='')

        seg_w1 = seg_total_w // 3
        seg_w2 = seg_total_w // 3
        seg_w3 = seg_total_w - seg_w1 - seg_w2
        seg_x0 = 0
        seg_y0 = 0
        seg_x1 = seg_x0 + seg_w1
        seg_x2 = seg_x1 + seg_w2
        seg_x3 = seg_x0 + seg_total_w

        def _show_hl(tag):
            segment_canvas.itemconfigure('hl1', state='hidden')
            segment_canvas.itemconfigure('hl2', state='hidden')
            segment_canvas.itemconfigure('hl3', state='hidden')
            segment_canvas.itemconfigure(tag, state='normal')

        def _hide_hl():
            segment_canvas.itemconfigure('hl1', state='hidden')
            segment_canvas.itemconfigure('hl2', state='hidden')
            segment_canvas.itemconfigure('hl3', state='hidden')

        # left highlight (rounded left corners) - 必须严格限制在第 1 段
        hl_r = seg_h // 2
        segment_canvas.create_oval(seg_x0, seg_y0, seg_x0 + hl_r * 2, seg_y0 + seg_h,
                                   fill=segment_active_bg, outline='', tags=('hl1',))
        segment_canvas.create_rectangle(seg_x0 + hl_r, seg_y0, seg_x1, seg_y0 + seg_h,
                                        fill=segment_active_bg, outline='', tags=('hl1',))

        # middle highlight (rectangle)
        segment_canvas.create_rectangle(seg_x1, seg_y0, seg_x2, seg_y0 + seg_h,
                                        fill=segment_active_bg, outline='', tags=('hl2',))

        # right highlight (rounded right corners) - 必须严格限制在第 3 段
        segment_canvas.create_oval(seg_x3 - hl_r * 2, seg_y0, seg_x3, seg_y0 + seg_h,
                                   fill=segment_active_bg, outline='', tags=('hl3',))
        segment_canvas.create_rectangle(seg_x2, seg_y0, seg_x3 - hl_r, seg_y0 + seg_h,
                                        fill=segment_active_bg, outline='', tags=('hl3',))

        _hide_hl()

        # clickable areas
        segment_canvas.create_rectangle(
            seg_x0, seg_y0, seg_x1, seg_y0 + seg_h, fill='', outline='', tags=('seg1',))
        segment_canvas.create_rectangle(
            seg_x1, seg_y0, seg_x2, seg_y0 + seg_h, fill='', outline='', tags=('seg2',))
        segment_canvas.create_rectangle(
            seg_x2, seg_y0, seg_x3, seg_y0 + seg_h, fill='', outline='', tags=('seg3',))

        # text
        seg_font_size = 9
        try:
            if isinstance(getattr(self, 'fonts', None), dict) and 'small' in self.fonts:
                seg_font_size = int(self.fonts['small'][1])
        except Exception:
            seg_font_size = 9
        seg_font = ('Segoe UI', seg_font_size, 'bold')

        segment_canvas.create_text((seg_x0 + seg_x1) / 2, seg_y0 + seg_h / 2, text='设备ID',
                                   fill=self.colors['text_primary'], font=seg_font, tags=('seg1',))
        segment_canvas.create_text((seg_x1 + seg_x2) / 2, seg_y0 + seg_h / 2, text='刷新',
                                   fill=self.colors['text_primary'], font=seg_font, tags=('seg2',))
        segment_canvas.create_text((seg_x2 + seg_x3) / 2, seg_y0 + seg_h / 2, text='设置',
                                   fill=self.colors['text_primary'], font=seg_font, tags=('seg3',))

        # separators (increase contrast)
        segment_canvas.create_line(
            seg_x1, seg_y0 + 5, seg_x1, seg_y0 + seg_h - 5, fill=segment_sep, width=1)
        segment_canvas.create_line(
            seg_x2, seg_y0 + 5, seg_x2, seg_y0 + seg_h - 5, fill=segment_sep, width=1)

        def _bind_segment(tag, hl_tag, command):
            segment_canvas.tag_bind(tag, '<Enter>', lambda e: _show_hl(hl_tag))
            segment_canvas.tag_bind(tag, '<Leave>', lambda e: _hide_hl())
            segment_canvas.tag_bind(tag, '<Button-1>', lambda e: command())
            segment_canvas.tag_bind(
                tag, '<ButtonRelease-1>', lambda e: _hide_hl())

        _bind_segment('seg1', 'hl1', self.get_device_udid)
        _bind_segment('seg2', 'hl2', self.refresh_all)
        _bind_segment('seg3', 'hl3', self.configure_server)

        # HDC状态指示器（初始放在屏幕外(x=-1000)，y 坐标定死防止跳动）
        status_container = tk.Frame(header, bg=self.colors['bg_secondary'])
        self.header_status_container = status_container

        # 预计算 status_y
        try:
            status_h = 24  # 预估高度
            status_y = max(0, int((header_h - status_h) / 2))
        except Exception:
            status_y = 23

        # Fix logic error where status_container was placed before status_y was defined
        status_container.place(x=-1000, y=status_y)

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

        self.root.bind(
            '<Configure>', self.schedule_header_segment_align, add=True)
        self.schedule_header_segment_align()

    def schedule_header_segment_align(self, *_):
        if self._header_align_after_id is not None:
            try:
                self.root.after_cancel(self._header_align_after_id)
            except Exception:
                pass
        self._header_align_after_id = self.root.after(
            30, self.align_header_segment)

    def align_header_segment(self):
        self._header_align_after_id = None
        if self.header_frame is None or self.header_segment_container is None or self.control_panel_content is None or self.header_status_container is None:
            return
        if not self.header_frame.winfo_ismapped() or not self.control_panel_content.winfo_ismapped():
            self.schedule_header_segment_align()
            return

        try:
            self.header_frame.update_idletasks()
            self.header_segment_container.update_idletasks()
            self.control_panel_content.update_idletasks()
            self.header_status_container.update_idletasks()

            # 对齐基准：优先使用控制中心卡片面板外框，避免内容区 padx 造成视觉偏移
            control_ref = getattr(
                self, 'control_panel_frame', None) or self.control_panel_content
            if control_ref is not None:
                control_ref.update_idletasks()
            control_right = control_ref.winfo_rootx() + control_ref.winfo_width()
            header_left = self.header_frame.winfo_rootx()

            seg_w = self.header_segment_container.winfo_width()
            if seg_w <= 1:
                seg_w = self.header_segment_container.winfo_reqwidth()

            status_w = self.header_status_container.winfo_width()
            if status_w <= 1:
                status_w = self.header_status_container.winfo_reqwidth()

            header_h = self.header_frame.winfo_height()
            seg_h = self.header_segment_container.winfo_height(
            ) or self.header_segment_container.winfo_reqheight()
            status_h = self.header_status_container.winfo_height(
            ) or self.header_status_container.winfo_reqheight()
            seg_y = max(0, int((header_h - seg_h) / 2))
            status_y = max(0, int((header_h - status_h) / 2))

            # 视觉补偿：segment Canvas 圆角背景左右各内缩约 2px，补偿后视觉右边缘更贴齐
            try:
                visual_right_offset = int(
                    round(2 * float(getattr(self, 'ui_scale', 1.0))))
            except Exception:
                visual_right_offset = 2
            # 初始对齐标志
            if not hasattr(self, '_first_align_done'):
                self._first_align_done = False

            # 只有在计算出有效坐标后才放置
            x = int(control_right - header_left - seg_w + visual_right_offset)
            if x >= 0:
                self._first_align_done = True
                self.header_segment_container.place(x=x, y=seg_y)
                self.header_status_container.place(
                    x=x - 14 - status_w, y=status_y)

            # 防止覆盖左侧标题
            left_limit = 0
            if self.header_left_section is not None and self.header_left_section.winfo_ismapped():
                try:
                    pad = int(round(12 * float(getattr(self, 'ui_scale', 1.0))))
                except Exception:
                    pad = 12
                left_limit = (self.header_left_section.winfo_rootx(
                ) + self.header_left_section.winfo_width()) - header_left + pad

            if status_x < left_limit:
                status_x = left_limit

            # 如果 status 太宽导致和 segment 重叠，则让 status 靠左极限，segment 仍保持右对齐
            if status_x + status_w + gap > x:
                status_x = max(left_limit, x - gap - status_w)

            self.header_segment_container.place_configure(x=x, y=seg_y)
            self.header_status_container.place_configure(
                x=status_x, y=status_y)

            self.header_segment_container.lift()
            self.header_status_container.lift()
        except Exception:
            self.schedule_header_segment_align()

    def draw_modern_icon(self, canvas):
        """显示 logo.ico 图标"""
        try:
            canvas.update_idletasks()
        except Exception:
            pass

        try:
            w = int(canvas.winfo_width())
            h = int(canvas.winfo_height())
        except Exception:
            w, h = 40, 40

        if w <= 1 or h <= 1:
            w, h = 40, 40

        # 加载 logo.ico 文件
        try:
            import os
            import sys
            from PIL import Image, ImageTk

            # 获取图标路径（兼容打包环境）
            if getattr(sys, 'frozen', False):
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))

            icon_path = os.path.join(base_path, "logo.ico")

            if os.path.exists(icon_path):
                # 加载并调整图标大小
                img = Image.open(icon_path)
                img = img.resize((w-4, h-4), Image.Resampling.LANCZOS)

                # 创建圆形遮罩（使用抗锯齿）
                size = min(w-4, h-4)
                # 创建更大的遮罩用于抗锯齿
                mask_size = size * 2
                mask = Image.new('L', (mask_size, mask_size), 0)
                from PIL import ImageDraw
                draw = ImageDraw.Draw(mask)
                # 在更大的画布上绘制圆形，然后缩小以获得抗锯齿效果
                draw.ellipse((2, 2, mask_size-2, mask_size-2), fill=255)
                mask = mask.resize((size, size), Image.Resampling.LANCZOS)

                # 创建圆形背景
                circular_img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
                circular_img.paste(img.resize(
                    (size, size), Image.Resampling.LANCZOS), (0, 0), mask)

                photo = ImageTk.PhotoImage(circular_img)

                # 清空画布并显示圆形图标
                canvas.delete("all")
                canvas.create_image(w//2, h//2, image=photo, anchor='center')

                # 保持引用防止垃圾回收
                canvas.image = photo
                return
        except Exception:
            # 如果加载失败，使用备用方案
            pass

        # 备用方案：绘制简单的圆形图标
        canvas.delete("all")
        size = min(w, h)
        margin = max(2, int(round(size * 0.05)))
        x0 = int((w - size) / 2) + margin
        y0 = int((h - size) / 2) + margin
        x1 = x0 + size - margin * 2
        y1 = y0 + size - margin * 2

        # 绘制渐变圆形背景
        canvas.create_oval(
            x0, y0, x1, y1, fill=self.colors['bg_accent'], outline='')

        # 绘制鸿蒙logo简化版
        cx = int((x0 + x1) / 2)
        cy = int((y0 + y1) / 2)
        top = int(round(y0 + (y1 - y0) * 0.18))
        bottom = int(round(y0 + (y1 - y0) * 0.82))
        left = int(round(x0 + (x1 - x0) * 0.24))
        right = int(round(x0 + (x1 - x0) * 0.76))

        points = [
            cx, top,
            left, cy,
            cx, bottom,
            right, cy,
        ]
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
        self.root.after(500, lambda: self.status_indicator.configure(
            bg=self.colors['bg_secondary']))

    def create_workspace(self, parent):
        """创建工作区域"""
        # 创建主工作区
        workspace = tk.Frame(parent, bg=self.colors['bg_primary'])
        workspace.pack(fill=tk.BOTH, expand=True)

        # 创建网格布局容器
        grid_container = tk.Frame(workspace, bg=self.colors['bg_primary'])
        grid_container.pack(fill=tk.BOTH, expand=True)

        # 配置网格权重
        grid_container.grid_columnconfigure(
            0, weight=10, uniform='main_panels')
        grid_container.grid_columnconfigure(
            1, weight=21, uniform='main_panels')
        grid_container.grid_columnconfigure(
            2, weight=10, uniform='main_panels')
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
        header = self.create_panel_header(
            panel, "应用列表", self.colors['bg_accent'])
        header.pack(fill=tk.X, padx=(15, 15), pady=(15, 10))

        # 应用列表容器
        list_container = tk.Frame(panel, bg=self.colors['bg_card'])
        list_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        # 创建应用列表（使用 Treeview 以精确控制行高，与版本列表一致）
        self.app_tree = self.create_modern_app_treeview(list_container)
        try:
            # Treeview and scrollbar are packed inside its own container
            self.app_tree._container.pack(fill=tk.BOTH, expand=True)
        except Exception:
            pass

        # 绑定选择事件
        self.app_tree.bind('<<TreeviewSelect>>', self.on_app_select)

    def create_version_panel(self, parent, row, column, columnspan=1):
        """创建版本面板"""
        # 面板容器
        panel = self.create_card_panel(parent, row, column, columnspan)

        # 面板头部
        header = self.create_panel_header(
            panel, "版本列表", self.colors['bg_success'])
        header.pack(fill=tk.X, padx=(15, 15), pady=(15, 10))

        # 版本列表容器
        list_container = tk.Frame(panel, bg=self.colors['bg_card'])
        list_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        # 创建现代化树形视图
        self.version_tree = self.create_modern_treeview(list_container)
        try:
            # Treeview and scrollbar are packed inside its own container
            self.version_tree._container.pack(fill=tk.BOTH, expand=True)
        except Exception:
            pass

        # 绑定选择事件
        self.version_tree.bind('<<TreeviewSelect>>', self.on_version_select)

    def create_control_panel(self, parent, row, column, columnspan=1):
        """创建控制面板"""
        # 面板容器
        panel = self.create_card_panel(parent, row, column, columnspan)
        self.control_panel_frame = panel

        # 面板头部
        header = self.create_panel_header(
            panel, "版本详情", self.colors['bg_warning'])
        header.pack(fill=tk.X, padx=(15, 15), pady=(15, 10))

        # 控制面板内容
        content = tk.Frame(panel, bg=self.colors['bg_card'])
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))

        self.control_panel_content = content
        self.schedule_header_segment_align()

        self.create_app_info_section(content)

        # 操作按钮区域
        self.create_action_buttons(content)

    def create_console_panel(self, parent, row, column, columnspan=3):
        """创建控制台面板"""
        panel = tk.Frame(parent, bg=self.colors['bg_card'], relief='flat')
        panel.grid(row=row, column=column, columnspan=columnspan, sticky='nsew',
                   padx=(0, 0), pady=(0, 10))

        panel.configure(highlightbackground='#2F3336', highlightthickness=1)

        # 面板头部
        header = self.create_panel_header(
            panel, "💻 控制台输出", self.colors['bg_danger'])
        header.pack(fill=tk.X, padx=(15, 15), pady=(15, 10))

        # 控制台内容 - 统一内边距
        console_container = tk.Frame(panel, bg=self.colors['bg_card'])
        console_container.pack(fill=tk.BOTH, expand=True,
                               padx=15, pady=(0, 15))

        # 创建现代化控制台
        self.create_modern_console(console_container)

    def create_card_panel(self, parent, row, column, columnspan=1):
        """创建卡片面板"""
        panel = tk.Frame(parent, bg=self.colors['bg_card'], relief='flat')
        # 最后一列(版本详情)不设右边距，确保对齐底部的控制台右边缘
        right_pad = 10 if column < 2 else 0
        panel.grid(row=row, column=column, columnspan=columnspan, sticky='nsew',
                   padx=(0, right_pad), pady=(0, 10))

        # 优化边框：使用更微妙的颜色和更薄的边框
        panel.configure(highlightbackground='#2F3336', highlightthickness=1)

        return panel

    def create_panel_header(self, parent, title, accent_color):
        """创建面板头部"""
        header = tk.Frame(parent, bg=self.colors['bg_card'])
        header.pack(fill=tk.X)

        # Scheme 1: 以旧版 4/40 为本机视觉基准，但在高 DPI/大字体下
        # 根据标题字体真实高度自动增高，避免固定 40 导致“很挤”。
        accent_bar = tk.Frame(header, bg=accent_color, height=4)
        accent_bar.pack(fill=tk.X)
        accent_bar.pack_propagate(False)

        title_row = tk.Frame(header, bg=self.colors['bg_card'], height=40)
        title_row.pack(fill=tk.X)

        title_label = tk.Label(title_row,
                               text=title,
                               bg=self.colors['bg_card'],
                               fg=self.colors['text_primary'],
                               font=self.fonts['heading'])
        title_label.pack(side=tk.LEFT, padx=0)

        ui_scale = 1.0
        try:
            ui_scale = float(getattr(self, 'ui_scale', 1.0))
        except Exception:
            ui_scale = 1.0

        try:
            title_row.update_idletasks()
            label_h = int(title_label.winfo_reqheight() or 0)
        except Exception:
            label_h = 0

        # 给标题留一点上下缓冲（随 ui_scale 增大），但保持本机旧版的紧凑观感
        min_pad = 2
        try:
            min_pad = max(2, int(round(2 * ui_scale)))
        except Exception:
            min_pad = 2

        title_row_h = 40
        if label_h > 0:
            title_row_h = max(40, label_h + min_pad * 2)

        title_row.configure(height=title_row_h)
        title_row.pack_propagate(False)

        # 色条以旧版 4px 为基准；只有当标题行明显变高时再轻微加粗
        bar_h = 4
        try:
            if title_row_h > 45:
                bar_h = max(4, int(round(4 * (float(title_row_h) / 40.0))))
        except Exception:
            bar_h = 4
        try:
            accent_bar.configure(height=bar_h)
        except Exception:
            pass

        return header

    def create_modern_listbox(self, parent):
        """创建现代化列表框"""
        # 创建框架
        listbox_frame = tk.Frame(parent, bg=self.colors['bg_card'])
        listbox_frame.pack(fill=tk.BOTH, expand=True)

        # 创建列表框
        listbox = tk.Listbox(listbox_frame,
                             bg=self.colors['bg_primary'],
                             fg=self.colors['text_primary'],
                             font=self.fonts['body'],
                             selectbackground=self.colors['bg_selection'],
                             selectforeground=self.colors['text_primary'],
                             relief='flat',
                             borderwidth=0,
                             highlightthickness=0,
                             activestyle='none')
        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 创建现代化滚动条
        scrollbar = self.create_modern_scrollbar(listbox_frame, listbox)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        return listbox

    def create_modern_app_treeview(self, parent):
        """创建应用列表 Treeview（单列，无表头，行高与版本列表一致）"""
        tree_frame = tk.Frame(parent, bg=self.colors['bg_card'])
        # packed by caller via tree._container

        tree = ttk.Treeview(tree_frame, columns=(),
                            show='tree', selectmode='browse', height=12)
        tree.configure(style='Modern.Treeview')

        tree.column('#0', width=220, anchor='w')

        tree.tag_configure('odd', background=self.colors['bg_card'])
        tree.tag_configure('even', background=self.colors['bg_secondary'])

        # 先 pack 滚动条
        scrollbar = self.create_modern_scrollbar(tree_frame, tree)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 再 pack Treeview
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        try:
            tree._container = tree_frame
            tree._vscrollbar = scrollbar
            scrollbar.lift()
        except Exception:
            pass

        return tree

    def create_modern_treeview(self, parent):
        """创建现代化树形视图"""
        # 创建框架
        tree_frame = tk.Frame(parent, bg=self.colors['bg_card'])
        # packed by caller via tree._container

        # 创建树形视图
        columns = ('version', 'date', 'action')
        tree = ttk.Treeview(tree_frame, columns=columns,
                            show='tree headings', height=12)

        # 配置列
        tree.heading('#0', text='描述', anchor='w')
        tree.heading('version', text='版本', anchor='center')
        tree.heading('date', text='发布日期', anchor='center')
        tree.heading('action', text='操作', anchor='center')

        tree.column('#0', width=240, anchor='w')
        tree.column('version', width=120, anchor='center')
        tree.column('date', width=160, anchor='center')
        tree.column('action', width=70, anchor='center')

        # 设置样式
        tree.configure(style='Modern.Treeview')

        # 斑马纹：增强行与字段的视觉区分
        tree.tag_configure('odd', background=self.colors['bg_card'])
        tree.tag_configure('even', background=self.colors['bg_secondary'])

        def forward_mouse_event_to_tree(event, sequence):
            try:
                x = tree.winfo_pointerx() - tree.winfo_rootx()
                y = tree.winfo_pointery() - tree.winfo_rooty()
                tree.event_generate(sequence, x=x, y=y)
            except Exception:
                pass

        def update_column_separators(*_):
            if not tree.winfo_ismapped():
                tree.after(50, update_column_separators)
                return

            separators = getattr(tree, '_col_separators', None)
            if not separators:
                separators = []
                tree._col_separators = separators

            if not hasattr(tree, '_separator_color'):
                tree._separator_color = self.colors['border']

            sep_color = tree._separator_color

            needed = 3
            while len(separators) < needed:
                # 分隔线挂在 tree_frame 上（覆盖层），避免 Treeview 选中重绘影响竖线观感
                sep = tk.Frame(tree_frame, bg=sep_color, width=1)
                sep.bind(
                    '<ButtonPress-1>', lambda e: forward_mouse_event_to_tree(e, '<ButtonPress-1>'), add=True)
                sep.bind(
                    '<B1-Motion>', lambda e: forward_mouse_event_to_tree(e, '<B1-Motion>'), add=True)
                sep.bind('<ButtonRelease-1>', lambda e: forward_mouse_event_to_tree(e,
                         '<ButtonRelease-1>'), add=True)
                sep.bind('<MouseWheel>', lambda e: forward_mouse_event_to_tree(
                    e, '<MouseWheel>'), add=True)
                sep.place_forget()
                separators.append(sep)

            for sep in separators:
                if str(sep.cget('bg')) != str(sep_color):
                    sep.configure(bg=sep_color)

            # 列边界（不包含最后一列）
            x_positions = []
            try:
                base_x = tree.winfo_x()
                x = base_x + int(tree.column('#0', 'width'))
                x_positions.append(x)

                x += int(tree.column('version', 'width'))
                x_positions.append(x)

                x += int(tree.column('date', 'width'))
                x_positions.append(x)
            except Exception:
                return

            height = tree.winfo_height()
            if height <= 1:
                tree.after(50, update_column_separators)
                return

            try:
                sb = getattr(tree, '_vscrollbar', None)
                sb_x = sb.winfo_x() if sb is not None else None
            except Exception:
                sb_x = None

            for i, x in enumerate(x_positions):
                try:
                    if sb_x is not None and x >= sb_x:
                        separators[i].place_forget()
                        continue
                except Exception:
                    pass

                separators[i].place(x=x, y=tree.winfo_y(),
                                    width=1, height=height)
                separators[i].lift()

            for sep in separators:
                sep.lift()

            try:
                sb = getattr(tree, '_vscrollbar', None)
                if sb is not None:
                    sb.lift()
            except Exception:
                pass

        # 初次显示/布局后绘制分隔线
        tree.bind('<Map>', lambda e: tree.after(
            0, update_column_separators), add=True)
        # Configure 事件在缩放时触发，但布局可能还没稳定，延迟执行
        def _on_configure(*_):
            tree.after(50, update_column_separators)
        tree.bind('<Configure>', _on_configure, add=True)
        # 拖拽列宽结束后重绘（Treeview 原生列拖拽触发在鼠标释放时更稳定）
        tree.bind('<ButtonRelease-1>', update_column_separators, add=True)
        # 选中行时 Treeview 会重绘，强制刷新分隔线层级与颜色
        tree.bind('<<TreeviewSelect>>', update_column_separators, add=True)
        tree.after(0, update_column_separators)

        # 创建滚动条（先 pack，确保获得固定宽度）
        scrollbar = self.create_modern_scrollbar(tree_frame, tree)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # 再 pack Treeview（占据剩余空间）
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        try:
            tree._container = tree_frame
            tree._vscrollbar = scrollbar
            scrollbar.lift()
        except Exception:
            pass

        # 包装 yscrollcommand 以检测滚动到底部（用于分页加载）
        try:
            def _on_tree_scroll(first, last):
                # 先调用 scrollbar.set 更新滚动条位置
                scrollbar.set(first, last)
                # 检测是否滚动到底部（last > 0.95 表示接近底部）
                try:
                    if float(last) > 0.95:
                        self._on_version_tree_scroll()
                except Exception:
                    pass

            # 只对版本列表（有 'version' 列的 tree）设置分页滚动检测
            if hasattr(tree, 'column') and 'version' in tree['columns']:
                tree.config(yscrollcommand=_on_tree_scroll)
        except Exception:
            pass

        tree.after(0, update_column_separators)

        return tree

    def create_modern_scrollbar(self, parent, widget):
        """创建现代化滚动条"""
        scrollbar = ttk.Scrollbar(
            parent, orient=tk.VERTICAL, command=widget.yview)
        widget.config(yscrollcommand=scrollbar.set)

        # 自定义滚动条样式
        scrollbar.configure(style='Modern.Vertical.TScrollbar')

        return scrollbar

    def create_app_info_section(self, parent):
        """创建应用信息区域"""
        info_frame = tk.Frame(parent,
                              bg=self.colors['bg_card'],
                              relief='flat',
                              borderwidth=1)
        info_frame.pack(fill=tk.X, pady=(0, 15))

        # 信息文本区域
        self.app_info_text = self.create_modern_text(info_frame, height=6)
        self.app_info_text._container.pack(fill=tk.X, padx=0, pady=10)

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
        self.uninstall_button.pack(fill=tk.X)

        # 工具按钮行
        tool_row = tk.Frame(button_frame, bg=self.colors['bg_card'])
        tool_row.pack(fill=tk.X)

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

    def _install_spinner_start(self, base_text=None):
        # 记录当前的运行中文案（如果不传则默认为 "正在安装..."）
        _running_text = base_text if base_text else "正在安装..."

        try:
            if not hasattr(self, 'install_button') or self.install_button is None:
                return
        except Exception:
            return

        try:
            if self._install_spinner_after_id is not None:
                try:
                    self.root.after_cancel(self._install_spinner_after_id)
                except Exception:
                    pass
                self._install_spinner_after_id = None
        except Exception:
            self._install_spinner_after_id = None

        try:
            if self._install_button_base_text is None:
                self._install_button_base_text = str(
                    self.install_button.cget('text'))
        except Exception:
            if self._install_button_base_text is None:
                self._install_button_base_text = "🚀 安装选中版本"

        self._install_spinner_idx = 0
        frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']

        def _tick():
            try:
                if not hasattr(self, 'install_button') or self.install_button is None:
                    self._install_spinner_after_id = None
                    return
                if str(self.install_button.cget('state')) == 'disabled':
                    ch = frames[self._install_spinner_idx % len(frames)]
                    self._install_spinner_idx += 1
                    self.install_button.config(text=f"{ch} {_running_text}")
                    self._install_spinner_after_id = self.root.after(90, _tick)
                else:
                    self._install_spinner_after_id = None
            except Exception:
                self._install_spinner_after_id = None

        try:
            self.install_button.config(state='disabled')
        except Exception:
            pass
        try:
            _tick()
        except Exception:
            pass

    def _install_spinner_stop(self):
        try:
            if self._install_spinner_after_id is not None:
                try:
                    self.root.after_cancel(self._install_spinner_after_id)
                except Exception:
                    pass
            self._install_spinner_after_id = None
        except Exception:
            self._install_spinner_after_id = None

        try:
            if hasattr(self, 'install_button') and self.install_button is not None:
                if self._install_button_base_text:
                    self.install_button.config(
                        text=self._install_button_base_text)
        except Exception:
            pass

    def create_modern_console(self, parent):
        """创建现代化控制台"""
        # 控制台容器
        console_frame = tk.Frame(parent, bg=self.colors['bg_card'])
        console_frame.pack(fill=tk.BOTH, expand=True)

        # 控制台文本区域
        self.log_text = self.create_modern_text(console_frame, height=10)
        self.log_text._container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

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
        """创建现代化文本区域"""
        text_frame = tk.Frame(parent, bg=self.colors['bg_primary'])

        text = tk.Text(text_frame,
                       bg='#0F1419',
                       fg=self.colors['text_primary'],
                       font=self.fonts['mono'],
                       width=1,
                       relief='flat',
                       borderwidth=0,
                       highlightthickness=0,
                       padx=10,
                       pady=10,
                       height=height)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.create_modern_scrollbar(
            text_frame, text).pack(side=tk.RIGHT, fill=tk.Y)

        text._container = text_frame

        return text

    def create_status_bar(self):
        """创建状态栏"""
        status_bar = tk.Frame(
            self.main_frame, bg=self.colors['bg_secondary'], height=30)
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
        allow_drag = False
        try:
            header = getattr(self, 'header_frame', None)
            if header is not None:
                w = event.widget
                while w is not None:
                    if w is header:
                        allow_drag = True
                        break
                    try:
                        w = w.master
                    except Exception:
                        break
        except Exception:
            allow_drag = False

        self._window_drag_active = bool(allow_drag)
        if not self._window_drag_active:
            return

        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def on_drag(self, event):
        """拖拽中"""
        if not getattr(self, '_window_drag_active', False):
            return
        x = self.root.winfo_x() + event.x - self.drag_start_x
        y = self.root.winfo_y() + event.y - self.drag_start_y
        self.root.geometry(f"+{x}+{y}")

    def stop_drag(self, event):
        """停止拖拽"""
        self._window_drag_active = False

    def center_window(self, window, width, height):
        window.update_idletasks()

        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()

        x = main_x + (main_width // 2) - (width // 2)
        y = main_y + (main_height - height) // 3 + 60

        x = max(0, x)
        y = max(0, y)

        window.geometry(f"{width}x{height}+{x}+{y}")

    def _style_entry_widget(self, entry):
        entry.configure(
            font=self.fonts['body'],
            bg=self.colors['bg_primary'],
            fg=self.colors['text_primary'],
            insertbackground=self.colors['text_primary'],
            relief='flat',
            bd=0,
            highlightthickness=1,
            highlightbackground=self.colors['border'],
            highlightcolor=self.colors['border']
        )

    def _style_dialog_button_widget(self, btn, *, bg, fg, active_bg, active_fg, bold=False, secondary=False):
        try:
            dpi = float(getattr(self, 'system_dpi', 96.0) or 96.0)
            btn_fs = -max(9, int(round(10 * (dpi / 72.0))))
        except Exception:
            btn_fs = 10
        btn.configure(
            font=('Segoe UI', btn_fs, 'bold' if bold else 'normal'),
            bg=bg,
            fg=fg,
            activebackground=active_bg,
            activeforeground=active_fg,
            relief='flat',
            bd=0,
            borderwidth=0,
            highlightthickness=1 if secondary else 0,
            highlightbackground=self.colors['border'] if secondary else bg,
            highlightcolor=self.colors['border'] if secondary else bg,
            padx=14,
            pady=7,
            cursor='hand2'
        )

        def _on_enter(_e):
            btn.configure(bg=active_bg)

        def _on_leave(_e):
            btn.configure(bg=bg)

        btn.bind('<Enter>', _on_enter)
        btn.bind('<Leave>', _on_leave)

    def _show_modal_dialog(self, title, message, variant, buttons):
        dialog = tk.Toplevel(self.root)
        try:
            dialog.attributes('-alpha', 0.0)
        except Exception:
            pass
        dialog.withdraw()
        dialog.title(title)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.configure(bg=self.colors['bg_secondary'])

        try:
            ui_scale = float(getattr(self, 'ui_scale', 1.0))
        except Exception:
            ui_scale = 1.0

        # Make border more visible (no layout change)
        try:
            border_thickness = max(1, int(round(1 * ui_scale)))
            dialog.configure(
                highlightthickness=border_thickness,
                highlightbackground='#3B4045',
                highlightcolor='#3B4045',
                bd=0,
            )
        except Exception:
            pass

        dialog_width = 620

        try:
            dialog.attributes('-alpha', 0.0)
        except Exception:
            pass

        dialog.grab_set()

        # Get icon color based on variant
        icon_colors = {
            'error': self.colors['bg_danger'],
            'warning': self.colors['bg_warning'],
            'question': self.colors['bg_accent'],
            'info': self.colors['bg_accent'],
        }
        icon_color = icon_colors.get(variant, self.colors['bg_accent'])

        content = tk.Frame(dialog, bg=self.colors['bg_secondary'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=14)

        top_row = tk.Frame(content, bg=self.colors['bg_secondary'])
        top_row.pack(fill=tk.X)
        top_row.grid_columnconfigure(1, weight=1)

        # Scale icon size based on DPI
        icon_size = 44
        try:
            ui_scale = float(getattr(self, 'ui_scale', 1.0))
            icon_size = int(round(44 * ui_scale))
        except Exception:
            pass

        icon_canvas = tk.Canvas(top_row, width=icon_size, height=icon_size,
                                bg=self.colors['bg_secondary'], highlightthickness=0)
        icon_canvas.grid(row=0, column=0, sticky='n',
                         padx=(0, 14), pady=(2, 0))
        icon_canvas.create_oval(2, 2, icon_size - 2,
                                icon_size - 2, fill=icon_color, outline='')

        # Draw geometric icons instead of emoji for better DPI compatibility
        center = icon_size // 2
        padding = int(round(icon_size * 0.25))

        if variant == 'error':
            # Draw X
            line_width = max(2, int(round(icon_size * 0.08)))
            icon_canvas.create_line(center - padding, center - padding, center + padding, center + padding,
                                    fill='white', width=line_width, capstyle='round')
            icon_canvas.create_line(center + padding, center - padding, center - padding, center + padding,
                                    fill='white', width=line_width, capstyle='round')
        elif variant == 'warning':
            # Draw taller triangle with exclamation
            triangle_radius = int(round(icon_size * 0.4))
            # taller than equilateral triangle
            h = int(round(triangle_radius * 1.2))
            points = [
                center, center - h,
                center - triangle_radius, center + h // 2,
                center + triangle_radius, center + h // 2
            ]
            icon_canvas.create_polygon(points, fill='white', outline='')
            # Draw exclamation mark in center (shifted up)
            exclamation_width = max(2, int(round(icon_size * 0.08)))
            exclamation_height = int(round(icon_size * 0.3))
            # Vertical line (shifted up)
            line_top = center - exclamation_height // 2 - 4
            line_bottom = center + exclamation_height // 6 - 4
            icon_canvas.create_rectangle(center - exclamation_width // 2, line_top,
                                         center + exclamation_width // 2, line_bottom,
                                         fill=icon_color, outline='')
            # Dot at bottom (shifted up)
            dot_size = max(2, int(round(icon_size * 0.08)))
            dot_y = line_bottom + dot_size + 2
            icon_canvas.create_oval(center - dot_size, dot_y,
                                    center + dot_size, dot_y + dot_size * 2,
                                    fill=icon_color, outline='')
        elif variant == 'question':
            # Draw question mark using text (more reliable than emoji)
            font_size = int(round(icon_size * 0.28))
            try:
                font_size = max(10, font_size)
            except Exception:
                pass
            icon_canvas.create_text(center, center, text='?', fill='white',
                                    font=('Segoe UI', font_size, 'bold'), anchor='center')
        elif variant == 'info':
            # Draw i using text
            font_size = int(round(icon_size * 0.5))
            icon_canvas.create_text(center, center, text='i', fill='white',
                                    font=('Segoe UI', font_size, 'bold'), anchor='center')
        else:
            # Default: draw i
            font_size = int(round(icon_size * 0.5))
            icon_canvas.create_text(center, center, text='i', fill='white',
                                    font=('Segoe UI', font_size, 'bold'), anchor='center')

        msg_container = tk.Frame(top_row, bg=self.colors['bg_secondary'])
        msg_container.grid(row=0, column=1, sticky='nw')

        msg_label = tk.Label(
            msg_container,
            text=str(message),
            font=self.fonts['body'],
            bg=self.colors['bg_secondary'],
            fg=self.colors['text_primary'],
            justify='left',
            anchor='w',
            wraplength=max(320, dialog_width - (icon_size + 14) - 40)
        )
        msg_label.pack(anchor='w')

        btn_row = tk.Frame(content, bg=self.colors['bg_secondary'])
        btn_row.pack(fill=tk.X, pady=(14, 0))

        result = {'value': None}

        def _on_close(value):
            result['value'] = value
            try:
                dialog.grab_release()
            except Exception:
                pass
            dialog.destroy()

        dialog.protocol('WM_DELETE_WINDOW', lambda: _on_close(None))

        btn_specs = []
        for b in buttons:
            if isinstance(b, tuple) and len(b) == 2:
                btn_specs.append(b)
        if not btn_specs:
            btn_specs = [('确定', True)]

        for i, (label, value) in enumerate(reversed(btn_specs)):
            is_primary = (i == 0)
            btn = tk.Button(btn_row, text=label,
                            command=lambda v=value: _on_close(v))
            if is_primary:
                self._style_dialog_button_widget(
                    btn,
                    bg=self.colors['bg_accent'],
                    fg='white',
                    active_bg=self.colors['hover'],
                    active_fg='white',
                    bold=True,
                    secondary=False
                )
            else:
                self._style_dialog_button_widget(
                    btn,
                    bg=self.colors['bg_selection'],
                    fg=self.colors['text_primary'],
                    active_bg='#343A3F',
                    active_fg=self.colors['text_primary'],
                    bold=False,
                    secondary=True
                )
            btn.pack(side=tk.RIGHT, padx=(10 if i == 0 else 0, 0))

        dialog.geometry(f"{dialog_width}x1")
        dialog.update_idletasks()
        dialog_height = dialog.winfo_reqheight()
        dialog_height = max(150, min(520, int(dialog_height)))
        self.center_window(dialog, dialog_width, dialog_height)

        try:
            dialog.deiconify()
            dialog.lift()
            dialog.focus_force()
        except Exception:
            pass

        try:
            dialog.attributes('-alpha', 1.0)
        except Exception:
            pass

        self.root.wait_window(dialog)
        return result['value']

    def show_error(self, title, message):
        self._show_modal_dialog(title, message, 'error', [('确定', True)])

    def show_warning(self, title, message):
        self._show_modal_dialog(title, message, 'warning', [('确定', True)])

    def ask_yesno(self, title, message):
        val = self._show_modal_dialog(title, message, 'question', [
                                      ('否', False), ('是', True)])
        return bool(val)

    def show_initial_config_dialog(self):
        """Show initial configuration dialog"""
        result = self.ask_yesno(
            "配置向导",
            "欢迎使用鸿蒙应用安装工具！\n\n未检测到初始配置。\n\n是否现在打开配置界面？"
        )

        if result:
            self.configure_server()
        else:
            # User clicked "No", exit the application
            self.log("User cancelled configuration, exiting application")
            self.root.quit()

    def log(self, message):
        """Add log message"""
        timestamp = time.strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        self.log_text.insert(tk.END, formatted_message + "\n")
        self.log_text.see(tk.END)

        # Only update if window is visible to prevent flashing
        if hasattr(self.root, '_window_visible') and self.root._window_visible:
            self.root.update_idletasks()

        # Update status bar
        self.status_info.config(text=message)

    def clear_log(self):
        """Clear log"""
        self.log_text.delete(1.0, tk.END)
        self.log(" Console cleared")

    def save_log(self):
        """保存日志"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".log",
                filetypes=[("日志文件", "*.log"),
                           ("文本文件", "*.txt"), ("所有文件", "*.*")],
                parent=self.root
            )
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get(1.0, tk.END))
                self.log(f"💾 日志已保存: {filename}")
                self._show_modal_dialog("成功", "日志保存成功", 'info', [('确定', True)])
        except Exception as e:
            self.log(f"❌ 保存失败: {str(e)}")
            self.show_error("错误", f"日志保存失败: {str(e)}")

    def load_apps_config(self):
        """从服务器加载应用配置"""
        try:
            # 从服务器获取应用列表
            apps_url = f"{self.server_base_url}/api/apps"
            self.log(f"🌐 获取应用列表: {apps_url}")

            response = requests.get(apps_url, headers=self._get_api_headers(), timeout=10)
            if response.status_code == 401:
                error_msg = 'API Key 无效或已过期'
                try:
                    error_data = response.json()
                    if error_data.get('error'):
                        error_msg = error_data.get('error')
                except Exception:
                    pass
                raise Exception(f"认证失败: {error_msg}\n\n请在设置中更新有效的 API Key。")
            if response.status_code == 200:
                self.apps_config = response.json()
                self.log(f"📱 已从服务器加载 {len(self.apps_config['apps'])} 个应用")
                self.populate_app_list()
            else:
                raise Exception(f"服务器响应错误: {response.status_code}")

        except requests.exceptions.RequestException as e:
            self.log(f"❌ 服务器连接失败: {str(e)}")
            self.show_error("错误", f"无法连接到服务器: {str(e)}\n\n请检查服务器地址配置或网络连接。")

        except Exception as e:
            self.log(f"❌ 配置加载失败: {str(e)}")
            self.show_error("错误", f"配置加载失败: {str(e)}")

    def _get_settings_path(self):
        system = platform.system()
        home = os.path.expanduser('~')

        if system == 'Windows':
            appdata = os.environ.get('APPDATA')
            if not appdata:
                appdata = home
            settings_dir = os.path.join(appdata, 'HarmonyOSInstaller')
        elif system == 'Darwin':
            settings_dir = os.path.join(
                home, 'Library', 'Application Support', 'HarmonyOSInstaller')
        else:
            config_home = os.environ.get('XDG_CONFIG_HOME')
            if not config_home:
                config_home = os.path.join(home, '.config')
            settings_dir = os.path.join(config_home, 'HarmonyOSInstaller')

        return os.path.join(settings_dir, 'settings.json')

    def _get_default_download_dir(self):
        system = platform.system()
        home = os.path.expanduser('~')

        if system == 'Windows':
            local_appdata = os.environ.get('LOCALAPPDATA')
            if not local_appdata:
                local_appdata = os.path.join(home, 'AppData', 'Local')
            return os.path.join(local_appdata, 'HarmonyOSInstaller', 'downloads')

        if system == 'Darwin':
            return os.path.join(home, 'Library', 'Application Support', 'HarmonyOSInstaller', 'downloads')

        data_home = os.environ.get('XDG_DATA_HOME')
        if not data_home:
            data_home = os.path.join(home, '.local', 'share')
        return os.path.join(data_home, 'HarmonyOSInstaller', 'downloads')

    def check_initial_config(self):
        """检查初始配置"""
        settings_path = self._get_settings_path()

        # 如果设置文件存在，检查配置是否完整
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    server_url = settings.get('server_base_url', '').strip()
                    download_dir = (settings.get(
                        'download_dir', '') or '').strip()
                    if not download_dir:
                        download_dir = self._get_default_download_dir()

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
        settings_path = self._get_settings_path()
        try:
            if os.path.exists(settings_path):
                with open(settings_path, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    self.server_base_url = settings.get('server_base_url', "")
                    self.download_dir = settings.get('download_dir', "")
                    self.api_key = settings.get('api_key', "")
                    if not self.download_dir:
                        self.download_dir = self._get_default_download_dir()
                    self.log(f"⚙️ 已加载本地设置")
            else:
                # 使用空设置，强制用户配置
                self.server_base_url = ""
                self.download_dir = self._get_default_download_dir()
                self.api_key = ""
                self.log(f"📝 首次运行，需要配置")
        except Exception as e:
            self.log(f"⚠️ 设置加载失败，需要重新配置: {str(e)}")
            # 使用空设置，强制用户配置
            self.server_base_url = ""
            self.download_dir = self._get_default_download_dir()
            self.api_key = ""

    def save_local_settings(self):
        """保存本地设置"""
        settings_path = self._get_settings_path()
        try:
            os.makedirs(os.path.dirname(settings_path), exist_ok=True)
            settings = {
                'server_base_url': self.server_base_url,
                'download_dir': self.download_dir,
                'api_key': self.api_key
            }
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            self.log(f"💾 设置已保存")
        except Exception as e:
            self.log(f"❌ 设置保存失败: {str(e)}")

    def _get_api_headers(self):
        """Get API request headers with X-API-Key if available"""
        headers = {}
        if self.api_key:
            headers['X-API-Key'] = self.api_key
        return headers

    def populate_app_list(self):
        """填充应用列表"""
        if not self.apps_config:
            return

        if not hasattr(self, 'app_tree'):
            return

        for item in self.app_tree.get_children():
            self.app_tree.delete(item)

        for idx, app in enumerate(self.apps_config['apps']):
            display_text = f" {app['name']}"
            row_tag = 'even' if idx % 2 == 0 else 'odd'
            self.app_tree.insert('', 'end', iid=str(
                idx), text=display_text, tags=(row_tag,))

        self.log("🚀 应用列表已更新")

        # 自动选中第一个应用
        if self.apps_config.get('apps') and len(self.apps_config['apps']) > 0:
            try:
                self.app_tree.selection_set('0')
                self.app_tree.see('0')
            except Exception:
                pass

    def on_app_select(self, event):
        """应用选择事件"""
        if hasattr(self, 'app_tree'):
            selection = self.app_tree.selection()
            if not selection:
                return
            try:
                index = int(selection[0])
            except Exception:
                return
        else:
            selection = self.app_listbox.curselection()
            if not selection:
                return
            index = selection[0]

        if index < len(self.apps_config['apps']):
            self.current_app = self.apps_config['apps'][index]
            self.log(f"📝 已选择: {self.current_app['name']}")
            self.update_control_center()
            self.load_version_list_async(select_first=True)

    def select_first_version(self):
        """选择第一个版本并显示详情"""
        if not hasattr(self, 'version_tree'):
            return

        versions = []
        try:
            versions = list(getattr(self, 'current_versions', []) or [])
        except Exception:
            versions = []

        if versions and isinstance(versions[0], dict):
            version = versions[0].get('version')
            version_id = versions[0].get('id')
            if version_id is not None:
                try:
                    iid = f"ver_{version_id}"
                    self.version_tree.selection_set(iid)
                    self.version_tree.see(iid)
                except Exception:
                    pass

                self.current_version = version
                return

    def show_version_info_by_id(self, version_id):
        """通过 version_id 精确显示版本特定信息"""
        if not self.current_app or not version_id:
            return
        version_info = self.get_version_info_by_id(version_id)
        if not version_info:
            return
        version_str = version_info.get('version', 'N/A')
        info = f"应用名称: {self.current_app.get('name', 'N/A')}\n"
        info += f"应用包名: {self.current_app.get('bundle_name', 'N/A')}\n"
        info += f"选中版本: {version_str}\n"
        info += f"发布日期: {version_info.get('release_date', 'N/A')}\n"
        info += f"应用入口: {self.current_app.get('main_ability', 'N/A')}\n"
        info += f"版本描述: {version_info.get('description', 'N/A')}\n"
        files = version_info.get('files', {})
        if isinstance(files, dict):
            info += f"\n文件信息:\n"
            info += f"  HAP: {files.get('hap', 'N/A')}\n"
            info += f"  HSP: {files.get('hsp', 'N/A')}\n"
        self.app_info_text.delete(1.0, tk.END)
        self.app_info_text.insert(1.0, info)

    def update_control_center(self):
        """Update control center with current app info"""
        if not self.current_app:
            return

        # Update button states
        if hasattr(self, 'install_button'):
            self.install_button.config(state='normal')
        if hasattr(self, 'uninstall_button'):
            self.uninstall_button.config(state='normal')

        # Keep status_text/status_indicator reserved for HDC connection status

    def on_version_select(self, event):
        """Version selection event"""
        selection = self.version_tree.selection()
        if not selection:
            return "break"

        # Get selected version
        item = selection[0]
        try:
            info = (getattr(self, '_version_item_map', {}) or {}).get(item)
            if isinstance(info, dict) and info.get('version'):
                version = info.get('version')
                version_id = info.get('id')
                self.current_version = version
                self.log(
                    f"📝 Selected version: {version} (version_id={version_id})")
                if version_id:
                    self.show_version_info_by_id(version_id)
                self.update_control_center()
        except Exception:
            pass

        return "break"

    def load_version_list_async(self, select_first=False, page=1, append=False):
        """异步加载版本列表，支持分页加载。"""
        if not self.current_app:
            return

        app_snapshot = self.current_app
        app_id = app_snapshot.get('id')

        # 检查是否切换了应用
        if self._ver_app_id != app_id:
            self._ver_app_id = app_id
            self._ver_page = 1
            self._ver_has_more = True
            append = False

        # 防止重复加载
        if self._ver_loading:
            return
        if page > 1 and not self._ver_has_more:
            return

        self._ver_loading = True
        self._ver_page = page

        # 如果不是追加模式，清空列表
        if not append:
            try:
                for iid in self.version_tree.get_children():
                    self.version_tree.delete(iid)
            except Exception:
                pass
            self.current_versions = []
            self._version_item_map = {}

        versions_url = f"{self.server_base_url}/api/apps/{app_id}/versions?page={page}&page_size={self._ver_page_size}"
        self.log(f"🌐 正在加载第 {page} 页版本列表")

        def _worker():
            try:
                response = requests.get(versions_url, headers=self._get_api_headers(), timeout=10)
                if response.status_code == 401:
                    error_msg = 'API Key 无效或已过期'
                    try:
                        error_data = response.json()
                        if error_data.get('error'):
                            error_msg = error_data.get('error')
                    except Exception:
                        pass
                    raise Exception(f"认证失败: {error_msg}\n\n请在设置中更新有效的 API Key。")
                if response.status_code != 200:
                    raise Exception(f"服务器响应错误: {response.status_code}")
                data = response.json()
                versions = (data or {}).get('versions', [])
                has_more = (data or {}).get('has_more', False)
                total = (data or {}).get('total', 0)
                if not isinstance(versions, list):
                    versions = []
                return True, {'versions': versions, 'has_more': has_more, 'total': total, 'page': page}
            except requests.exceptions.RequestException as e:
                return False, f"无法连接到服务器: {str(e)}"
            except Exception as e:
                return False, f"版本加载失败: {str(e)}"

        def _on_done(ok, payload):
            self._ver_loading = False

            if self.current_app is not app_snapshot:
                return

            if not ok:
                self.log(f"❌ 版本加载失败: {payload}")
                self.show_error("错误", str(payload))
                return

            versions = payload.get('versions', [])
            self._ver_has_more = payload.get('has_more', False)
            total = payload.get('total', 0)

            # 计算起始索引用于斑马纹
            start_idx = len(self.current_versions)
            self.current_versions.extend(versions)

            for idx, version_info in enumerate(versions):
                if not isinstance(version_info, dict):
                    continue
                version = version_info.get('version', '')
                description = version_info.get('description', '')
                release_date = version_info.get('release_date', '')
                status = '🚀'
                row_tag = 'even' if (start_idx + idx) % 2 == 0 else 'odd'

                iid = None
                try:
                    vid = version_info.get('id')
                    if vid is not None and str(vid):
                        iid = f"ver_{vid}"
                except Exception:
                    iid = None
                if not iid:
                    iid = f"ver_{start_idx + idx}"

                try:
                    self._version_item_map[iid] = version_info
                except Exception:
                    pass

                try:
                    self.version_tree.insert('', 'end', iid=iid, text=description,
                                             values=(version, release_date, status),
                                             tags=(row_tag,))
                except Exception:
                    pass

            self.log(f"📦 已加载第 {page} 页，共 {len(versions)} 个版本 (总计 {len(self.current_versions)}/{total})")

            if select_first and page == 1:
                try:
                    self.select_first_version()
                except Exception:
                    pass

        def _run():
            ok, payload = _worker()
            try:
                self.root.after(0, lambda: _on_done(ok, payload))
            except Exception:
                pass

        threading.Thread(target=_run, daemon=True).start()

    def _on_version_tree_scroll(self, *args):
        """检测 Treeview 滚动到底部，触发加载下一页。"""
        if self._ver_loading or not self._ver_has_more:
            return

        try:
            # 获取滚动位置
            tree = self.version_tree
            first, last = tree.yview()
            # 如果滚动到底部 (last > 0.95 表示接近底部)
            if last > 0.95:
                self._load_next_versions_page()
        except Exception:
            pass

    def _load_next_versions_page(self):
        """加载下一页版本。"""
        if self._ver_loading or not self._ver_has_more:
            return
        next_page = self._ver_page + 1
        self.load_version_list_async(select_first=False, page=next_page, append=True)

    def detect_hdc_tool(self):
        """检测HDC工具"""
        try:
            # 更新状态为检测中

            self.log("🔍 检测HDC工具...")

            system = platform.system()
            arch = platform.machine()

            # Get application root directory (use sys._MEIPASS for packaged app)
            if getattr(sys, 'frozen', False):
                # Packaged application
                base_path = sys._MEIPASS
                self.log(f"📦 运行在打包模式，基础路径: {base_path}")
            else:
                # Development environment
                base_path = os.path.dirname(os.path.abspath(__file__))
                self.log(f"🛠️ 运行在开发模式，基础路径: {base_path}")

            self.log(f"💻 系统: {system}, 架构: {arch}")

            # 确定HDC路径
            hdc_path = None
            if system == "Darwin":
                if arch == "arm64":
                    hdc_path = os.path.join(base_path, "hdc_arm", "hdc")
                else:
                    hdc_path = os.path.join(base_path, "hdc_x86", "hdc_x86")
            elif system == "Windows":
                hdc_path = os.path.join(base_path, "hdc_win", "hdc_w.exe")
            elif system == "Linux":
                if arch == "aarch64":
                    hdc_path = os.path.join(base_path, "hdc_arm", "hdc")
                else:
                    hdc_path = os.path.join(base_path, "hdc_x86", "hdc_x86")

            self.hdc_path = hdc_path
            self.log(f"🎯 预期HDC路径: {self.hdc_path}")

            # 检查文件是否存在
            if self.hdc_path and os.path.exists(self.hdc_path):
                self.log(f"✅ HDC工具找到: {self.hdc_path}")

                # 测试HDC工具是否可用
                try:
                    _run_kwargs = {}
                    try:
                        if platform.system() == 'Windows':
                            _run_kwargs['creationflags'] = getattr(
                                subprocess, 'CREATE_NO_WINDOW', 0)
                            si = subprocess.STARTUPINFO()
                            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                            _run_kwargs['startupinfo'] = si
                    except Exception:
                        _run_kwargs = {}

                    result = subprocess.run([self.hdc_path, "--version"],
                                            capture_output=True, text=True, timeout=5, **_run_kwargs)
                    if result.returncode == 0:
                        self.log(f"✅ HDC工具可用: {result.stdout.strip()}")
                        device_ok = False
                        try:
                            device_ok, device_out = self.run_hdc_command(
                                "list targets", show_output=False)
                            if device_ok:
                                lines = [ln.strip() for ln in (
                                    device_out or '').splitlines() if ln.strip()]
                                device_ok = len(lines) > 0
                        except Exception:
                            device_ok = False

                        if device_ok:
                            if hasattr(self, 'status_text'):
                                self.status_text.config(
                                    text="HDC已连接", fg=self.colors['bg_success'])
                            if hasattr(self, 'status_indicator'):
                                self.update_status_indicator('success')
                            self.install_button.config(state='normal')
                            self.uninstall_button.config(state='normal')
                        else:
                            if hasattr(self, 'status_text'):
                                self.status_text.config(
                                    text="设备未连接", fg=self.colors['bg_warning'])
                            if hasattr(self, 'status_indicator'):
                                self.update_status_indicator('warning')
                            self.install_button.config(state='disabled')
                            self.uninstall_button.config(state='disabled')
                        # UDID button moved to header bar
                    else:
                        raise Exception(f"HDC版本检查失败: {result.stderr}")
                except subprocess.TimeoutExpired:
                    self.log("⚠️ HDC工具响应超时，但文件存在")
                    if hasattr(self, 'status_text'):
                        self.status_text.config(
                            text="HDC连接超时", fg=self.colors['bg_warning'])
                    if hasattr(self, 'status_indicator'):
                        self.update_status_indicator('warning')
                    self.install_button.config(state='normal')
                    self.uninstall_button.config(state='normal')
                    # UDID button moved to header bar
                except Exception as e:
                    self.log(f"❌ HDC工具测试失败: {str(e)}")
                    if hasattr(self, 'status_text'):
                        self.status_text.config(
                            text="HDC不可用", fg=self.colors['bg_danger'])
                    if hasattr(self, 'status_indicator'):
                        self.update_status_indicator('danger')
                    self.install_button.config(state='disabled')
                    self.uninstall_button.config(state='disabled')
                    # UDID button moved to header bar
            else:
                self.log(f"❌ HDC工具未找到: {self.hdc_path}")
                if hasattr(self, 'status_text'):
                    self.status_text.config(
                        text="HDC未连接", fg=self.colors['bg_danger'])
                if hasattr(self, 'status_indicator'):
                    self.update_status_indicator('danger')
                self.install_button.config(state='disabled')
                self.uninstall_button.config(state='disabled')
                # UDID button moved to header bar

        except Exception as e:
            self.log(f"❌ HDC检测异常: {str(e)}")
            if hasattr(self, 'status_text'):
                self.status_text.config(
                    text="HDC检测失败", fg=self.colors['bg_danger'])
            if hasattr(self, 'status_indicator'):
                self.update_status_indicator('danger')

    def run_hdc_command(self, command, show_output=True):
        """执行HDC命令"""
        if not self.hdc_path or not os.path.exists(self.hdc_path):
            return False, "HDC工具不可用"

        try:
            self.log(f"⚡ 执行: {command}")
            self.log(f"&#x1d4cb; HDC&#x8def;&#x5f84;: {self.hdc_path}")
            self.log(
                f"&#x1d4cb; HDC&#x5b58;&#x5728;: {os.path.exists(self.hdc_path)}")

            try:
                import shlex
                args = [self.hdc_path] + \
                    shlex.split(command, posix=(
                        platform.system() != 'Windows'))
            except Exception:
                args = [self.hdc_path] + command.split()

            _run_kwargs = {}
            try:
                if platform.system() == 'Windows':
                    _run_kwargs['creationflags'] = getattr(
                        subprocess, 'CREATE_NO_WINDOW', 0)
                    si = subprocess.STARTUPINFO()
                    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                    _run_kwargs['startupinfo'] = si
            except Exception:
                _run_kwargs = {}

            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=30,
                **_run_kwargs
            )

            stdout_text = result.stdout or ''
            stderr_text = result.stderr or ''
            combined = (stdout_text + "\n" + stderr_text).lower()

            hdc_text_error_markers = (
                'error:',
                'error code:',
                'failed to ',
            )

            no_device_markers = (
                'no device',
                'device not found',
                'not connected',
                'no targets',
                'offline',
                'unauthorized',
                'fail to connect',
                'failed to connect',
                'connection refused',
                'timeout',
            )

            if any(m in combined for m in no_device_markers):
                return False, (stderr_text.strip() or stdout_text.strip() or '设备未连接')

            hdc_fail_markers = (
                '[fail]',
                'need connect-key',
                'need connect key',
                'executecommand need connect-key',
                'executecommand need connect key',
            )

            if any(m in combined for m in hdc_fail_markers):
                return False, (stderr_text.strip() or stdout_text.strip() or 'HDC执行失败')

            if any(m in combined for m in hdc_text_error_markers):
                return False, (stderr_text.strip() or stdout_text.strip() or 'HDC执行失败')

            if result.returncode == 0:
                if show_output:
                    self.log("✅ 命令执行成功")
                return True, stdout_text
            else:
                error_msg = stderr_text.strip() if stderr_text else "未知错误"
                self.log(f"❌ 执行失败: {error_msg}")
                return False, error_msg

        except subprocess.TimeoutExpired:
            self.log("⏰ 命令超时")
            return False, "命令执行超时"
        except Exception as e:
            self.log(f"❌ 执行异常: {str(e)}")
            return False, str(e)

    def format_hdc_error(self, raw_text):
        text = (raw_text or '').strip()
        low = text.lower()

        if 'need connect-key' in low or 'need connect key' in low:
            return "未检测到已授权的设备连接。\n\n请按以下步骤操作：\n1) 使用 USB 连接设备\n2) 在设备上确认 HDC 授权/连接提示\n3) 返回电脑端点击“刷新”后重试"

        if 'no device' in low or 'device not found' in low or 'not connected' in low or 'no targets' in low:
            return "未检测到设备连接。\n\n请使用 USB 连接鸿蒙设备并确保设备已开启调试模式，然后点击“刷新”重试。"

        if '[fail]' in low:
            cleaned = text.replace('[Fail]', '').replace('[FAIL]', '').strip()
            if cleaned:
                return f"HDC 执行失败：{cleaned}"
            return "HDC 执行失败，请确认设备连接与授权后重试。"

        if 'uninstall missing installed bundle' in low or 'failed to uninstall bundle' in low and 'missing installed bundle' in low:
            return (
                "卸载失败：设备上未安装该应用。\n\n"
                "说明：当前设备找不到这个包名对应的已安装应用，所以无法卸载。\n\n"
                "你可以：\n"
                "1) 直接点击【安装选中版本】进行安装\n"
                "2) 或点击【刷新】确认设备连接后再操作"
            )

        if 'failed to retrieve specified package information' in low or 'is not installed' in low:
            return (
                "操作失败：设备上未安装该应用。\n\n"
                "说明：当前设备找不到该包名的应用，停止/启动等操作会失败属于正常现象。\n\n"
                "建议：直接点击【安装选中版本】进行安装。"
            )

        if 'install sign info inconsistent' in low:
            return (
                "安装失败：签名不一致。\n\n"
                "含义：设备上可能残留了同包名应用/模块，但签名与本次安装包不同；或本次 HAP/HSP 不是同一套证书签名。\n\n"
                "建议你在客户端里按下面做（从上到下）：\n"
                "1) 点击右侧【卸载】一次（已做彻底卸载与清理），完成后再点【安装选中版本】重试\n"
                "2) 点击【刷新】后再重试安装（确保设备连接状态正常）\n"
                "3) 如果仍失败：\n"
                "   - 说明安装包签名确实不一致（HAP/HSP 不同证书或不是同一次构建）\n"
                "   - 请让构建/打包同事确认该版本的 HAP 与 HSP 来自同一次构建、同一证书签名\n\n"
                "如果你愿意，把客户端日志里 bm install 的完整输出发我，我可以进一步判断是哪一种冲突。"
            )

        return text if text else "HDC 执行失败，请确认设备连接与授权后重试。"

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
                self.show_warning(
                    "警告", "未获取到设备UDID。\n\n请确认设备已连接并完成 HDC 授权，然后点击“刷新”重试。")
        else:
            self.show_error(
                "错误", f"获取UDID失败:\n{self.format_hdc_error(output)}")

    def show_udid_dialog(self, udid):
        """显示带有复制按钮的 UDID 对话框"""
        # 先创建对话框
        dialog = tk.Toplevel(self.root)
        try:
            dialog.attributes('-alpha', 0.0)
        except Exception:
            pass
        dialog.withdraw()
        dialog.title("设备 UDID")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.configure(bg=self.colors['bg_secondary'])

        try:
            dialog.attributes('-alpha', 0.0)
        except Exception:
            pass

        content = tk.Frame(dialog, bg=self.colors['bg_secondary'])
        content.pack(fill=tk.BOTH, expand=True, padx=20, pady=18)

        udid_label = tk.Label(content, text="设备UDID:",
                              font=('Segoe UI', 12, 'bold'),
                              bg=self.colors['bg_secondary'], fg=self.colors['text_primary'])
        udid_label.pack(anchor='w', pady=(0, 10))

        udid_card = tk.Frame(content, bg=self.colors['bg_card'], highlightthickness=1,
                             highlightbackground=self.colors['border'])
        udid_card.pack(fill=tk.X)

        udid_value = tk.Label(
            udid_card,
            text=str(udid),
            font=('Consolas', 11),
            bg=self.colors['bg_card'],
            fg=self.colors['text_primary'],
            justify='left',
            anchor='w',
            wraplength=400
        )
        udid_value.pack(fill=tk.X, padx=12, pady=12)

        # Button frame
        button_frame = tk.Frame(content, bg=self.colors['bg_secondary'])
        button_frame.pack(fill=tk.X, pady=(16, 0))

        cancel_btn = tk.Button(button_frame, text="取消", command=dialog.destroy)
        self._style_dialog_button_widget(
            cancel_btn,
            bg=self.colors['bg_selection'],
            fg=self.colors['text_primary'],
            active_bg='#343A3F',
            active_fg=self.colors['text_primary'],
            bold=False,
            secondary=True
        )
        cancel_btn.pack(side='right')

        copy_btn = tk.Button(button_frame, text="复制 UDID",
                             command=lambda: self.copy_udid(udid))
        self._style_dialog_button_widget(
            copy_btn,
            bg=self.colors['bg_accent'],
            fg='white',
            active_bg=self.colors['hover'],
            active_fg='white',
            bold=True,
            secondary=False
        )
        copy_btn.pack(side='right', padx=(0, 10))

        # Update window to ensure it's ready
        dialog.update_idletasks()

        self.center_window(dialog, 460, 240)

        try:
            dialog.update_idletasks()
        except Exception:
            pass

        try:
            dialog.deiconify()
            dialog.lift()
            dialog.focus_force()
        except Exception:
            pass

        try:
            dialog.attributes('-alpha', 1.0)
        except Exception:
            pass

        # Make modal
        dialog.grab_set()
        dialog.focus_set()

    def copy_udid(self, udid):
        """将 UDID 复制到剪贴板，显示提示并关闭对话框"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(udid)
            self.show_toast("UDID 复制成功!")
            # Find and close the dialog
            for widget in self.root.winfo_children():
                if isinstance(widget, tk.Toplevel) and widget.title() == "设备 UDID":
                    widget.destroy()
                    break
        except Exception as e:
            self.log(f"复制 UDID 失败: {str(e)}")
            self.show_toast(f"复制 UDID 失败: {str(e)}")

    def show_toast(self, message):
        """显示提示"""
        toast = getattr(self, '_toast_window', None)
        toast_label = getattr(self, '_toast_label', None)
        toast_after_id = getattr(self, '_toast_after_id', None)
        toast_canvas = getattr(self, '_toast_canvas', None)
        toast_text_id = getattr(self, '_toast_text_id', None)

        # Calculate position before creating window
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        main_height = self.root.winfo_height()

        scale = 1.0
        try:
            scale = float(getattr(self, 'ui_scale', 1.0) or 1.0)
        except Exception:
            scale = 1.0
        toast_width = max(180, int(round(180 * scale)))
        toast_height = max(36, int(round(36 * scale)))
        toast_radius = max(18, int(round(18 * scale)))
        x = main_x + (main_width // 2) - (toast_width // 2)
        y = main_y + (main_height // 2) - (toast_height // 2)
        try:
            header = getattr(self, 'header_frame', None)
            if header is not None and header.winfo_exists():
                header_y = int(header.winfo_rooty())
                header_h = int(header.winfo_height())
                if header_h > 0:
                    y = header_y + (header_h // 2) - (toast_height // 2)
        except Exception:
            pass

        try:
            if toast is None or not toast.winfo_exists():
                toast = tk.Toplevel(self.root)
                toast.overrideredirect(True)
                transparent_key = '#010203'
                toast.configure(bg=transparent_key)
                toast.withdraw()
                try:
                    toast.attributes('-alpha', 0.0)
                except Exception:
                    pass
                try:
                    toast.attributes('-topmost', True)
                except Exception:
                    pass

                try:
                    toast.attributes('-transparentcolor', transparent_key)
                except Exception:
                    pass

                def _round_rect(canvas, x1, y1, x2, y2, r, **kwargs):
                    points = [
                        x1 + r, y1,
                        x2 - r, y1,
                        x2, y1,
                        x2, y1 + r,
                        x2, y2 - r,
                        x2, y2,
                        x2 - r, y2,
                        x1 + r, y2,
                        x1, y2,
                        x1, y2 - r,
                        x1, y1 + r,
                        x1, y1,
                    ]
                    return canvas.create_polygon(points, smooth=True, **kwargs)

                toast_canvas = tk.Canvas(
                    toast,
                    width=toast_width,
                    height=toast_height,
                    bg=transparent_key,
                    highlightthickness=0,
                    bd=0,
                )
                toast_canvas.pack(fill='both', expand=True)

                _round_rect(toast_canvas, 0, 0, toast_width, toast_height, toast_radius,
                            fill='#2F3336', outline='')
                toast_text_id = toast_canvas.create_text(
                    toast_width // 2,
                    toast_height // 2,
                    text='',
                    fill='#E7E9EA',
                    font=getattr(self, 'fonts', {}).get(
                        'body', ('Segoe UI', 10)),
                )

                toast_label = None

                self._toast_window = toast
                self._toast_label = toast_label
                self._toast_canvas = toast_canvas
                self._toast_text_id = toast_text_id
                self._toast_after_id = None
        except Exception:
            return

        try:
            toast.geometry(f"{toast_width}x{toast_height}+{x}+{y}")
        except Exception:
            pass

        try:
            if toast_canvas is not None and toast_text_id is not None:
                try:
                    toast_canvas.itemconfigure(toast_text_id, text=message)
                except Exception:
                    pass
            elif toast_label is not None:
                toast_label.configure(text=message)
        except Exception:
            pass

        try:
            if toast_after_id is not None:
                toast.after_cancel(toast_after_id)
        except Exception:
            pass

        try:
            toast.update_idletasks()
        except Exception:
            pass

        try:
            toast.deiconify()
            toast.lift()
        except Exception:
            pass

        try:
            try:
                toast.attributes('-topmost', True)
            except Exception:
                pass
            toast.attributes('-alpha', 1.0)
        except Exception:
            pass

        def _hide_toast():
            try:
                if toast is None or not toast.winfo_exists():
                    return
            except Exception:
                return

            try:
                toast.attributes('-alpha', 0.0)
            except Exception:
                pass
            try:
                toast.withdraw()
            except Exception:
                pass
            self._toast_after_id = None

        try:
            self._toast_after_id = toast.after(3000, _hide_toast)
        except Exception:
            pass

    def install_selected_version(self):
        """安装选中版本"""
        selection = self.version_tree.selection()
        if not selection:
            self.show_warning("警告", "请选择要安装的版本")
            return

        if not self.current_app:
            self.show_warning("警告", "请选择应用")
            return

        selected_iid = selection[0]
        version_info = None
        try:
            version_info = (getattr(self, '_version_item_map',
                            {}) or {}).get(selected_iid)
        except Exception:
            version_info = None

        version_id = None
        version_str = None
        if isinstance(version_info, dict):
            version_id = version_info.get('id')
            version_str = version_info.get('version')

        if not version_id:
            self.show_error("错误", "无法获取选中版本，请先刷新版本列表后重试。")
            return

        if version_str is None:
            version_str = ''

        self.log(
            f"&#x1d4cb; &#x9009;&#x4e2d;&#x7684;&#x7248;&#x672c;&#x53f7;: '{version_str}' (version_id={version_id})")

        try:
            self.root.after(0, self._install_spinner_start)
        except Exception:
            try:
                self._install_spinner_start()
            except Exception:
                pass

        thread = threading.Thread(
            target=self.install_app_version, args=(version_info,))
        thread.daemon = True
        thread.start()

    def install_app_version(self, version_info):
        """安装应用版本"""
        if not version_info:
            return
        version_id = version_info.get('id')
        version_str = version_info.get('version')
        try:
            self.log(f"🚀 开始安装版本ID {version_id} 版本号 {version_str}")

            try:
                dev_ok, dev_out = self.run_hdc_command(
                    "list targets", show_output=False)
                lines = [ln.strip()
                         for ln in (dev_out or '').splitlines() if ln.strip()]
                if not dev_ok or len(lines) == 0:
                    self.show_error("错误", "未检测到已连接设备，请通过 USB 连接鸿蒙设备后重试。")
                    return
            except Exception:
                self.show_error("错误", "设备检测失败，请通过 USB 连接鸿蒙设备后重试。")
                return

            # 下载文件
            if not self.download_version_files(version_info):
                return

            # 获取本地文件路径
            app_download_dir = os.path.join(
                self.download_dir, str(self.current_app['id']), str(version_info['id']))
            hap_file = os.path.join(
                app_download_dir, version_info['files']['hap'])
            hsp_file = os.path.join(
                app_download_dir, version_info['files']['hsp'])

            # 转换为绝对路径，避免相对路径问题
            hap_file = os.path.abspath(hap_file)
            hsp_file = os.path.abspath(hsp_file)

            self.log(f"📁 HAP文件绝对路径: {hap_file}")
            self.log(f"📁 HSP文件绝对路径: {hsp_file}")

            deploy_path = version_info.get(
                'deploy_path', f"data/local/tmp/{self.current_app['id']}")

            # Ensure deploy_path uses forward slashes for Android
            deploy_path = deploy_path.replace('\\', '/')
            self.log(f"Deploy path (Android format): {deploy_path}")

            # 检查文件是否存在
            if not os.path.exists(hap_file):
                self.log(f"❌ HAP文件不存在: {hap_file}")
                self.show_error(
                    "错误", f"HAP文件不存在:\n{hap_file}\n\n请检查下载是否完成或文件是否被删除。")
                return

            if not os.path.exists(hsp_file):
                self.log(f"❌ HSP文件不存在: {hsp_file}")
                self.show_error(
                    "错误", f"HSP文件不存在:\n{hsp_file}\n\n请检查下载是否完成或文件是否被删除。")
                return

            self.log(
                f"✅ 文件检查通过: HAP={os.path.basename(hap_file)}, HSP={os.path.basename(hsp_file)}")

            # 安装步骤
            android_deploy_path = deploy_path.replace('\\', '/')
            hap_remote = f"{android_deploy_path}/{os.path.basename(hap_file)}"
            hsp_remote = f"{android_deploy_path}/{os.path.basename(hsp_file)}"
            steps = [
                ("停止应用",
                 f"shell aa force-stop {self.current_app['bundle_name']}"),
                ("彻底卸载旧版本",
                 f"shell bm uninstall -n {self.current_app['bundle_name']}"),
                ("清理安装包缓存", f"shell rm -f {hsp_remote} {hap_remote}"),
                ("上传HSP", f"file send {hsp_file} {android_deploy_path}"),
                ("上传HAP", f"file send {hap_file} {android_deploy_path}"),
                ("安装应用", f"shell bm install -p {hsp_remote} -p {hap_remote}"),
                ("启动应用",
                 f"shell aa start -a {self.current_app['main_ability']} -b {self.current_app['bundle_name']} -m entry")
            ]

            for step_name, command in steps:
                self.log(f"&#x1f4cb; {step_name}...")
                success, output = self.run_hdc_command(
                    command, show_output=True)

                # &#x663e;&#x793a;&#x547d;&#x4ee4;&#x8f93;&#x51fa;
                if output:
                    self.log(f"&#x1d4cb; &#x8f93;&#x51fa;: {output.strip()}")

                # &#x68c0;&#x67e5;&#x662f;&#x5426;&#x5931;&#x8d25;
                if not success:
                    self.log(f"&#x274c; {step_name}&#x5931;&#x8d25;")

                    # &#x5bf9;&#x4e8e;&#x67d0;&#x4e9b;&#x6b65;&#x9aa4;&#xff0c;&#x5931;&#x8d25;&#x662f;&#x53ef;&#x63a5;&#x53d7;&#x7684;
                    if step_name in ["停止应用", "彻底卸载旧版本"]:
                        self.log(
                            f"&#x26a0;&#xfe0f; {step_name}&#x5931;&#x8d25;&#xff0c;&#x4f46;&#x7ee7;&#x7eed;&#x6267;&#x884c;")
                        continue
                    elif step_name == "启动应用":
                        self.log(
                            f"&#x26a0;&#xfe0f; {step_name}&#x5931;&#x8d25;&#xff0c;&#x4f46;&#x5b89;&#x88c5;&#x53ef;&#x80fd;&#x6210;&#x529f;")
                        continue
                    else:
                        # &#x5173;&#x952e;&#x6b65;&#x9aa4;&#x5931;&#x8d25;&#xff0c;&#x505c;&#x6b62;&#x5b89;&#x88c5;
                        self.show_error(
                            "错误", f"{step_name}失败:\n{self.format_hdc_error(output)}")
                        return

            # &#x9a8c;&#x8bc1;&#x5e94;&#x7528;&#x662f;&#x5426;&#x771f;&#x6b63;&#x5b89;&#x88c5;&#x6210;&# Verify if app is truly installed successfully
            self.log("Verifying installation result...")

            # Wait a moment for installation to complete
            time.sleep(2)

            # Method 1: Use bm dump to check if app is installed
            verify_success, verify_output = self.run_hdc_command(
                f"shell bm dump -n {self.current_app['bundle_name']}", show_output=True)

            # Method 2: Use bm dump -a to list all installed apps
            list_success, list_output = self.run_hdc_command(
                "shell bm dump -a", show_output=False)

            app_installed = False
            verify_low = (verify_output or '').lower()
            list_low = (list_output or '').lower()
            if verify_success and verify_output and "error:" not in verify_low and "[fail]" not in verify_low and "need connect-key" not in verify_low:
                app_installed = True
                self.log("App installation verification successful (bm dump)")
            elif list_success and list_output and "[fail]" not in list_low and "need connect-key" not in list_low and self.current_app['bundle_name'] in list_output:
                app_installed = True
                self.log("App installation verification successful (bm dump -a)")

            if app_installed:
                self.log("Installation completed successfully")
                self._show_modal_dialog(
                    "安装成功", f"应用版本 {version_str} 安装成功！\n\n请在设备上验证", 'info', [('确定', True)])

                # Try to start the app
                self.log("Attempting to start the app...")
                start_success, start_output = self.run_hdc_command(
                    f"shell aa start -a {self.current_app['main_ability']} -b {self.current_app['bundle_name']} -m entry", show_output=True)
                if start_success:
                    self.log("App started successfully")
                else:
                    self.log(
                        f"App start failed, but installation succeeded: {start_output}")
            else:
                self.log("Installation verification failed")
                self.log(f"bm dump output: {verify_output}")
                self.log(f"bm dump -a output: {list_output}")
                self.show_warning(
                    "安装警告", "应用安装完成但验证失败。\n\n应用可能未正确安装。\n\n请在设备上手动检查。")
        except Exception as e:
            self.log(f"&#x274c; &#x5b89;&#x88c5;&#x5f02;&#x5e38;: {str(e)}")
            self.show_error("安装错误", f"安装异常：{str(e)}")

        finally:
            try:
                self.root.after(0, self._install_spinner_stop)
            except Exception:
                try:
                    self._install_spinner_stop()
                except Exception:
                    pass
            try:
                self.root.after(0, lambda: hasattr(
                    self, 'install_button') and self.install_button.config(state='normal'))
            except Exception:
                try:
                    self.install_button.config(state='normal')
                except Exception:
                    pass

    def get_version_info_by_id(self, version_id):
        """通过 version_id 获取版本信息（精确，避免版本号重复歧义）"""
        try:
            vid = int(version_id)
        except Exception:
            return None

        try:
            url = f"{self.server_base_url}/api/versions/{vid}/info"
            self.log(f"🌐 获取版本信息: {url}")

            response = requests.get(url, headers=self._get_api_headers(), timeout=10)
            if response.status_code == 401:
                error_msg = 'API Key 无效或已过期'
                try:
                    error_data = response.json()
                    if error_data.get('error'):
                        error_msg = error_data.get('error')
                except Exception:
                    pass
                self.log(f"❌ 认证失败: {error_msg}")
                return None
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, dict):
                    # /info 为兼容旧格式可能不带 id，这里补齐，供下载/安装流程使用
                    data['id'] = vid
                return data
            else:
                self.log(f"❌ 版本信息获取失败: HTTP {response.status_code}")
                return None
        except requests.exceptions.RequestException:
            return None
        except Exception as e:
            self.log(f"❌ 版本信息获取失败: {str(e)}")
            return None

    def download_version_files(self, version_info):
        """下载版本文件"""
        try:
            # 检查version_info是否为字典类型
            if not isinstance(version_info, dict):
                self.log(f"❌ 版本信息格式错误: 期望字典，实际收到 {type(version_info)}")
                self.show_error("错误", f"版本信息格式错误: {type(version_info)}")
                return False

            version_id = version_info.get('id')
            if not version_id:
                self.log("❌ 版本信息中缺少 version_id，无法下载文件")
                self.show_error("错误", "版本信息中缺少 version_id，无法下载文件")
                return False

            files = version_info.get('files', {})
            if not isinstance(files, dict):
                self.log(f"❌ 文件信息格式错误: 期望字典，实际收到 {type(files)}")
                self.show_error("错误", f"文件信息格式错误: {type(files)}")
                return False

            hap_filename = files.get('hap')
            hsp_filename = files.get('hsp')

            if not hap_filename or not hsp_filename:
                self.log("❌ 版本信息中缺少文件信息")
                self.show_error("错误", "版本信息中缺少文件信息")
                return False

            # 创建app_id对应的下载目录
            app_download_dir = os.path.join(
                self.download_dir, str(self.current_app['id']), str(version_id))
            if not os.path.exists(app_download_dir):
                os.makedirs(app_download_dir)
                self.log(f"📁 创建应用下载目录: {app_download_dir}")

            # 下载HAP文件
            hap_url = f"{self.server_base_url}/api/versions/{version_id}/files/hap/download"
            hap_local_path = os.path.join(app_download_dir, hap_filename)

            if not self._is_local_file_complete(hap_url, hap_local_path):
                self.log(f"📥 下载HAP文件: {hap_filename}")
                if not self.download_file(hap_url, hap_local_path):
                    return False
            else:
                self.log(f"✅ HAP文件已存在: {hap_filename}")

            # 下载HSP文件
            hsp_url = f"{self.server_base_url}/api/versions/{version_id}/files/hsp/download"
            hsp_local_path = os.path.join(app_download_dir, hsp_filename)

            if not self._is_local_file_complete(hsp_url, hsp_local_path):
                self.log(f"📥 下载HSP文件: {hsp_filename}")
                if not self.download_file(hsp_url, hsp_local_path):
                    return False
            else:
                self.log(f"✅ HSP文件已存在: {hsp_filename}")

            return True

        except Exception as e:
            self.log(f"❌ 文件下载失败: {str(e)}")
            self.show_error("错误", f"文件下载失败: {str(e)}")
            return False

    def download_file(self, url, local_path):
        """下载单个文件"""
        try:
            tmp_path = f"{local_path}.part"
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

            response = requests.get(url, headers=self._get_api_headers(), stream=True, timeout=30)
            if response.status_code == 401:
                error_msg = 'API Key 无效或已过期'
                try:
                    error_data = response.json()
                    if error_data.get('error'):
                        error_msg = error_data.get('error')
                except Exception:
                    pass
                self.log(f"❌ 下载失败 - 认证失败: {error_msg}")
                return False
            if response.status_code == 200:
                total_size = int(response.headers.get(
                    'content-length', 0) or 0)
                downloaded = 0

                with open(tmp_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)

                            if total_size > 0:
                                progress = (downloaded / total_size) * 100
                                self.log(f"📊 下载进度: {progress:.1f}%")

                if total_size > 0 and downloaded != total_size:
                    try:
                        os.remove(tmp_path)
                    except Exception:
                        pass
                    self.log(
                        f"❌ 下载不完整: {os.path.basename(local_path)} ({downloaded}/{total_size})")
                    return False

                try:
                    os.replace(tmp_path, local_path)
                except Exception:
                    try:
                        if os.path.exists(local_path):
                            os.remove(local_path)
                    except Exception:
                        pass
                    os.replace(tmp_path, local_path)

                self.log(f"✅ 文件下载完成: {os.path.basename(local_path)}")
                return True
            else:
                self.log(f"❌ 下载失败: HTTP {response.status_code}")
                return False

        except Exception as e:
            self.log(f"❌ 下载异常: {str(e)}")
            try:
                tmp_path = f"{local_path}.part"
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass
            return False

    def _is_local_file_complete(self, url, local_path):
        try:
            if not os.path.exists(local_path):
                return False
        except Exception:
            return False

        expected = 0
        try:
            r = requests.head(url, timeout=10, allow_redirects=True)
            if r.status_code in (200, 206):
                expected = int(r.headers.get('content-length', 0) or 0)
        except Exception:
            expected = 0

        if expected <= 0:
            return True

        try:
            actual = os.path.getsize(local_path)
        except Exception:
            return False

        if actual == expected:
            return True

        try:
            os.remove(local_path)
        except Exception:
            pass
        return False

    def uninstall_current_app(self):
        """卸载当前应用"""
        if not self.current_app:
            self.show_warning("警告", "请先选择要卸载的应用")
            return

        try:
            dev_ok, dev_out = self.run_hdc_command(
                "list targets", show_output=False)
            lines = [ln.strip()
                     for ln in (dev_out or '').splitlines() if ln.strip()]
            if not dev_ok or len(lines) == 0:
                self.show_error(
                    "卸载失败", "未检测到已连接设备，请通过 USB 连接鸿蒙设备并完成 HDC 授权后重试。")
                return
        except Exception:
            self.show_error("卸载失败", "设备检测失败，请通过 USB 连接鸿蒙设备并完成 HDC 授权后重试。")
            return

        self.log(f"🗑️ 卸载应用: {self.current_app['name']}")

        # Clean uninstall (do not keep data) to avoid signature conflicts
        success, output = self.run_hdc_command(
            f"shell bm uninstall -n {self.current_app['bundle_name']}")

        if success:
            self.log("✅ 卸载成功")
            # self._show_modal_dialog("卸载成功", "应用卸载成功", 'info', [('确定', True)])
            self.show_toast("应用卸载成功")
        else:
            self.log(f"❌ 卸载失败: {output}")
            self.show_error(
                "卸载失败", f"应用卸载失败：\n{self.format_hdc_error(output)}")

    def refresh_all(self):
        """刷新所有信息"""
        self.log("🔄 刷新中...")
        self.detect_hdc_tool()
        try:
            if hasattr(self, 'app_tree'):
                sel = self.app_tree.selection()
                if sel:
                    self.app_tree.selection_remove(sel)
        except Exception:
            pass
        try:
            if hasattr(self, 'version_tree'):
                sel = self.version_tree.selection()
                if sel:
                    self.version_tree.selection_remove(sel)
        except Exception:
            pass
        try:
            self.current_app = None
            self.current_version = None
        except Exception:
            pass
        self.load_apps_list_async()

    def configure_server(self):
        """配置服务器地址和下载目录"""
        dialog = tk.Toplevel(self.root)
        dialog.withdraw()
        dialog.title("设置")
        dialog.configure(bg=self.colors['bg_secondary'])
        dialog.resizable(True, True)

        try:
            dialog.attributes('-alpha', 0.0)
        except Exception:
            pass

        # 设为模态对话框
        dialog.transient(self.root)
        dialog.grab_set()

        # 居中显示
        dialog.update_idletasks()
        self.center_window(dialog, 620, 520)

        # 变量来跟踪用户选择
        config_saved = [False]

        content = tk.Frame(dialog, bg=self.colors['bg_secondary'])
        content.pack(fill=tk.BOTH, expand=True, padx=24, pady=20)

        title_label = tk.Label(content, text="⚙️ 设置",
                               font=self.fonts['title'],
                               fg=self.colors['text_primary'],
                               bg=self.colors['bg_secondary'])
        title_label.pack(pady=(0, 16))

        form_card = tk.Frame(content, bg=self.colors['bg_card'], highlightthickness=1,
                             highlightbackground=self.colors['border'])
        form_card.pack(fill='x')

        config_frame = tk.Frame(form_card, bg=self.colors['bg_card'])
        config_frame.pack(padx=18, pady=16, fill='x')

        # 服务器地址输入
        tk.Label(config_frame, text="🌐 服务器地址:",
                 font=self.fonts['body'],
                 fg=self.colors['text_secondary'],
                 bg=self.colors['bg_card']).pack(anchor='w', pady=(0, 6))

        url_entry = tk.Entry(config_frame)
        self._style_entry_widget(url_entry)
        url_entry.pack(fill='x', ipady=6, pady=(0, 14))
        url_entry.insert(0, self.server_base_url)

        # API Key 输入
        tk.Label(config_frame, text="🔑 API Key:",
                 font=self.fonts['body'],
                 fg=self.colors['text_secondary'],
                 bg=self.colors['bg_card']).pack(anchor='w', pady=(0, 6))

        api_key_entry = tk.Entry(config_frame, show='*')
        self._style_entry_widget(api_key_entry)
        api_key_entry.pack(fill='x', ipady=6, pady=(0, 14))
        api_key_entry.insert(0, self.api_key)

        # 下载目录输入
        tk.Label(config_frame, text="📁 下载目录:",
                 font=self.fonts['body'],
                 fg=self.colors['text_secondary'],
                 bg=self.colors['bg_card']).pack(anchor='w', pady=(0, 6))

        download_frame = tk.Frame(config_frame, bg=self.colors['bg_card'])
        download_frame.pack(fill='x', pady=(0, 4))

        download_entry = tk.Entry(download_frame)
        self._style_entry_widget(download_entry)
        download_entry.pack(side='left', fill='x', expand=True, ipady=6)
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
                               command=browse_directory)
        self._style_dialog_button_widget(
            browse_btn,
            bg=self.colors['bg_selection'],
            fg=self.colors['text_primary'],
            active_bg='#343A3F',
            active_fg=self.colors['text_primary'],
            bold=False,
            secondary=True
        )
        browse_btn.pack(side='right', padx=(10, 0))

        # 说明文本
        info_text = """配置说明：
• 服务器地址：提供应用和版本信息的API端点
• API Key：SaaS系统认证密钥，由管理员分配
• 下载目录：存储下载的HAP/HSP文件
• 配置会自动保存，下次启动时加载
• 必须确保服务器地址正确且可访问
• 未设置API Key将无法访问受保护的API端点"""

        info_card = tk.Frame(content, bg=self.colors['bg_card'], highlightthickness=1,
                             highlightbackground=self.colors['border'])
        info_card.pack(fill='x', pady=(14, 0))

        info_label = tk.Label(info_card, text=info_text,
                              font=self.fonts['small'],
                              fg=self.colors['text_muted'],
                              bg=self.colors['bg_card'],
                              justify='left')
        info_label.pack(anchor='w', padx=18, pady=14)

        button_frame = tk.Frame(content, bg=self.colors['bg_secondary'])
        button_frame.pack(fill=tk.X, pady=(18, 0))

        def save_config():
            new_url = url_entry.get().strip()
            new_download_dir = download_entry.get().strip()
            new_api_key = api_key_entry.get().strip()

            if not new_url:
                self.show_warning("警告", "请输入有效的服务器地址")
                return

            if not new_download_dir:
                self.show_warning("警告", "请输入有效的下载目录")
                return

            self.server_base_url = new_url
            self.download_dir = new_download_dir
            self.api_key = new_api_key

            # 创建新的下载目录
            if not os.path.exists(self.download_dir):
                os.makedirs(self.download_dir)

            # 保存设置
            self.save_local_settings()

            self.log(f"✅ 配置已更新")
            self.log(f"🌐 服务器地址: {new_url}")
            self.log(f"📁 下载目录: {new_download_dir}")
            if new_api_key:
                self.log(f"🔑 API Key 已设置")
            else:
                self.log(f"⚠️ 未设置 API Key")

            config_saved[0] = True
            dialog.destroy()

        def cancel_config():
            # 直接关闭配置窗口
            dialog.destroy()

        cancel_btn = tk.Button(button_frame, text="取消", command=cancel_config)
        self._style_dialog_button_widget(
            cancel_btn,
            bg=self.colors['bg_selection'],
            fg=self.colors['text_primary'],
            active_bg='#343A3F',
            active_fg=self.colors['text_primary'],
            bold=False,
            secondary=True
        )
        cancel_btn.pack(side='right')

        save_btn = tk.Button(button_frame, text="保存", command=save_config)
        self._style_dialog_button_widget(
            save_btn,
            bg=self.colors['bg_accent'],
            fg='white',
            active_bg=self.colors['hover'],
            active_fg='white',
            bold=True,
            secondary=False
        )
        save_btn.pack(side='right', padx=(0, 10))

        try:
            dialog.update_idletasks()
        except Exception:
            pass

        try:
            req_w = max(620, int(dialog.winfo_reqwidth()))
            req_h = max(520, int(dialog.winfo_reqheight()))
            screen_h = int(dialog.winfo_screenheight())
            max_h = max(300, int(screen_h * 0.85))
            final_h = min(req_h, max_h)
            self.center_window(dialog, req_w, final_h)
        except Exception:
            try:
                self.center_window(dialog, 620, 520)
            except Exception:
                pass

        try:
            dialog.deiconify()
            dialog.lift()
            dialog.focus_force()
        except Exception:
            pass

        try:
            dialog.attributes('-alpha', 1.0)
        except Exception:
            pass

        # 等待对话框关闭
        self.root.wait_window(dialog)

        # 如果配置已保存，重新加载应用列表
        if config_saved[0]:
            self.load_apps_list_async()


def main():
    try:
        import ctypes
        try:
            ctypes.windll.user32.SetProcessDpiAwarenessContext(
                ctypes.c_void_p(-4))
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass
    except Exception:
        ctypes = None

    def _win_force_foreground(hwnd):
        try:
            if ctypes is None:
                return False
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            fg = user32.GetForegroundWindow()
            if fg == hwnd:
                user32.SetForegroundWindow(hwnd)
                user32.SetFocus(hwnd)
                return True

            fg_tid = user32.GetWindowThreadProcessId(fg, None)
            cur_tid = kernel32.GetCurrentThreadId()
            try:
                user32.AttachThreadInput(cur_tid, fg_tid, True)
                user32.SetForegroundWindow(hwnd)
                user32.SetFocus(hwnd)
                return True
            finally:
                try:
                    user32.AttachThreadInput(cur_tid, fg_tid, False)
                except Exception:
                    pass
        except Exception:
            return False

    root = tk.Tk()
    root.title("HarmonyOS App Installer")
    root.withdraw()
    root.geometry("1400x900")
    root.resizable(True, True)

    # Set dark background immediately to prevent white flash
    root.configure(bg='#0F1419')

    def _set_window_icon():
        try:
            if getattr(sys, 'frozen', False):
                # PyInstaller 打包环境
                base_path = sys._MEIPASS
            else:
                # 开发环境
                base_path = os.path.dirname(os.path.abspath(__file__))

            # 优先尝试PNG格式
            png_path = os.path.join(base_path, 'logo.png')

            # 尝试使用PNG图标（需要PIL库）
            if os.path.exists(png_path):
                try:
                    from PIL import Image, ImageTk
                    img = Image.open(png_path)

                    # 确保图像有透明通道（RGBA）
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')

                    # 创建透明背景的PhotoImage
                    photo = ImageTk.PhotoImage(img)
                    root.iconphoto(True, photo)
                    # 保持引用防止垃圾回收
                    root._icon_photo = photo
                    return
                except Exception:
                    pass

        except Exception:
            pass

    _set_window_icon()

    try:
        dpi = None
        if platform.system() == 'Windows' and ctypes is not None:
            try:
                hwnd = int(root.winfo_id())
                dpi = int(ctypes.windll.user32.GetDpiForWindow(hwnd))
            except Exception:
                try:
                    dpi = int(ctypes.windll.user32.GetDpiForSystem())
                except Exception:
                    dpi = None

        if not dpi:
            try:
                dpi = float(root.winfo_fpixels('1i'))
            except Exception:
                dpi = None

        if dpi:
            root._system_dpi = float(dpi)

        pass
    except Exception:
        pass

    def _get_center_xy(target_w, target_h):
        try:
            if platform.system() == 'Windows':
                import ctypes

                class _RECT(ctypes.Structure):
                    _fields_ = [('left', ctypes.c_long), ('top', ctypes.c_long),
                                ('right', ctypes.c_long), ('bottom', ctypes.c_long)]

                SPI_GETWORKAREA = 0x0030
                rect = _RECT()
                ok = ctypes.windll.user32.SystemParametersInfoW(
                    SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
                if ok:
                    wa_w = int(rect.right - rect.left)
                    wa_h = int(rect.bottom - rect.top)
                    x = int(rect.left + (wa_w - target_w) / 2)
                    y = int(rect.top + (wa_h - target_h) / 2)
                    return x, y
        except Exception:
            pass

        try:
            x = int((root.winfo_screenwidth() // 2) - (target_w // 2))
            y = int((root.winfo_screenheight() // 2) - (target_h // 2))
            return x, y
        except Exception:
            return 0, 0

    # Center window on screen with dynamic size based on screen dimensions
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    width = int(screen_width * 2 / 3)
    height = int(screen_height * 4 / 5)
    x, y = _get_center_xy(width, height)
    root.geometry(f'{width}x{height}+{x}+{y}')

    # Create app (window is already dark)
    app = ModernDesignInstaller(root)

    # Avoid UI flashing during first layout; enable after we have a stable first frame
    root._window_visible = False

    _post_show_finalized = False

    def _post_show_finalize():
        nonlocal _post_show_finalized
        if _post_show_finalized:
            return

        try:
            if not root.winfo_ismapped():
                root.after(30, _post_show_finalize)
                return
        except Exception:
            pass

        _post_show_finalized = True

        # CRITICAL: Force layout calculation while still transparent
        try:
            root.update_idletasks()
            if hasattr(app, 'align_header_segment'):
                app.align_header_segment()
            root.update()  # Force an actual draw cycle
        except Exception:
            pass

        # 直接显示主窗口
        try:
            root.attributes('-alpha', 1.0)
        except Exception:
            pass

        _fg_ok = False
        try:
            _fg_ok = _win_force_foreground(root.winfo_id())
        except Exception:
            _fg_ok = False

        def _force_foreground_retry_once():
            try:
                _win_force_foreground(root.winfo_id())
            except Exception:
                pass

        if not _fg_ok:
            root.after(250, _force_foreground_retry_once)

        root._window_visible = True

    _show_root_after_id = None

    def _do_show_root():
        nonlocal _show_root_after_id
        _show_root_after_id = None
        root.deiconify()
        root.after(0, _post_show_finalize)
        root.after(30, _post_show_finalize)

    def _show_root():
        nonlocal _show_root_after_id
        if _show_root_after_id is not None:
            return
        _do_show_root()

    root.after(0, _show_root)

    root.mainloop()


if __name__ == "__main__":
    main()
