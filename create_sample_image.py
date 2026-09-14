from PIL import Image, ImageDraw, ImageFont

# Create high-res invoice image
width, height = 900, 500
img = Image.new("RGB", (width, height), color=(255, 255, 255))
draw = ImageDraw.Draw(img)

# Use Windows Arial font with full Vietnamese Unicode support
font_path = "/mnt/c/Windows/Fonts/arial.ttf"
try:
    title_font = ImageFont.truetype(font_path, 26)
    sub_font = ImageFont.truetype(font_path, 18)
    body_font = ImageFont.truetype(font_path, 16)
    bold_font = ImageFont.truetype("/mnt/c/Windows/Fonts/arialbd.ttf", 18)
except Exception as e:
    print(f"Fallback font: {e}")
    title_font = ImageFont.load_default()
    sub_font = title_font
    body_font = title_font
    bold_font = title_font

# Header
draw.text((180, 25), "CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM", fill=(0, 0, 0), font=title_font)
draw.text((270, 65), "Độc lập - Tự do - Hạnh phúc", fill=(0, 0, 0), font=sub_font)
draw.line([(100, 100), (800, 100)], fill=(180, 180, 180), width=2)

# Invoice Title
draw.text((320, 120), "HÓA ĐƠN BÁN HÀNG", fill=(20, 20, 20), font=bold_font)
draw.text((600, 120), "Số: HD-2026/001", fill=(80, 80, 80), font=body_font)

# Details
draw.text((80, 170), "Khách hàng: Nguyễn Văn An", fill=(0, 0, 0), font=body_font)
draw.text((80, 200), "Địa chỉ: Số 123 Đường Giải Phóng, Hà Nội", fill=(0, 0, 0), font=body_font)
draw.text((80, 230), "Mã số thuế: 0101234567", fill=(0, 0, 0), font=body_font)

# Items Table
draw.rectangle([(80, 270), (820, 310)], fill=(240, 240, 240), outline=(200, 200, 200))
draw.text((90, 280), "STT", fill=(0, 0, 0), font=body_font)
draw.text((150, 280), "Tên hàng hóa / Dịch vụ", fill=(0, 0, 0), font=body_font)
draw.text((500, 280), "Số lượng", fill=(0, 0, 0), font=body_font)
draw.text((600, 280), "Đơn giá (VNĐ)", fill=(0, 0, 0), font=body_font)
draw.text((720, 280), "Thành tiền", fill=(0, 0, 0), font=body_font)

# Row 1
draw.text((90, 325), "1", fill=(0, 0, 0), font=body_font)
draw.text((150, 325), "Máy tính bảng iPad Pro 11 inch", fill=(0, 0, 0), font=body_font)
draw.text((530, 325), "1", fill=(0, 0, 0), font=body_font)
draw.text((600, 325), "21.500.000", fill=(0, 0, 0), font=body_font)
draw.text((720, 325), "21.500.000", fill=(0, 0, 0), font=body_font)

draw.line([(80, 360), (820, 360)], fill=(220, 220, 220), width=1)

# Row 2 (English items)
draw.text((90, 375), "2", fill=(0, 0, 0), font=body_font)
draw.text((150, 375), "Apple Pencil Pro Stylus (Accessories)", fill=(0, 0, 0), font=body_font)
draw.text((530, 375), "1", fill=(0, 0, 0), font=body_font)
draw.text((600, 375), "3.500.000", fill=(0, 0, 0), font=body_font)
draw.text((720, 375), "3.500.000", fill=(0, 0, 0), font=body_font)

draw.line([(80, 410), (820, 410)], fill=(180, 180, 180), width=2)

# Total
draw.text((500, 430), "Tổng cộng thanh toán:", fill=(0, 0, 0), font=bold_font)
draw.text((710, 430), "25.000.000 VNĐ", fill=(180, 0, 0), font=bold_font)

img.save("sample_vn_invoice.png")
print("Invoice saved with crisp TrueType Vietnamese text!")
