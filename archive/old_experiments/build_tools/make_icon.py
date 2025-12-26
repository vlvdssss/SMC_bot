"""Create SMC icon directly as .ico"""
from PIL import Image, ImageDraw, ImageFont

# Create gradient background - SMC style
img = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Gradient background (dark to lighter)
for y in range(256):
    alpha = int(255 * (1 - y / 256))
    color = (26 + y // 8, 29 + y // 8, 35 + y // 8, 255)
    draw.line([(0, y), (255, y)], fill=color)

# Draw glowing border
for i in range(5):
    alpha = int(100 - i * 15)
    draw.rectangle(
        [(i, i), (255 - i, 255 - i)],
        outline=(0, 200 + i * 10, 150 - i * 10, 255 - alpha),
        width=2
    )

# Draw "SMC" text with glow effect
try:
    font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf', 80)
except:
    try:
        font = ImageFont.truetype('arial.ttf', 80)
    except:
        font = None

if font:
    # Glow effect
    for offset in range(3, 0, -1):
        alpha = int(100 - offset * 20)
        for dx in [-offset, 0, offset]:
            for dy in [-offset, 0, offset]:
                draw.text(
                    (128 + dx, 128 + dy),
                    'SMC',
                    fill=(0, 200, 150, alpha),
                    font=font,
                    anchor='mm'
                )
    
    # Main text
    draw.text((128, 128), 'SMC', fill=(255, 255, 255, 255), font=font, anchor='mm')

# Save as .ico with multiple sizes
icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
img.save('app_icon.ico', format='ICO', sizes=icon_sizes)
print('✓ Icon created: app_icon.ico')
