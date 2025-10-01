#!/bin/bash

# Chemin vers ton projet
PROJECT_PATH="$1"
VENV_PATH="$PROJECT_PATH/venv"
REQUIREMENTS_FILE="$PROJECT_PATH/requirements.txt"

# Vérification que le chemin du projet a été fourni
if [ -z "$PROJECT_PATH" ]; then
    echo "Erreur : Le chemin du projet n'a pas été spécifié."
    echo "Usage : $0 <chemin_du_projet>"
    exit 1
fi

# Vérification si le répertoire du projet existe
if [ ! -d "$PROJECT_PATH" ]; then
    echo "Erreur : Le répertoire du projet '$PROJECT_PATH' n'existe pas."
    exit 1
fi

# Création de l'environnement virtuel si nécessaire
if [ ! -d "$VENV_PATH" ]; then
    echo "Création de l'environnement virtuel..."
    python3 -m venv "$VENV_PATH"
    if [ $? -ne 0 ]; then
        echo "Erreur lors de la création de l'environnement virtuel."
        exit 1
    fi
else
    echo "L'environnement virtuel existe déjà."
fi

# Activation de l'environnement virtuel
echo "Activation de l'environnement virtuel..."
source "$VENV_PATH/bin/activate"

# Vérification si requirements.txt existe
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "Le fichier requirements.txt n'existe pas, création d'un fichier de base."
    echo "influxdb-client" > "$REQUIREMENTS_FILE"
fi

# Installation des dépendances
echo "Installation des dépendances depuis requirements.txt..."
pip install -r "$REQUIREMENTS_FILE"

# Affichage d'un message pour l'utilisateur
echo "L'environnement virtuel est prêt et les dépendances sont installées."
echo "Pour activer l'environnement virtuel à l'avenir, exécutez :"
echo "source $VENV_PATH/bin/activate"
