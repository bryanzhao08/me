import os
import glob
from PIL import Image

def compress_images():
    photo_dir = "assets/photos"
    files = glob.glob(os.path.join(photo_dir, "*.*"))
    max_size = 1200
    
    for file in files:
        if file.lower().endswith(('.jpg', '.jpeg', '.png')):
            try:
                img = Image.open(file)
                # Check EXIF orientation
                try:
                    import piexif
                    if "exif" in img.info:
                        exif_dict = piexif.load(img.info["exif"])
                        if piexif.ImageIFD.Orientation in exif_dict["0th"]:
                            orientation = exif_dict["0th"].pop(piexif.ImageIFD.Orientation)
                            if orientation == 2:
                                img = img.transpose(Image.FLIP_LEFT_RIGHT)
                            elif orientation == 3:
                                img = img.rotate(180)
                            elif orientation == 4:
                                img = img.rotate(180).transpose(Image.FLIP_LEFT_RIGHT)
                            elif orientation == 5:
                                img = img.rotate(-90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
                            elif orientation == 6:
                                img = img.rotate(-90, expand=True)
                            elif orientation == 7:
                                img = img.rotate(90, expand=True).transpose(Image.FLIP_LEFT_RIGHT)
                            elif orientation == 8:
                                img = img.rotate(90, expand=True)
                except Exception:
                    pass
                
                # Resize
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
                
                # Save
                if file.lower().endswith('.png'):
                    # Convert to JPG and remove old PNG
                    rgb_im = img.convert('RGB')
                    new_file = file.rsplit('.', 1)[0] + '.jpg'
                    rgb_im.save(new_file, 'JPEG', quality=75, progressive=True)
                    print(f"Converted and compressed: {file} -> {new_file}")
                    if os.path.exists(file):
                        os.remove(file)
                else:
                    img.save(file, 'JPEG', quality=75, progressive=True)
                    print(f"Compressed: {file}")
            except Exception as e:
                print(f"Error processing {file}: {e}")

if __name__ == "__main__":
    compress_images()
