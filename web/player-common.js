/**
 * Shared Video Player Configuration and Utility Module for LMS
 */
const LMSPlayer = {
    /**
     * Initializes a Video.js player with consistent LMS styling and settings.
     * @param {string} elementId - The ID of the video element
     * @param {object} options - Optional configuration overrides
     * @returns {object} The Video.js player instance
     */
    createPlayer(elementId, options = {}) {
        if (typeof videojs === 'undefined') {
            console.error("Video.js is not loaded on this page!");
            return null;
        }

        const defaultOptions = {
            controls: true,
            autoplay: true,
            preload: 'auto',
            fluid: true,
            playbackRates: [0.5, 1, 1.25, 1.5, 2],
            controlBar: {
                children: [
                    'playToggle',
                    'volumePanel',
                    'currentTimeDisplay',
                    'timeDivider',
                    'durationDisplay',
                    'progressControl',
                    'playbackRateMenuButton',
                    'subsCapsButton',
                    'fullscreenToggle'
                ]
            }
        };

        const config = { ...defaultOptions, ...options };
        const player = videojs(elementId, config);

        player.ready(() => {
            player.addClass('vjs-big-play-centered');
        });

        return player;
    },

    /**
     * Clears existing remote text tracks and adds new ones from the manifest.
     * @param {object} player - The Video.js player instance
     * @param {Array} subtitleTracks - Array of subtitle objects (from manifest)
     */
    setSubtitles(player, subtitleTracks) {
        if (!player) return;

        // Clear any previous remote text tracks
        if (typeof player.remoteTextTracks === 'function') {
            const remoteTracks = player.remoteTextTracks();
            if (remoteTracks && remoteTracks.length > 0) {
                // Iterate backwards to safely remove tracks
                for (let i = remoteTracks.length - 1; i >= 0; i--) {
                    player.removeRemoteTextTrack(remoteTracks[i]);
                }
            }
        } else if (player.textTracks) {
            // Fallback for clearing tracks if remoteTextTracks is not direct
            const tracks = player.textTracks();
            for (let i = tracks.length - 1; i >= 0; i--) {
                player.removeTrack(tracks[i]);
            }
        }

        // Add each subtitle track dynamically
        if (Array.isArray(subtitleTracks)) {
            subtitleTracks.forEach(track => {
                if (track && track.location) {
                    player.addRemoteTextTrack({
                        kind: 'subtitles',
                        srclang: track.code || 'en',
                        label: track.language || 'English',
                        src: track.location,
                        default: false
                    }, false);
                }
            });
        }
    },

    /**
     * Copies text to the clipboard, providing a fallback for non-secure contexts (HTTP over LAN).
     * @param {string} text - The text to copy
     * @returns {Promise} Resolves when copied, rejects on failure
     */
    copyToClipboard(text) {
        // Modern approach for secure contexts (HTTPS/localhost)
        if (navigator.clipboard && window.isSecureContext) {
            return navigator.clipboard.writeText(text);
        }

        // Fallback for non-secure contexts (HTTP over LAN)
        return new Promise((resolve, reject) => {
            try {
                const textArea = document.createElement("textarea");
                textArea.value = text;

                // Ensure the textarea is off-screen but part of the DOM
                textArea.style.position = "fixed";
                textArea.style.left = "-9999px";
                textArea.style.top = "0";

                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();

                const successful = document.execCommand('copy');
                document.body.removeChild(textArea);

                if (successful) {
                    resolve();
                } else {
                    reject(new Error("Unable to copy to clipboard"));
                }
            } catch (err) {
                reject(err);
            }
        });
    }
};
