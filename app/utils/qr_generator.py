import io
import os
from typing import Optional
import qrcode
from PIL import Image, ImageDraw, ImageFont


def get_unicode_font(size: int = 14) -> ImageFont.ImageFont:
    """自动探测操作系统中支持中韩双语的 TrueType 字体"""
    font_candidates = [
        # macOS 常见支持中韩双语的高清字体
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        # Windows 常见中韩字体
        "C:\\Windows\\Fonts\\msyh.ttc",
        "C:\\Windows\\Fonts\\malgun.ttf",
        "C:\\Windows\\Fonts\\simsun.ttc",
        # Linux 常见 CJK 字体
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    ]
    for p in font_candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def create_qr_code_image(content: str, label: Optional[str] = None, sub_label: Optional[str] = None) -> bytes:
    """
    生成带文字标识的物资二维码实物标签贴纸图片 (PNG 格式字节流，完美支持中文字符与韩文)
    
    :param content: 二维码内嵌内容 (如: 资产唯一编号 AST-2026-0001)
    :param label: 二维码下方物资名称 (如: 索尼 A7M4 相机)
    :param sub_label: 二维码下方编号 (如: AST-2026-0001)
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(content)
    qr.make(fit=True)

    # 基础二维码图像 (RGB)
    qr_img = qr.make_image(fill_color="#0f172a", back_color="#ffffff").convert("RGB")
    qr_w, qr_h = qr_img.size

    # 如果不需要附加文字，直接返回纯二维码
    if not label and not sub_label:
        buffer = io.BytesIO()
        qr_img.save(buffer, format="PNG")
        return buffer.getvalue()

    # 加载各层字体
    header_font = get_unicode_font(13)
    id_font = get_unicode_font(13)
    name_font = get_unicode_font(13)

    # 制作带有标题区域的“资产实物标签纸”排版
    header_h = 36
    footer_h = 58 if sub_label else 34
    total_w = qr_w
    total_h = qr_h + header_h + footer_h

    canvas = Image.new("RGB", (total_w, total_h), color="#ffffff")
    draw = ImageDraw.Draw(canvas)

    # 1. 绘制外边框与顶部沉浸式色条
    draw.rectangle([(0, 0), (total_w - 1, total_h - 1)], outline="#cbd5e1", width=2)
    draw.rectangle([(0, 0), (total_w - 1, header_h)], fill="#0284c7")

    # 2. 绘制顶部项目标识
    draw.text((12, 9), "QR-Link 共享资产标签 (공유자원)", fill="#ffffff", font=header_font)

    # 3. 贴入中间二维码
    canvas.paste(qr_img, (0, header_h))

    # 4. 绘制底部物资编号与中文名称
    footer_start_y = header_h + qr_h + 6
    if sub_label:
        draw.text((14, footer_start_y), f"编号: {sub_label}", fill="#0f172a", font=id_font)
    if label:
        # 如果名称较长，截取前 18 个字符并加省略号
        display_label = label if len(label) <= 18 else label[:17] + "..."
        draw.text((14, footer_start_y + 24), f"名称: {display_label}", fill="#334155", font=name_font)

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG")
    return buffer.getvalue()
