# GPTokens

`GPTokens` est un indicateur Linux qui affiche un etat local de consommation ChatGPT dans la zone de notification.

Le projet repose sur une petite extension Chromium/Brave et un bridge Python en `native messaging`. L'extension observe certaines requetes ChatGPT dans le navigateur, calcule un etat local, puis l'envoie a un indicateur GTK qui lit `~/.config/gptokens/usage_state.json`.

## Ce que fait le projet

- affiche un resume de quota dans un indicateur Linux
- conserve les donnees localement sur la machine
- evite de rejouer des cookies ou d'appeler des endpoints externes hors navigateur
- fonctionne avec Brave, Chrome et Chromium via `native messaging`

## Architecture

Le flux est le suivant :

1. l'extension navigateur observe les requetes `chatgpt.com/backend-api/.../conversation`
2. elle calcule un etat local a partir des informations disponibles
3. le native host Python ecrit cet etat dans `~/.config/gptokens/usage_state.json`
4. l'indicateur GTK lit ce fichier periodiquement et met a jour son affichage

## Pre-requis

### Linux

Le projet cible un environnement Linux avec GTK 3 et AppIndicator.

### Paquets systeme

Le code Python n'a pas de dependances `pip` obligatoires pour l'indicateur, mais il faut les bindings GTK/AppIndicator systeme. Par exemple selon la distribution :

```bash
python3-gi
libayatana-appindicator3
```

## Installation

### 1. Cloner le depot

```bash
git clone <URL_DU_DEPOT>
cd GPTokens
```

### 2. Lancer l'indicateur

```bash
python3 chatgpt_indicator.py
```

### 3. Charger l'extension compagnon

Dans Brave, Chrome ou Chromium :

1. ouvrir la page des extensions
2. activer le mode developpeur
3. cliquer sur `Load unpacked`
4. selectionner le dossier `browser_extension/`

### 4. Installer le native host

Recuperer l'identifiant de l'extension depuis la page des extensions, puis lancer :

```bash
python3 install_native_host.py brave <EXTENSION_ID>
```

Navigateurs supportes par le script :

- `brave`
- `brave-beta`
- `chrome`
- `chromium`

### 5. Utilisation

- ouvrir `chatgpt.com` dans le navigateur configure
- envoyer quelques messages
- laisser l'extension synchroniser l'etat local
- verifier que l'indicateur affiche le pourcentage restant

## Arborescence

- `chatgpt_indicator.py` : indicateur GTK/AppIndicator
- `gptokens_native_host.py` : bridge Python pour `native messaging`
- `install_native_host.py` : installation du manifeste du native host
- `browser_extension/` : extension Chromium/Brave

## Limitations

- le suivi est purement local a la machine et au profil navigateur equipes de l'extension
- les usages faits sur mobile, sur une autre machine ou dans un autre navigateur ne seront pas visibles
- les regles de quota dans `browser_extension/quota.json` restent des estimations locales
- ce projet n'est pas un outil officiel OpenAI

## Confidentialite

Le projet est pense pour fonctionner localement :

- l'etat est stocke dans `~/.config/gptokens/usage_state.json`
- le suivi depend du navigateur et du profil utilises
- aucune instruction du README n'exige l'export de cookies ou l'utilisation d'un service tiers

## Licence

Ajouter ici la licence choisie pour la publication GitHub.
