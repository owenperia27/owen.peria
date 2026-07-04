#!/usr/bin/env node
/**
 * fix-image-dimensions.js
 * ------------------------------------------------------------------
 * Scans every .html file in this folder, finds <img> tags that don't
 * yet have width/height, reads the REAL pixel dimensions of the local
 * image file they point to, and writes those dimensions into the tag.
 *
 * Why this matters: once width/height are present, the browser derives
 * the image's correct intrinsic aspect-ratio and reserves the right
 * box size BEFORE the file has even started downloading — no reflow,
 * no cumulative layout shift, and native loading="lazy" works properly
 * again because the browser finally knows where every image will sit.
 * Nothing is cropped: each photo keeps ITS OWN ratio (portrait stays
 * portrait, landscape stays landscape).
 *
 * Usage:
 *   1) npm install image-size
 *   2) node fix-image-dimensions.js
 *
 * Safe to re-run: images that already have width AND height are left
 * completely untouched.
 * ------------------------------------------------------------------
 */

const fs = require('fs');
const path = require('path');
const { imageSize } = require('image-size');

const ROOT = __dirname;
const htmlFiles = fs
  .readdirSync(ROOT)
  .filter((f) => f.toLowerCase().endsWith('.html'));

// Matches a whole <img ...> tag (self-closing or not), attributes captured as one group.
const IMG_TAG_RE = /<img\b((?:[^>]|\n)*?)\/?>/gi;
const SRC_RE = /\bsrc\s*=\s*(["'])(.*?)\1/i;
const HAS_WIDTH_RE = /\bwidth\s*=/i;
const HAS_HEIGHT_RE = /\bheight\s*=/i;

let totalFixed = 0;
let totalSkippedAlready = 0;
let totalMissing = 0;

htmlFiles.forEach((file) => {
  const filePath = path.join(ROOT, file);
  let html = fs.readFileSync(filePath, 'utf8');
  let fixedInFile = 0;

  html = html.replace(IMG_TAG_RE, (tag, attrs) => {
    const hasWidth = HAS_WIDTH_RE.test(attrs);
    const hasHeight = HAS_HEIGHT_RE.test(attrs);

    if (hasWidth && hasHeight) {
      totalSkippedAlready++;
      return tag; // already sized — leave completely untouched
    }
    if (hasWidth || hasHeight) {
      // Only one of the two present: don't risk creating a duplicate
      // attribute. Flag it so it can be fixed by hand.
      console.warn(`  ⚠️  ${file}: width/height partiels, ignoré → ${tag.slice(0, 90)}...`);
      return tag;
    }

    const srcMatch = attrs.match(SRC_RE);
    if (!srcMatch) return tag; // no src found, leave alone

    const src = srcMatch[2];
    if (/^(https?:)?\/\//i.test(src) || src.startsWith('data:')) {
      return tag; // remote or inline image, nothing local to read
    }

    const imgPath = path.join(ROOT, decodeURIComponent(src));
    if (!fs.existsSync(imgPath)) {
      totalMissing++;
      console.warn(`  ⚠️  ${file}: file introuvable → ${src}`);
      return tag;
    }

    try {
      const buffer = fs.readFileSync(imgPath);
      const { width, height } = imageSize(buffer);
      fixedInFile++;
      totalFixed++;
      // Insert width/height right after the src attribute's tag start,
      // i.e. just append to the existing attribute string.
      const closing = tag.trim().endsWith('/>') ? ' />' : '>';
      return `<img${attrs.replace(/\s*\/?$/, '')} width="${width}" height="${height}"${closing}`;
    } catch (err) {
      console.warn(`  ⚠️  ${file}: lecture impossible → ${src} (${err.message})`);
      return tag;
    }
  });

  if (fixedInFile > 0) {
    fs.writeFileSync(filePath, html, 'utf8');
  }
  console.log(`${file}: ${fixedInFile} image(s) corrigée(s)`);
});

console.log(
  `\n✅ Terminé — ${totalFixed} image(s) corrigée(s), ${totalSkippedAlready} déjà correctes, ${totalMissing} fichier(s) introuvable(s).`
);
