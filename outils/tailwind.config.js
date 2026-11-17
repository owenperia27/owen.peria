/** Compilation hors ligne du CSS Tailwind d'owenperia.com.
 *  Remplace le compilateur cdn.tailwindcss.com (v3.4.17) qui tournait chez le visiteur.
 *  Voir outils/LISEZMOI.txt pour la commande. */
module.exports = {
  content: ['../*.html'],
  theme: { extend: {} },
  plugins: [],
};
