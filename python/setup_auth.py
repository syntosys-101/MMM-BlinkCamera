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

        login_success = False
        needs_2fa = False
        
        try:
            await blink.start()
            
            # Check if login actually succeeded
            if blink.auth.token and blink.account_id:
                login_success = True
                print("✓ Logged in!")
            else:
                print("\n✗ Login completed but missing auth data")
                check = input("Did you receive a 2FA code? [y/N]: ").strip().lower()
                if check == "y":
                    needs_2fa = True
                else:
                    print("Login failed. Please check your credentials.")
                    sys.exit(1)
            
        except Exception as e:
            err_str = str(e).lower()
            err_type = type(e).__name__
            
            print(f"\nLogin exception: {e}")
            
            if any(x in err_str for x in ["2fa", "pin", "verify", "key", "email", "code"]) or \
               any(x in err_type.lower() for x in ["2fa", "twofactor"]):
                needs_2fa = True
            else:
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
                await blink.send_2fa_code(pin)
                await blink.setup_post_verify()
                
                # Verify it worked
                if blink.auth.token and blink.account_id:
                    login_success = True
                    print("✓ Verified!")
                else:
                    print("✗ Verification seemed to work but auth data is missing")
                    sys.exit(1)
                    
            except Exception as e2:
                print(f"✗ Verification failed: {e2}")
                sys.exit(1)

        if not login_success:
            print("✗ Login was not successful")
            sys.exit(1)

        # Save full credentials with all auth data
        creds = {
            "username": email,
            "device_id": "MagicMirror-BlinkCamera",
            "awaiting_2fa": False,
            "token": blink.auth.token,
            "host": blink.auth.host,
            "region_id": blink.auth.region_id,
            "client_id": blink.auth.client_id,
            "account_id": blink.auth.account_id,
        }
        
        # Add optional attributes if they exist
        for attr in ["user_id", "refresh_token", "expires_in"]:
            if hasattr(blink.auth, attr):
                val = getattr(blink.auth, attr)
                if val is not None:
                    creds[attr] = val
        
        # Also save URLs base
        if hasattr(blink, 'urls') and blink.urls:
            if hasattr(blink.urls, 'base_url'):
                creds["base_url"] = blink.urls.base_url
        
        creds_file.write_text(json.dumps(creds, indent=2))
        print("✓ Saved authentication")
        
        print("\nDEBUG: Saved credentials contain:")
        for k, v in creds.items():
            if k in ["token", "refresh_token", "password"]:
                print(f"  {k}: {'[SAVED]' if v else 'None'}")
            else:
                print(f"  {k}: {v}")

        # List cameras
        try:
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
        except Exception as e:
            print(f"\nWarning: Could not list cameras: {e}")
            print("But authentication is saved. Try restarting MagicMirror.")

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
