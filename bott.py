from flask import Flask, request, jsonify
import yt_dlp

app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({
        "status": "ok",
        "endpoint": "/extract?url=YOUTUBE_URL"
    })

@app.route("/extract")
def extract():
    url = request.args.get("url")

    if not url:
        return jsonify({"error": "No URL provided"}), 400

    if "youtube.com" not in url and "youtu.be" not in url:
        return jsonify({"error": "Invalid YouTube URL"}), 400

    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "no_warnings": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"]
            }
        },
        "http_headers": {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 11; Pixel 5) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Mobile Safari/537.36"
            )
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        formats = []

        for f in info.get("formats", []):
            # Progressive MP4 only (video + audio)
            if (
                f.get("ext") == "mp4"
                and f.get("acodec") != "none"
                and f.get("vcodec") != "none"
                and f.get("height") in [360, 720]
            ):
                formats.append({
                    "quality": f"{f.get('height')}p",
                    "url": f.get("url")
                })

        return jsonify({
            "title": info.get("title"),
            "formats": formats
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run()
