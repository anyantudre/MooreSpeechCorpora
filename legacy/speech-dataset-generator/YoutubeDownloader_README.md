# YoutubeDownloader - Documentation

## Vue d'ensemble

La classe `YoutubeDownloader` est une solution complète pour télécharger des playlists et vidéos YouTube avec automatisation du pipeline de traitement audio. Elle encapsule toutes les fonctionnalités des scripts individuels dans une interface orientée objet simple à utiliser.

## Fonctionnalités

- ✅ **Téléchargement de playlists** : Télécharge toutes les vidéos d'une playlist YouTube
- ✅ **Téléchargement de vidéos individuelles** : Télécharge une seule vidéo YouTube
- ✅ **Traitement par lots** : Traite plusieurs URLs (mélange de playlists et vidéos)
- ✅ **Lecture depuis fichier** : Lit les URLs depuis un fichier texte
- ✅ **Pipeline automatisé** : Exécute automatiquement tout le pipeline (MP3→WAV→Chunks→HuggingFace)
- ✅ **Gestion d'erreurs** : Gestion robuste des erreurs avec messages informatifs
- ✅ **Évitement des doublons** : Skip automatique des fichiers déjà téléchargés

## Installation

Assurez-vous d'avoir les dépendances requises :

```bash
pip install pytubefix
pip install -r requirements.txt
```

## Utilisation de base

### 1. Initialisation

```python
from youtube_downloader import YoutubeDownloader

# Initialisation avec répertoire par défaut
downloader = YoutubeDownloader()

# Ou avec un répertoire personnalisé
downloader = YoutubeDownloader(output_dir="./mes_telechargements")
```

### 2. Téléchargement d'une playlist

```python
playlist_url = "https://www.youtube.com/playlist?list=PLxxxxxxxxx"
result = downloader.download_playlist(playlist_url)
print(f"Playlist téléchargée dans: {result}")
```

### 3. Téléchargement d'une vidéo

```python
video_url = "https://www.youtube.com/watch?v=xxxxxxxxx"
result = downloader.download_video(video_url)
print(f"Vidéo téléchargée: {result}")
```

### 4. Téléchargement depuis une liste d'URLs

```python
urls = [
    "https://www.youtube.com/watch?v=xxxxxxxxx",
    "https://www.youtube.com/playlist?list=PLxxxxxxxxx",
    "https://www.youtube.com/watch?v=yyyyyyyyy"
]
results = downloader.download_from_urls_list(urls)
print(f"Fichiers téléchargés: {results}")
```

### 5. Téléchargement depuis un fichier

```python
# Contenu du fichier urls.txt :
# https://www.youtube.com/watch?v=xxxxxxxxx
# https://www.youtube.com/playlist?list=PLxxxxxxxxx

results = downloader.download_from_file("urls.txt")
print(f"Fichiers téléchargés: {results}")
```

## Automatisation avancée

### Téléchargement simple

```python
# Téléchargement uniquement
results = downloader.automate_download(
    urls_source="urls.txt",  # ou une liste d'URLs
    run_full_pipeline=False
)

print(f"Téléchargements: {results['downloaded_paths']}")
if results['error']:
    print(f"Erreur: {results['error']}")
```

### Pipeline complet

```python
# Téléchargement + Pipeline complet (MP3→WAV→Chunks→HuggingFace)
results = downloader.automate_download(
    urls_source="urls.txt",
    run_full_pipeline=True,
    hf_repo="votre-username/votre-repo",
    min_duration=4,
    max_duration=20,
    raw_data_dir="./data/wav_files",
    chunked_data_dir="./data/chunks"
)

print(f"Pipeline terminé: {results['pipeline_completed']}")
print(f"Fichiers traités: {results['downloaded_paths']}")
```

## Méthodes disponibles

### `__init__(output_dir="./data/youtube-mp3-downloads")`
Initialise le téléchargeur avec un répertoire de sortie.

### `download_playlist(playlist_url, custom_output_dir=None)`
Télécharge une playlist complète.
- **Retour**: Chemin du dossier de la playlist ou None si échec

### `download_video(video_url, custom_output_dir=None)`
Télécharge une vidéo individuelle.
- **Retour**: Chemin du fichier téléchargé ou None si échec

### `download_from_urls_list(urls_list)`
Traite une liste d'URLs (mélange playlists/vidéos).
- **Retour**: Liste des chemins des fichiers/dossiers téléchargés

### `download_from_file(urls_file_path)`
Lit et traite les URLs depuis un fichier.
- **Retour**: Liste des chemins des fichiers/dossiers téléchargés

### `automate_download(urls_source, run_full_pipeline=False, **pipeline_kwargs)`
Automatise le processus complet.
- **urls_source**: Chemin vers fichier ou liste d'URLs
- **run_full_pipeline**: Si True, exécute tout le pipeline
- **pipeline_kwargs**: Paramètres du pipeline (hf_repo, durées, etc.)
- **Retour**: Dictionnaire avec résultats et statuts

## Paramètres du pipeline

Quand `run_full_pipeline=True`, vous pouvez spécifier :

- `hf_repo` (requis) : Repository Hugging Face (ex: "username/repo-name")
- `raw_data_dir` : Répertoire pour fichiers WAV (défaut: "./data/raw_wav_audios")
- `chunked_data_dir` : Répertoire pour chunks (défaut: "./data/chunked_wav_audios")
- `min_duration` : Durée minimum en secondes (défaut: 4)
- `max_duration` : Durée maximum en secondes (défaut: 20)

## Gestion des erreurs

La classe gère automatiquement :
- URLs invalides ou inaccessibles
- Fichiers déjà existants (skip automatique)
- Erreurs de téléchargement individuelles
- Problèmes de pipeline

Les erreurs sont affichées avec des messages informatifs et n'interrompent pas le traitement des autres URLs.

## Structure des fichiers de sortie

```
output_dir/
├── playlist_PLxxxxxxxxx/
│   ├── video1.mp3
│   ├── video2.mp3
│   └── ...
├── video_individuelle.mp4
└── autre_video.mp4
```

## Exemples d'utilisation complète

Voir le fichier `example_usage.py` pour des exemples détaillés d'utilisation.

## Dépendances

- `pytubefix` : Pour télécharger depuis YouTube
- Scripts existants dans `helpers/` et `create_dataset/`
- `utils.py` pour la fonction `sanitize_filename`

## Notes importantes

1. **Formats de sortie** : 
   - Playlists → MP3
   - Vidéos individuelles → MP4 (audio seulement)

2. **Noms de fichiers** : Tous les titres sont automatiquement nettoyés pour éviter les caractères problématiques.

3. **Performance** : Le téléchargement est séquentiel pour éviter la surcharge des serveurs YouTube.

4. **Respect des limites** : Utilisez de manière responsable en respectant les conditions d'utilisation de YouTube. 