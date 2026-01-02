# MMM-BlinkCamera

A MagicMirror² module for displaying Blink security camera snapshots and motion videos.

## Features

- 📷 Live camera thumbnails
- 🎬 Motion video playback
- 🔄 Carousel or grid display modes
- 🔐 Full 2FA authentication support
- 🔋 Battery status display
- 🚨 Armed/motion status indicators

## Requirements

- MagicMirror² (2.0+)
- Python 3.9+
- Blink account with cameras

## Installation

### 1. Clone the module

```bash
cd ~/MagicMirror/modules
git clone https://github.com/YOUR-USERNAME/MMM-BlinkCamera.git
cd MMM-BlinkCamera
```

> **Note:** Replace `YOUR-USERNAME` with your GitHub username after you create the repository.

### 2. Install dependencies

```bash
chmod +x install.sh
./install.sh
```

Or manually:
```bash
pip3 install blinkpy aiohttp aiofiles
```

### 3. Authenticate with Blink

**This step is required for 2FA:**

```bash
python3 python/setup_auth.py
```

Follow the prompts to enter your Blink credentials and 2FA PIN.

### 4. Configure MagicMirror

Add to `config/config.js`:

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

## Configuration

| Option | Default | Description |
|--------|---------|-------------|
| `email` | *required* | Blink account email |
| `password` | *required* | Blink account password |
| `updateInterval` | `300000` | Snapshot refresh (ms) |
| `motionCheckInterval` | `30000` | Motion check interval (ms) |
| `showCameraName` | `true` | Show camera name overlay |
| `showLastUpdate` | `true` | Show update timestamp |
| `showMotionVideos` | `true` | Auto-play motion clips |
| `maxWidth` | `"400px"` | Maximum display width |
| `cameras` | `[]` | Specific cameras (empty = all) |
| `displayMode` | `"carousel"` | `carousel` or `grid` |
| `carouselInterval` | `10000` | Carousel rotation (ms) |

## Example Configs

### Grid view with specific cameras

```javascript
{
    module: "MMM-BlinkCamera",
    position: "bottom_right",
    config: {
        email: "you@email.com",
        password: "password",
        displayMode: "grid",
        maxWidth: "180px",
        cameras: ["Front Door", "Backyard"]
    }
}
```

### Fast refresh, no motion videos

```javascript
{
    module: "MMM-BlinkCamera",
    position: "top_left",
    config: {
        email: "you@email.com",
        password: "password",
        updateInterval: 60000,
        showMotionVideos: false
    }
}
```

## Troubleshooting

### "2FA Required" message

Run the setup script to complete authentication:
```bash
cd ~/MagicMirror/modules/MMM-BlinkCamera
python3 python/setup_auth.py
```

### "Python dependencies missing"

```bash
pip3 install blinkpy aiohttp aiofiles
```

If that fails:
```bash
pip3 install --user blinkpy aiohttp aiofiles
```

### Cameras not loading

1. Check MagicMirror logs: `pm2 logs MagicMirror`
2. Verify cameras work in Blink app
3. Re-run setup script to refresh authentication

### Authentication expired

Blink tokens can expire. Re-authenticate:
```bash
python3 python/setup_auth.py
```

## How It Works

This module uses a hybrid Python/Node.js architecture:

1. **Frontend** (`MMM-BlinkCamera.js`): Standard MagicMirror module handling display
2. **Backend** (`node_helper.js`): Node.js helper that spawns Python processes
3. **Python scripts**: Use `blinkpy` library to communicate with Blink's API
4. **Express routes**: Serve camera images efficiently via HTTP

The `blinkpy` library is actively maintained and handles Blink's authentication system, including 2FA and token refresh.

## File Structure

```
MMM-BlinkCamera/
├── MMM-BlinkCamera.js     # Main module
├── MMM-BlinkCamera.css    # Styles
├── node_helper.js         # Node backend
├── package.json
├── install.sh
├── python/
│   ├── blink_auth.py      # Authentication
│   ├── blink_fetch.py     # Fetch cameras
│   ├── blink_motion.py    # Motion detection
│   ├── setup_auth.py      # Interactive setup
│   └── requirements.txt
└── images/                # Camera images (auto-created)
```

## Security

Credentials are stored locally in:
- `python/config.json` - Email/password
- `python/credentials.json` - Auth tokens

Set appropriate permissions:
```bash
chmod 600 python/config.json python/credentials.json
```

## License

MIT
