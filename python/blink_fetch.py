#!/usr/bin/env python3
"""
Blink Camera Fetch for MMM-BlinkCamera
Fetches camera data and saves thumbnails to files using saved credentials
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

async def main():
    try:
        from aiohttp import ClientSession
        from blinkpy.blinkpy import Blink
        from blinkpy.auth import Auth
    except ImportError as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return

    script_dir = Path(__file__).parent
    config_file = script_dir / "config.json"
    creds_file = script_dir / "credentials.json"
    
    # Get images directory from args or use default
    images_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else script_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    if not config_file.exists() or not creds_file.exists():
        print(json.dumps({"success": False, "requires_reauth": True, "error": "Missing config or credentials"}))
        return

    config = json.loads(config_file.read_text())
    creds = json.loads(creds_file.read_text())

    if creds.get("awaiting_2fa"):
        print(json.dumps({"success": False, "requires_2fa": True}))
        return

    if not creds.get("token") or not creds.get("account_id"):
        print(json.dumps({"success": False, "requires_reauth": True, "error": "Incomplete credentials"}))
        return

    async with ClientSession() as session:
        blink = Blink(session=session)
        
        # Create auth with saved credentials including token
        auth_data = {
            "username": creds.get("username", config.get("email")),
            "password": config.get("password"),
            "device_id": creds.get("device_id", "MagicMirror-BlinkCamera"),
            "token": creds.get("token"),
            "host": creds.get("host"),
            "region_id": creds.get("region_id"),
            "client_id": creds.get("client_id"),
            "account_id": creds.get("account_id"),
            "user_id": creds.get("user_id"),
            "refresh_token": creds.get("refresh_token"),
        }
        
        auth = Auth(auth_data, no_prompt=True, session=session)
        blink.auth = auth

        try:
            # Use start() - it should use the existing token if valid
            await blink.start()
            
            cameras_data = {}
            
            for name, camera in blink.cameras.items():
                cam_info = {
                    "name": name,
                    "armed": camera.arm,
                    "motion": camera.motion_detected,
                    "battery": getattr(camera, "battery", None),
                    "temperature": getattr(camera, "temperature", None),
                    "hasImage": False,
                    "updated": None
                }
                
                # Download and save thumbnail
                try:
                    if hasattr(camera, "thumbnail") and camera.thumbnail:
                        thumb_url = camera.thumbnail
                        if thumb_url:
                            if thumb_url.startswith("http"):
                                full_url = thumb_url
                            else:
                                full_url = f"https://{blink.auth.host}{thumb_url}"
                            
                            headers = {"token-auth": blink.auth.token}
                            async with session.get(full_url, headers=headers) as resp:
                                if resp.status == 200:
                                    image_data = await resp.read()
                                    image_path = images_dir / f"{name}.jpg"
                                    image_path.write_bytes(image_data)
                                    cam_info["hasImage"] = True
                                    cam_info["updated"] = datetime.now().strftime("%H:%M:%S")
                except Exception as img_err:
                    sys.stderr.write(f"Image error for {name}: {img_err}\n")
                
                cameras_data[name] = cam_info
            
            # Update saved credentials with refreshed token
            if blink.auth.token:
                creds["token"] = blink.auth.token
            if hasattr(blink.auth, 'refresh_token') and blink.auth.refresh_token:
                creds["refresh_token"] = blink.auth.refresh_token
            creds_file.write_text(json.dumps(creds, indent=2))
            
            print(json.dumps({"success": True, "cameras": cameras_data}))

        except Exception as e:
            err = str(e).lower()
            sys.stderr.write(f"Fetch error: {e}\n")
            
            # Check if we need re-authentication
            if any(x in err for x in ["token", "auth", "login", "unauthorized", "401", "403", "2fa", "pin"]):
                print(json.dumps({"success": False, "requires_reauth": True, "error": str(e)}))
            else:
                print(json.dumps({"success": False, "error": str(e)}))

if __name__ == "__main__":
    asyncio.run(main())
