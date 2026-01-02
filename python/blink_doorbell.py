#!/usr/bin/env python3
"""
Blink Doorbell Monitor for MMM-BlinkCamera
Monitors doorbell for button press/motion and outputs events
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
        print(json.dumps({"event": "error", "error": str(e)}))
        sys.stdout.flush()
        return

    script_dir = Path(__file__).parent
    config_file = script_dir / "config.json"
    creds_file = script_dir / "credentials.json"
    images_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else script_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    if not config_file.exists() or not creds_file.exists():
        print(json.dumps({"event": "error", "error": "Missing config or credentials"}))
        sys.stdout.flush()
        return

    config = json.loads(config_file.read_text())
    creds = json.loads(creds_file.read_text())
    
    # Track previous states
    prev_motion = {}
    
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
            await blink.start()
            
            # Send startup event
            print(json.dumps({"event": "started", "cameras": list(blink.cameras.keys())}))
            sys.stdout.flush()
            
            # Find doorbells
            doorbells = {name: cam for name, cam in blink.cameras.items() 
                        if cam.product_type == 'lotus' or 'doorbell' in name.lower()}
            
            if not doorbells:
                print(json.dumps({"event": "warning", "message": "No doorbells found"}))
                sys.stdout.flush()
            
            # Initialize previous motion states
            for name, cam in blink.cameras.items():
                prev_motion[name] = cam.motion_detected
            
            poll_interval = config.get("doorbell_poll_interval", 5)
            
            while True:
                try:
                    # Refresh camera data
                    await blink.refresh()
                    
                    for name, camera in blink.cameras.items():
                        current_motion = camera.motion_detected
                        
                        # Detect motion state change (False -> True)
                        if current_motion and not prev_motion.get(name, False):
                            is_doorbell = name in doorbells
                            event_type = "doorbell" if is_doorbell else "motion"
                            
                            # Snap fresh picture
                            image_path = images_dir / f"{name}.jpg"
                            try:
                                await camera.snap_picture()
                                await asyncio.sleep(2)  # Wait for snap to process
                                await blink.refresh()
                                await camera.image_to_file(str(image_path))
                            except Exception as snap_err:
                                sys.stderr.write(f"Snap error: {snap_err}\n")
                            
                            # Send event
                            event_data = {
                                "event": event_type,
                                "camera": name,
                                "time": datetime.now().strftime("%H:%M:%S"),
                                "hasImage": image_path.exists(),
                            }
                            
                            print(json.dumps(event_data))
                            sys.stdout.flush()
                        
                        prev_motion[name] = current_motion
                    
                    # Update credentials if token refreshed
                    if blink.auth.token and blink.auth.token != creds.get("token"):
                        creds["token"] = blink.auth.token
                        if hasattr(blink.auth, 'refresh_token') and blink.auth.refresh_token:
                            creds["refresh_token"] = blink.auth.refresh_token
                        creds_file.write_text(json.dumps(creds, indent=2))
                    
                    await asyncio.sleep(poll_interval)
                    
                except Exception as poll_err:
                    sys.stderr.write(f"Poll error: {poll_err}\n")
                    await asyncio.sleep(poll_interval)

        except Exception as e:
            print(json.dumps({"event": "error", "error": str(e)}))
            sys.stdout.flush()

if __name__ == "__main__":
    asyncio.run(main())
