#!/bin/bash
# LeadFinder – Script de lancement automatique

set -e

echo "==============================="
echo "   LeadFinder – Démarrage"
echo "==============================="
echo ""

# 1. Vérifier que Python 3 est installé
if command -v python3 &>/dev/null; then
    PY=python3
    PIP=pip3
elif command -v python &>/dev/null; then
    PY=python
    PIP=pip
else
    echo "ERREUR : Python 3 n'est pas installé sur ce Mac."
    echo ""
    echo "Pour l'installer :"
    echo "  1. Va sur https://www.python.org/downloads/"
    echo "  2. Télécharge la dernière version pour Mac"
    echo "  3. Installe-la, puis relance ce script"
    echo ""
    exit 1
fi

echo "Python trouvé : $($PY --version)"
echo ""

# 2. Vérifier que le fichier .env existe
if [ ! -f .env ]; then
    echo "ERREUR : Le fichier .env est manquant."
    echo ""
    echo "Pour le créer :"
    echo "  1. Copie le fichier .env.example et renomme-le en .env"
    echo "  2. Remplace COLLE_TA_CLE_GOOGLE_ICI par ta vraie clé Google API"
    echo ""
    exit 1
fi

echo "Fichier .env trouvé."
echo ""

# 3. Installer les dépendances
echo "Installation des dépendances (peut prendre 1-2 minutes la première fois)..."
$PIP install -r requirements.txt --quiet
echo "Dépendances OK."
echo ""

# 4. Lancer l'application
PORT=8060
echo "Lancement de LeadFinder sur http://127.0.0.1:$PORT"
echo "Pour arrêter : appuie sur Ctrl+C dans ce terminal"
echo ""

# 5. Ouvrir le navigateur après 2 secondes (en arrière-plan)
(sleep 2 && open "http://127.0.0.1:$PORT") &

# 6. Démarrer le serveur
$PY app.py
