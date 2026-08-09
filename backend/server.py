from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import yt_dlp
import os
import uuid
import re
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Music Download API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOWNLOADS_DIR = Path("/tmp/music_downloads")
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

class DownloadRequest(BaseModel):
    url: str

def sanitize_filename(name: str) -> str:
    """Remove invalid filename characters."""
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = name.strip()[:100]
    return name

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "music-download-api"}

@app.post("/api/download")
async def download_audio(req: DownloadRequest):
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL requise")
    
    # Basic YouTube URL validation
    if not any(d in url for d in ['youtube.com', 'youtu.be', 'music.youtube.com']):
        raise HTTPException(status_code=400, detail="Lien YouTube uniquement")
    
    download_id = str(uuid.uuid4())[:8]
    output_template = str(DOWNLOADS_DIR / f"{download_id}.%(ext)s")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': output_template,
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
    }
    
    try:
        logger.info(f"Downloading: {url}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            title = info.get('title', 'Unknown')
            safe_title = sanitize_filename(title)
        
        # Find the output MP3 file
        mp3_path = DOWNLOADS_DIR / f"{download_id}.mp3"
        
        if not mp3_path.exists():
            raise HTTPException(status_code=500, detail="Échec de la conversion MP3")
        
        filename = f"{safe_title}.mp3"
        
        logger.info(f"Download complete: {filename}")
        
        return FileResponse(
            path=str(mp3_path),
            media_type='audio/mpeg',
            filename=filename,
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'X-Download-Id': download_id
            }
        )
        
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"yt-dlp error: {e}")
        raise HTTPException(status_code=400, detail=f"Erreur YouTube: {str(e)[:200]}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Erreur serveur: {str(e)[:200]}")
    finally:
        # Cleanup old files (keep last 10)
        try:
            files = sorted(DOWNLOADS_DIR.glob("*.mp3"), key=os.path.getmtime, reverse=True)
            for f in files[10:]:
                f.unlink()
        except:
            pass

@app.get("/api/")
async def root():
    return {"message": "Music Download API — POST /api/download with {\"url\": \"youtube_url\"}"}

# Serve frontend SPA
_STATIC_DIR = Path(__file__).parent / "static"
if _STATIC_DIR.exists():
    from fastapi.staticfiles import StaticFiles
    app.mount("/static", StaticFiles(directory=str(_STATIC_DIR / "static")), name="frontend-static")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        if full_path.startswith("api/"):
            return {"detail": "Not Found"}
        file_path = _STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        index = _STATIC_DIR / "index.html"
        if index.exists():
            return FileResponse(str(index))
        return {"detail": "Not Found"}

# Railway startup
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
