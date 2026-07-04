# The issue is the regex [^>]* doesn't match newlines.
# We need a different approach: use a non-greedy match with DOTALL.
# But [^>]* by definition doesn't match >, but DOES match newlines in DOTALL.
# Actually [^>]* does NOT include DOTALL because [^>] is a character class, not .
# So [^>] already matches newlines. The issue must be elsewhere.

# Let's just do a simple string replacement approach instead.

with open("index.html", "r", encoding="utf-8") as f:
    content = f.read()

# Simple: replace all occurrences of data-src="assets/ with src="assets/ 
# These are only on <img> tags in this file.
content = content.replace(' data-src="assets/', ' src="assets/')
content = content.replace('\n            src="assets/', '\n            src="assets/')  # keep multiline alignment

# Now for any img tag that has src=assets/ but no loading=, add loading="lazy"
# We do this by finding <img ... src="assets/... > tags without loading= and adding it
import re
def add_lazy(m):
    tag = m.group(0)
    if 'loading=' in tag or 'loading =' in tag:
        return tag
    # Add before />
    tag = re.sub(r'\s*/>', ' loading="lazy" />', tag)
    return tag

content = re.sub(r'<img\b[^>]*src="assets/[^>]*/>', add_lazy, content, flags=re.DOTALL)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(content)

# Final check
remaining = [l for l in content.split('\n') if 'data-src' in l and '<img' in l]
print(f"Remaining data-src lines on img: {len(remaining)}")
# Also check any img without loading=
import re
imgs = re.findall(r'<img\b[^>]*/>', content, flags=re.DOTALL)
no_loading = [i[:80] for i in imgs if 'loading=' not in i and 'src="assets/' in i]
print(f"Images without loading=: {len(no_loading)}")
for n in no_loading:
    print(" ", n)
