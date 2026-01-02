/* MagicMirror² Module: MMM-BlinkCamera
 * 
 * Displays Blink camera snapshots and motion videos
 * Uses blinkpy Python library for reliable Blink API access
 * 
 * By: Claude AI Assistant
 * License: MIT
 */

Module.register("MMM-BlinkCamera", {
    // Module defaults
    defaults: {
        email: "",
        password: "",
        updateInterval: 5 * 60 * 1000,      // 5 minutes
        motionCheckInterval: 30 * 1000,      // 30 seconds
        showCameraName: true,
        showLastUpdate: true,
        showMotionVideos: true,
        maxWidth: "400px",
        cameras: [],                         // Empty = all cameras
        displayMode: "carousel",             // carousel, grid, single
        carouselInterval: 10000,             // 10 seconds
        retryDelay: 30000,                   // Retry on error after 30s
        doorbellMonitor: true,               // Monitor for doorbell presses
        doorbellSound: "doorbell.mp3",       // Sound file to play
        doorbellDuration: 15000,             // How long to show doorbell popup (15s)
        doorbellVolume: 0.8,                 // Volume 0-1
    },

    // Required scripts
    getScripts: function() {
        return [];
    },

    // Required styles
    getStyles: function() {
        return [this.file("MMM-BlinkCamera.css")];
    },

    // Module startup
    start: function() {
        Log.info("Starting module: " + this.name);
        
        // State variables
        this.cameras = {};
        this.cameraNames = [];
        this.currentIndex = 0;
        this.loaded = false;
        this.error = null;
        this.status = "Initializing...";
        this.requires2FA = false;
        this.motionVideo = null;
        this.carouselTimer = null;
        this.doorbellAlert = null;
        this.doorbellTimer = null;
        this.audioElement = null;

        // Validate required config
        if (!this.config.email || !this.config.password) {
            this.error = "Missing email or password in config";
            this.updateDom();
            return;
        }

        // Send config to node_helper
        this.sendSocketNotification("CONFIG", this.config);
    },

    // Generate DOM content
    getDom: function() {
        const wrapper = document.createElement("div");
        wrapper.className = "blink-wrapper";

        // Doorbell alert (highest priority - shows over everything)
        if (this.doorbellAlert) {
            wrapper.appendChild(this.createDoorbellAlert());
            return wrapper;
        }

        // Error state
        if (this.error) {
            wrapper.innerHTML = '<div class="blink-error">' +
                '<span class="blink-error-icon">⚠️</span>' +
                '<span class="blink-error-text">' + this.error + '</span>' +
                '</div>';
            return wrapper;
        }

        // 2FA required state
        if (this.requires2FA) {
            wrapper.innerHTML = '<div class="blink-2fa">' +
                '<div class="blink-2fa-icon">🔐</div>' +
                '<div class="blink-2fa-title">2FA Required</div>' +
                '<div class="blink-2fa-text">Run setup script:</div>' +
                '<div class="blink-2fa-cmd">python3 ~/MagicMirror/modules/MMM-BlinkCamera/python/setup_auth.py</div>' +
                '</div>';
            return wrapper;
        }

        // Loading state
        if (!this.loaded) {
            wrapper.innerHTML = '<div class="blink-loading">' +
                '<div class="blink-spinner"></div>' +
                '<div class="blink-status">' + this.status + '</div>' +
                '</div>';
            return wrapper;
        }

        // Motion video display
        if (this.motionVideo) {
            wrapper.appendChild(this.createMotionVideoElement());
            return wrapper;
        }

        // No cameras
        if (this.cameraNames.length === 0) {
            wrapper.innerHTML = '<div class="blink-empty">No cameras found</div>';
            return wrapper;
        }

        // Display based on mode
        if (this.config.displayMode === "grid") {
            wrapper.appendChild(this.createGridView());
        } else {
            wrapper.appendChild(this.createCarouselView());
        }

        return wrapper;
    },

    // Create carousel view (single camera at a time)
    createCarouselView: function() {
        const container = document.createElement("div");
        container.className = "blink-carousel";

        if (this.currentIndex >= this.cameraNames.length) {
            this.currentIndex = 0;
        }

        const cameraName = this.cameraNames[this.currentIndex];
        const camera = this.cameras[cameraName];
        
        if (camera) {
            container.appendChild(this.createCameraCard(cameraName, camera));
        }

        return container;
    },

    // Create grid view (all cameras)
    createGridView: function() {
        const container = document.createElement("div");
        container.className = "blink-grid";

        for (const name of this.cameraNames) {
            const camera = this.cameras[name];
            if (camera) {
                const item = document.createElement("div");
                item.className = "blink-grid-item";
                item.appendChild(this.createCameraCard(name, camera, true));
                container.appendChild(item);
            }
        }

        return container;
    },

    // Create a camera card element
    createCameraCard: function(name, camera, small) {
        const card = document.createElement("div");
        card.className = "blink-camera-card" + (small ? " blink-small" : "");
        card.style.maxWidth = this.config.maxWidth;

        // Image container
        const imgContainer = document.createElement("div");
        imgContainer.className = "blink-image-container";

        // Thumbnail image - use Express route
        if (camera.hasImage) {
            const img = document.createElement("img");
            img.className = "blink-image";
            // Use the Express route to get the image
            img.src = "/" + this.name + "/camera/" + encodeURIComponent(name) + "?t=" + Date.now();
            img.alt = name;
            img.onerror = function() {
                this.style.display = "none";
                this.nextSibling.style.display = "flex";
            };
            imgContainer.appendChild(img);
        }

        // Placeholder (shown if no image or on error)
        const placeholder = document.createElement("div");
        placeholder.className = "blink-placeholder";
        placeholder.innerHTML = "📷";
        placeholder.style.display = camera.hasImage ? "none" : "flex";
        imgContainer.appendChild(placeholder);

        // Overlay with name and status
        const overlay = document.createElement("div");
        overlay.className = "blink-overlay";

        if (this.config.showCameraName) {
            const nameEl = document.createElement("div");
            nameEl.className = "blink-camera-name";
            nameEl.textContent = name;
            overlay.appendChild(nameEl);
        }

        const statusEl = document.createElement("div");
        statusEl.className = "blink-camera-status";
        if (camera.armed) {
            statusEl.innerHTML += '<span title="Armed">🔴</span>';
        }
        if (camera.motion) {
            statusEl.innerHTML += '<span class="blink-motion-icon" title="Motion">🏃</span>';
        }
        overlay.appendChild(statusEl);

        imgContainer.appendChild(overlay);
        card.appendChild(imgContainer);

        // Timestamp
        if (this.config.showLastUpdate && camera.updated) {
            const timestamp = document.createElement("div");
            timestamp.className = "blink-timestamp";
            timestamp.textContent = "Updated: " + camera.updated;
            card.appendChild(timestamp);
        }

        // Battery
        if (camera.battery) {
            const battery = document.createElement("div");
            battery.className = "blink-battery";
            battery.textContent = "🔋 " + camera.battery;
            card.appendChild(battery);
        }

        return card;
    },

    // Create motion video element
    createMotionVideoElement: function() {
        const container = document.createElement("div");
        container.className = "blink-video-container";
        container.style.maxWidth = this.config.maxWidth;

        const header = document.createElement("div");
        header.className = "blink-video-header";
        header.innerHTML = '<span class="blink-video-icon">🎬</span> Motion: ' + this.motionVideo.camera;
        container.appendChild(header);

        const video = document.createElement("video");
        video.className = "blink-video";
        video.autoplay = true;
        video.muted = true;
        video.playsInline = true;
        // Use Express route for video
        video.src = "/" + this.name + "/video/" + encodeURIComponent(this.motionVideo.camera) + "?t=" + Date.now();
        
        const self = this;
        video.onended = function() {
            self.motionVideo = null;
            self.updateDom();
        };
        video.onerror = function() {
            self.motionVideo = null;
            self.updateDom();
        };

        container.appendChild(video);

        return container;
    },

    // Create doorbell alert element
    createDoorbellAlert: function() {
        const container = document.createElement("div");
        container.className = "blink-doorbell-alert";

        const header = document.createElement("div");
        header.className = "blink-doorbell-header";
        header.innerHTML = '<span class="blink-doorbell-icon">🔔</span> DOORBELL';
        container.appendChild(header);

        const camera = document.createElement("div");
        camera.className = "blink-doorbell-camera";
        camera.textContent = this.doorbellAlert.camera;
        container.appendChild(camera);

        const time = document.createElement("div");
        time.className = "blink-doorbell-time";
        time.textContent = this.doorbellAlert.time;
        container.appendChild(time);

        // Image
        if (this.doorbellAlert.hasImage) {
            const imgContainer = document.createElement("div");
            imgContainer.className = "blink-doorbell-image-container";
            
            const img = document.createElement("img");
            img.className = "blink-doorbell-image";
            img.src = "/" + this.name + "/camera/" + encodeURIComponent(this.doorbellAlert.camera) + "?t=" + Date.now();
            img.alt = "Doorbell";
            imgContainer.appendChild(img);
            container.appendChild(imgContainer);
        }

        return container;
    },

    // Play doorbell sound
    playDoorbellSound: function() {
        const self = this;
        
        // Stop any existing sound
        if (this.audioElement) {
            this.audioElement.pause();
            this.audioElement = null;
        }

        // Create audio element
        this.audioElement = new Audio();
        this.audioElement.volume = this.config.doorbellVolume;
        
        // Try module's sound file first, then fallback to a generated tone
        const soundPath = "/" + this.name + "/sounds/" + this.config.doorbellSound;
        
        this.audioElement.src = soundPath;
        this.audioElement.onerror = function() {
            // Fallback: generate a simple doorbell tone using Web Audio API
            self.playGeneratedDoorbell();
        };
        
        this.audioElement.play().catch(function(e) {
            Log.warn("MMM-BlinkCamera: Could not play sound: " + e);
            self.playGeneratedDoorbell();
        });
    },

    // Generate doorbell sound using Web Audio API
    playGeneratedDoorbell: function() {
        try {
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const volume = this.config.doorbellVolume;
            
            // Play two-tone doorbell (ding-dong)
            const playTone = function(freq, startTime, duration) {
                const oscillator = audioCtx.createOscillator();
                const gainNode = audioCtx.createGain();
                
                oscillator.connect(gainNode);
                gainNode.connect(audioCtx.destination);
                
                oscillator.frequency.value = freq;
                oscillator.type = "sine";
                
                gainNode.gain.setValueAtTime(volume * 0.3, startTime);
                gainNode.gain.exponentialRampToValueAtTime(0.01, startTime + duration);
                
                oscillator.start(startTime);
                oscillator.stop(startTime + duration);
            };
            
            const now = audioCtx.currentTime;
            playTone(830, now, 0.5);        // Ding (high)
            playTone(660, now + 0.5, 0.7);  // Dong (low)
            
            // Repeat once
            playTone(830, now + 1.5, 0.5);
            playTone(660, now + 2.0, 0.7);
            
        } catch (e) {
            Log.warn("MMM-BlinkCamera: Could not generate sound: " + e);
        }
    },

    // Show doorbell alert
    showDoorbellAlert: function(payload) {
        const self = this;
        
        // Clear any existing timer
        if (this.doorbellTimer) {
            clearTimeout(this.doorbellTimer);
        }
        
        // Set alert data
        this.doorbellAlert = payload;
        
        // Play sound
        this.playDoorbellSound();
        
        // Update display
        this.updateDom();
        
        // Auto-dismiss after duration
        this.doorbellTimer = setTimeout(function() {
            self.doorbellAlert = null;
            self.doorbellTimer = null;
            self.updateDom();
            // Refresh cameras to get latest image
            self.sendSocketNotification("REFRESH", {});
        }, this.config.doorbellDuration);
    },

    // Start carousel rotation
    startCarousel: function() {
        if (this.carouselTimer) {
            clearInterval(this.carouselTimer);
        }

        if (this.config.displayMode === "carousel" && this.cameraNames.length > 1) {
            const self = this;
            this.carouselTimer = setInterval(function() {
                if (!self.motionVideo) {
                    self.currentIndex = (self.currentIndex + 1) % self.cameraNames.length;
                    self.updateDom();
                }
            }, this.config.carouselInterval);
        }
    },

    // Handle socket notifications from node_helper
    socketNotificationReceived: function(notification, payload) {
        Log.info(this.name + " received: " + notification);

        switch (notification) {
            case "STATUS":
                this.status = payload;
                if (!this.loaded) {
                    this.updateDom();
                }
                break;

            case "ERROR":
                this.error = payload;
                this.loaded = false;
                this.updateDom();
                // Retry after delay
                const self = this;
                setTimeout(function() {
                    self.error = null;
                    self.sendSocketNotification("CONFIG", self.config);
                }, this.config.retryDelay);
                break;

            case "2FA_REQUIRED":
                this.requires2FA = true;
                this.loaded = false;
                this.updateDom();
                break;

            case "CAMERAS":
                this.cameras = payload.cameras || {};
                this.cameraNames = Object.keys(this.cameras);
                
                // Filter if specific cameras requested
                if (this.config.cameras && this.config.cameras.length > 0) {
                    this.cameraNames = this.cameraNames.filter(function(name) {
                        return this.config.cameras.indexOf(name) !== -1;
                    }, this);
                }

                this.loaded = true;
                this.requires2FA = false;
                this.error = null;
                this.updateDom();
                this.startCarousel();
                break;

            case "MOTION":
                if (this.config.showMotionVideos && payload && payload.camera) {
                    this.motionVideo = payload;
                    this.updateDom();
                }
                break;

            case "DOORBELL":
                if (payload && payload.camera) {
                    this.showDoorbellAlert(payload);
                }
                break;
        }
    },

    // Suspend module (called when hidden)
    suspend: function() {
        if (this.carouselTimer) {
            clearInterval(this.carouselTimer);
            this.carouselTimer = null;
        }
    },

    // Resume module (called when shown)
    resume: function() {
        this.startCarousel();
    },

    // Handle notifications from other modules
    notificationReceived: function(notification, payload, sender) {
        if (notification === "BLINK_REFRESH") {
            this.sendSocketNotification("REFRESH", {});
        }
    }
});
