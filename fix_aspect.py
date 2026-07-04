import re

# Image dimensions
dims = {
    'DSC00231.webp': '2422/3162',
    'DSC00318.webp': '2872/3860',
    'DSC03180-5.webp': '6000/4000',
    'DSC04588.webp': '4000/5313',
    'DSC05094.webp': '4672/7008',
    'DSC05214.webp': '4433/5911',
    'DSC07978.webp': '2640/3300',
    'DSC08492.webp': '1075/1433',
    'DSC08603.webp': '1372/1830',
    'DSC08891.webp': '4024/6036',
    'DSC08908-Modifier.webp': '6397/7230',
    'DSC09915.webp': '4128/5504',
    'DSCF2573.webp': '8736/11648',
    'DSCF2633.webp': '3317/4356',
    'HR9A0769.webp': '5464/8192',
    'HR9A0808.webp': '5464/8192',
    'HR9A0911.webp': '3662/4621',
    'HR9A0963.webp': '4396/6584',
    'SIM01217.webp': '4672/6382',
    'SIM01733.webp': '4238/6357',
    'SIM01938.webp': '7008/4672',
    'SIM02244.webp': '1211/1518'
}

with open("index.html", "r", encoding="utf-8") as f:
    content = f.read()

def add_aspect(m):
    tag = m.group(0)
    # Check if inside gallery... we assume all img tags in index.html are in the gallery
    # Find the src or data-src to get filename
    src_match = re.search(r'(?:data-)?src="assets/([^"]+)"', tag)
    if not src_match:
        return tag
    filename = src_match.group(1)
    if filename in dims:
        ratio = dims[filename]
        # Add style="aspect-ratio: W/H;" if not present
        if 'style="aspect-ratio:' not in tag:
            # Add before />
            tag = re.sub(r'\s*/>', f' style="aspect-ratio: {ratio};" />', tag)
    return tag

content = re.sub(r'<img\b[^>]*/>', add_aspect, content, flags=re.DOTALL)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Aspect ratio added to index.html")
