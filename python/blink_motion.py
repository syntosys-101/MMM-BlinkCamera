#!/usr/bin/env python3
"""
Blink Motion Detection for MMM-BlinkCamera
Checks for new motion videos and saves them to files
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
    except ImportError:
        print(json.dumps({"success": False, "has_motion": False}))
        return

    script_dir = Path(__file__).parent
    config_file = script_dir / "config.json"
    creds_file = script_dir / "credentials.json"
    state_file = script_dir / ".motion_state"
    
    images_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else script_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    if not config_file.exists() or not creds_file.exists():
        print(json.dumps({"success": False, "has_motion": False}))
        return

    config = json.loads(config_file.read_text())
    creds = json.loads(creds_file.read_text())

    if creds.get("awaiting_2fa") or not creds.get("token") or not creds.get("account_id"):
        print(json.dumps({"success": False, "has_motion": False}))
        return

    # Load last motion state
    last_motion = {}
    if state_file.exists():
        try:
            last_motion = json.loads(state_file.read_text())
        except:
            pass

    async with ClientSession() as session:
        blink = Blink(session=session)
        
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
            # Use saved credentials, don't re-login
            await blink.setup_post_verify()
            await blink.refresh()
            
            new_motion_camera = None
            
            for name, camera in blink.cameras.items():
                if camera.motion_detected:
                    last_seen = last_motion.get(name, "")
                    clip_url = getattr(camera, "clip", None)
                    
                    if clip_url and clip_url != last_seen:
                        try:
                            full_url = f"https://{blink.auth.host}{clip_url}" if not clip_url.startswith("http") else clip_url
                            
                            async with session.get(full_url, headers={"token-auth": blink.auth.token}) as resp:
                                if resp.status == 200:
                                    video_data = await resp.read()
                                    video_path = images_dir / f"{name}_motion.mp4"
                                    video_path.write_bytes(video_data)
                                    
                                    new_motion_camera = name
                                    last_motion[name] = clip_url
                        except:
                            pass
            
            state_file.write_text(json.dumps(last_motion))
            
            if new_motion_camera:
                print(json.dumps({"success": True, "has_motion": True, "camera": new_motion_camera}))
            else:
                print(json.dumps({"success": True, "has_motion": False}))

        except Exception as e:
            print(json.dumps({"success": False, "has_motion": False, "error": str(e)}))

if __name__ == "__main__":
    asyncio.run(main())
