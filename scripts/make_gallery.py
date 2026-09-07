import re
import os

def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. CREATE gallery.html
    # Remove from HERO to PHOTOGRAPHY
    gallery = re.sub(
        r'<!-- ─── HERO ─────────────────────────────── -->.*?<!-- ─── PHOTOGRAPHY ───────────────────────── -->',
        '<!-- ─── PHOTOGRAPHY ───────────────────────── -->',
        content,
        flags=re.DOTALL
    )
    # Remove from FUN to SCRIPTS
    gallery = re.sub(
        r'<!-- ─── FUN / ABOUT ───────────────────────── -->.*?<!-- ─── SCRIPTS ───────────────────────────── -->',
        '<!-- ─── SCRIPTS ───────────────────────────── -->',
        gallery,
        flags=re.DOTALL
    )
    # Remove "view full gallery" button in gallery.html
    gallery = re.sub(
        r'<div class="gallery-redirect reveal".*?</div>',
        '',
        gallery,
        flags=re.DOTALL
    )
    # Update nav links in gallery.html to point to index.html
    gallery = re.sub(r'href="#', r'href="index.html#', gallery)
    
    with open('gallery.html', 'w', encoding='utf-8') as f:
        f.write(gallery)
    print("Created gallery.html")

    # 2. UPDATE index.html
    # Extract photo items and update grid
    photo_item_pattern = r'(<div class="photo-item" [^>]*onclick="openLightbox\(\d+\)".*?</div>\s*</div>\s*</div>)'
    photo_items = re.findall(photo_item_pattern, content, flags=re.DOTALL)
    
    # We want indices: 0-9, 14-22, 29, 24
    keep_indices = list(range(10)) + list(range(14, 23)) + [29, 24]
    
    new_items_html = ""
    for new_idx, old_idx in enumerate(keep_indices):
        item_html = photo_items[old_idx]
        # Update onclick
        item_html = re.sub(r'onclick="openLightbox\(\d+\)"', f'onclick="openLightbox({new_idx})"', item_html)
        new_items_html += item_html + "\n      "

    # Replace old grid with new grid
    # Find start and end of grid
    grid_start_idx = content.find('<div class="photo-grid contact-mode reveal" id="photoGrid">')
    grid_start_idx = content.find('>', grid_start_idx) + 1
    
    # We need to find the matching closing div for the grid.
    # It ends right before <div class="gallery-redirect reveal"
    grid_end_idx = content.find('<div class="gallery-redirect reveal"', grid_start_idx)
    
    content = content[:grid_start_idx] + "\n      " + new_items_html.strip() + "\n    " + content[grid_end_idx:]
    
    # Now update JS photoData array
    # Extract photoData
    data_match = re.search(r'const photoData = \[(.*?)\];', content, flags=re.DOTALL)
    if data_match:
        data_str = data_match.group(1)
        # Split by },
        # Actually better to just match each { ... }
        objects = re.findall(r'\{[^}]+\}', data_str)
        
        new_data_str = ",\n      ".join([objects[i] for i in keep_indices])
        
        content = content[:data_match.start(1)] + "\n      " + new_data_str + "\n    " + content[data_match.end(1):]

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Updated index.html")

if __name__ == "__main__":
    main()
