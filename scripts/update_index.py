import re

def update_index():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace newphoto2.png with newphoto2.jpg
    content = content.replace('newphoto2.png', 'newphoto2.jpg')
    
    # Add decoding="async" to img tags that don't have it
    def add_async(match):
        tag = match.group(0)
        if 'decoding="async"' not in tag:
            # insert after <img
            return tag.replace('<img ', '<img decoding="async" ')
        return tag

    content = re.sub(r'<img [^>]+>', add_async, content)
    
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    update_index()
