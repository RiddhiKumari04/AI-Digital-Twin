# /tmp/test_connections.py
import os
import asyncio
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import google.generativeai as genai

async def test():
    load_dotenv()
    
    # 1. Test Mongo
    uri = os.getenv("MONGO_URI", "mongodb+srv://twinx:twinx@twinx.0a4mucd.mongodb.net/?appName=TwinX")
    print(f"Testing Mongo with URI: {uri[:30]}...")
    try:
        client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
        await client.admin.command("ping")
        print("✅ MongoDB: Connected")
    except Exception as e:
        print(f"❌ MongoDB: Failed - {e}")

    # 2. Test Gemini
    key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    print(f"Testing Gemini with key: {key[:6]}...{key[-3:] if key else ''}")
    if not key:
        print("❌ Gemini: Key missing")
    else:
        try:
            genai.configure(api_key=key)
            models = list(genai.list_models())
            print(f"✅ Gemini: Connected ({len(models)} models)")
        except Exception as e:
            print(f"❌ Gemini: Failed - {e}")

if __name__ == "__main__":
    asyncio.run(test())
