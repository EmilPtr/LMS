function formatDuration(seconds) {
    if (!seconds) return 'Unknown';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    if (hrs > 0) return `${hrs}h ${mins}m`;
    return `${mins}m`;
}

async function initPlayer() {
    const urlParams = new URLSearchParams(window.location.search);
    const movieId = urlParams.get('id');

    if (!movieId) {
        showError("No movie ID specified in the URL.");
        return;
    }

    try {
        const response = await fetch('../manifest.json');
        const manifest = await response.json();
        
        if (!manifest || !manifest.movies) {
            showError("Manifest is empty or corrupted.");
            return;
        }

        const movie = manifest.movies.find(m => m.id === movieId);

        if (!movie) {
            showError(`Movie with ID '${movieId}' was not found in the manifest.`);
            return;
        }

        // Setup the player
        document.getElementById('movie-title-header').textContent = `Playing: ${movie.name}`;
        document.getElementById('movie-title').textContent = movie.name;
        document.getElementById('movie-duration').textContent = `Duration: ${formatDuration(movie.length)}`;
        
        const player = document.getElementById('video-player');
        player.src = movie.location;
        if (movie.thumbnail) {
            player.poster = movie.thumbnail;
        }

        document.getElementById('player-view').style.display = 'flex';
    } catch (err) {
        console.error("Error loading movie:", err);
        showError("Failed to fetch or parse the manifest.json file.");
    }
}

function showError(msg) {
    document.getElementById('movie-title-header').textContent = "Error";
    document.getElementById('error-message').textContent = msg;
    document.getElementById('error-view').style.display = 'block';
}

document.addEventListener('DOMContentLoaded', initPlayer);
