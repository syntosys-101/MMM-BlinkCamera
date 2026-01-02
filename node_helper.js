/* Node Helper for MMM-BlinkCamera
 * 
 * Handles Python backend communication and serves images via Express
 */

const NodeHelper = require("node_helper");
const { spawn } = require("child_process");
const path = require("path");
const fs = require("fs");
const Log = require("logger");

module.exports = NodeHelper.create({
    // Initialize
    start: function() {
        Log.log("MMM-BlinkCamera helper started");
        
        this.config = null;
        this.started = false;
        this.updateTimer = null;
        this.motionTimer = null;
        this.pythonDir = path.join(__dirname, "python");
        this.imagesDir = path.join(__dirname, "images");
        
        // Create images directory
        if (!fs.existsSync(this.imagesDir)) {
            fs.mkdirSync(this.imagesDir, { recursive: true });
        }

        // Set up Express routes
        this.setupRoutes();
    },

    // Set up Express routes for serving images and videos
    setupRoutes: function() {
        const self = this;

        // Route: GET /MMM-BlinkCamera/camera/:name
        this.expressApp.get("/" + this.name + "/camera/:name", function(req, res) {
            const cameraName = decodeURIComponent(req.params.name);
            const imagePath = path.join(self.imagesDir, cameraName + ".jpg");
            
            if (fs.existsSync(imagePath)) {
                res.setHeader("Content-Type", "image/jpeg");
                res.setHeader("Cache-Control", "no-cache, no-store, must-revalidate");
                res.sendFile(imagePath);
            } else {
                res.status(404).send("Image not found");
            }
        });

        // Route: GET /MMM-BlinkCamera/video/:name
        this.expressApp.get("/" + this.name + "/video/:name", function(req, res) {
            const cameraName = decodeURIComponent(req.params.name);
            const videoPath = path.join(self.imagesDir, cameraName + "_motion.mp4");
            
            if (fs.existsSync(videoPath)) {
                res.setHeader("Content-Type", "video/mp4");
                res.setHeader("Cache-Control", "no-cache, no-store, must-revalidate");
                res.sendFile(videoPath);
            } else {
                res.status(404).send("Video not found");
            }
        });

        Log.log("MMM-BlinkCamera: Express routes configured");
    },

    // Handle socket notifications from module
    socketNotificationReceived: function(notification, payload) {
        Log.log("MMM-BlinkCamera helper received: " + notification);

        if (notification === "CONFIG") {
            this.config = payload;
            this.initializeModule();
        } else if (notification === "REFRESH") {
            this.fetchCameras();
        }
    },

    // Initialize the module
    initializeModule: function() {
        const self = this;

        // Save credentials config for Python
        this.saveConfig();

        // Check Python dependencies
        this.checkPython(function(ok) {
            if (!ok) {
                self.sendSocketNotification("ERROR", 
                    "Python dependencies missing. Run: pip3 install blinkpy aiohttp aiofiles");
                return;
            }

            // Check for existing auth
            self.checkAuth(function(hasAuth) {
                if (hasAuth) {
                    self.sendSocketNotification("STATUS", "Loading cameras...");
                    self.fetchCameras();
                    self.startTimers();
                } else {
                    self.sendSocketNotification("STATUS", "Authenticating...");
                    self.authenticate();
                }
            });
        });
    },

    // Save config for Python scripts
    saveConfig: function() {
        const configPath = path.join(this.pythonDir, "config.json");
        const config = {
            email: this.config.email,
            password: this.config.password,
            device_id: "MagicMirror-BlinkCamera"
        };
        fs.writeFileSync(configPath, JSON.stringify(config, null, 2));
    },

    // Check Python dependencies
    checkPython: function(callback) {
        const pythonCmd = spawn("python3", ["-c", "import blinkpy, aiohttp, aiofiles"]);
        
        pythonCmd.on("close", function(code) {
            callback(code === 0);
        });

        pythonCmd.on("error", function() {
            callback(false);
        });
    },

    // Check for existing authentication
    checkAuth: function(callback) {
        const credsPath = path.join(this.pythonDir, "credentials.json");
        
        if (fs.existsSync(credsPath)) {
            try {
                const creds = JSON.parse(fs.readFileSync(credsPath, "utf8"));
                if (creds.token && creds.account_id && !creds.awaiting_2fa) {
                    callback(true);
                    return;
                }
            } catch (e) {
                Log.error("MMM-BlinkCamera: Error reading credentials: " + e.message);
            }
        }
        callback(false);
    },

    // Authenticate with Blink
    authenticate: function() {
        const self = this;
        const scriptPath = path.join(this.pythonDir, "blink_auth.py");

        this.runPython(scriptPath, [], function(result) {
            if (result.success) {
                self.sendSocketNotification("STATUS", "Authenticated!");
                self.fetchCameras();
                self.startTimers();
            } else if (result.requires_2fa) {
                self.sendSocketNotification("2FA_REQUIRED", {});
            } else {
                self.sendSocketNotification("ERROR", result.error || "Authentication failed");
            }
        });
    },

    // Fetch camera data
    fetchCameras: function() {
        const self = this;
        const scriptPath = path.join(this.pythonDir, "blink_fetch.py");

        this.runPython(scriptPath, [this.imagesDir], function(result) {
            if (result.success && result.cameras) {
                self.sendSocketNotification("CAMERAS", {
                    cameras: result.cameras
                });
            } else if (result.requires_reauth) {
                self.authenticate();
            } else if (result.error) {
                Log.error("MMM-BlinkCamera: Fetch error: " + result.error);
                // Don't send error notification on refresh failures, just log
            }
        });
    },

    // Check for motion
    checkMotion: function() {
        const self = this;
        const scriptPath = path.join(this.pythonDir, "blink_motion.py");

        this.runPython(scriptPath, [this.imagesDir], function(result) {
            if (result.has_motion && result.camera) {
                self.sendSocketNotification("MOTION", {
                    camera: result.camera
                });
            }
        });
    },

    // Run a Python script and parse JSON output
    runPython: function(scriptPath, args, callback) {
        const self = this;
        let stdout = "";
        let stderr = "";

        const pythonArgs = [scriptPath].concat(args || []);
        const proc = spawn("python3", pythonArgs, {
            cwd: this.pythonDir
        });

        proc.stdout.on("data", function(data) {
            stdout += data.toString();
        });

        proc.stderr.on("data", function(data) {
            stderr += data.toString();
            // Log errors but filter out info messages
            const msg = data.toString().trim();
            if (msg && !msg.includes("INFO")) {
                Log.warn("MMM-BlinkCamera Python: " + msg);
            }
        });

        proc.on("close", function(code) {
            // Try to parse JSON from stdout
            try {
                // Find the last valid JSON line
                const lines = stdout.trim().split("\n");
                for (let i = lines.length - 1; i >= 0; i--) {
                    try {
                        const result = JSON.parse(lines[i]);
                        callback(result);
                        return;
                    } catch (e) {
                        continue;
                    }
                }
                // No valid JSON found
                callback({ success: false, error: "No valid response" });
            } catch (e) {
                callback({ success: false, error: stderr || "Python script failed" });
            }
        });

        proc.on("error", function(err) {
            callback({ success: false, error: err.message });
        });
    },

    // Start update timers
    startTimers: function() {
        const self = this;

        // Clear existing timers
        if (this.updateTimer) clearInterval(this.updateTimer);
        if (this.motionTimer) clearInterval(this.motionTimer);

        // Camera update timer
        this.updateTimer = setInterval(function() {
            self.fetchCameras();
        }, this.config.updateInterval);

        // Motion check timer
        if (this.config.showMotionVideos) {
            this.motionTimer = setInterval(function() {
                self.checkMotion();
            }, this.config.motionCheckInterval);
        }

        Log.log("MMM-BlinkCamera: Timers started");
    },

    // Stop on shutdown
    stop: function() {
        if (this.updateTimer) clearInterval(this.updateTimer);
        if (this.motionTimer) clearInterval(this.motionTimer);
        Log.log("MMM-BlinkCamera helper stopped");
    }
});
