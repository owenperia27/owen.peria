#!/bin/bash
# Double-clique ce fichier pour voir le site en local, tel qu'il sera en ligne.
# Ferme la fenêtre du Terminal (ou Ctrl+C) pour arrêter.
cd "$(dirname "$0")" || exit 1
PORT=4180
echo "Le site est visible sur http://localhost:$PORT  (fermer cette fenêtre pour arrêter)"
( sleep 1; open "http://localhost:$PORT/" ) &
exec /usr/bin/python3 -I - "$PORT" <<'PY'
import sys, os, http.server, socketserver
class H(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        p = super().translate_path(path)
        # adresses propres comme sur Vercel : /info -> info.html, /festivals -> festivals.html (même si un dossier festivals/ existe)
        if (not os.path.exists(p) or os.path.isdir(p)) and os.path.isfile(p.rstrip("/") + ".html") and not path.endswith("/"):
            return p.rstrip("/") + ".html"
        return p
    def log_message(self, *a): pass
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("127.0.0.1", int(sys.argv[1])), H) as s:
    s.serve_forever()
PY
