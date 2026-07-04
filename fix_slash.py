import glob
import re

for filepath in glob.glob("*.html"):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the trailing slash issue in img tags
    # <img ... / loading="eager" ...> -> <img ... loading="eager" ... />
    def fix_img(m):
        full_tag = m.group(0)
        # remove all rogue slashes before the closing bracket if they are standalone
        # Actually, let's just use a simple regex on the whole tag.
        # It looks like: <img ... / loading="eager" decoding="async" fetchpriority="high">
        inside = m.group(1)
        # remove trailing slashes from inside
        inside = re.sub(r'/\s*$', '', inside).strip()
        # remove rogue ' / ' in the middle, this might be tricky, it's before loading=
        inside = re.sub(r'/\s+(loading=)', r'\1', inside)
        return f"<img {inside} />"

    content = re.sub(r'<img\s+(.*?)>', fix_img, content, flags=re.IGNORECASE)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
