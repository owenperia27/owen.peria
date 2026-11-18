# Régie photo — mode d'emploi

Pour changer les photos du site sans toucher au code, une seule commande :

```
python3 scripts/regie.py
```

Une page s'ouvre dans ton navigateur. La première fois, l'ordinateur prépare tout seul
ce qu'il faut (une minute environ) : tu n'as rien à installer.

En haut, tu choisis une page du site (Accueil, Artists, Studio, Personal, Festivals,
Info, et les trois pages de projet). Sur les pages qui ont plusieurs séries, une deuxième
rangée de boutons te laisse choisir la série.

Clique une photo : un volet s'ouvre à droite.

- **Remplacer** — choisis une autre photo dans la photothèque, ou importe-la.
  Si la photo est aussi utilisée sur d'autres pages, la régie te demande si tu veux
  la changer partout ou seulement ici.
- **Légende** — écris en anglais ce que montre la photo (c'est ce que lisent les
  moteurs de recherche et les personnes qui n'ont pas l'image à l'écran).
  La légende est retenue : si tu remets cette photo ailleurs, elle la retrouve.
- **Recadrer** — choisis un format (libre, comme sur la page, 2:3, 1:1, 16:9…),
  déplace le cadre ou tire ses coins, puis valide. La photo d'origine n'est jamais
  modifiée : une version recadrée prend sa place sur la page, et tu peux toujours
  revenir à l'originale en la rechoisissant dans la photothèque.
- **Monter / Descendre** — change la place de la photo dans la mosaïque.
- **Retirer de la page** — la photo quitte la page mais reste dans la photothèque.

En bas de la mosaïque, **« + Ajouter une photo »** ajoute une photo à la fin.

**Importer des photos** (dans la fenêtre de la photothèque) accepte des JPG et des PNG :
ils sont convertis au format du site et préparés en trois tailles, pour que les pages
restent légères sur téléphone. Tu peux écrire le nom à leur donner dans la case prévue
(sinon la régie en propose un) ; elles sont rangées dans le dossier de la page ouverte.

Sur l'**Accueil**, les photos n'ont pas le même ordre sur ordinateur et sur téléphone :
ce sont deux boutons séparés en haut. Ajouter, retirer ou remplacer se fait dans la
mosaïque, et l'ordre sur téléphone se met à jour tout seul ; le deuxième bouton sert
seulement à changer cet ordre-là. Une même photo ne peut pas être deux fois sur l'accueil.

Sur certaines pages (Festivals, Info, la couverture des pages de projet), les photos sont
posées à la main dans une mise en page sur mesure : on peut les remplacer, les légender et
les recadrer, mais pas en ajouter ni en retirer.

Chaque changement est écrit tout de suite dans le site : il n'y a pas de bouton
« Enregistrer ». En haut à droite, **« Annuler la dernière modification »** revient en
arrière, autant de fois que nécessaire (une copie de chaque page est gardée avant chaque
changement, dans `scripts/sauvegardes`).

Rien ne part sur internet : tout se passe sur ton ordinateur. Quand tu as fini, ferme la
fenêtre du terminal (ou Ctrl+C). Pour mettre les changements en ligne, c'est l'envoi
habituel vers le site.
