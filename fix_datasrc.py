import re

# Fix index.html: all data-src on <img> tags → src + loading="lazy"
with open("index.html", "r", encoding="utf-8") as f:
    content = f.read()

def fix_img_tag(m):
    tag = m.group(0)
    # Only process img tags with data-src and without src
    if 'data-src=' not in tag or re.search(r'\bsrc=', tag):
        return tag
    tag = re.sub(r'\bdata-src=', 'src=', tag)
    if 'loading=' not in tag:
        tag = re.sub(r'(\bdecoding=)', r'loading="lazy" \1', tag)
    return tag

content = re.sub(r'<img\b[^>]*>', fix_img_tag, content, flags=re.DOTALL)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(content)
print("index.html fixed")
