let currentRelease = null;
let currentTrackIndex = -1;
let shufflePlaylist = [];
let shuffleIndex = -1;

// Playback Modes: 'repeat-all', 'repeat-one', 'shuffle'
let playbackMode = 'repeat-all';

function formatDuration(seconds) {
    if (!seconds) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

async function initRelease() {
    const urlParams = new URLSearchParams(window.location.search);
    const releaseId = urlParams.get('id');

    if (!releaseId) {
        showError("No release ID specified.");
        return;
    }

    try {
        const response = await fetch('/manifest.json');
        const manifest = await response.json();
        
        if (!manifest || !manifest.releases) {
            showError("Failed to fetch library releases.");
            return;
        }

        currentRelease = manifest.releases.find(r => r.id === releaseId);

        if (!currentRelease) {
            showError(`Release not found with ID: ${releaseId}`);
            return;
        }

        // Display UI
        document.getElementById('release-header-title').textContent = currentRelease.name;
        document.getElementById('album-title').textContent = currentRelease.name;
        document.getElementById('track-count').textContent = `${currentRelease.songs.length} Tracks`;
        document.getElementById('album-cover').src = currentRelease.cover || '../asset/placeholder.png';

        renderTracks();
        setupPlayer();

        document.getElementById('release-content').style.display = 'flex';
    } catch (err) {
        console.error("Error loading release:", err);
        showError("Failed to load or parse manifest.");
    }
}

function renderTracks() {
    const list = document.getElementById('track-list');
    list.innerHTML = '';

    currentRelease.songs.forEach((song, idx) => {
        const li = document.createElement('li');
        li.className = 'track-item';
        li.id = `track-${idx}`;
        
        const titleSpan = document.createElement('span');
        titleSpan.textContent = `${idx + 1}. ${song.name}`;
        
        const durSpan = document.createElement('span');
        durSpan.textContent = formatDuration(song.duration);

        li.appendChild(titleSpan);
        li.appendChild(durSpan);

        li.addEventListener('click', () => {
            playTrack(idx);
        });

        list.appendChild(li);
    });
}

function setupPlayer() {
    const player = document.getElementById('audio-player');
    const modeBtn = document.getElementById('mode-btn');
    const nextBtn = document.getElementById('next-btn');
    const prevBtn = document.getElementById('prev-btn');

    // Cycle mode button
    modeBtn.addEventListener('click', () => {
        if (playbackMode === 'repeat-all') {
            playbackMode = 'repeat-one';
        } else if (playbackMode === 'repeat-one') {
            playbackMode = 'shuffle';
            generateShufflePlaylist();
        } else {
            playbackMode = 'repeat-all';
        }
        updateModeUI();
    });

    // Auto-next when song ends
    player.addEventListener('ended', () => {
        handleTrackEnded();
    });

    nextBtn.addEventListener('click', playNext);
    prevBtn.addEventListener('click', playPrev);
}

function updateModeUI() {
    const modeBtn = document.getElementById('mode-btn');
    const statusText = document.getElementById('player-mode-status');

    let modeLabel = "Repeat All";
    if (playbackMode === 'repeat-one') modeLabel = "Repeat One";
    if (playbackMode === 'shuffle') modeLabel = "Shuffle";

    modeBtn.textContent = `Mode: ${modeLabel}`;
    statusText.textContent = `Mode: ${modeLabel}`;
}

function generateShufflePlaylist() {
    if (!currentRelease || !currentRelease.songs.length) return;
    const songCount = currentRelease.songs.length;
    
    // Create list of indices: [0, 1, ..., n-1]
    shufflePlaylist = Array.from({length: songCount}, (_, i) => i);
    
    // Fisher-Yates shuffle
    for (let i = songCount - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shufflePlaylist[i], shufflePlaylist[j]] = [shufflePlaylist[j], shufflePlaylist[i]];
    }
    
    // If there's currently a playing track, put it at the very beginning of the shuffle list
    if (currentTrackIndex !== -1) {
        const currentIdxInShuffle = shufflePlaylist.indexOf(currentTrackIndex);
        if (currentIdxInShuffle !== -1) {
            shufflePlaylist.splice(currentIdxInShuffle, 1);
        }
        shufflePlaylist.unshift(currentTrackIndex);
    }
    
    shuffleIndex = 0;
}

function playTrack(index) {
    if (!currentRelease || index < 0 || index >= currentRelease.songs.length) return;

    // Update highlighting
    if (currentTrackIndex !== -1) {
        const oldActive = document.getElementById(`track-${currentTrackIndex}`);
        if (oldActive) oldActive.classList.remove('active');
    }

    currentTrackIndex = index;
    const newActive = document.getElementById(`track-${currentTrackIndex}`);
    if (newActive) newActive.classList.add('active');

    // Scroll into view
    if (newActive) {
        newActive.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    // If we are playing a song directly in Shuffle mode, make sure shuffleIndex aligns with it
    if (playbackMode === 'shuffle') {
        const sIdx = shufflePlaylist.indexOf(index);
        if (sIdx !== -1) {
            shuffleIndex = sIdx;
        } else {
            generateShufflePlaylist();
            shuffleIndex = shufflePlaylist.indexOf(index);
        }
    }

    const song = currentRelease.songs[index];
    const player = document.getElementById('audio-player');
    player.src = song.location;
    player.play();

    document.getElementById('now-playing-title').textContent = song.name;
}

function handleTrackEnded() {
    if (playbackMode === 'repeat-one') {
        // Loop same song
        const player = document.getElementById('audio-player');
        player.currentTime = 0;
        player.play();
    } else {
        playNext();
    }
}

function playNext() {
    if (!currentRelease || !currentRelease.songs.length) return;

    if (playbackMode === 'shuffle') {
        shuffleIndex++;
        if (shuffleIndex >= shufflePlaylist.length) {
            // Loop shuffle playlist: generate a new permutation
            generateShufflePlaylist();
        }
        const nextTrackIdx = shufflePlaylist[shuffleIndex];
        playTrack(nextTrackIdx);
    } else {
        // 'repeat-all'
        let nextIdx = currentTrackIndex + 1;
        if (nextIdx >= currentRelease.songs.length) {
            nextIdx = 0; // Loop back to beginning
        }
        playTrack(nextIdx);
    }
}

function playPrev() {
    if (!currentRelease || !currentRelease.songs.length) return;

    if (playbackMode === 'shuffle') {
        shuffleIndex--;
        if (shuffleIndex < 0) {
            shuffleIndex = shufflePlaylist.length - 1; // loop back to end of shuffle list
        }
        const prevTrackIdx = shufflePlaylist[shuffleIndex];
        playTrack(prevTrackIdx);
    } else {
        // 'repeat-all' or 'repeat-one'
        let prevIdx = currentTrackIndex - 1;
        if (prevIdx < 0) {
            prevIdx = currentRelease.songs.length - 1; // loop to end
        }
        playTrack(prevIdx);
    }
}

function showError(msg) {
    document.getElementById('release-header-title').textContent = "Error";
    document.getElementById('error-message').textContent = msg;
    document.getElementById('error-view').style.display = 'block';
}

document.addEventListener('DOMContentLoaded', initRelease);
