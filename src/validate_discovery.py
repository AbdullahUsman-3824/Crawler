from src.video_validator import validate_discovered_videos

if __name__ == "__main__":
    videos = validate_discovered_videos(probe_comments=False)

    print(f"\nMetadata validation completed " f"for {len(videos)} videos.")
