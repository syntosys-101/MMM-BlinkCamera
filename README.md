# MMM-BlinkCamera

A MagicMirror² module for displaying Blink security camera snapshots, motion videos, and doorbell alerts.

![MagicMirror²](https://img.shields.io/badge/MagicMirror²-Module-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.9+-yellow)

## Features

- 📷 **Live camera thumbnails** - Auto-refreshing snapshots from all your cameras
- 🎬 **Motion video playback** - Automatically plays motion clips when detected
- 🔔 **Doorbell alerts** - Fullscreen popup with sound when doorbell is pressed
- 🔄 **Display modes** - Carousel (rotate) or grid (all at once)
- 🔐 **Full 2FA support** - Interactive setup handles two-factor authentication
- 🔋 **Status indicators** - Battery level, armed status, motion alerts
- 🔄 **Auto token refresh** - Stays connected without manual re-auth

## Screenshots

| Carousel Mode | Grid Mode | Doorbell Alert |
|---------------|-----------|----------------|
| Single camera rotating | All cameras at once | Fullscreen visitor popup |

## Requirements

- MagicMirror² 2.0+
- Python 3.9+
- Blink account with cameras
- Audio output (for doorbell sound)

## Installation

### 1. Clone the module

```bash
cd ~/MagicMirror/modules
git clone https://github.com/YOUR-USERNAME/MMM-BlinkCamera.git
cd MMM-BlinkCamera
```

### 2. Install dependencies

```bash
chmod +x install.sh python/*.py
./install.sh
```

Or manually:
```bash
pip3 install blinkpy aiohttp aiofiles
```

### 3. Authenticate with Blink (Required)

```bash
python3 python/setup_auth.py
```

This interactive script will:
1. Ask for your Blink email and password
2. Trigger a 2FA code to your phone/email
3. Verify the PIN and save credentials

### 4. Configure MagicMirror

Add to `~/MagicMirror/config/config.js`:

```javascript
{
    module: "MMM-BlinkCamera",
    position: "middle_center",
    config: {
        email: "your-blink-email@example.com",
        password: "your-blink-password"
    }
}
```

### 5. Restart MagicMirror

```bash
pm2 restart MagicMirror
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `email` | *required* | Blink account email |
| `password` | *required* | Blink account password |
| `updateInterval` | `300000` | Thumbnail refresh interval (ms) |
| `motionCheckInterval` | `30000` | Motion check interval (ms) |
| `showCameraName` | `true` | Show camera name overlay |
| `showLastUpdate` | `true` | Show last update timestamp |
| `showMotionVideos` | `true` | Auto-play motion clips |
| `maxWidth` | `"400px"` | Maximum camera display width |
| `cameras` | `[]` | Filter to specific cameras (empty = all) |
| `displayMode` | `"carousel"` | `"carousel"` or `"grid"` |
| `carouselInterval` | `10000` | Time between camera rotation (ms) |
| `doorbellMonitor` | `true` | Enable doorbell press detection |
| `doorbellSound` | `"doorbell.mp3"` | Custom sound file in sounds/ |
| `doorbellDuration` | `15000` | How long to show doorbell alert (ms) |
| `doorbellVolume` | `0.8` | Sound volume (0.0 - 1.0) |

## Example Configurations

### Basic - Single Camera View
```javascript
{
    module: "MMM-BlinkCamera",
    position: "top_right",
    config: {
        email: "you@email.com",
        password: "password"
    }
}
```

### Grid View - Multiple Cameras
```javascript
{
    module: "MMM-BlinkCamera",
    position: "bottom_right",
    config: {
        email: "you@email.com",
        password: "password",
        displayMode: "grid",
        maxWidth: "180px",
        cameras: ["Front Door", "Backyard", "Garage"]
    }
}
```

### Security Dashboard - Fast Refresh
```javascript
{
    module: "MMM-BlinkCamera",
    position: "middle_center",
    config: {
        email: "you@email.com",
        password: "password",
        updateInterval: 60000,      // Refresh every minute
        displayMode: "grid",
        maxWidth: "300px"
    }
}
```

### Doorbell Focus - Custom Sound
```javascript
{
    module: "MMM-BlinkCamera",
    position: "top_left",
    config: {
        email: "you@email.com",
        password: "password",
        cameras: ["Doorbell"],
        doorbellMonitor: true,
        doorbellSound: "chime.mp3",
        doorbellDuration: 20000,
        doorbellVolume: 1.0
    }
}
```

## Doorbell Alerts

When someone presses your Blink doorbell:

1. 🔔 **Sound plays** - Custom MP3 or generated ding-dong tone
2. 📸 **Fresh snapshot** - Captures new image immediately
3. 🚨 **Fullscreen alert** - Orange flashing popup with visitor image
4. ⏱️ **Auto-dismiss** - Returns to normal after configured duration

### Custom Doorbell Sound

Place any MP3 file in the `sounds/` folder:

```bash
cp ~/Downloads/my-chime.mp3 ~/MagicMirror/modules/MMM-BlinkCamera/sounds/
```

Then configure:
```javascript
doorbellSound: "my-chime.mp3"
```

If no custom sound exists, the module generates a pleasant two-tone ding-dong using the Web Audio API.

## Motion Detection

The module monitors all cameras for motion events:

- **Motion indicator** - Pulsing 🏃 icon on camera overlay
- **Video playback** - Automatically plays motion clips (if `showMotionVideos: true`)
- **Doorbell integration** - Doorbell presses trigger as motion events

## Notifications

### Incoming (from other modules)

| Notification | Payload | Description |
|--------------|---------|-------------|
| `BLINK_REFRESH` | none | Force refresh all cameras |

### Outgoing (to other modules)

| Notification | Payload | Description |
|--------------|---------|-------------|
| `DOORBELL` | `{camera, time}` | Doorbell was pressed |
| `MOTION` | `{camera, time}` | Motion detected |

Example: Trigger other modules when doorbell rings
```javascript
// In another module
notificationReceived: function(notification, payload) {
    if (notification === "DOORBELL") {
        // Turn on lights, send notification, etc.
    }
}
```

## Troubleshooting

### "2FA Required" message

Run the interactive setup:
```bash
cd ~/MagicMirror/modules/MMM-BlinkCamera
python3 python/setup_auth.py
```

### "Python dependencies missing"

```bash
pip3 install blinkpy aiohttp aiofiles --break-system-packages
```

### Cameras not loading

1. Check logs: `pm2 logs MagicMirror`
2. Verify cameras work in Blink mobile app
3. Re-run `python3 python/setup_auth.py`

### Images not showing

Test image download directly:
```bash
cd ~/MagicMirror/modules/MMM-BlinkCamera
python3 python/blink_fetch.py
ls -la images/
```

### Doorbell not detecting

1. Ensure `doorbellMonitor: true` in config
2. Check that doorbell appears in Blink app
3. View logs: `pm2 logs MagicMirror | grep -i doorbell`

### No sound on doorbell

1. Check audio output: `speaker-test -t sine -f 1000 -l 1`
2. Verify volume: `amixer set Master 80%`
3. Try custom MP3 in sounds/ folder

### Authentication expired

Blink tokens expire periodically. Re-authenticate:
```bash
python3 python/setup_auth.py
pm2 restart MagicMirror
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    MagicMirror²                         │
├─────────────────────────────────────────────────────────┤
│  MMM-BlinkCamera.js (Frontend)                          │
│  - Display camera images                                │
│  - Handle doorbell alerts                               │
│  - Play sounds                                          │
├─────────────────────────────────────────────────────────┤
│  node_helper.js (Backend)                               │
│  - Spawn Python processes                               │
│  - Express routes for images                            │
│  - Manage doorbell monitor process                      │
├─────────────────────────────────────────────────────────┤
│  Python Scripts                                         │
│  - blinkpy library for Blink API                        │
│  - blink_fetch.py: Get thumbnails                       │
│  - blink_doorbell.py: Monitor events                    │
│  - setup_auth.py: Handle 2FA                            │
└─────────────────────────────────────────────────────────┘
```

## File Structure

```
MMM-BlinkCamera/
├── MMM-BlinkCamera.js      # Frontend module
├── MMM-BlinkCamera.css     # Styles
├── node_helper.js          # Node.js backend
├── package.json
├── install.sh
├── README.md
├── LICENSE
├── python/
│   ├── blink_auth.py       # Initial authentication
│   ├── blink_fetch.py      # Fetch camera images
│   ├── blink_motion.py     # Check motion status
│   ├── blink_doorbell.py   # Doorbell monitor daemon
│   ├── setup_auth.py       # Interactive 2FA setup
│   ├── config.json         # Credentials (auto-generated)
│   ├── credentials.json    # Auth tokens (auto-generated)
│   └── requirements.txt
├── sounds/                 # Custom doorbell sounds
│   └── README.md
└── images/                 # Camera snapshots (auto-created)
```

## Security Notes

Credentials are stored locally:
- `python/config.json` - Email and password
- `python/credentials.json` - Auth tokens

Secure these files:
```bash
chmod 600 python/config.json python/credentials.json
```

⚠️ **Never commit credentials to git!** The `.gitignore` excludes these files.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## Credits

- [blinkpy](https://github.com/fronzbot/blinkpy) - Python library for Blink API
- [MagicMirror²](https://magicmirror.builders/) - The open source modular smart mirror platform

## License

MIT License - see [LICENSE](LICENSE) file

## Support

- 🐛 [Report bugs](https://github.com/YOUR-USERNAME/MMM-BlinkCamera/issues)
- 💡 [Request features](https://github.com/YOUR-USERNAME/MMM-BlinkCamera/issues)
- 📖 [MagicMirror² Forum](https://forum.magicmirror.builders/)
