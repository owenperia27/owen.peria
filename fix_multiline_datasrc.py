import re

with open("index.html", "r", encoding="utf-8") as f:
    content = f.read()

# Replace ALL remaining data-src= on img tags (including multiline)
# Using DOTALL flag to match across lines
def fix_img_tag(m):
    tag = m.group(0)
    if 'data-src=' not in tag:
        return tag
    # Already has a real src? skip (shouldn't happen on img tags)
    if re.search(r'\bsrc\s*=\s*["\'](?!data:)', tag):
        return tag
    # Replace data-src → src
    tag = tag.replace('data-src=', 'src=')
    # Add loading="lazy" if missing, before decoding= or before />
    if 'loading=' not in tag:
        tag = re.sub(r'(\bdecoding=)', r'loading="lazy" \1', tag)
        if 'loading=' not in tag:
            # add before closing />
            tag = re.sub(r'\s*/>', ' loading="lazy" />', tag)
    return tag

content = re.sub(r'<img\b[^>]*>', fix_img_tag, content, flags=re.DOTALL)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(content)

# Verify
remaining = re.findall(r'<img\b[^>]*data-src[^>]*>', content, flags=re.DOTALL)
print(f"Remaining data-src on img tags: {len(remaining)}")
if remaining:
    for r in remaining:
        print(" ", r[:100])
