#!/usr/bin/env python3
"""Vérifie, sans serveur, que chaque référence locale des pages existe sur le
disque et qu'aucune n'est absolue. Usage : python3 outils/verifier-chemins.py [dossier]"""
import os, re, sys, glob
from urllib.parse import unquote

racine = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pages = sorted(glob.glob(os.path.join(racine, "*.html")) + glob.glob(os.path.join(racine, "festivals", "*.html")))
erreurs = absolues = total = 0

def locale(v):
    return v and not re.match(r"^(https?:|mailto:|tel:|data:|javascript:|//)", v)

for p in pages:
    t = open(p, encoding="utf-8").read()
    rel = os.path.relpath(p, racine)
    refs = []
    for m in re.finditer(r'\b(src|srcset|href|poster)=(["\'])(.*?)\2', t, flags=re.S):
        nom, val = m.group(1), m.group(3)
        if nom == "srcset":
            refs += [c.strip().split(" ")[0] for c in val.split(",") if c.strip()]
        else:
            refs.append(val)
    refs += [m.group(2) for m in re.finditer(r"url\((['\"]?)([^)'\"]+)\1\)", t)]
    for m in re.finditer(r"<script(?![^>]*ld\+json)[^>]*>(.*?)</script>", t, flags=re.S):
        refs += [s.group(2) for s in re.finditer(r"(['\"])(/?(?:\.\./)*(?:assets|css|fonts|artists|studio|personal|og|bvas-rio-loco|rose-festival|francofolies)/[^'\"]*)\1", m.group(1))]
    ids = set(re.findall(r'\bid=["\']([^"\']+)["\']', t))
    for r in refs:
        if not locale(r):
            continue
        total += 1
        if r.startswith("#"):
            if len(r) > 1 and r[1:] not in ids:
                print(f"{rel}: ancre introuvable {r}"); erreurs += 1
            continue
        if r.startswith("/"):
            print(f"{rel}: référence absolue {r}"); absolues += 1; continue
        cible = unquote(re.split(r"[?#]", r)[0])
        if not os.path.exists(os.path.normpath(os.path.join(os.path.dirname(p), cible))):
            print(f"{rel}: fichier introuvable {r}"); erreurs += 1
print(f"{len(pages)} pages, {total} références locales : {erreurs} erreur(s), {absolues} référence(s) absolue(s)")
sys.exit(1 if erreurs or absolues else 0)
