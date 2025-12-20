"""Create temporary SMC icon"""
from PIL import Image, ImageDraw, ImageFont

# Create image with dark background
img = Image.new('RGBA', (512, 512), (26, 29, 35, 255))
draw = ImageDraw.Draw(img)

# Draw border
draw.rectangle([(0, 0), (511, 511)], outline=(0, 200, 150, 255), width=10)

# Draw text
try:
    font = ImageFont.truetype('arial.ttf', 180)
except:
    font = ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 180)

draw.text((256, 256), 'SMC', fill=(0, 200, 150, 255), font=font, anchor='mm')

# Save
img.save('smc_icon.png')
print('✓ Temporary icon created: smc_icon.png')
