import re

with open("index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove the specific inline style from img tags
# Since it might have indentation and newlines, we can use a regex that matches the line or just the attribute.
# In the file it looks like:
#             style="image-rendering: -webkit-optimize-contrast; image-rendering: crisp-edges;"
content = re.sub(r'\s*style="image-rendering: -webkit-optimize-contrast; image-rendering: crisp-edges;"', '', content)

# 2. Inject CSS right before the first </style>
# We find the first occurrence of </style>
css_to_inject = """
    @media (max-width: 767px) {
      #gallery {
        padding: 0.75rem !important;
      }
      .grid-wrapper {
        grid-template-columns: repeat(2, 1fr) !important;
        gap: 0.6rem !important;
      }
      .grid-item {
        height: auto !important;
        aspect-ratio: 3/4 !important;
        will-change: transform;
        overflow: hidden;
      }
      .grid-item img {
        width: 100% !important;
        height: 100% !important;
        object-fit: cover !important;
      }
    }
"""

content = content.replace('</style>', css_to_inject + '  </style>', 1)

with open("index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
