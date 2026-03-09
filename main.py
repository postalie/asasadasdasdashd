import asyncio
import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, Security
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from config import (
    API_ID, API_HASH, BOT_TOKEN, API_KEY,
    USER_PHONE, USER_PASSWORD
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Telegram Complaint Server")

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

client = TelegramClient('session', API_ID, API_HASH)
bot_entity = None


class ComplaintRequest(BaseModel):
    target_bot: str  # @username бота для жалобы
    reason: str


class ComplaintResponse(BaseModel):
    success: bool
    message: str


async def init_telegram():
    """Инициализация Telegram клиента"""
    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            logger.info("Требуется авторизация...")
            await client.send_code_request(USER_PHONE)
            # Код нужно ввести вручную при первом запуске
            # или создать сессию заранее
        
        await client.start(bot_token=BOT_TOKEN)
        
        global bot_entity
        bot_entity = await client.get_entity("@reportsillegalbot")
        logger.info("✅ Telegram инициализирован")
        
    except Exception as e:
        logger.error(f"Ошибка инициализации: {e}")
        raise


async def check_bot_status() -> bool:
    """Проверка, отвечает ли @reportsillegalbot"""
    try:
        await client.send_message(bot_entity, "/start")
        await asyncio.sleep(2)
        
        messages = await client.get_messages(bot_entity, limit=5)
        return len(messages) > 0
    except Exception as e:
        logger.error(f"Ошибка проверки бота: {e}")
        return False


async def send_complaint(target_bot: str, reason: str) -> bool:
    """Отправка жалобы через @reportsillegalbot"""
    try:
        # Команда /complain
        await client.send_message(bot_entity, "/complain")
        await asyncio.sleep(2)
        
        # Юзернейм бота
        await client.send_message(bot_entity, target_bot)
        await asyncio.sleep(2)
        
        # Причина
        await client.send_message(bot_entity, reason)
        await asyncio.sleep(3)
        
        # Чтение ответа
        messages = await client.get_messages(bot_entity, limit=3)
        if messages:
            response_text = messages[0].text
            logger.info(f"Ответ бота: {response_text}")
            
            if "Your complaint against" in response_text and "has been submitted" in response_text:
                return True
        return False
        
    except Exception as e:
        logger.error(f"Ошибка отправки жалобы: {e}")
        return False


@app.on_event("startup")
async def startup_event():
    await init_telegram()


@app.on_event("shutdown")
async def shutdown_event():
    await client.disconnect()


@app.get("/health")
async def health_check():
    """Проверка сервера"""
    return {"status": "ok"}


@app.post("/api/check", response_model=ComplaintResponse)
async def check_bot(api_key: str = Security(API_KEY_HEADER)):
    """Проверка работоспособности бота"""
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Неверный API ключ")
    
    if await check_bot_status():
        return ComplaintResponse(success=True, message="Бот работает")
    else:
        raise HTTPException(status_code=500, detail="Бот не отвечает")


@app.post("/api/complaint", response_model=ComplaintResponse)
async def submit_complaint(
    complaint: ComplaintRequest,
    api_key: str = Security(API_KEY_HEADER)
):
    """Отправка жалобы"""
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Неверный API ключ")
    
    # Валидация target_bot
    target = complaint.target_bot
    if not target.startswith("@"):
        target = "@" + target
    
    success = await send_complaint(target, complaint.reason)
    
    if success:
        return ComplaintResponse(
            success=True,
            message="Жалоба успешно отправлена"
        )
    else:
        raise HTTPException(status_code=500, detail="Ошибка отправки жалобы")


if __name__ == "__main__":
    import uvicorn
    from config import HOST, PORT
    
    # SSL сертификаты
    import os
    SSL_CERT = f"/etc/letsencrypt/live/reps.mooo.com/fullchain.pem"
    SSL_KEY = f"/etc/letsencrypt/live/reps.mooo.com/privkey.pem"
    
    if os.path.exists(SSL_CERT) and os.path.exists(SSL_KEY):
        print("🔒 HTTPS включён")
        uvicorn.run(app, host=HOST, port=PORT, ssl_certfile=SSL_CERT, ssl_keyfile=SSL_KEY)
    else:
        print("⚠️  HTTPS не найден, запуск в HTTP режиме")
        uvicorn.run(app, host=HOST, port=PORT)
