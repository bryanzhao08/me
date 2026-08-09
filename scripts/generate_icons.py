import os
from PIL import Image, ImageDraw, ImageFilter

out_dir = "/Users/bryan/Downloads/me/assets/icons"
os.makedirs(out_dir, exist_ok=True)

# Colors based on "Geometric Silence"
bg_color = (15, 15, 18)
stroke_color = (200, 200, 210)
accent_color = (96, 165, 250)

def draw_canon5d(draw):
    # Brutalist, large pro body
    draw.rectangle([20, 30, 80, 70], outline=stroke_color, width=2)
    draw.rectangle([35, 20, 65, 30], outline=stroke_color, width=2)
    draw.ellipse([30, 35, 70, 75], outline=stroke_color, width=2)
    draw.ellipse([40, 45, 60, 65], outline=accent_color, width=1)
    draw.line([25, 35, 25, 45], fill=stroke_color, width=2)

def draw_rebel(draw):
    # Smaller APS-C body
    draw.rectangle([25, 35, 75, 65], outline=stroke_color, width=1)
    draw.rectangle([40, 25, 60, 35], outline=stroke_color, width=1)
    draw.ellipse([35, 35, 65, 65], outline=stroke_color, width=1)
    draw.ellipse([45, 45, 55, 55], outline=accent_color, width=1)

def draw_iphone(draw):
    # iPhone 14
    draw.rounded_rectangle([30, 15, 70, 85], radius=6, outline=stroke_color, width=2)
    draw.ellipse([35, 20, 45, 30], outline=stroke_color, width=1)
    draw.ellipse([35, 35, 45, 45], outline=stroke_color, width=1)
    draw.ellipse([50, 28, 55, 33], outline=accent_color, width=1) # Flash

def create_icon(name, draw_func):
    img = Image.new('RGBA', (100, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw_func(draw)
    
    # Apply subtle anti-aliasing / glow
    img = img.resize((200, 200), Image.Resampling.LANCZOS)
    img = img.filter(ImageFilter.SMOOTH)
    img.save(f"{out_dir}/{name}.png")
    print(f"Generated {name}.png")

create_icon('canon5d', draw_canon5d)
create_icon('rebel', draw_rebel)
create_icon('iphone', draw_iphone)
