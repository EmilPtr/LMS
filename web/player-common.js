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
    }
};
