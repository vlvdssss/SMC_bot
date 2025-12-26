"""
Create .ico file from image for PyInstaller
"""
from PIL import Image
import sys

def create_icon(input_image, output_ico):
    """Convert image to .ico format with multiple sizes."""
    try:
        # Open the image
        img = Image.open(input_image)
        
        # Convert to RGBA if needed
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        
        # Create icon with multiple sizes
        icon_sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
        
        # Save as .ico
        img.save(output_ico, format='ICO', sizes=icon_sizes)
        print(f"✓ Icon created successfully: {output_ico}")
        return True
        
    except Exception as e:
        print(f"✗ Error creating icon: {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python create_icon.py <input_image>")
        print("Example: python create_icon.py smc_icon.png")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = 'app_icon.ico'
    
    if create_icon(input_file, output_file):
        print(f"Icon ready for PyInstaller!")
    else:
        sys.exit(1)
