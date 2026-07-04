import glob
import re

def process_html(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # 1. Remove any <script> block containing IntersectionObserver or transparentPixel
    # These scripts wrap DOMContentLoaded and observer logic
    content = re.sub(
        r'\s*<script>\s*document\.addEventListener\s*\(\s*["\']DOMContentLoaded["\'].*?</script>',
        '',
        content,
        flags=re.DOTALL
    )

    # 2. Replace data-src="..." with src="..." and add loading="lazy"
    # Find img tags that have data-src but no src
    def fix_img(m):
        tag = m.group(0)
        # If the tag already has a src=, skip (eager images)
        if re.search(r'\bsrc=', tag):
            return tag
        # Replace data-src with src
        tag = re.sub(r'\bdata-src=', 'src=', tag)
        # Add loading="lazy" if missing (before decoding or closing)
        if 'loading=' not in tag:
            tag = re.sub(r'(\bdecoding=)', r'loading="lazy" \1', tag)
        return tag

    content = re.sub(r'<img\s[^>]*>', fix_img, content, flags=re.DOTALL)

    # 3. Remove content-visibility inline style from personal.html
    if 'personal.html' in filepath:
        content = re.sub(
            r'\s*style="content-visibility:\s*auto;\s*contain-intrinsic-size:\s*auto\s*3000px;"',
            '',
            content
        )

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  Modified: {filepath}")
    else:
        print(f"  No change: {filepath}")

html_files = glob.glob("*.html")
print(f"Processing {len(html_files)} files...")
for fp in sorted(html_files):
    process_html(fp)
print("Done.")
