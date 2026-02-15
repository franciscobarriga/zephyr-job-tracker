#!/usr/bin/env python3
"""
Start the Zephyr application
"""

import uvicorn
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    # Check for required environment variables
    required_vars = ["SUPABASE_URL", "SUPABASE_ANON_KEY"]
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print(f"❌ Error: Missing required environment variables: {', '.join(missing)}")
        print("   Please set them in your .env file")
        exit(1)
    
    print("🌪️  Starting Zephyr Server")
    print("=" * 60)
    print(f"📍 Local:   http://localhost:8000")
    print(f"📍 Network: http://0.0.0.0:8000")
    print("=" * 60)
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload on code changes
        log_level="info"
    )
