/**
 * Live Camera Stream & Frame Capture Controller
 */

window.CameraManager = {
    stream: null,
    video: null,
    canvas: null,

    init: function() {
        this.video = document.getElementById('cameraVideo');
        this.canvas = document.getElementById('cameraCanvas');
    },

    start: async function(onSuccess, onError) {
        this.init();
        if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
            const err = "Camera API (getUserMedia) not supported in this browser environment.";
            if (onError) onError(err);
            return;
        }

        try {
            const constraints = {
                video: {
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'environment'
                },
                audio: false
            };

            this.stream = await navigator.mediaDevices.getUserMedia(constraints);
            this.video.srcObject = this.stream;
            this.video.style.display = 'block';
            
            const offlineMsg = document.getElementById('cameraOfflineMsg');
            if (offlineMsg) offlineMsg.style.display = 'none';

            if (onSuccess) onSuccess();
        } catch (err) {
            console.error("Camera access error:", err);
            let userMsg = "Unable to access webcam. Please verify browser camera permissions.";
            if (err.name === 'NotAllowedError') {
                userMsg = "Camera access was blocked. Please permit camera access in your browser settings.";
            } else if (err.name === 'NotFoundError') {
                userMsg = "No video input hardware found on this machine. You can use Image Upload or the Simulator Bridge.";
            }
            if (onError) onError(userMsg);
        }
    },

    captureSnapshot: function() {
        if (!this.video || !this.video.videoWidth) {
            throw new Error("Camera stream is not ready for capture.");
        }

        this.canvas.width = this.video.videoWidth;
        this.canvas.height = this.video.videoHeight;
        const ctx = this.canvas.getContext('2d');
        ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height);

        // Return base64 JPEG
        return this.canvas.toDataURL('image/jpeg', 0.90);
    },

    stop: function() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
        if (this.video) {
            this.video.srcObject = null;
        }
        const offlineMsg = document.getElementById('cameraOfflineMsg');
        if (offlineMsg) offlineMsg.style.display = 'block';
    }
};
