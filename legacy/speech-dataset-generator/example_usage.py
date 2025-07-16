#!/usr/bin/env python3
"""
Exemple d'utilisation de la classe YoutubeDownloader
"""

from youtube_downloader import YoutubeDownloader


def main():
    """Exemples d'utilisation de la classe YoutubeDownloader"""
    
    print("=== EXEMPLES D'UTILISATION DE YOUTUBEDOWNLOADER ===\n")
    
    # Créer une instance du téléchargeur
    downloader = YoutubeDownloader(output_dir="./data/my_downloads")
    
    # Exemple 1: Télécharger une seule vidéo
    print("1. Téléchargement d'une vidéo unique:")
    video_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # Exemple d'URL
    # result = downloader.download_video(video_url)
    # print(f"Résultat: {result}\n")
    
    # Exemple 2: Télécharger une playlist
    print("2. Téléchargement d'une playlist:")
    playlist_url = "https://www.youtube.com/playlist?list=PLYour_Playlist_ID"  # Remplacer par une vraie playlist
    # result = downloader.download_playlist(playlist_url)
    # print(f"Résultat: {result}\n")
    
    # Exemple 3: Télécharger depuis une liste d'URLs
    print("3. Téléchargement depuis une liste d'URLs:")
    urls_list = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/playlist?list=PLYour_Playlist_ID",
        "https://www.youtube.com/watch?v=Another_Video_ID"
    ]
    # results = downloader.download_from_urls_list(urls_list)
    # print(f"Résultats: {results}\n")
    
    # Exemple 4: Télécharger depuis un fichier d'URLs
    print("4. Téléchargement depuis un fichier d'URLs:")
    # Créer un fichier d'exemple urls.txt
    with open("example_urls.txt", "w") as f:
        f.write("https://www.youtube.com/watch?v=dQw4w9WgXcQ\n")
        f.write("https://www.youtube.com/playlist?list=PLYour_Playlist_ID\n")
    
    # results = downloader.download_from_file("example_urls.txt")
    # print(f"Résultats: {results}\n")
    
    # Exemple 5: Automatisation complète avec pipeline
    print("5. Automatisation complète avec pipeline:")
    # results = downloader.automate_download(
    #     urls_source="example_urls.txt",
    #     run_full_pipeline=True,
    #     hf_repo="votre-username/votre-repo",
    #     min_duration=3,
    #     max_duration=15,
    #     raw_data_dir="./data/wav_files",
    #     chunked_data_dir="./data/chunks"
    # )
    # print(f"Résultats du pipeline: {results}\n")
    
    # Exemple 6: Téléchargement simple avec automatisation partielle
    print("6. Automatisation simple (téléchargement uniquement):")
    # results = downloader.automate_download(
    #     urls_source=["https://www.youtube.com/watch?v=dQw4w9WgXcQ"],
    #     run_full_pipeline=False
    # )
    # print(f"Résultats: {results}\n")
    
    print("Tous les exemples sont commentés. Décommentez ceux que vous voulez tester!")
    print("N'oubliez pas de remplacer les URLs d'exemple par de vraies URLs YouTube.")


if __name__ == "__main__":
    main() 