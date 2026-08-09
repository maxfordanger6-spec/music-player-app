from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import yt_dlp, os, uuid, re, logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Music Download API")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

DOWNLOADS_DIR = Path("/tmp/music_downloads")
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)

class DownloadRequest(BaseModel):
    url: str

def sanitize_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', '', name).strip()[:100]

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.post("/api/download")
async def download_audio(req: DownloadRequest):
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL requise")
    if not any(d in url for d in ['youtube.com', 'youtu.be', 'music.youtube.com']):
        raise HTTPException(status_code=400, detail="Lien YouTube uniquement")
    
    download_id = str(uuid.uuid4())[:8]
    output_template = str(DOWNLOADS_DIR / f"{download_id}.%(ext)s")
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        'outtmpl': output_template,
        'quiet': True, 'no_warnings': True, 'extract_flat': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            safe_title = sanitize_filename(info.get('title', 'Unknown'))
        
        mp3_path = DOWNLOADS_DIR / f"{download_id}.mp3"
        if not mp3_path.exists():
            raise HTTPException(status_code=500, detail="Échec conversion MP3")
        
        filename = f"{safe_title}.mp3"
        return FileResponse(path=str(mp3_path), media_type='audio/mpeg', filename=filename,
                          headers={'Content-Disposition': f'attachment; filename="{filename}"'})
    except yt_dlp.utils.DownloadError as e:
        raise HTTPException(status_code=400, detail=f"Erreur: {str(e)[:200]}")
    finally:
        try:
            for f in sorted(DOWNLOADS_DIR.glob("*.mp3"), key=os.path.getmtime, reverse=True)[10:]:
                f.unlink()
        except: pass
