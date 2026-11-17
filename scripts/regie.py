#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Régie photo — owenperia.com.

Ouvre une page dans le navigateur pour remplacer, légender, recadrer, déplacer,
retirer, ajouter et importer les photos du site. Rien n'est envoyé sur internet :
tout tourne sur cet ordinateur et écrit directement dans les fichiers du site.

    python3 scripts/regie.py
"""
import html
import http.server
import json
import os
import re
import shutil
import socketserver
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 8901                      # 8900 est pris par la régie de rowenstudio.fr
LARGEURS = (600, 1200, 2000)     # les tailles fabriquées en phase 5
QUALITE = 80
MARGE_MINI = 1.15                # on ne fabrique une taille que si l'original est 15 % plus large
SEUIL_SRC = 1400                 # au-delà, le src pointe vers une version plus petite
SRC_MAXI = 1200
DOSSIERS_IMAGES = ["assets", "artists", "studio", "personal",
                   "bvas-rio-loco", "rose-festival", "francofolies"]
SAUVEGARDES = os.path.join(RACINE, "scripts", "sauvegardes")
FICHIER_LEGENDES = os.path.join(RACINE, "scripts", "legendes.json")
JOURNAL = os.path.join(SAUVEGARDES, "journal.json")

RE_IMG = re.compile(r'<img\b[^>]*>', re.I)
RE_SUFFIXE = re.compile(r'-(?:%s)(?=\.webp$)' % "|".join(str(l) for l in LARGEURS))

# Chaque page du site : ses séries de photos (mosaïques) et son dossier d'images.
# "zone" = le conteneur de la mosaïque, repéré par sa balise d'ouverture et son rang
# dans le fichier. "jumelle" = la même mosaïque réécrite ailleurs dans la page
# (pages projet : une version téléphone et une version ordinateur, mêmes photos).
PAGES = [
    {"f": "index.html", "nom": "Accueil", "dossier": "assets",
     "series": [{"nom": "Mosaïque", "zone": ('<div class="masonry-gallery">', 0)}],
     "ordre_mobile": True},
    {"f": "artists.html", "nom": "Artists", "dossier": "artists",
     "series": [{"nom": "Mosaïque", "zone": ('<div class="grid-wrapper">', 0),
                 "copies_mobiles": True}]},
    {"f": "studio.html", "nom": "Studio & Editorial", "dossier": "studio",
     "series": [{"nom": None, "zone": ('<div class="columns-2 md:columns-3 gap-6 p-4 md:px-12 [column-fill:_auto]">', k)}
                for k in range(3)]},
    {"f": "personal.html", "nom": "Personal projects", "dossier": "personal",
     "series": [{"nom": "Mosaïque",
                 "zone": ('<div class="columns-2 md:columns-3 gap-4 md:gap-6 p-4 md:p-12 space-y-4 md:space-y-6 [column-fill:_auto]">', 0)}]},
    {"f": "festivals.html", "nom": "Festivals", "dossier": None, "series": []},
    {"f": "info.html", "nom": "Info & Contact", "dossier": None, "series": []},
    {"f": "festivals/bvas.html", "nom": "Projet — BVAS (Rio Loco)", "dossier": "bvas-rio-loco",
     "series": [{"nom": "Mosaïque", "zone": ('<div class="gallery-mobile">', 0),
                 "jumelle": ('<div class="gallery-desktop">', 0)}]},
    {"f": "festivals/rose.html", "nom": "Projet — Rose Festival", "dossier": "rose-festival",
     "series": [{"nom": "Mosaïque", "zone": ('<div class="gallery-mobile">', 0),
                 "jumelle": ('<div class="gallery-desktop">', 0)}]},
    {"f": "festivals/francofolies.html", "nom": "Projet — Francofolies", "dossier": "francofolies",
     "series": [{"nom": "Mosaïque", "zone": ('<div class="francofolies-gallery">', 0)}]},
]


# ------------------------------------------------------------------ Pillow
def pillow():
    """Première utilisation : fabrique un .venv, y installe Pillow, et s'y relance."""
    try:
        from PIL import Image  # noqa: F401
        return
    except ImportError:
        pass
    venv = os.path.join(RACINE, ".venv")
    py = os.path.join(venv, "bin", "python")
    if not os.path.exists(py):
        print("Première utilisation : j'installe de quoi fabriquer les images du site…")
        subprocess.run([sys.executable, "-m", "venv", venv], check=True)
        subprocess.run([py, "-m", "pip", "install", "--quiet", "--upgrade", "pip"], check=False)
        subprocess.run([py, "-m", "pip", "install", "--quiet", "pillow"], check=True)
    if os.path.abspath(sys.executable) != os.path.abspath(py):
        os.execv(py, [py] + sys.argv)


