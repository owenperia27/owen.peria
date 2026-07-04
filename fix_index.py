import re

with open("index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Replace the injected mobile CSS with the requested fluid structure
bad_css = r'@media\s*\(\s*max-width:\s*767px\s*\)\s*\{\s*#gallery\s*\{[^\}]+\}\s*\.grid-wrapper\s*\{[^\}]+\}\s*\.grid-item\s*\{[^\}]+\}\s*\.grid-item\s*img\s*\{[^\}]+\}\s*\}'
good_css = """@media (max-width: 767px) {
      .grid-wrapper { grid-template-columns: repeat(2, 1fr) !important; gap: 0.6rem !important; }
      .grid-col { display: flex; flex-direction: column; gap: 0.6rem !important; }
      .grid-item img { display: block; width: 100% !important; height: auto !important; object-fit: cover; }
    }"""
content = re.sub(bad_css, good_css, content, flags=re.DOTALL)

# 2. Add contain: paint to the global .grid-item class
# The global class looks like:
#     .grid-item {
#       display: block;
#       width: 100%;
#       line-height: 0;
#       overflow: hidden;
#     }
# We can just match `.grid-item {` and insert `contain: paint;` inside.
# But wait, there might be multiple occurrences (like inside media queries), but we only want the main one.
# So we just regex the specific block:
def repl_grid_item(match):
    block = match.group(0)
    if 'contain: paint;' not in block:
        return block.replace('overflow: hidden;', 'overflow: hidden;\n      contain: paint;')
    return block
content = re.sub(r'\.grid-item\s*\{[^}]*overflow:\s*hidden;[^}]*\}', repl_grid_item, content, count=1)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
