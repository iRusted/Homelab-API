from fastapi import FastAPI, Header, HTTPException
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import asyncio
import httpx
import os
import dotenv

dotenv.load_dotenv()

app = FastAPI()

API_KEY = os.getenv("API_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")

last_heartbeat = None
offline_alerted = False
TIMEOUT = 90


async def discord_alert(message):
    async with httpx.AsyncClient() as client:
        await client.post(
            DISCORD_WEBHOOK,
            json={"content": message},
            timeout=10
        )


async def watchdog():
    global offline_alerted

    while True:
        await asyncio.sleep(10)

        now = datetime.now(timezone.utc)

        if last_heartbeat is None:
            continue

        elapsed = (now - last_heartbeat).total_seconds()

        if elapsed > TIMEOUT and not offline_alerted:
            offline_alerted = True
            await discord_alert(
                "🔴 **RUSTYSERVER OFFLINE**\n"
                f"No heartbeat received for {int(elapsed)} seconds."
            )

        elif elapsed <= TIMEOUT and offline_alerted:
            offline_alerted = False
            await discord_alert(
                "🟢 **RUSTYSERVER RECOVERED**\n"
                "Heartbeat connection restored."
            )


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(watchdog())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)


@app.post("/api/v1/heartbeat")
async def heartbeat(
    payload: dict,
    authorization: str = Header()
):
    global last_heartbeat

    if not API_KEY or authorization != f"Bearer {API_KEY}":
        raise HTTPException(401, "Unauthorized")

    last_heartbeat = datetime.now(timezone.utc)

    print("Heartbeat:", payload)

    return {
        "received": True,
        "timestamp": last_heartbeat.isoformat()
    }


@app.get("/test-alert")
async def test_alert():
    await discord_alert("🧪 RustyStatus test alert!")
    return {"sent": True}