# ------------------------------------------------------------- petits outils
def lire(p):
    with open(os.path.join(RACINE, p), encoding="utf-8") as f:
        return f.read()


def ecrire(p, s):
    with open(os.path.join(RACINE, p), "w", encoding="utf-8") as f:
        f.write(s)


def attribut(balise, nom):
    m = re.search(r'\b%s="([^"]*)"' % nom, balise)
    return m.group(1) if m else ""


def echapper(t):
    return html.escape(t, quote=False).replace('"', "&quot;")


def original_de(src):
    """/assets/X-600.webp -> /assets/X.webp (le fichier d'origine)."""
    return RE_SUFFIXE.sub("", src)


def chemin_disque(src):
    return os.path.join(RACINE, src.lstrip("/"))


def legendes():
    if os.path.exists(FICHIER_LEGENDES):
        with open(FICHIER_LEGENDES, encoding="utf-8") as f:
            return json.load(f)
    return {}


def noter_legende(base, alt):
    if not alt:
        return
    d = legendes()
    if d.get(base) == alt:
        return
    d[base] = alt
    with open(FICHIER_LEGENDES, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def phototheque():
    """Toutes les photos disponibles (les originaux, pas les tailles fabriquées)."""
    out = []
    for d in DOSSIERS_IMAGES:
        dossier = os.path.join(RACINE, d)
        if not os.path.isdir(dossier):
            continue
        for f in sorted(os.listdir(dossier)):
            if f.endswith(".webp") and not RE_SUFFIXE.search(f):
                out.append("/%s/%s" % (d, f))
    return out


# ------------------------------------------------------- images (Pillow)
def dimensions(src):
    from PIL import Image
    with Image.open(chemin_disque(src)) as im:
        return im.width, im.height


def fabriquer_tailles(base):
    """Fabrique les versions 600/1200/2000 manquantes (jamais d'agrandissement).

    Mêmes règles que scripts/outils/fabriquer-tailles.js (phase 5).
    """
    from PIL import Image
    source = chemin_disque(base)
    with Image.open(source) as im:
        largeur, hauteur = im.width, im.height
        for l in LARGEURS:
            if largeur < l * MARGE_MINI:
                continue
            cible = chemin_disque(base[:-5] + "-%d.webp" % l)
            if os.path.exists(cible):
                continue
            copie = im.convert("RGB")
            copie = copie.resize((l, max(1, round(hauteur * l / largeur))), Image.LANCZOS)
            copie.save(cible, "WEBP", quality=QUALITE, method=5)


def tailles_existantes(base):
    """[(chemin, largeur réelle)] pour l'original et ses versions, du plus petit au plus grand."""
    out = []
    for l in LARGEURS:
        chemin = base[:-5] + "-%d.webp" % l
        if os.path.exists(chemin_disque(chemin)):
            out.append((chemin, dimensions(chemin)[0]))
    out.append((base, dimensions(base)[0]))
    vues, propre = set(), []
    for chemin, largeur in sorted(out, key=lambda x: x[1]):
        if largeur in vues:
            continue
        vues.add(largeur)
        propre.append((chemin, largeur))
    return propre


def src_et_srcset(base):
    """Le src et le srcset à écrire, selon la règle de la phase 5."""
    fabriquer_tailles(base)
    tailles = tailles_existantes(base)
    srcset = ", ".join("%s %dw" % (c, l) for c, l in tailles)
    largeur_origine = tailles[-1][1]
    if largeur_origine <= SEUIL_SRC:
        src = base
    else:
        petites = [c for c, l in tailles if l <= SRC_MAXI]
        src = petites[-1] if petites else base
    return src, srcset


# --------------------------------------------------- lecture du HTML (divs)
def _tags(s, debut, fin):
    """Balises <div>/</div> entre debut et fin, commentaires ignorés."""
    for m in re.finditer(r'<!--.*?-->|<div\b[^>]*>|</div\s*>', s[debut:fin], re.S | re.I):
        if m.group(0).startswith("<!--"):
            continue
        yield debut + m.start(), debut + m.end(), m.group(0).startswith("</")


def bloc_div(s, ouverture):
    """ouverture = index du '<' d'un <div…>. Renvoie (debut_interieur, fin_interieur, fin)."""
    fin_ouverture = s.index(">", ouverture) + 1
    profondeur = 1
    for a, b, fermante in _tags(s, fin_ouverture, len(s)):
        profondeur += -1 if fermante else 1
        if profondeur == 0:
            return fin_ouverture, a, b
    raise ValueError("balise <div> non refermée")


def enfants_div(s, debut, fin):
    """Les <div> enfants directs : [(ouverture, debut_interieur, fin_interieur, fin)]."""
    out, profondeur, courant = [], 0, None
    for a, b, fermante in _tags(s, debut, fin):
        if fermante:
            profondeur -= 1
            if profondeur == 0 and courant:
                out.append((courant[0], courant[1], a, b))
                courant = None
        else:
            if profondeur == 0:
                courant = (a, b)
            profondeur += 1
    return out


def nb_img(s, debut, fin):
    return len(RE_IMG.findall(s[debut:fin]))


def colonnes_de(s, debut, fin):
    """Les colonnes d'une mosaïque : [(debut_interieur, fin_interieur)].

    Descend à travers les emballages à enfant unique, puis décide : si les enfants
    contiennent une seule photo chacun, ce sont les photos (une seule colonne) ;
    sinon ce sont les colonnes.
    """
    while True:
        enfants = [e for e in enfants_div(s, debut, fin) if nb_img(s, e[0], e[3])]
        if not enfants:
            return [(debut, fin)]
        if len(enfants) == 1 and nb_img(s, enfants[0][0], enfants[0][3]) > 1:
            debut, fin = enfants[0][1], enfants[0][2]
            continue
        if all(nb_img(s, e[0], e[3]) == 1 for e in enfants):
            return [(debut, fin)]
        return [(e[1], e[2]) for e in enfants]


def photos_de_colonne(s, debut, fin):
    """Les blocs-photo d'une colonne : [(debut, fin, balise_img, position_img)]."""
    out = []
    for ouverture, _, _, f in enfants_div(s, debut, fin):
        if nb_img(s, ouverture, f) == 1:
            m = RE_IMG.search(s, ouverture, f)
            out.append((ouverture, f, m.group(0), m.start()))
    return out


def est_copie_mobile(s, debut_bloc, position_img):
    """Vrai si ce bloc est une copie « mobile-extra » (page Artists)."""
    return "mobile-extra" in s[debut_bloc:position_img]


def zone_de(s, marqueur):
    """(debut_interieur, fin_interieur) de la zone repérée par (texte, rang)."""
    texte, rang = marqueur
    pos = -1
    for _ in range(rang + 1):
        pos = s.index(texte, pos + 1)
    debut, fin, _ = bloc_div(s, pos)
    return debut, fin


# ---------------------------------------------------------- écriture d'un <img>
def reecrire_img(balise, base, alt):
    """Réécrit src, srcset, alt, width et height ; garde le reste (sizes, class…)."""
    meme_photo = original_de(attribut(balise, "src")) == base
    src, srcset = src_et_srcset(base)
    out = re.sub(r'\bsrc="[^"]*"', lambda _: 'src="%s"' % src, balise, count=1)
    if 'srcset="' in out:
        out = re.sub(r'\bsrcset="[^"]*"', lambda _: 'srcset="%s"' % srcset, out, count=1)
    else:
        out = out.replace('src="%s"' % src, 'src="%s" srcset="%s"' % (src, srcset), 1)
    out = re.sub(r'\balt="[^"]*"', lambda _: 'alt="%s"' % echapper(alt), out, count=1)
    if not meme_photo:
        # on ne réécrit les dimensions que pour une photo qui change : celles déjà
        # écrites décrivent le fichier d'origine et donnent la bonne proportion.
        w, h = dimensions(base)
        out = re.sub(r'\bwidth="[^"]*"', 'width="%d"' % w, out, count=1)
        out = re.sub(r'\bheight="[^"]*"', 'height="%d"' % h, out, count=1)
    return out


def normaliser_chargement(s):
    """La 1re photo de la page se charge tout de suite, les autres à l'approche."""
    balises = list(RE_IMG.finditer(s))
    for k in range(len(balises) - 1, -1, -1):
        m = balises[k]
        b = nouvelle = m.group(0)
        nouvelle = re.sub(r'\s*\bfetchpriority="[^"]*"', '', nouvelle)
        nouvelle = re.sub(r'\s*\bloading="[^"]*"', '', nouvelle)
        if k == 0:
            marque = ' fetchpriority="high"'
            if ' alt="' in nouvelle:
                nouvelle = nouvelle.replace(' alt="', marque + ' alt="', 1)
            else:
                nouvelle = nouvelle[:-1].rstrip() + marque + nouvelle[-1]
        else:
            marque = ' loading="lazy"'
            if ' decoding="' in nouvelle:
                nouvelle = nouvelle.replace(' decoding="', marque + ' decoding="', 1)
            elif ' width="' in nouvelle:
                nouvelle = nouvelle.replace(' width="', marque + ' width="', 1)
            else:
                nouvelle = nouvelle[:-1].rstrip() + marque + nouvelle[-1]
        if nouvelle != b:
            s = s[:m.start()] + nouvelle + s[m.end():]
    return s


# ------------------------------------------------------------ état des pages
def serie_nom(s, page, serie, k):
    if serie.get("nom"):
        return serie["nom"]
    debut, _ = zone_de(s, serie["zone"])
    titres = list(re.finditer(r'<h2\b[^>]*>(.*?)</h2>', s[:debut], re.S | re.I))
    if titres:
        return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', titres[-1].group(1))).strip()
    return "Série %d" % (k + 1)


def photos_de_serie(s, serie):
    """Les photos d'une série, dans l'ordre : [(balise_img, position_img)]."""
    debut, fin = zone_de(s, serie["zone"])
    out = []
    for a, b in colonnes_de(s, debut, fin):
        for d, _, balise, position in photos_de_colonne(s, a, b):
            if est_copie_mobile(s, d, position):
                continue
            out.append((balise, position))
    return out


def infos_photo(balise, i, legendes_connues):
    src = attribut(balise, "src")
    base = original_de(src)
    alt = html.unescape(attribut(balise, "alt"))
    return {"i": i, "base": base, "src": src, "alt": alt,
            "legende_connue": legendes_connues.get(base, ""),
            "w": attribut(balise, "width"), "h": attribut(balise, "height")}


def etat_page(page):
    s = lire(page["f"])
    connues = legendes()
    vues = set()
    series = []
    for k, serie in enumerate(page["series"]):
        photos = []
        for i, (balise, position) in enumerate(photos_de_serie(s, serie)):
            photos.append(infos_photo(balise, i, connues))
            vues.add(position)
        if serie.get("jumelle"):
            for _, position in photos_de_serie(s, {"zone": serie["jumelle"]}):
                vues.add(position)
        if serie.get("copies_mobiles"):
            debut, fin = zone_de(s, serie["zone"])
            for a, b in colonnes_de(s, debut, fin):
                for d, _, _, position in photos_de_colonne(s, a, b):
                    if est_copie_mobile(s, d, position):
                        vues.add(position)
        series.append({"nom": serie_nom(s, page, serie, k), "photos": photos})
    if page.get("ordre_mobile"):
        ordre = lire_ordre_mobile(s)
        principales = {p["src"]: p for p in series[0]["photos"]}
        photos = []
        for i, src in enumerate(ordre):
            if src in principales:
                photos.append(dict(principales[src], i=i))
        series.append({"nom": "Même mosaïque — ordre sur téléphone", "photos": photos,
                       "mobile": True})
    fixes = []
    for i, m in enumerate(RE_IMG.finditer(s)):
        if m.start() in vues or not attribut(m.group(0), "src").endswith(".webp"):
            continue
        fixes.append(dict(infos_photo(m.group(0), i, connues), fixe=True))
    return {"f": page["f"], "nom": page["nom"], "dossier": page.get("dossier"),
            "series": series, "fixes": fixes}


# -------------------------------------------------- ordre mobile de l'accueil
def lire_ordre_mobile(s):
    m = re.search(r'var mobileOrder = \[(.*?)\n      \];', s, re.S)
    if not m:
        return []
    return re.findall(r"'([^']+)'", m.group(1))


def ecrire_ordre_mobile(s, srcs):
    """Réécrit le tableau mobileOrder d'index.html (4 adresses par ligne)."""
    m = re.search(r'(var mobileOrder = \[)(.*?)(\n      \];)', s, re.S)
    if not m:
        return s
    milieu = len(srcs) // 2 + len(srcs) % 2
    lignes = []
    for titre, part in (("colonne GAUCHE", srcs[:milieu]), ("colonne DROITE", srcs[milieu:])):
        lignes.append("        // --- %s ---" % titre)
        for i in range(0, len(part), 4):
            bout = ", ".join("'%s'" % x for x in part[i:i + 4])
            lignes.append("        " + bout + ("," if i + 4 < len(part) or titre.endswith("GAUCHE") else ""))
    return s[:m.start(2)] + "\n" + "\n".join(lignes) + s[m.end(2):]


def synchroniser_ordre_mobile(s, srcs_page):
    """Garde l'ordre téléphone existant : retire les photos parties, ajoute les neuves."""
    ancien = [x for x in lire_ordre_mobile(s) if x in srcs_page]
    for src in srcs_page:
        if src not in ancien:
            ancien.append(src)
    return ecrire_ordre_mobile(s, ancien)


# ------------------------------------------------------- écriture d'une série
def repartir(n, colonnes):
    base, reste = divmod(n, colonnes)
    return [base + (1 if i < reste else 0) for i in range(colonnes)]


def ecrire_zone(s, marqueur, photos, copies_mobiles=False):
    """Réécrit une mosaïque : les blocs-photo sont déplacés, jamais réinventés."""
    debut, fin = zone_de(s, marqueur)
    cols = colonnes_de(s, debut, fin)
    anciens, anciennes_copies = {}, {}   # base -> bloc existant (réutilisé tel quel)
    modele = modele_copie = None
    for a, b in cols:
        for d, f, balise, _ in photos_de_colonne(s, a, b):
            bloc = s[d:f]
            base = original_de(attribut(balise, "src"))
            if "mobile-extra" in bloc[:bloc.index("<img")]:
                modele_copie = modele_copie or bloc
                anciennes_copies.setdefault(base, bloc)
                continue
            modele = modele or bloc
            anciens.setdefault(base, bloc)
    if modele is None:
        raise ValueError("mosaïque vide : impossible de savoir comment écrire une photo")

    def bloc_pour(photo, copie=False):
        if copie:
            gabarit = anciennes_copies.get(photo["base"]) or modele_copie or modele
        else:
            gabarit = anciens.get(photo["base"], modele)
        balise = RE_IMG.search(gabarit).group(0)
        neuve = reecrire_img(balise, photo["base"], photo["alt"])
        return gabarit.replace(balise, neuve, 1)

    tailles = repartir(len(photos), len(cols))
    decoupe, k = [], 0
    for t in tailles:
        decoupe.append(photos[k:k + t])
        k += t
    copies = []
    if copies_mobiles and len(cols) >= 3:
        derniere = decoupe[-1]
        moitie = len(derniere) // 2 + len(derniere) % 2
        copies = [derniere[:moitie], derniere[moitie:]] + [[]] * (len(cols) - 2)

    for index_col in range(len(cols) - 1, -1, -1):
        a, b = cols[index_col]
        existants = photos_de_colonne(s, a, b)
        blocs = [bloc_pour(p) for p in decoupe[index_col]]
        if copies:
            blocs += [bloc_pour(p, True) for p in copies[index_col]]
        if existants:
            prefixe = s[a:existants[0][0]]
            suffixe = s[existants[-1][1]:b]
            ecarts = [s[existants[j - 1][1]:existants[j][0]] for j in range(1, len(existants))]
        else:
            prefixe, suffixe, ecarts = s[a:b], "", []
        defaut = ecarts[-1] if ecarts else "\n" + " " * 8
        corps = ""
        for j, bloc in enumerate(blocs):
            if j:
                corps += ecarts[j - 1] if j - 1 < len(ecarts) else defaut
            corps += bloc
        s = s[:a] + prefixe + corps + suffixe + s[b:]
    return s


def enregistrer_serie(page, index_serie, photos, etiquette):
    """Écrit une série entière (remplacement, légende, ordre, ajout, retrait)."""
    for p in photos:
        if not os.path.exists(chemin_disque(p["base"])):
            raise ValueError("photo introuvable : %s" % p["base"])
    if page.get("ordre_mobile"):
        # sur l'accueil, l'ordre sur téléphone repère chaque photo par son adresse :
        # une même photo deux fois et il ne s'y retrouve plus.
        bases = [p["base"] for p in photos]
        deja = [original_de(attribut(b, "src"))
                for b, _ in photos_de_serie(lire(page["f"]), page["series"][0])]
        apres = [b for b in set(bases) if bases.count(b) > 1]
        avant = [b for b in set(deja) if deja.count(b) > 1]
        nouveaux = [b for b in apres if b not in avant]
        if nouveaux:
            raise ValueError("Cette photo est déjà sur l'accueil : %s. Sur l'accueil, "
                             "chaque photo ne peut y être qu'une fois." % nouveaux[0].split("/")[-1])
    s = lire(page["f"])
    series = page["series"]
    if page.get("ordre_mobile") and index_serie == len(series):
        # l'onglet « ordre sur téléphone » ne touche que le tableau de l'accueil
        sauvegarder(page["f"], etiquette)
        s = ecrire_ordre_mobile(s, [src_et_srcset(p["base"])[0] for p in photos])
        ecrire(page["f"], s)
        return [page["f"]]
    serie = series[index_serie]
    sauvegarder(page["f"], etiquette)
    s = ecrire_zone(s, serie["zone"], photos, serie.get("copies_mobiles", False))
    if serie.get("jumelle"):
        s = ecrire_zone(s, serie["jumelle"], photos)
    s = normaliser_chargement(s)
    if page.get("ordre_mobile"):
        s = synchroniser_ordre_mobile(s, [src_et_srcset(p["base"])[0] for p in photos])
    ecrire(page["f"], s)
    for p in photos:
        noter_legende(p["base"], p["alt"])
    return [page["f"]]


def enregistrer_fixe(page, i, base, alt, etiquette):
    """Photo hors mosaïque (couverture, portrait) : on remplace sur place."""
    s = lire(page["f"])
    balises = list(RE_IMG.finditer(s))
    if i >= len(balises):
        raise ValueError("photo introuvable sur la page")
    sauvegarder(page["f"], etiquette)
    m = balises[i]
    s = s[:m.start()] + reecrire_img(m.group(0), base, alt) + s[m.end():]
    s = normaliser_chargement(s)
    ecrire(page["f"], s)
    noter_legende(base, alt)
    return [page["f"]]


def remplacer_partout(ancienne, nouvelle, alt, etiquette):
    """Remplace une photo sur toutes les pages où elle apparaît."""
    touchees = []
    for page in PAGES:
        s = lire(page["f"])
        if ancienne not in s and original_de(ancienne) not in s:
            continue
        concernee = False
        for m in list(RE_IMG.finditer(s))[::-1]:
            if original_de(attribut(m.group(0), "src")) != ancienne:
                continue
            if not concernee:
                sauvegarder(page["f"], etiquette)
                concernee = True
            s = s[:m.start()] + reecrire_img(m.group(0), nouvelle, alt) + s[m.end():]
        if not concernee:
            continue
        s = normaliser_chargement(s)
        if page.get("ordre_mobile"):
            srcs = [attribut(b, "src") for b, _ in photos_de_serie(s, page["series"][0])]
            s = synchroniser_ordre_mobile(s, srcs)
        ecrire(page["f"], s)
        touchees.append(page["f"])
    noter_legende(nouvelle, alt)
    return touchees


def pages_utilisant(base):
    out = []
    for page in PAGES:
        s = lire(page["f"])
        if re.search(r'src="%s(-\d+)?\.webp"' % re.escape(base[:-5]), s):
            out.append(page["nom"])
    return out


# ------------------------------------------------------------------ recadrage
def recadrer(base, x, y, w, h):
    """Nouvelle photo recadrée ; l'original n'est jamais modifié."""
    from PIL import Image
    with Image.open(chemin_disque(base)) as im:
        im = im.convert("RGB")
        W, H = im.size
        x, y = max(0.0, min(float(x), 1.0)), max(0.0, min(float(y), 1.0))
        w = max(0.02, min(float(w), 1.0 - x))
        h = max(0.02, min(float(h), 1.0 - y))
        coupe = im.crop((round(x * W), round(y * H), round((x + w) * W), round((y + h) * H)))
    nouvelle = base[:-5] + "-recadre.webp"
    k = 2
    while os.path.exists(chemin_disque(nouvelle)):
        nouvelle = "%s-recadre-%d.webp" % (base[:-5], k)
        k += 1
    coupe.save(chemin_disque(nouvelle), "WEBP", quality=QUALITE, method=5)
    fabriquer_tailles(nouvelle)
    noter_legende(nouvelle, legendes().get(base, ""))
    return nouvelle


# ------------------------------------------------------------------ import
def nom_propre(propose, dossier, secours):
    racine = re.sub(r'[^a-z0-9]+', '-', (propose or secours).lower()).strip("-") or "photo"
    if re.match(r'^(dsc|img|hr9a|sim|dscf|p\d)', racine):
        racine = dossier.strip("/")
    base = "/%s/%s.webp" % (dossier, racine)
    k = 2
    while os.path.exists(chemin_disque(base)):
        base = "/%s/%s-%02d.webp" % (dossier, racine, k)
        k += 1
    return base


def importer(corps_brut, type_contenu, dossier, nom):
    from PIL import Image, ImageOps
    import io
    if dossier not in DOSSIERS_IMAGES:
        raise ValueError("dossier inconnu")
    limite = type_contenu.split("boundary=")[-1].encode()
    ajoutees = []
    for partie in corps_brut.split(b"--" + limite):
        if b"filename=" not in partie:
            continue
        entete, _, contenu = partie.partition(b"\r\n\r\n")
        fichier = re.search(rb'filename="([^"]*)"', entete).group(1).decode()
        if not fichier:
            continue
        contenu = contenu.rstrip(b"\r\n-")
        base = nom_propre(nom, dossier, os.path.splitext(fichier)[0])
        im = ImageOps.exif_transpose(Image.open(io.BytesIO(contenu))).convert("RGB")
        if im.width > 2000 or im.height > 2000:
            im.thumbnail((2000, 2000), Image.LANCZOS)
        im.save(chemin_disque(base), "WEBP", quality=QUALITE, method=5)
        fabriquer_tailles(base)
        ajoutees.append(base)
    return ajoutees


# ------------------------------------------------------------- sauvegardes
def journal():
    if os.path.exists(JOURNAL):
        with open(JOURNAL, encoding="utf-8") as f:
            return json.load(f)
    return []


def sauvegarder(fichier, etiquette):
    os.makedirs(SAUVEGARDES, exist_ok=True)
    horodatage = time.strftime("%Y%m%d-%H%M%S") + "-%03d" % (time.time() % 1 * 1000)
    copie = "%s__%s" % (horodatage, fichier.replace("/", "-"))
    shutil.copy2(os.path.join(RACINE, fichier), os.path.join(SAUVEGARDES, copie))
    entrees = journal()
    entrees.append({"quand": horodatage, "fichier": fichier, "copie": copie, "quoi": etiquette})
    with open(JOURNAL, "w", encoding="utf-8") as f:
        json.dump(entrees[-200:], f, ensure_ascii=False, indent=2)


def annuler():
    entrees = journal()
    if not entrees:
        raise ValueError("Il n'y a rien à annuler.")
    derniere = entrees[-1]["quand"]
    refaites = []
    while entrees and entrees[-1]["quand"] == derniere:
        e = entrees.pop()
        shutil.copy2(os.path.join(SAUVEGARDES, e["copie"]), os.path.join(RACINE, e["fichier"]))
        refaites.append(e["fichier"])
    with open(JOURNAL, "w", encoding="utf-8") as f:
        json.dump(entrees, f, ensure_ascii=False, indent=2)
    return refaites, entrees[-1]["quoi"] if entrees else ""


# ------------------------------------------------------------------ serveur
class Regie(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=RACINE, **k)

    def log_message(self, *a):
        pass

    def _json(self, data, code=200):
        corps = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corps)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self):
        chemin = urllib.parse.urlparse(self.path).path
        if chemin == "/":
            with open(os.path.join(RACINE, "scripts", "regie.html"), "rb") as f:
                corps = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corps)
            return
        if chemin == "/api/etat":
            return self._json({
                "pages": [etat_page(p) for p in PAGES],
                "phototheque": phototheque(),
                "dossiers": DOSSIERS_IMAGES,
                "annulations": len(journal()),
                "derniere": journal()[-1]["quoi"] if journal() else "",
            })
        return super().do_GET()

    def do_POST(self):
        chemin = urllib.parse.urlparse(self.path).path
        requete = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        brut = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        try:
            if chemin == "/api/importer":
                ajoutees = importer(brut, self.headers.get("Content-Type", ""),
                                    requete.get("dossier", ["assets"])[0],
                                    requete.get("nom", [""])[0])
                return self._json({"ok": True, "ajoutees": ajoutees})
            d = json.loads(brut or b"{}")
            if chemin == "/api/serie":
                page = [p for p in PAGES if p["f"] == d["page"]][0]
                pages = enregistrer_serie(page, d["serie"], d["photos"], d.get("quoi", "modification"))
                return self._json({"ok": True, "pages": pages})
            if chemin == "/api/fixe":
                page = [p for p in PAGES if p["f"] == d["page"]][0]
                pages = enregistrer_fixe(page, d["i"], d["base"], d["alt"], d.get("quoi", "modification"))
                return self._json({"ok": True, "pages": pages})
            if chemin == "/api/partout":
                pages = remplacer_partout(d["ancienne"], d["nouvelle"], d["alt"],
                                          d.get("quoi", "remplacement partout"))
                return self._json({"ok": True, "pages": pages})
            if chemin == "/api/recadrer":
                return self._json({"ok": True, "base": recadrer(d["base"], d["x"], d["y"], d["w"], d["h"])})
            if chemin == "/api/usages":
                return self._json({"ok": True, "pages": pages_utilisant(d["base"])})
            if chemin == "/api/annuler":
                pages, reste = annuler()
                return self._json({"ok": True, "pages": pages, "reste": reste})
        except Exception as e:  # noqa: BLE001
            return self._json({"ok": False, "erreur": str(e)}, 500)
        self._json({"ok": False, "erreur": "adresse inconnue"}, 404)


def fermer_ancienne_regie():
    import urllib.request
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/api/etat" % PORT, timeout=3) as r:
            if "pages" not in json.loads(r.read()):
                return False
    except Exception:  # noqa: BLE001
        return False
    pids = subprocess.run(["lsof", "-tiTCP:%d" % PORT, "-sTCP:LISTEN"],
                          capture_output=True, text=True).stdout.split()
    for pid in pids:
        if int(pid) != os.getpid():
            os.kill(int(pid), 15)
    return bool(pids)


def main():
    pillow()
    os.chdir(RACINE)
    socketserver.TCPServer.allow_reuse_address = True
    srv = None
    for essai in range(2):
        try:
            srv = socketserver.TCPServer(("127.0.0.1", PORT), Regie)
            break
        except OSError:
            if essai == 0 and fermer_ancienne_regie():
                print("Ancienne régie fermée, ouverture de la nouvelle…")
                time.sleep(1)
                continue
            print("Le port %d est occupé par un autre programme : ferme-le, puis relance." % PORT)
            return
    with srv:
        url = "http://127.0.0.1:%d/" % PORT
        print("Régie photo ouverte sur %s   (Ctrl+C pour fermer)" % url)
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\nFermé.")


if __name__ == "__main__":
    main()
