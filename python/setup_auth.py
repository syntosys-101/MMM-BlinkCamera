#!/usr/bin/env python3
"""
Interactive Setup for MMM-BlinkCamera
Handles initial authentication including 2FA
"""

import asyncio
import json
import sys
from pathlib import Path
from getpass import getpass

async def main():
    print("\n" + "=" * 50)
    print("  MMM-BlinkCamera Setup")
    print("=" * 50 + "\n")

    try:
        from aiohttp import ClientSession
        from blinkpy.blinkpy import Blink
        from blinkpy.auth import Auth
    except ImportError:
        print("ERROR: Missing dependencies!")
        print("Run: pip3 install blinkpy aiohttp aiofiles")
        sys.exit(1)

    script_dir = Path(__file__).parent
    config_file = script_dir / "config.json"
    creds_file = script_dir / "credentials.json"

    # Get credentials
    email = None
    password = None

    if config_file.exists():
        try:
            cfg = json.loads(config_file.read_text())
            email = cfg.get("email")
            if email:
                print(f"Found existing config for: {email}")
                use = input("Use these credentials? [Y/n]: ").strip().lower()
                if use == "n":
                    email = None
                else:
                    password = cfg.get("password")
        except:
            pass

    if not email:
        email = input("Blink email: ").strip()
        password = getpass("Blink password: ")
        
        config_file.write_text(json.dumps({
            "email": email,
            "password": password,
            "device_id": "MagicMirror-BlinkCamera"
        }, indent=2))
        print("✓ Saved credentials")

    print("\nConnecting to Blink...")

    async with ClientSession() as session:
        blink = Blink(session=session)
        
        auth = Auth({
            "username": email,
            "password": password,
            "device_id": "MagicMirror-BlinkCamera"
        }, no_prompt=True, session=session)
        blink.auth = auth

        needs_2fa = False
        
        try:
            await blink.start()
            print("✓ Logged in!")
            
        except Exception as e:
            err_str = str(e).lower()
            err_type = type(e).__name__
            
            print(f"\nDEBUG: Exception type: {err_type}")
            print(f"DEBUG: Exception message: {e}")
            
            # Check for 2FA requirement
            if any(x in err_str for x in ["2fa", "pin", "verify", "key", "email", "code"]) or \
               any(x in err_type.lower() for x in ["2fa", "twofactor"]):
                needs_2fa = True
            else:
                print(f"\n✗ Login error: {e}")
                check = input("\nDid you receive a 2FA code on your phone/email? [y/N]: ").strip().lower()
                if check == "y":
                    needs_2fa = True
                else:
                    print("Login failed. Please check your credentials.")
                    sys.exit(1)

        if needs_2fa:
            print("\n" + "-" * 40)
            print("  Two-Factor Authentication")
            print("-" * 40)
            print("\nEnter the verification code sent to your phone/email.")
            
            pin = input("\nEnter PIN: ").strip()
            
            if not pin:
                print("Cancelled.")
                sys.exit(1)
            
            print("Verifying...")
            
            try:
                # Try different methods depending on blinkpy version
                verified = False
                
                # Method 1: Try blink.auth.send_auth_key (older versions)
                if hasattr(blink.auth, 'send_auth_key'):
                    await blink.auth.send_auth_key(blink, pin)
                    verified = True
                
                # Method 2: Try blinkpy.helpers.util (some versions)
                if not verified:
                    try:
                        from blinkpy.helpers.util import send_auth_key
                        await send_auth_key(blink, pin)
                        verified = True
                    except ImportError:
                        pass
                
                # Method 3: Try validate_login + setup_post_verify
                if not verified:
                    if hasattr(blink.auth, 'validate_login'):
                        await blink.auth.validate_login(blink, pin)
                        verified = True
                
                # Method 4: Direct API approach for newer versions
                if not verified:
                    if hasattr(blink.auth, 'login_handler'):
                        await blink.auth.login_handler.send_auth_key(blink, pin)
                        verified = True

                # Method 5: Check for async_send_auth_key
                if not verified:
                    if hasattr(blink.auth, 'async_send_auth_key'):
                        await blink.auth.async_send_auth_key(blink, pin)
                        verified = True
                
                # Method 6: Try setting key directly and completing setup
                if not verified:
                    blink.key_required = False
                    blink.auth.data["2fa_token"] = pin
                    await blink.setup_login_ids()
                    await blink.setup_urls()
                    verified = True

                # Complete setup
                if hasattr(blink, 'setup_post_verify'):
                    await blink.setup_post_verify()
                
                print("✓ Verified!")
                
            except Exception as e2:
                print(f"✗ Verification failed: {e2}")
                print("\nDEBUG: Available auth methods:")
                print([m for m in dir(blink.auth) if not m.startswith('_')])
                print("\nDEBUG: Available blink methods:")
                print([m for m in dir(blink) if not m.startswith('_')])
                sys.exit(1)

        # Save credentials
        creds = {
            "username": email,
            "token": blink.auth.token,
            "host": blink.auth.host,
            "region_id": blink.auth.region_id,
            "client_id": blink.auth.client_id,
            "account_id": blink.auth.account_id,
            "device_id": "MagicMirror-BlinkCamera",
            "awaiting_2fa": False
        }
        creds_file.write_text(json.dumps(creds, indent=2))
        print("✓ Saved authentication")

        # List cameras
        await blink.refresh()
        
        print("\n" + "-" * 40)
        print("  Your Cameras")
        print("-" * 40)
        
        if blink.cameras:
            for name, cam in blink.cameras.items():
                status = "Armed" if cam.arm else "Disarmed"
                print(f"  • {name} ({status})")
        else:
            print("  No cameras found")

        print("\n" + "=" * 50)
        print("  Setup Complete!")
        print("=" * 50)
        print("\nAdd to your MagicMirror config/config.js:\n")
        print(f'''{{
    module: "MMM-BlinkCamera",
    position: "middle_center",
    config: {{
        email: "{email}",
        password: "YOUR_PASSWORD"
    }}
}}''')
        print()

if __name__ == "__main__":
    asyncio.run(main())
