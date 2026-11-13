import os

class Config:
    API_ID = int(os.environ.get("API_ID", 0))
    API_HASH = os.environ.get("API_HASH", "")
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    MONGO_DB_URL = os.environ.get("MONGO_DB_URL", "")
    
    ADMIN = [int(admin_id) for admin_id in os.environ.get("ADMIN", "123456789").split()]
    MAX_CONCURRENT_TRANSMISSIONS = int(os.environ.get("MAX_CONCURRENT_TRANSMISSIONS", 4))
    
    WEB_SUPPORT = True
    LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", 0)) if os.environ.get("LOG_CHANNEL") else None
    BOT_UPTIME = 0
