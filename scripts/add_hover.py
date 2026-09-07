import re

def main():
    with open('index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Update the HTML elements for hovering
    content = content.replace(
        '''<div class="cam-viewer-card" onclick="highlightPhotos('canon5d', this)">''',
        '''<div class="cam-viewer-card" onclick="highlightPhotos('canon5d', this)" onmouseenter="hoverHighlight('canon5d', this, true)" onmouseleave="hoverHighlight('canon5d', this, false)">'''
    )
    content = content.replace(
        '''<div class="cam-viewer-card" onclick="highlightPhotos('rebel', this)">''',
        '''<div class="cam-viewer-card" onclick="highlightPhotos('rebel', this)" onmouseenter="hoverHighlight('rebel', this, true)" onmouseleave="hoverHighlight('rebel', this, false)">'''
    )
    content = content.replace(
        '''<div class="cam-viewer-card" onclick="highlightPhotos('iphone', this)">''',
        '''<div class="cam-viewer-card" onclick="highlightPhotos('iphone', this)" onmouseenter="hoverHighlight('iphone', this, true)" onmouseleave="hoverHighlight('iphone', this, false)">'''
    )

    # 2. Insert the hoverHighlight function
    js_code = """let activeCamGlow = null;

      function hoverHighlight(camId, cardEl, isEnter) {
        if (activeCamGlow === camId) return; // if it's already locked via click, do nothing
        
        const items = document.querySelectorAll('.photo-item');
        if (isEnter) {
          if (cardEl) cardEl.classList.add('glow-' + camId);
          items.forEach(item => {
            if (item.getAttribute('data-cam') === camId) {
              item.classList.add('glow-' + camId);
            }
          });
        } else {
          // On mouse leave, we remove the hover glow.
          // Note: we only remove it if activeCamGlow != camId, which is handled by the guard above.
          if (cardEl) cardEl.classList.remove('glow-' + camId);
          items.forEach(item => {
            if (item.getAttribute('data-cam') === camId) {
              item.classList.remove('glow-' + camId);
            }
          });
        }
      }"""

    content = content.replace('let activeCamGlow = null;', js_code)

    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Successfully added hover functionality to camera cards.")

if __name__ == "__main__":
    main()
