"""
图形界面 — PDF 导出为图片

功能：
  - 选择 PDF 文件 + 输出目录
  - 选择图片格式（PNG/JPEG/TIFF/BMP/WEBP）
  - 调节 DPI 和质量
  - 选择页面范围（全部 / 自定义）
  - 实时进度条
  - 完成后打开输出目录
"""

import os
import re
import threading
import tkinter as tk
import ctypes
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from src.converter import (
    pdf_to_images,
    SUPPORTED_FORMATS,
    FORMAT_KEYS,
    DEFAULT_FORMAT,
)


class PDF2ImageApp:
    """PDF 导出为图片 — 主窗口"""

    def __init__(self):
        self._enable_dpi_awareness()
        self.root = tk.Tk()
        self.root.title("PDF导出为图片")
        self.root.resizable(True, True)
        self._setup_style()

        self.pdf_path = tk.StringVar()
        self.out_dir = tk.StringVar()
        self.fmt_var = tk.StringVar(value=DEFAULT_FORMAT)
        self.dpi_var = tk.IntVar(value=200)
        self.quality_var = tk.IntVar(value=90)

        # 页面范围
        self.page_range_var = tk.StringVar(value="all")  # "all" 或 "custom"
        self.custom_pages_var = tk.StringVar()

        # 扫描件增强
        self.enhance_var = tk.BooleanVar(value=False)
        self.enhance_sharpness = tk.IntVar(value=80)
        self.enhance_cutoff = tk.IntVar(value=2)
        self.enhance_contrast = tk.DoubleVar(value=1.15)
        self.dpi_var.trace_add("write", lambda *_: self._refresh_summary())
        self.quality_var.trace_add("write", lambda *_: self._refresh_summary())
        self.page_range_var.trace_add("write", lambda *_: self._refresh_summary())
        self.custom_pages_var.trace_add("write", lambda *_: self._refresh_summary())

        self._build_ui()
        self._apply_initial_window_size()
        self._running = False

    @staticmethod
    def _enable_dpi_awareness():
        """尽量避免 Windows 对 Tk 窗口做模糊缩放。"""
        if os.name != "nt":
            return
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # 主题样式 — 参考 ResumeDetective (PyQt6) 设计语言
    # ------------------------------------------------------------------
    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        bg      = "#f5f5f7"    # 窗口背景
        card_bg = "#ffffff"     # 卡片/输入框背景
        fg      = "#1d1d1f"     # 主文字
        sec_fg  = "#8e8e93"     # 辅助文字
        accent  = "#007aff"     # 强调蓝
        border  = "#d8d8de"     # 边框色

        self.root.configure(bg=bg)

        font      = ("Microsoft YaHei UI", 11)
        font_sm   = ("Microsoft YaHei UI", 10)
        font_btn  = ("Microsoft YaHei UI", 11, "bold")
        font_bold = ("Microsoft YaHei UI", 11, "bold")

        # 全局默认
        style.configure(".", background=bg, foreground=fg, font=font)
        style.configure("TFrame", background=bg)
        style.configure("Card.TFrame", background=card_bg)
        style.configure("TLabel", background=card_bg, foreground=fg)
        style.configure("Card.TLabel", background=card_bg, foreground=fg)
        style.configure("Secondary.TLabel", background=card_bg, foreground=sec_fg, font=font_sm)
        style.configure("Status.TLabel", background=card_bg, foreground=sec_fg, font=font_sm)
        style.configure("Hero.TFrame", background=card_bg)
        style.configure("HeroTitle.TLabel", background=card_bg, foreground=fg,
                        font=("Microsoft YaHei UI", 18, "bold"))
        style.configure("HeroSub.TLabel", background=card_bg, foreground=sec_fg,
                        font=("Microsoft YaHei UI", 11))
        style.configure("Hint.TLabel", background=card_bg, foreground=sec_fg,
                        font=font_sm)
        style.configure("Value.TLabel", background=card_bg, foreground=accent,
                        font=("Microsoft YaHei UI", 11, "bold"))

        # 标题区
        style.configure("Header.TLabel", background=card_bg, foreground=fg,
                        font=font_bold)

        # 主按钮 — 蓝色
        style.configure("TButton", background=accent, foreground="white",
                        borderwidth=0, focuscolor="none", font=font_btn,
                        padding=(30, 10))
        style.map("TButton",
                   background=[("active", "#0066d9")],
                   relief=[("pressed", "flat")])

        # 次要按钮 — 白底 + 边框（如 ResumeDetective）
        style.configure("Browse.TButton", background=card_bg, foreground=fg,
                        borderwidth=1, focuscolor="none",
                        font=font, padding=(10, 6))
        style.map("Browse.TButton",
                   background=[("active", "#f0f3f6"), ("pressed", "#e7ebf0")],
                   relief=[("pressed", "sunken")])

        # 输入框 — 白底 + 边框
        style.configure("TEntry", fieldbackground=card_bg, borderwidth=1,
                        bordercolor=border, padding=(10, 7))
        style.configure("TCombobox", fieldbackground=card_bg, borderwidth=1,
                        bordercolor=border, padding=(8, 5),
                        arrowcolor=sec_fg)
        style.configure("TRadiobutton", background=card_bg, foreground=fg,
                        indicatorforeground=accent)
        style.configure("TCheckbutton", background=card_bg, foreground=fg,
                        indicatorforeground=accent)
        style.map("TRadiobutton", background=[("active", card_bg)])
        style.map("TCheckbutton", background=[("active", card_bg)])

        # 滑块
        style.configure("Horizontal.TScale", background=card_bg, troughcolor="#e8e8ed",
                        slidercolor=accent, sliderlength=20, borderwidth=0)

        # 进度条
        style.configure("TProgressbar", background=accent, troughcolor="#e8e8ed",
                        borderwidth=0, thickness=6)

        # 分隔线
        style.configure("TSeparator", background="#e5e5ea")

        # LabelFrame — 卡片分组
        style.configure("Card.TLabelframe", background=card_bg, foreground=fg,
                        bordercolor=border, borderwidth=1, relief="solid",
                        padding=8)
        style.configure("Card.TLabelframe.Label", background=card_bg, foreground=fg,
                        font=font_sm)

    # ------------------------------------------------------------------
    # 布局
    # ------------------------------------------------------------------
    def _build_ui(self):
        main = ttk.Frame(self.root, padding=18)
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(0, weight=1)

        hero = ttk.Frame(main, style="Hero.TFrame", padding=(18, 16))
        hero.grid(row=0, column=0, sticky=tk.EW, pady=(0, 12))
        hero.columnconfigure(0, weight=1)
        ttk.Label(hero, text="PDF 导出为图片", style="HeroTitle.TLabel").grid(
            row=0, column=0, sticky=tk.W
        )
        ttk.Label(
            hero,
            text="把 PDF 页面批量导出成清晰图片，适合留档、发图和打印前检查。",
            style="HeroSub.TLabel",
        ).grid(row=1, column=0, sticky=tk.W, pady=(6, 12))
        stats = ttk.Frame(hero, style="Hero.TFrame")
        stats.grid(row=2, column=0, sticky=tk.W)
        self.summary_var = tk.StringVar(value="PNG · 200 DPI · 全部页面")
        ttk.Label(stats, text="当前配置", style="Hint.TLabel").pack(side=tk.LEFT)
        ttk.Label(stats, textvariable=self.summary_var, style="Value.TLabel").pack(
            side=tk.LEFT, padx=(8, 0)
        )

        # ── 文件区卡片 ──
        file_card = ttk.LabelFrame(main, text="文件位置", style="Card.TLabelframe",
                                   padding=(12, 10))
        file_card.grid(row=1, column=0, sticky=tk.EW, pady=(0, 12))
        file_card.columnconfigure(0, weight=1)

        # PDF 文件
        ttk.Label(file_card, text="PDF 文件", style="Header.TLabel").grid(
            row=0, column=0, sticky=tk.W, pady=(0, 4))
        pdf_row = ttk.Frame(file_card, style="Card.TFrame")
        pdf_row.grid(row=1, column=0, sticky=tk.EW)
        pdf_row.columnconfigure(0, weight=1)
        ttk.Entry(pdf_row, textvariable=self.pdf_path).grid(
            row=0, column=0, sticky=tk.EW, padx=(0, 6))
        ttk.Button(pdf_row, text="浏览…", command=self._browse_pdf,
                   style="Browse.TButton").grid(row=0, column=1)
        ttk.Label(file_card, text="选择一个 PDF，程序会自动带出默认输出文件夹。",
                  style="Secondary.TLabel").grid(row=2, column=0, sticky=tk.W, pady=(4, 0))

        # 输出目录
        ttk.Label(file_card, text="输出目录", style="Header.TLabel").grid(
            row=3, column=0, sticky=tk.W, pady=(12, 4))
        out_row = ttk.Frame(file_card, style="Card.TFrame")
        out_row.grid(row=4, column=0, sticky=tk.EW)
        out_row.columnconfigure(0, weight=1)
        ttk.Entry(out_row, textvariable=self.out_dir).grid(
            row=0, column=0, sticky=tk.EW, padx=(0, 6))
        ttk.Button(out_row, text="浏览…", command=self._browse_output,
                   style="Browse.TButton").grid(row=0, column=1)
        ttk.Label(file_card, text="建议使用单独文件夹，避免和原有图片混在一起。",
                  style="Secondary.TLabel").grid(row=5, column=0, sticky=tk.W, pady=(4, 0))

        # ── 选项区卡片 ──
        opt_card = ttk.LabelFrame(main, text="导出设置", style="Card.TLabelframe",
                                  padding=(12, 10))
        opt_card.grid(row=2, column=0, sticky=tk.EW, pady=(0, 12))
        opt_card.columnconfigure(0, weight=1)

        # 图片格式 + DPI 同行
        row_fmt = ttk.Frame(opt_card, style="Card.TFrame")
        row_fmt.grid(row=0, column=0, sticky=tk.W, pady=(0, 8))
        ttk.Label(row_fmt, text="格式", style="Header.TLabel").pack(
            side=tk.LEFT, padx=(0, 8))
        self.fmt_combo = ttk.Combobox(
            row_fmt, textvariable=self.fmt_var, values=FORMAT_KEYS,
            state="readonly", width=10)
        self.fmt_combo.pack(side=tk.LEFT)
        self.fmt_combo.bind("<<ComboboxSelected>>", self._on_fmt_change)
        self.fmt_desc = ttk.Label(row_fmt, text="", style="Secondary.TLabel")
        self.fmt_desc.pack(side=tk.LEFT, padx=(10, 0))
        self._update_fmt_desc()

        row_dpi = ttk.Frame(opt_card, style="Card.TFrame")
        row_dpi.grid(row=1, column=0, sticky=tk.W, pady=(0, 8))
        ttk.Label(row_dpi, text="DPI", style="Header.TLabel").pack(
            side=tk.LEFT, padx=(0, 8))
        for val in (150, 200, 300, 400):
            ttk.Radiobutton(
                row_dpi, text=str(val), variable=self.dpi_var, value=val
            ).pack(side=tk.LEFT, padx=6)

        # 质量（仅 JPEG/WEBP）
        self.quality_frame = ttk.Frame(opt_card, style="Card.TFrame")
        self.quality_frame.grid(row=2, column=0, sticky=tk.W, pady=(0, 8))
        self.quality_frame.grid_remove()
        ttk.Label(self.quality_frame, text="质量",
                  style="Header.TLabel").pack(side=tk.LEFT, padx=(0, 8))
        self.quality_scale = ttk.Scale(
            self.quality_frame, from_=10, to=100,
            variable=self.quality_var, orient=tk.HORIZONTAL, length=220)
        self.quality_scale.pack(side=tk.LEFT)
        self.quality_label = ttk.Label(self.quality_frame, text="90", width=3)
        self.quality_label.pack(side=tk.LEFT, padx=(4, 4))
        ttk.Label(self.quality_frame, text="JPEG / WEBP",
                  style="Secondary.TLabel").pack(side=tk.LEFT)
        self.quality_var.trace_add("write", lambda *_: self.quality_label.config(
            text=str(self.quality_var.get())))

        # 扫描件增强
        row_enh = ttk.Frame(opt_card, style="Card.TFrame")
        row_enh.grid(row=3, column=0, sticky=tk.W, pady=(0, 4))
        self.enhance_cb = ttk.Checkbutton(
            row_enh, text="扫描件增强",
            variable=self.enhance_var,
            command=self._on_enhance_toggle,
        )
        self.enhance_cb.pack(side=tk.LEFT)
        ttk.Label(row_enh, text="锐化 / 去黄 / 对比度",
                  style="Secondary.TLabel").pack(side=tk.LEFT, padx=(6, 0))

        # ── 增强参数（默认隐藏）──
        self.enhance_params_frame = ttk.Frame(opt_card, style="Card.TFrame",
                                               padding=(8, 6))
        self.enhance_params_frame.grid(row=4, column=0, sticky=tk.EW, pady=(4, 0))
        self.enhance_params_frame.grid_remove()

        # 锐化
        ttk.Label(self.enhance_params_frame,
                  text="锐化", font=("Microsoft YaHei UI", 10)).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 4))
        ttk.Scale(self.enhance_params_frame, from_=0, to=200,
                  variable=self.enhance_sharpness, orient=tk.HORIZONTAL,
                  length=220).grid(row=0, column=1, padx=(0, 4))
        self.sharp_label = ttk.Label(self.enhance_params_frame,
                                     text="80", width=4, font=("Microsoft YaHei UI", 10))
        self.sharp_label.grid(row=0, column=2)
        self.enhance_sharpness.trace_add("write", lambda *_: self.sharp_label.config(
            text=str(self.enhance_sharpness.get())))

        # 去黄
        ttk.Label(self.enhance_params_frame,
                  text="去黄", font=("Microsoft YaHei UI", 10)).grid(
            row=1, column=0, sticky=tk.W, padx=(0, 4), pady=(4, 0))
        ttk.Scale(self.enhance_params_frame, from_=0, to=10,
                  variable=self.enhance_cutoff, orient=tk.HORIZONTAL,
                  length=220).grid(row=1, column=1, padx=(0, 4), pady=(4, 0))
        self.cutoff_label = ttk.Label(self.enhance_params_frame,
                                      text="2", width=4, font=("Microsoft YaHei UI", 10))
        self.cutoff_label.grid(row=1, column=2, pady=(4, 0))
        self.enhance_cutoff.trace_add("write", lambda *_: self.cutoff_label.config(
            text=str(self.enhance_cutoff.get())))

        # 对比度
        ttk.Label(self.enhance_params_frame,
                  text="对比度", font=("Microsoft YaHei UI", 10)).grid(
            row=2, column=0, sticky=tk.W, padx=(0, 4), pady=(4, 0))
        ttk.Scale(self.enhance_params_frame, from_=1.0, to=2.0,
                  variable=self.enhance_contrast, orient=tk.HORIZONTAL,
                  length=220).grid(row=2, column=1, padx=(0, 4), pady=(4, 0))
        self.contrast_label = ttk.Label(self.enhance_params_frame,
                                        text="1.15", width=4, font=("Microsoft YaHei UI", 10))
        self.contrast_label.grid(row=2, column=2, pady=(4, 0))
        self.enhance_contrast.trace_add("write", lambda *_: self.contrast_label.config(
            text=f"{self.enhance_contrast.get():.2f}"))

        # 恢复默认按钮
        ttk.Button(self.enhance_params_frame, text="恢复默认",
                   style="Browse.TButton",
                   command=self._enhance_reset_default).grid(
            row=0, column=3, rowspan=3, sticky=tk.SE, padx=(10, 0))

        # 页面范围
        row_page = ttk.Frame(opt_card, style="Card.TFrame")
        row_page.grid(row=5, column=0, sticky=tk.W, pady=(6, 0))
        ttk.Label(row_page, text="页面",
                  style="Header.TLabel").pack(side=tk.LEFT, padx=(0, 8))
        self.all_radio = ttk.Radiobutton(
            row_page, text="全部", variable=self.page_range_var, value="all"
        )
        self.all_radio.pack(side=tk.LEFT)
        self.custom_radio = ttk.Radiobutton(
            row_page, text="自定义", variable=self.page_range_var, value="custom"
        )
        self.custom_radio.pack(side=tk.LEFT, padx=(8, 4))
        self.custom_entry = ttk.Entry(row_page, textvariable=self.custom_pages_var, width=20)
        self.custom_entry.pack(side=tk.LEFT)
        ttk.Label(row_page, text="1,3,5-10",
                  style="Secondary.TLabel").pack(side=tk.LEFT, padx=(4, 0))

        action_card = ttk.Frame(main, style="Hero.TFrame", padding=(16, 14))
        action_card.grid(row=3, column=0, sticky=tk.EW)
        action_card.columnconfigure(0, weight=1)
        ttk.Label(action_card, text="导出进度", style="Header.TLabel").grid(
            row=0, column=0, sticky=tk.W
        )
        ttk.Label(
            action_card,
            text="确认设置后开始导出，过程中会实时显示当前进度。",
            style="Hint.TLabel",
        ).grid(row=1, column=0, sticky=tk.W, pady=(4, 10))

        # ── 底部按钮 + 进度 ──
        btn_frame = ttk.Frame(action_card, style="Hero.TFrame")
        btn_frame.grid(row=2, column=0, pady=(0, 10))
        self.btn_convert = ttk.Button(btn_frame, text="开始导出",
                                      command=self._start_convert)
        self.btn_convert.pack()

        self.progress = ttk.Progressbar(action_card, length=620, mode="determinate")
        self.progress.grid(row=3, column=0, sticky=tk.EW, pady=(0, 6))

        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(action_card, textvariable=self.status_var,
                  style="Status.TLabel").grid(
            row=4, column=0, sticky=tk.W)
        self._refresh_summary()

    def _apply_initial_window_size(self):
        self.root.update_idletasks()
        req_w = self.root.winfo_reqwidth()
        req_h = self.root.winfo_reqheight()
        width = max(780, req_w + 24)
        height = max(700, req_h + 24)
        self.root.minsize(760, 660)
        self._center_window(width, height)

    def _center_window(self, w: int, h: int):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w = min(w, sw - 80)
        h = min(h, sh - 80)
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ------------------------------------------------------------------
    # 格式联动
    # ------------------------------------------------------------------
    def _on_fmt_change(self, event=None):
        self._update_fmt_desc()
        self._update_fmt_quality_visibility()
        self._refresh_summary()

    def _update_fmt_desc(self):
        fmt = self.fmt_var.get()
        if fmt in SUPPORTED_FORMATS:
            self.fmt_desc.config(text=SUPPORTED_FORMATS[fmt][2])

    def _update_fmt_quality_visibility(self):
        """JPEG/WEBP 显示质量滑动条，其他格式隐藏"""
        fmt = self.fmt_var.get()
        if fmt in ("JPEG", "WEBP"):
            self.quality_frame.grid()
        else:
            self.quality_frame.grid_remove()
        self._refresh_summary()

    # ------------------------------------------------------------------
    # 事件
    # ------------------------------------------------------------------
    def _on_enhance_toggle(self):
        """勾选/取消增强时，展开或收起参数面板"""
        if self.enhance_var.get():
            self.enhance_params_frame.grid()
        else:
            self.enhance_params_frame.grid_remove()
        self._refresh_summary()

    def _enhance_reset_default(self):
        """恢复增强参数为默认值"""
        self.enhance_sharpness.set(80)
        self.enhance_cutoff.set(2)
        self.enhance_contrast.set(1.15)
        self._refresh_summary()

    def _browse_pdf(self):
        path = filedialog.askopenfilename(
            title="选择 PDF 文件",
            filetypes=[("PDF 文件", "*.pdf"), ("所有文件", "*.*")],
        )
        if not path:
            return
        self.pdf_path.set(path)

        # 自动设置输出目录
        p = Path(path)
        default_out = p.parent / f"{p.stem}_图片"
        self.out_dir.set(str(default_out))
        self._refresh_summary()

    def _browse_output(self):
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.out_dir.set(path)
            self._refresh_summary()

    def _refresh_summary(self):
        if self.page_range_var.get() == "all":
            page_text = "全部页面"
        else:
            custom = self.custom_pages_var.get().strip()
            page_text = f"页面 {custom}" if custom else "自定义页面"
        parts = [self.fmt_var.get(), f"{self.dpi_var.get()} DPI", page_text]
        if self.fmt_var.get() in ("JPEG", "WEBP"):
            parts.append(f"质量 {self.quality_var.get()}")
        if self.enhance_var.get():
            parts.append("增强已开启")
        self.summary_var.set(" · ".join(parts))

    def _parse_pages(self, total: int) -> list:
        """解析用户输入的页面范围，返回 0-based 页码列表"""
        if self.page_range_var.get() == "all":
            return list(range(total))

        raw = self.custom_pages_var.get().strip()
        if not raw:
            raise ValueError("请填写页面范围，或选择「全部页面」")

        pages = []
        # 支持格式: 1,3,5-10,12
        parts = re.split(r"[,，\s]+", raw)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-", 1)
                start, end = int(a.strip()), int(b.strip())
                if start < 1 or end > total or start > end:
                    raise ValueError(f"页码范围无效: {part}（共 {total} 页）")
                pages.extend(range(start - 1, end))
            else:
                n = int(part)
                if n < 1 or n > total:
                    raise ValueError(f"页码无效: {n}（共 {total} 页）")
                pages.append(n - 1)

        if not pages:
            raise ValueError("未解析到有效页码")

        # 去重并保持顺序
        seen = set()
        return [p for p in pages if not (p in seen or seen.add(p))]  # type: ignore

    def _start_convert(self):
        if self._running:
            return

        pdf = self.pdf_path.get().strip()
        out = self.out_dir.get().strip()

        if not pdf:
            messagebox.showwarning("提示", "请先选择 PDF 文件")
            return
        if not os.path.isfile(pdf):
            messagebox.showerror("错误", "PDF 文件不存在")
            return
        if not out:
            messagebox.showwarning("提示", "请选择输出目录")
            return

        # 验证 PDF 可打开并获取页数
        try:
            import fitz
            doc = fitz.open(pdf)
            total = len(doc)
            doc.close()
        except Exception as e:
            messagebox.showerror("错误", f"无法打开 PDF 文件:\n{e}")
            return

        # 验证页面范围
        try:
            pages = self._parse_pages(total)
        except ValueError as e:
            messagebox.showerror("页面范围错误", str(e))
            return

        self._running = True
        self.btn_convert.config(state=tk.DISABLED, text="导出中...")
        self.progress["value"] = 0
        self.status_var.set("准备中...")
        self.root.update()

        fmt = self.fmt_var.get()
        dpi = self.dpi_var.get()
        quality = self.quality_var.get()
        enhance = self.enhance_var.get()
        sharpness = self.enhance_sharpness.get()
        cutoff = self.enhance_cutoff.get()
        contrast = self.enhance_contrast.get()

        t = threading.Thread(
            target=self._do_convert,
            args=(pdf, out, fmt, dpi, quality, pages, enhance,
                  sharpness, cutoff, contrast),
            daemon=True,
        )
        t.start()

    def _do_convert(self, pdf, out, fmt, dpi, quality, pages,
                    enhance, sharpness, cutoff, contrast):
        try:
            generated = pdf_to_images(
                pdf, out, fmt=fmt, dpi=dpi, quality=quality,
                pages=pages, progress_cb=self._on_progress,
                image_enhance=enhance,
                enhance_sharpness=sharpness,
                enhance_cutoff=cutoff,
                enhance_contrast=contrast,
            )
            self.root.after(0, self._on_success, out, generated)
        except Exception as e:
            self.root.after(0, self._on_error, str(e))

    def _on_progress(self, current, total, stage):
        self.root.after(0, self._update_ui, current, total, stage)

    def _update_ui(self, current, total, stage):
        if stage:
            self.status_var.set(stage)
        if total > 0:
            pct = int(current / total * 100)
            self.progress["value"] = pct
            self.progress["maximum"] = 100
            self.status_var.set(f"正在导出第 {current}/{total} 张...")
        self.root.update()

    def _on_success(self, out_dir, generated):
        count = len(generated)
        # 计算总大小
        total_size = sum(os.path.getsize(f) for f in generated)
        size_str = self._fmt_size(total_size)

        self.status_var.set(f"✓ 导出完成！共 {count} 张图片 ({size_str})")
        self.progress["value"] = 100
        self._reset_btn()

        if messagebox.askyesno("完成", f"导出成功！\n共 {count} 张图片\n目录: {out_dir}\n总大小: {size_str}\n\n是否打开输出文件夹？"):
            try:
                os.startfile(out_dir)
            except Exception:
                pass

    def _on_error(self, msg):
        friendly = msg
        if "No such file" in msg or "not found" in msg.lower():
            friendly = f"文件未找到。\n{msg}"
        elif "Permission denied" in msg or "拒绝访问" in msg:
            friendly = f"访问被拒绝，请检查文件是否被占用。\n{msg}"

        self.status_var.set("✗ 导出失败")
        self.progress["value"] = 0
        self._reset_btn()
        messagebox.showerror("导出失败", friendly)

    def _reset_btn(self):
        self.btn_convert.config(state=tk.NORMAL, text="开始导出")
        self._running = False

    @staticmethod
    def _fmt_size(byte: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if byte < 1024:
                return f"{byte:.1f} {unit}"
            byte /= 1024
        return f"{byte:.1f} TB"

    # ------------------------------------------------------------------
    # 启动
    # ------------------------------------------------------------------
    def run(self):
        self.root.mainloop()
