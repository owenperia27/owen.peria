#!/usr/bin/env node
/**
 * fabriquer-tailles.js — owenperia.com, phase 5
 *
 * Fabrique, à côté de chaque photo WebP du site, trois versions plus petites :
 *   photo.webp  ->  photo-600.webp, photo-1200.webp, photo-2000.webp
 *
 * Le navigateur choisit ensuite la plus petite version qui suffit à l'écran
 * du visiteur (attributs srcset / sizes dans les pages).
 *
 * Garanties :
 *   - l'original n'est JAMAIS modifié ni supprimé ;
 *   - aucune version n'est agrandie au-delà de la largeur de l'original ;
 *   - relançable sans risque : ce qui existe déjà est ignoré (sauf --refaire).
 *
 * Usage :
 *   node scripts/outils/fabriquer-tailles.js            # fabrique ce qui manque
 *   node scripts/outils/fabriquer-tailles.js --essai    # n'écrit rien, liste
 *   node scripts/outils/fabriquer-tailles.js --refaire  # réécrit tout
 */

'use strict';

// ─── Réglages (volontairement en dur, en haut, faciles à relire) ────────────

const LARGEURS = [600, 1200, 2000];   // largeurs fabriquées, en pixels
const QUALITE = 80;                   // qualité WebP (0-100)
const EFFORT = 5;                     // effort de compression WebP (0-6)

// Une version n'est fabriquée que si l'original est au moins 15 % plus large :
// en dessous, le fichier produit pèserait presque autant pour rien.
const MARGE_MINI = 1.15;

const DOSSIERS = [
  'assets',
  'artists',
  'studio',
  'personal',
  'bvas-rio-loco',
  'rose-festival',
  'francofolies',
];

// ─── Code ───────────────────────────────────────────────────────────────────

const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

const RACINE = path.resolve(__dirname, '..', '..');
const ESSAI = process.argv.includes('--essai');
const REFAIRE = process.argv.includes('--refaire');

// Une photo "originale" est un .webp dont le nom ne finit pas par -<largeur>.
const SUFFIXE = new RegExp('-(' + LARGEURS.join('|') + ')\\.webp$', 'i');

function originaux(dossier) {
  const abs = path.join(RACINE, dossier);
  if (!fs.existsSync(abs)) return [];
  return fs
    .readdirSync(abs)
    .filter((f) => f.toLowerCase().endsWith('.webp') && !SUFFIXE.test(f))
    .sort()
    .map((f) => path.join(abs, f));
}

function nomVariante(fichier, largeur) {
  return fichier.replace(/\.webp$/i, '-' + largeur + '.webp');
}

async function traiter(fichier) {
  const meta = await sharp(fichier).metadata();
  const faits = [];

  for (const largeur of LARGEURS) {
    // Jamais d'agrandissement, et pas de version quasi identique à l'original.
    if (largeur * MARGE_MINI > meta.width) continue;

    const sortie = nomVariante(fichier, largeur);
    if (!REFAIRE && fs.existsSync(sortie)) continue;

    if (ESSAI) {
      faits.push(path.relative(RACINE, sortie) + ' (essai)');
      continue;
    }

    // Écriture par fichier temporaire : une interruption ne laisse pas
    // de .webp tronqué qu'une relance prendrait pour un fichier fini.
    const tmp = sortie + '.tmp';
    await sharp(fichier)
      .resize({ width: largeur, withoutEnlargement: true })
      .webp({ quality: QUALITE, effort: EFFORT })
      .toFile(tmp);
    fs.renameSync(tmp, sortie);

    faits.push(path.relative(RACINE, sortie));
  }

  return { largeur: meta.width, hauteur: meta.height, faits };
}

(async () => {
  let nbOriginaux = 0;
  let nbFaits = 0;
  let octets = 0;

  for (const dossier of DOSSIERS) {
    const fichiers = originaux(dossier);
    if (!fichiers.length) continue;
    console.log('\n— ' + dossier + ' (' + fichiers.length + ' photos)');

    for (const fichier of fichiers) {
      nbOriginaux++;
      const r = await traiter(fichier);
      for (const f of r.faits) {
        nbFaits++;
        if (!ESSAI) octets += fs.statSync(path.join(RACINE, f)).size;
        console.log('  + ' + f);
      }
      if (!r.faits.length) {
        console.log(
          '  = ' + path.basename(fichier) +
          ' (rien à faire, ' + r.largeur + ' × ' + r.hauteur + ' px)'
        );
      }
    }
  }

  console.log(
    '\n' + nbOriginaux + ' originaux lus, ' + nbFaits + ' fichiers ' +
    (ESSAI ? 'à fabriquer' : 'fabriqués') +
    (octets ? ' (' + (octets / 1048576).toFixed(1) + ' Mo ajoutés sur le disque)' : '')
  );
})().catch((e) => {
  console.error('Erreur :', e.message);
  process.exit(1);
});
