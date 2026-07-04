import os
import re
import glob
import subprocess

def get_image_size(src):
    if src.startswith('/'):
        src = src[1:]
    path = os.path.join(os.getcwd(), src)
    if os.path.exists(path):
        try:
            # use sips to get width and height on macOS
            out = subprocess.check_output(['sips', '-g', 'pixelWidth', '-g', 'pixelHeight', path]).decode('utf-8')
            w, h = None, None
            for line in out.splitlines():
                if 'pixelWidth' in line:
                    w = int(line.split(':')[-1].strip())
                elif 'pixelHeight' in line:
                    h = int(line.split(':')[-1].strip())
            if w and h:
                return w, h
        except:
            pass
    return None, None

def process_html_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove content-visibility: auto;
    content = re.sub(r'content-visibility:\s*auto;?', '', content)

    # 1. Remove third-party lazy loading scripts
    # We match <script ... lazyload ...></script> or similar.
    content = re.sub(r'<script[^>]*lazyload[^>]*>.*?</script>', '', content, flags=re.IGNORECASE|re.DOTALL)

    # Make sure .grid-wrapper, .grid-col, .grid-item have will-change: transform; transform: translateZ(0);
    # Since we can't easily parse CSS with regex safely, we can just ensure the block has it.
    # The prompt says: "Dans le CSS principal, applique cette propriété CSS native ultra-agressive sur TOUS les éléments conteneurs qui ont un défilement overflow (y compris la galerie photo)"
    # We can inject it into <style> if it's not there, or replace existing blocks.
    # A safer way is to just add a global style at the end of <style> or in <head> to target them.
    # The instructions say: "Dans le CSS principal... sur TOUS les éléments conteneurs qui ont un défilement overflow"
    # I can add this rule to the <style> block:
    # .grid-wrapper, .grid-col, .grid-item, main, body { will-change: transform; transform: translateZ(0); }
    # Wait, the prompt says "tous les éléments conteneurs qui ont un défilement overflow". Usually that's the grid or body.
    
    # 2. Forcage du déchargement (contain: layout paint;) on <img> tags in galleries.
    # We can add this to the CSS: img { contain: layout paint; }
    
    # Let's add a comprehensive <style> block right before </style> or </head> to enforce these CSS rules.
    css_rules = """
    /* SAFARI MEMORY FIXES */
    .grid-wrapper, .grid-col, .grid-item, #gallery, main {
      will-change: transform;
      transform: translateZ(0);
    }
    .grid-item img, #gallery img, main img {
      contain: layout paint;
    }
    """
    if '</style>' in content:
        content = content.replace('</style>', css_rules + '\n  </style>')
    else:
        content = content.replace('</head>', '<style>' + css_rules + '</style>\n</head>')

    # 3. & 4. Images processing
    # We need to find all <img> tags, update their loading, decoding, fetchpriority, and style/aspect-ratio.
    # We'll use a regex to find <img> tags, then replace them.
    img_pattern = re.compile(r'<img\s+([^>]+)>', re.IGNORECASE)
    
    img_count = 0
    
    def repl_img(match):
        nonlocal img_count
        attrs_str = match.group(1)
        
        # Extract src
        src_match = re.search(r'src=["\']([^"\']+)["\']', attrs_str, re.IGNORECASE)
        src = src_match.group(1) if src_match else ""
        
        # Remove existing loading, decoding, fetchpriority, style with aspect-ratio
        attrs_str = re.sub(r'\bloading=["\']?(?:lazy|eager)["\']?', '', attrs_str, flags=re.IGNORECASE)
        attrs_str = re.sub(r'\bdecoding=["\']?(?:async|sync|auto)["\']?', '', attrs_str, flags=re.IGNORECASE)
        attrs_str = re.sub(r'\bfetchpriority=["\']?(?:high|low|auto)["\']?', '', attrs_str, flags=re.IGNORECASE)
        
        # We also need to add aspect-ratio to style, or create a style attribute.
        # It's easier to just strip aspect-ratio and height from existing style, or just add a new style if we don't mess up existing.
        w, h = get_image_size(src)
        aspect_ratio_style = ""
        if w and h:
            aspect_ratio_style = f"height: auto; aspect-ratio: {w} / {h};"
        else:
            aspect_ratio_style = f"height: auto;" # fallback
            
        # Check if style exists
        if 'style="' in attrs_str:
            attrs_str = re.sub(r'style="([^"]*)"', lambda m: f'style="{m.group(1).rstrip(";")} ; {aspect_ratio_style}"', attrs_str)
        elif "style='" in attrs_str:
            attrs_str = re.sub(r"style='([^']*)'", lambda m: f"style='{m.group(1).rstrip(';')} ; {aspect_ratio_style}'", attrs_str)
        else:
            attrs_str += f' style="{aspect_ratio_style}"'

        # Clean up multiple spaces
        attrs_str = re.sub(r'\s+', ' ', attrs_str).strip()
        
        img_count += 1
        
        if img_count <= 3:
            # First 3 images: eager, async, high
            new_img = f'<img {attrs_str} loading="eager" decoding="async" fetchpriority="high">'
        else:
            # Rest: lazy, async
            new_img = f'<img {attrs_str} loading="lazy" decoding="async">'
            
        return new_img
        
    content = img_pattern.sub(repl_img, content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

for filepath in glob.glob("*.html"):
    process_html_file(filepath)
    print(f"Processed {filepath}")

