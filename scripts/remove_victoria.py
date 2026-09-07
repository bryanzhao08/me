import re

def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove the div for "victoria peak after dark"
    # It has onclick="openLightbox(9)" and the h4 is "victoria peak after dark"
    pattern_div = r'<div class="photo-item"[^>]*onclick="openLightbox\(9\)".*?</div>\s*</div>\s*</div>\s*'
    content = re.sub(pattern_div, '', content, flags=re.DOTALL)

    # Decrement the onclick index for all subsequent items
    def decrement_index(match):
        idx = int(match.group(1))
        if idx > 9:
            return f'onclick="openLightbox({idx-1})"'
        return match.group(0)
    
    content = re.sub(r'onclick="openLightbox\((\d+)\)"', decrement_index, content)

    # Remove the object from photoData
    # It has title: 'victoria peak after dark'
    pattern_obj = r"\s*\{\s*title:\s*'victoria peak after dark'.*?\},"
    content = re.sub(pattern_obj, '', content, flags=re.DOTALL)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Successfully removed victoria peak after dark and updated indices.")

if __name__ == "__main__":
    main()
