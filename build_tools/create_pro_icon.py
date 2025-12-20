"""Create professional SMC trading icon with modern design."""

from PIL import Image, ImageDraw, ImageFont
import os

def create_professional_icon():
    """Create a modern, professional trading icon."""
    
    # Create sizes for .ico file
    sizes = [256, 128, 64, 48, 32, 16]
    images = []
    
    for size in sizes:
        # Create image with transparency
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Modern color scheme - gradient from cyan to green
        gradient_start = (0, 200, 150)  # Cyan-green
        gradient_end = (0, 255, 180)    # Bright green
        
        # Draw rounded rectangle background with gradient effect
        margin = size // 10
        for i in range(margin, size - margin):
            ratio = (i - margin) / (size - 2 * margin)
            r = int(gradient_start[0] + (gradient_end[0] - gradient_start[0]) * ratio)
            g = int(gradient_start[1] + (gradient_end[1] - gradient_start[1]) * ratio)
            b = int(gradient_start[2] + (gradient_end[2] - gradient_start[2]) * ratio)
            
            draw.line([(margin, i), (size - margin, i)], fill=(r, g, b, 255), width=1)
        
        # Draw border
        border_width = max(2, size // 32)
        draw.rounded_rectangle(
            [margin, margin, size - margin, size - margin],
            radius=size // 8,
            outline=(255, 255, 255, 220),
            width=border_width
        )
        
        # Draw trading chart symbol - candlestick pattern
        center_x = size // 2
        center_y = size // 2
        
        # Scale based on icon size
        candle_width = size // 12
        wick_width = max(1, size // 48)
        
        # Draw 3 candlesticks representing market structure
        candles = [
            # (x_offset, height, is_bullish)
            (-size // 4, size // 6, True),   # Left - bullish
            (0, size // 4, False),            # Center - bearish (larger)
            (size // 4, size // 5, True),    # Right - bullish
        ]
        
        for x_offset, candle_height, is_bullish in candles:
            x = center_x + x_offset
            
            # Wick
            wick_top = center_y - candle_height
            wick_bottom = center_y + candle_height // 3
            draw.line([(x, wick_top), (x, wick_bottom)], fill=(255, 255, 255, 240), width=wick_width)
            
            # Candle body
            if is_bullish:
                # Green/white candle (hollow or filled)
                body_top = center_y - candle_height // 2
                body_bottom = center_y + candle_height // 6
                draw.rectangle(
                    [x - candle_width, body_top, x + candle_width, body_bottom],
                    fill=(255, 255, 255, 230),
                    outline=(255, 255, 255, 255)
                )
            else:
                # Red/dark candle
                body_top = center_y - candle_height // 3
                body_bottom = center_y + candle_height // 4
                draw.rectangle(
                    [x - candle_width, body_top, x + candle_width, body_bottom],
                    fill=(40, 40, 40, 200),
                    outline=(255, 255, 255, 255)
                )
        
        # Add small "SMC" text at bottom for larger sizes
        if size >= 64:
            try:
                # Try to use a nice font
                font_size = max(8, size // 12)
                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()
                
                text = "SMC"
                # Get text bounding box
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                text_x = (size - text_width) // 2
                text_y = size - margin - text_height - size // 20
                
                # Draw text with shadow
                draw.text((text_x + 1, text_y + 1), text, fill=(0, 0, 0, 100), font=font)
                draw.text((text_x, text_y), text, fill=(255, 255, 255, 255), font=font)
            except:
                pass
        
        images.append(img)
    
    # Save as .ico file
    output_path = os.path.join(os.path.dirname(__file__), 'app_icon.ico')
    images[0].save(
        output_path,
        format='ICO',
        sizes=[(img.width, img.height) for img in images],
        append_images=images[1:]
    )
    
    print(f"✓ Professional icon created: {output_path}")
    return output_path

if __name__ == "__main__":
    create_professional_icon()
