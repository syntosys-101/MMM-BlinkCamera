#!/usr/bin/env python3
"""
Blink Authentication for MMM-BlinkCamera
"""

import asyncio
import json
import sys
from pathlib import Path

async def main():
    try:
        from aiohttp import ClientSession
        from blinkpy.blinkpy import Blink
        from blinkpy.auth import Auth
    except ImportError as e:
        print(json.dumps({"success": False, "error": f"Missing: {e}. Run: pip3 install blinkpy aiohttp aiofiles"}))
        return

    script_dir = Path(__file__).parent
    config_file = script_dir / "config.json"
    creds_file = script_dir / "credentials.json"

    if not config_file.exists():
        print(json.dumps({"success": False, "error": "Config not found"}))
        return

    config = json.loads(config_file.read_text())

    async with ClientSession() as session:
        blink = Blink(session=session)
        
        auth = Auth({
            "username": config["email"],
            "password": config["password"],
            "device_id": config.get("device_id", "MagicMirror-BlinkCamera")
        }, no_prompt=True, session=session)
        blink.auth = auth

        try:
            await blink.start()
            
            # Save credentials
            creds = {
                "username": config["email"],
                "token": blink.auth.token,
                "host": blink.auth.host,
                "region_id": blink.auth.region_id,
                "client_id": blink.auth.client_id,
                "account_id": blink.auth.account_id,
                "device_id": config.get("device_id", "MagicMirror-BlinkCamera"),
                "awaiting_2fa": False
            }
            creds_file.write_text(json.dumps(creds, indent=2))
            
            print(json.dumps({"success": True}))

        except Exception as e:
            err = str(e).lower()
            if "2fa" in err or "pin" in err or "verify" in err:
                # Save partial state
                partial = {
                    "username": config["email"],
                    "device_id": config.get("device_id", "MagicMirror-BlinkCamera"),
                    "awaiting_2fa": True
                }
                for attr in ["token", "host", "region_id", "client_id", "account_id"]:
                    if hasattr(blink.auth, attr):
                        val = getattr(blink.auth, attr)
                        if val:
                            partial[attr] = val
                creds_file.write_text(json.dumps(partial, indent=2))
                print(json.dumps({"success": False, "requires_2fa": True}))
            else:
                print(json.dumps({"success": False, "error": str(e)}))

if __name__ == "__main__":
    asyncio.run(main())
