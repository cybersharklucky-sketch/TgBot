from flask import Flask, request, jsonify
import yt_dlp

app = Flask(__name__)

@app.route("/extract")
def extract():
    url = request.args.get("url")
    if not url:
        return jsonify({"error": "No URL"}), 400

    ydl_opts = {
        "quiet": True,
        "skip_download": True
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    formats = []
    for f in info.get("formats", []):
        if f.get("ext") == "mp4" and f.get("height") in [360, 720]:
            formats.append({
                "quality": f"{f.get('height')}p",
                "url": f.get("url")
            })

    return jsonify({
        "title": info.get("title"),
        "formats": formats
    })

if __name__ == "__main__":
    app.run()
