"""
Ana Giriş Noktası (Entry Point).

Bu dosya uygulamanın yapılandırmasını yapar ve ortamı başlatır.
Mantık kodları ilgili katmanlara (llms, araclar, enviroments) bölünmüştür.
"""

import os
import sys
import asyncio
from dotenv import load_dotenv
import uvicorn

# Windows asyncio workaround for Python 3.8+ (prevents 'Event loop is closed' error)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# .env dosyalarini yukle (yerel override varsa onu en son uygula)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.append(_PROJECT_ROOT)


load_dotenv(dotenv_path=os.path.join(_PROJECT_ROOT, ".env"))
load_dotenv(dotenv_path=os.path.join(_PROJECT_ROOT, ".env.local"), override=True)
load_dotenv(dotenv_path=os.path.join(_PROJECT_ROOT, ".env.model"), override=True)
load_dotenv(dotenv_path=os.path.join(_PROJECT_ROOT, ".env.secrets"), override=True)

from MarketingApp.llms import BaseModel
from MarketingApp.llms.runtime_config import get_base_model_name, get_model_api_key
from MarketingApp.araclar import BASE_ARACLAR
from MarketingApp.enviroments.telegram import init_bot_env, run_telegram_bot
from MarketingApp.enviroments.heartbeat import heartbeat_loop
from MarketingApp.enviroments.discord_bot import run_discord_bot, init_discord_env

try:
    from MarketingApp.panel.api import app as panel_app, set_base_model
    _PANEL_IMPORT_ERROR = None
except Exception as panel_import_error:
    panel_app = None
    set_base_model = None
    _PANEL_IMPORT_ERROR = panel_import_error

async def _run_panel_server():
    """FastAPI panelini ana uygulamayla aynı process'te çalıştırır."""
    if panel_app is None:
        raise RuntimeError(f"Panel uygulamasi yuklenemedi: {_PANEL_IMPORT_ERROR}")

    host = os.getenv("PANEL_HOST", "127.0.0.1")
    port = int(os.getenv("PANEL_PORT", "8001"))
    config = uvicorn.Config(panel_app, host=host, port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    print("🚀 Mimar başlatılıyor...")

    # API anahtarlarını .env'den oku
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
    MODEL_API_KEY = get_model_api_key()
    MODEL_NAME = get_base_model_name()

    if not TELEGRAM_TOKEN:
        raise ValueError("❌ TELEGRAM_TOKEN .env dosyasında bulunamadı!")
    if not MODEL_API_KEY:
        raise ValueError("❌ LLM API anahtarı bulunamadı!")

    # 1. Orkestratör modeli oluştur
    base_model = BaseModel(api_key=MODEL_API_KEY, model=MODEL_NAME)
    
    # Panel yüklendiyse modeli bağla
    if set_base_model:
        set_base_model(base_model)
        base_model.log_message("sistem", "Mimar backend API ve Bot başlatılıyor...")
    else:
        print(f"ℹ️ Panel API yüklenemedi, panel devre dışı: {_PANEL_IMPORT_ERROR}")
        base_model.log_message("sistem", "Mimar bot başlatılıyor (panel devre dışı).")

    # 2. BaseModel'in doğrudan kullandığı minimal araç setini hazırla
    base_arac_map = {func.__name__: func for func in BASE_ARACLAR}

    # 3. Telegram ortamına bağımlılıkları enjekte et
    init_bot_env(
        base_model=base_model,
        genel_araclar=BASE_ARACLAR,
        genel_arac_map=base_arac_map
    )

    # 4. Bot, API Sunucusu ve Discord'u aynı anda çalıştır
    if set_base_model and panel_app:
        print("🌐 Panel API Sunucusu aktif ediliyor...")
    else:
        print(f"ℹ️ Panel import edilemediği için devre dışı: {_PANEL_IMPORT_ERROR}")
    
    bot_task = run_telegram_bot(token=TELEGRAM_TOKEN)
    
    # Çekirdek görevler
    tasks = [
        bot_task,
        heartbeat_loop(base_model),
    ]

    if set_base_model and panel_app:
        tasks.append(_run_panel_server())
    
    # Discord opsiyonel — token varsa çalıştır
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    if DISCORD_TOKEN:
        init_discord_env(base_model)
        tasks.append(run_discord_bot(token=DISCORD_TOKEN, base_model=base_model))
        print("🎮 Discord bot aktif edildi.")
    else:
        print("ℹ️ Discord devre dışı (DISCORD_TOKEN .env'de bulunamadı).")
    
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
