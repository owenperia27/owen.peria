#!/usr/bin/env python3
"""Réécrit les chemins locaux absolus (/css/…, /assets/…, /info) en chemins
relatifs, pour que le site s'ouvre en double-clic. Idempotent."""
import os, re, sys, glob

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGES_NAV = {"studio", "personal", "info", "artists", "festivals"}

def pages(racine):
    return sorted(glob.glob(os.path.join(racine, "*.html")) + glob.glob(os.path.join(racine, "festivals", "*.html")))

def convertir(chemin, profondeur, navigation):
    """chemin absolu '/…' -> relatif à la page (profondeur 0 = racine, 1 = festivals/)."""
    if not chemin.startswith("/") or chemin.startswith("//"):
        return chemin
    m = re.match(r"^(/[^?#]*)([?#].*)?$", chemin)
    corps, suite = m.group(1), m.group(2) or ""
    prefixe = "../" * profondeur
    if navigation:
        if corps == "/":
            cible = "index.html"
        else:
            nom = corps.strip("/")
            if nom.startswith("festivals/"):
                cible = nom + ".html"
                if profondeur == 1:
                    return nom.split("/", 1)[1] + ".html" + suite
            elif nom in PAGES_NAV:
                cible = nom + ".html"
            else:
                cible = nom
        return prefixe + cible + suite
    return prefixe + corps.lstrip("/") + suite

def reecrire(texte, profondeur):
    def attr(m):
        nom, q, val = m.group(1), m.group(2), m.group(3)
        if nom == "srcset":
            parts = []
            for cand in val.split(","):
                cand = cand.strip()
                u, _, d = cand.partition(" ")
                parts.append((convertir(u, profondeur, False) + (" " + d if d else "")))
            val = ", ".join(parts)
        elif nom == "href":
            if val.startswith("/") and not val.startswith("//"):
                nav = not re.search(r"\.(css|woff2?|webp|jpe?g|png|svg|ico)(\?|$)", val)
                val = convertir(val, profondeur, nav)
        elif nom in ("src", "poster"):
            val = convertir(val, profondeur, False)
        return f"{nom}={q}{val}{q}"
    texte = re.sub(r'\b(src|srcset|href|poster)=(["\'])(.*?)\2', attr, texte, flags=re.S)
    texte = re.sub(r"url\((['\"]?)(/[^)'\"]*)\1\)",
                   lambda m: "url(%s%s%s)" % (m.group(1), convertir(m.group(2), profondeur, False), m.group(1)), texte)
    # chaînes de chemins dans les <script> (hors JSON-LD)
    def script(m):
        if "ld+json" in m.group(1):
            return m.group(0)
        corps = re.sub(r"(['\"])(/(?:assets|css|fonts|artists|studio|personal|og|bvas-rio-loco|rose-festival|francofolies)/[^'\"]*)\1",
                       lambda s: s.group(1) + convertir(s.group(2), profondeur, False) + s.group(1), m.group(3))
        return m.group(1) + m.group(2) + corps + m.group(4)
    texte = re.sub(r"(<script[^>]*>)()(.*?)(</script>)", script, texte, flags=re.S)
    return texte

if __name__ == "__main__":
    racine = sys.argv[1] if len(sys.argv) > 1 else RACINE
    for p in pages(racine):
        prof = 1 if os.path.basename(os.path.dirname(p)) == "festivals" else 0
        t = open(p, encoding="utf-8").read()
        n = reecrire(t, prof)
        if n != t:
            open(p, "w", encoding="utf-8").write(n)
            print("réécrit :", os.path.relpath(p, racine))
