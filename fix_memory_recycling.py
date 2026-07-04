import glob
import re

js_script = """
<script>
  document.addEventListener("DOMContentLoaded", () => {
    // Sélectionne toutes les images (on suppose que les images de galerie sont les principales)
    // On peut cibler plus spécifiquement si nécessaire, mais l'instruction dit "de chaque image de la galerie (sauf les 3 premières)"
    const images = Array.from(document.querySelectorAll("img"));
    const galleryImages = images.slice(3);
    
    // Pixel transparent pour vider le src proprement sans afficher d'icône d'erreur
    const transparentPixel = "data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7";

    // Étape A : Stocker le src et vider l'image
    galleryImages.forEach(img => {
      if (img.src && !img.getAttribute('data-src')) {
        img.setAttribute('data-src', img.src);
        img.src = transparentPixel;
      }
    });

    // Observer pour le recyclage
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        const img = entry.target;
        const dataSrc = img.getAttribute('data-src');
        if (!dataSrc) return;
        
        if (entry.isIntersecting) {
          // Étape B : Injection du src pour affichage
          if (img.src !== dataSrc) {
            img.src = dataSrc;
          }
        } else {
          // Étape C : Suppression du src pour libérer la RAM (texture unloading)
          // On ne le fait que si ce n'est pas déjà le pixel transparent
          if (img.src !== transparentPixel) {
            img.src = transparentPixel;
          }
        }
      });
    }, {
      rootMargin: "300px 0px 300px 0px", // Précharge légèrement avant l'affichage
      threshold: 0
    });

    galleryImages.forEach(img => {
      observer.observe(img);
    });
  });
</script>
"""

css_script = """
<style>
  /* OPTIMISATION SCROLL FLUIDE */
  html, body {
    scroll-behavior: smooth;
    -webkit-overflow-scrolling: touch;
  }
</style>
"""

for filepath in glob.glob("*.html"):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Inject CSS before </head> if not already there
    if "/* OPTIMISATION SCROLL FLUIDE */" not in content:
        content = re.sub(r'</head>', f'{css_script}</head>', content, flags=re.IGNORECASE)

    # Inject JS before </body> if not already there
    if "data:image/gif;base64" not in content:
        content = re.sub(r'</body>', f'{js_script}\n</body>', content, flags=re.IGNORECASE)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
