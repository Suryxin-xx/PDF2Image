"""
PDF导出为图片 - 主入口

将 PDF 的每一页导出为图片文件，支持多种图片格式。

用法:
    python main.py                    # GUI 模式
    python main.py input.pdf          # CLI 模式（默认 PNG, 200 DPI）
    python main.py input.pdf -f JPEG --dpi 300 -q 95
    python main.py input.pdf -f TIFF -p 1-5,8,10
"""

import sys
import os
import argparse


if getattr(sys, "frozen", False):
    os.chdir(os.path.dirname(sys.executable))

from src.gui import PDF2ImageApp
from src.converter import pdf_to_images, FORMAT_KEYS, DEFAULT_FORMAT


def _fmt_size(byte: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if byte < 1024:
            return f"{byte:.1f} {unit}"
        byte /= 1024
    return f"{byte:.1f} TB"


def cli_mode():
    parser = argparse.ArgumentParser(
        description="将 PDF 导出为图片"
    )
    parser.add_argument("input", help="PDF 文件路径")
    parser.add_argument("-o", "--output", help="输出目录（默认: PDF文件名_图片/）")
    parser.add_argument("-f", "--format", default=DEFAULT_FORMAT,
                        choices=FORMAT_KEYS,
                        help=f"图片格式（默认: {DEFAULT_FORMAT}）")
    parser.add_argument("--dpi", type=int, default=200, help="渲染 DPI（默认: 200）")
    parser.add_argument("-q", "--quality", type=int, default=90,
                        help="JPEG/WEBP 质量 1-100（默认: 90）")
    parser.add_argument("-p", "--pages", help="页面范围，如: 1,3,5-10（默认: 全部）")
    args = parser.parse_args()

    if not os.path.isfile(args.input):
        print(f"[错误] 文件不存在: {args.input}")
        sys.exit(1)

    # 解析页面范围
    pages = None
    if args.pages:
        import fitz
        doc = fitz.open(args.input)
        total = len(doc)
        doc.close()

        import re
        raw = args.pages
        parsed = []
        parts = re.split(r"[,，\s]+", raw)
        for part in parts:
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-", 1)
                start, end = int(a.strip()), int(b.strip())
                if start < 1 or end > total or start > end:
                    print(f"[错误] 页码范围无效: {part}")
                    sys.exit(1)
                parsed.extend(range(start - 1, end))
            else:
                n = int(part)
                if n < 1 or n > total:
                    print(f"[错误] 页码无效: {n}")
                    sys.exit(1)
                parsed.append(n - 1)
        pages = sorted(set(parsed))

    # 输出目录
    from pathlib import Path
    inp = Path(args.input)
    out_dir = args.output or str(inp.parent / f"{inp.stem}_图片")
    os.makedirs(out_dir, exist_ok=True)

    def cb(current, total, stage):
        if total > 0:
            print(f"\r  进度: {current}/{total} 张 ({int(current/total*100)}%)", end="")
        sys.stdout.flush()

    try:
        print(f"PDF:    {args.input}")
        print(f"输出:   {out_dir}")
        print(f"格式:   {args.format}")
        print(f"DPI:    {args.dpi}")
        if args.format in ("JPEG", "WEBP"):
            print(f"质量:   {args.quality}")
        if pages is not None:
            print(f"页数:   {len(pages)} 页（自定义）")
        else:
            import fitz
            d = fitz.open(args.input)
            print(f"页数:   {len(d)} 页（全部）")
            d.close()

        generated = pdf_to_images(
            args.input, out_dir,
            fmt=args.format,
            dpi=args.dpi,
            quality=args.quality,
            pages=pages,
            progress_cb=cb,
        )
        print()
        total_size = sum(os.path.getsize(f) for f in generated)
        print(f"\n✓ 导出完成！共 {len(generated)} 张图片，总大小 {_fmt_size(total_size)}")
        print(f"  目录: {out_dir}")
    except Exception as e:
        print(f"\n[错误] {e}")
        sys.exit(1)


def main():
    if len(sys.argv) > 1:
        cli_mode()
    else:
        app = PDF2ImageApp()
        app.run()


if __name__ == "__main__":
    main()
