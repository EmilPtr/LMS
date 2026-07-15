// Continue Watching Local Storage Management Helpers
function getSavedPosition(showName, seasonNumber, episodeIndex) {
    try {
        const stored = localStorage.getItem('lms_continue_watching');
        if (stored) {
            const entry = JSON.parse(stored);
            if (entry && 
                entry.showName === showName && 
                entry.seasonNumber === seasonNumber && 
                entry.episodeIndex === episodeIndex) {
                return entry.position;
            }
        }
    } catch (e) {
        console.error("Error fetching playback position:", e);
    }
    return 0;
}

function savePlaybackPosition(showName, seasonNumber, episodeIndex, episodeTitle, position) {
    // Only save if we have watched more than 1 second of content
    if (position < 1) return;

    const entry = {
        showName: showName,
        seasonNumber: seasonNumber,
        episodeIndex: episodeIndex,
        episodeTitle: episodeTitle,
        position: position,
        timestamp: Date.now()
    };
    
    localStorage.setItem('lms_continue_watching', JSON.stringify(entry));
}

function clearPlaybackPosition(showName, seasonNumber, episodeIndex) {
    try {
        const stored = localStorage.getItem('lms_continue_watching');
        if (stored) {
            const entry = JSON.parse(stored);
            if (entry && 
                entry.showName === showName && 
                entry.seasonNumber === seasonNumber && 
                entry.episodeIndex === episodeIndex) {
                localStorage.removeItem('lms_continue_watching');
            }
        }
    } catch (e) {
        console.error("Error clearing continue watching:", e);
    }
}

// Player initialization and controller
async function initPlayer() {
    const urlParams = new URLSearchParams(window.location.search);
    const showName = urlParams.get('show');
    const seasonStr = urlParams.get('season');
    const episodeStr = urlParams.get('episode');

    if (!showName || !seasonStr || !episodeStr) {
        showError("Invalid URL parameters. Missing show, season, or episode identifiers.");
        return;
    }

    const seasonNumber = parseInt(seasonStr, 10);
    const episodeIndex = parseInt(episodeStr, 10);

    // Setup back button
    document.getElementById('back-btn').onclick = () => {
        window.location.href = `show.html?id=${encodeURIComponent(showName)}`;
    };

    try {
        const response = await fetch('../manifest.json');
        const manifest = await response.json();

        if (!manifest || !manifest.shows) {
            showError("Manifest is empty or corrupted.");
            return;
        }

        // Find the show
        const show = manifest.shows.find(s => s.name === showName);
        if (!show) {
            showError(`Show '${showName}' was not found in the manifest.`);
            return;
        }

        // Find the season
        const season = show.seasons.find(s => s.season === seasonNumber);
        if (!season) {
            showError(`Season ${seasonNumber} of Show '${showName}' was not found.`);
            return;
        }

        // Find the episode
        const episode = season.episodes && season.episodes[episodeIndex];
        if (!episode) {
            showError(`Episode ${episodeIndex + 1} of Season ${seasonNumber} was not found.`);
            return;
        }

        const episodeTitle = episode.name;
        const episodeCode = `S${seasonNumber}E${episodeIndex + 1}`;

        // Populate details
        document.getElementById('player-header-title').textContent = `Playing: ${showName} - ${episodeCode}`;
        document.getElementById('show-title-display').textContent = showName;
        document.getElementById('episode-code-display').textContent = episodeCode;
        document.getElementById('episode-title-display').textContent = episodeTitle;

        const player = document.getElementById('video-player');
        player.src = episode.location;
        if (show.thumbnail) {
            player.poster = show.thumbnail;
        }

        // Build flat episode list across all seasons for next/prev traversing
        const sortedSeasons = [...show.seasons].sort((a, b) => a.season - b.season);
        let allEpisodesFlat = [];
        sortedSeasons.forEach(s => {
            if (s.episodes) {
                s.episodes.forEach((ep, idx) => {
                    allEpisodesFlat.push({
                        seasonNumber: s.season,
                        episodeIndex: idx,
                        episodeData: ep
                    });
                });
            }
        });

        const currentFlatIdx = allEpisodesFlat.findIndex(item => 
            item.seasonNumber === seasonNumber && item.episodeIndex === episodeIndex
        );

        // Next and Previous Button configurations
        const prevBtn = document.getElementById('prev-ep-btn');
        const nextBtn = document.getElementById('next-ep-btn');

        if (currentFlatIdx > 0) {
            prevBtn.style.display = 'inline-block';
            prevBtn.onclick = () => {
                const prevEp = allEpisodesFlat[currentFlatIdx - 1];
                window.location.href = `watch.html?show=${encodeURIComponent(showName)}&season=${prevEp.seasonNumber}&episode=${prevEp.episodeIndex}`;
            };
        } else {
            prevBtn.style.display = 'none';
        }

        if (currentFlatIdx < allEpisodesFlat.length - 1) {
            nextBtn.style.display = 'inline-block';
            nextBtn.onclick = () => {
                const nextEp = allEpisodesFlat[currentFlatIdx + 1];
                window.location.href = `watch.html?show=${encodeURIComponent(showName)}&season=${nextEp.seasonNumber}&episode=${nextEp.episodeIndex}`;
            };
        } else {
            nextBtn.style.display = 'none';
        }

        // Handle resume playback position
        const savedTime = getSavedPosition(showName, seasonNumber, episodeIndex);
        if (savedTime > 0) {
            player.addEventListener('loadedmetadata', () => {
                player.currentTime = savedTime;
            }, { once: true });
        }

        // Save progress tracking variables
        let lastSavedSec = -1;

        // Save progress periodically on timeupdate
        player.addEventListener('timeupdate', () => {
            const currentSec = Math.floor(player.currentTime);
            // Save every 3 seconds to avoid writing too frequently
            if (currentSec !== lastSavedSec && currentSec % 3 === 0) {
                lastSavedSec = currentSec;
                savePlaybackPosition(showName, seasonNumber, episodeIndex, episodeTitle, player.currentTime);
            }
        });

        // Save progress on pause
        player.addEventListener('pause', () => {
            savePlaybackPosition(showName, seasonNumber, episodeIndex, episodeTitle, player.currentTime);
        });

        // Save progress on window/page exit
        window.addEventListener('beforeunload', () => {
            savePlaybackPosition(showName, seasonNumber, episodeIndex, episodeTitle, player.currentTime);
        });

        // Clear progress when episode finishes
        player.addEventListener('ended', () => {
            clearPlaybackPosition(showName, seasonNumber, episodeIndex);
        });

        // Show player view
        document.getElementById('player-view').style.display = 'flex';

    } catch (err) {
        console.error("Error loading episode player:", err);
        showError("Failed to fetch or parse manifest.json.");
    }
}

function showError(msg) {
    document.getElementById('player-header-title').textContent = "Error";
    document.getElementById('error-message').textContent = msg;
    document.getElementById('error-view').style.display = 'block';
}

document.addEventListener('DOMContentLoaded', initPlayer);
