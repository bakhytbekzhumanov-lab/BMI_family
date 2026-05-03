from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from telegram import Update
from app.core.config import settings
from app.db.base import engine, Base
from app.bot.app import build_application
from app.modules.health.router import router as health_router

_telegram_app = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _telegram_app

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    _telegram_app = build_application()
    await _telegram_app.initialize()

    if settings.telegram_webhook_url:
        await _telegram_app.bot.set_webhook(
            url=f"{settings.telegram_webhook_url}/telegram/webhook",
            allowed_updates=["message", "callback_query"],
        )
        await _telegram_app.start()
    else:
        await _telegram_app.updater.start_polling()
        await _telegram_app.start()

    yield

    await _telegram_app.stop()
    await _telegram_app.shutdown()
    await engine.dispose()


app = FastAPI(title="Family Ecosystem", lifespan=lifespan)
app.include_router(health_router)


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request) -> Response:
    data = await request.json()
    update = Update.de_json(data, _telegram_app.bot)
    await _telegram_app.process_update(update)
    return Response(status_code=200)


@app.get("/ping")
async def ping():
    return {"status": "ok"}
