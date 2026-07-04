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
        self.root = tk.Tk()
        self.root.title("PDF导出为图片 v1.0")
        self.root.resizable(False, False)
        self._center_window(620, 440)

        self.pdf_path = tk.StringVar()
        self.out_dir = tk.StringVar()
        self.fmt_var = tk.StringVar(value=DEFAULT_FORMAT)
        self.dpi_var = tk.IntVar(value=200)
        self.quality_var = tk.IntVar(value=90)

        # 页面范围
        self.page_range_var = tk.StringVar(value="all")  # "all" 或 "custom"
        self.custom_pages_var = tk.StringVar()

        self._build_ui()
        self._running = False

    # ------------------------------------------------------------------
    # 布局
    # ------------------------------------------------------------------
    def _build_ui(self):
        main = ttk.Frame(self.root, padding=14)
        main.pack(fill=tk.BOTH, expand=True)

        # --- 第0行：输入 PDF ---
        ttk.Label(main, text="PDF 文件：").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Entry(main, textvariable=self.pdf_path, width=50).grid(
            row=0, column=1, padx=6, pady=(0, 5)
        )
        ttk.Button(main, text="浏览...", command=self._browse_pdf, width=10).grid(
            row=0, column=2, pady=(0, 5)
        )

        # --- 第1行：输出目录 ---
        ttk.Label(main, text="输出目录：").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Entry(main, textvariable=self.out_dir, width=50).grid(
            row=1, column=1, padx=6, pady=(0, 5)
        )
        ttk.Button(main, text="浏览...", command=self._browse_output, width=10).grid(
            row=1, column=2, pady=(0, 5)
        )

        # --- 分隔 ---
        ttk.Separator(main, orient=tk.HORIZONTAL).grid(
            row=2, column=0, columnspan=3, sticky=tk.EW, pady=(6, 8)
        )

        # --- 第2行：图片格式 ---
        fmt_row = ttk.Frame(main)
        fmt_row.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=(0, 4))

        ttk.Label(fmt_row, text="图片格式：").pack(side=tk.LEFT)
        self.fmt_combo = ttk.Combobox(
            fmt_row,
            textvariable=self.fmt_var,
            values=FORMAT_KEYS,
            state="readonly",
            width=10,
        )
        self.fmt_combo.pack(side=tk.LEFT, padx=(4, 10))
        self.fmt_combo.bind("<<ComboboxSelected>>", self._on_fmt_change)

        # 格式说明
        self.fmt_desc = ttk.Label(fmt_row, text="", foreground="gray", font=("", 9))
        self.fmt_desc.pack(side=tk.LEFT)
        self._update_fmt_desc()

        # --- 第3行：DPI ---
        dpi_row = ttk.Frame(main)
        dpi_row.grid(row=4, column=0, columnspan=3, sticky=tk.W, pady=(0, 6))

        ttk.Label(dpi_row, text="DPI：").pack(side=tk.LEFT)
        for val in (150, 200, 300, 400):
            ttk.Radiobutton(
                dpi_row, text=str(val), variable=self.dpi_var, value=val
            ).pack(side=tk.LEFT, padx=3)

        # --- 第4行：质量（仅 JPEG/WEBP 时可见）---
        self.quality_frame = ttk.Frame(main)
        self.quality_frame.grid(row=5, column=0, columnspan=3, sticky=tk.W, pady=(0, 8))

        ttk.Label(self.quality_frame, text="图片质量：").pack(side=tk.LEFT)
        self.quality_scale = ttk.Scale(
            self.quality_frame,
            from_=10,
            to=100,
            variable=self.quality_var,
            orient=tk.HORIZONTAL,
            length=180,
        )
        self.quality_scale.pack(side=tk.LEFT, padx=6)
        self.quality_label = ttk.Label(self.quality_frame, text="90", width=4)
        self.quality_label.pack(side=tk.LEFT)
        # 同步数值显示
        self.quality_var.trace_add("write", lambda *_: self.quality_label.config(
            text=str(self.quality_var.get())
        ))

        # --- 第5行：页面范围 ---
        page_frame = ttk.Frame(main)
        page_frame.grid(row=6, column=0, columnspan=3, sticky=tk.W, pady=(0, 8))

        ttk.Label(page_frame, text="页面范围：").pack(side=tk.LEFT)
        self.all_radio = ttk.Radiobutton(
            page_frame, text="全部页面", variable=self.page_range_var, value="all"
        )
        self.all_radio.pack(side=tk.LEFT)
        self.custom_radio = ttk.Radiobutton(
            page_frame, text="自定义：", variable=self.page_range_var, value="custom"
        )
        self.custom_radio.pack(side=tk.LEFT, padx=(10, 4))
        self.custom_entry = ttk.Entry(page_frame, textvariable=self.custom_pages_var, width=18)
        self.custom_entry.pack(side=tk.LEFT)
        ttk.Label(
            page_frame,
            text="如: 1,3,5-10",
            foreground="gray",
            font=("", 9),
        ).pack(side=tk.LEFT, padx=(4, 0))

        # --- 第6行：转换按钮 ---
        self.btn_convert = ttk.Button(
            main, text="开始导出", command=self._start_convert, width=18
        )
        self.btn_convert.grid(row=7, column=0, columnspan=3, pady=(4, 6))

        # --- 第7行：进度条 ---
        self.progress = ttk.Progressbar(main, length=580, mode="determinate")
        self.progress.grid(row=8, column=0, columnspan=3, pady=(0, 4))

        # --- 第8行：状态 ---
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(main, textvariable=self.status_var, foreground="#555").grid(
            row=9, column=0, columnspan=3, sticky=tk.W
        )

        # --- 底部提示 ---
        ttk.Label(
            main,
            text="💡 支持 PDF 文件，导出图片保存到指定目录。",
            foreground="gray",
            font=("", 9),
        ).grid(row=10, column=0, columnspan=3, sticky=tk.W, pady=(6, 0))

        self._update_fmt_quality_visibility()

    def _center_window(self, w: int, h: int):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    # ------------------------------------------------------------------
    # 格式联动
    # ------------------------------------------------------------------
    def _on_fmt_change(self, event=None):
        self._update_fmt_desc()
        self._update_fmt_quality_visibility()

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

    # ------------------------------------------------------------------
    # 事件
    # ------------------------------------------------------------------
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

    def _browse_output(self):
        path = filedialog.askdirectory(title="选择输出目录")
        if path:
            self.out_dir.set(path)

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

        t = threading.Thread(
            target=self._do_convert,
            args=(pdf, out, fmt, dpi, quality, pages),
            daemon=True,
        )
        t.start()

    def _do_convert(self, pdf, out, fmt, dpi, quality, pages):
        try:
            generated = pdf_to_images(
                pdf, out, fmt=fmt, dpi=dpi, quality=quality,
                pages=pages, progress_cb=self._on_progress,
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
