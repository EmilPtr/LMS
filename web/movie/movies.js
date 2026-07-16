let moviesData = [];

// Helper to format seconds into readable string
function formatDuration(seconds) {
    if (!seconds) return 'Unknown';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    
    if (hrs > 0) {
        return `${hrs}h ${mins}m`;
    }
    return `${mins}m`;
}

// Function to create a movie card element
function createMovieCard(movie) {
    const card = document.createElement('div');
    card.className = 'media-card';
    
    // Poster image (thumbnail or placeholder)
    const poster = document.createElement('img');
    poster.className = 'media-poster';
    if (movie.thumbnail) {
        poster.src = movie.thumbnail;
    } else {
        poster.src = '../asset/placeholder.png';
    }
    poster.alt = movie.name;
    
    // Title
    const title = document.createElement('div');
    title.className = 'media-title';
    title.textContent = movie.name;
    
    // Duration
    const duration = document.createElement('div');
    duration.className = 'media-duration';
    duration.textContent = formatDuration(movie.length);
    
    // Add click event to navigate to playback page
    card.addEventListener('click', () => {
        window.location.href = `watch.html?id=${movie.id}`;
    });

    card.appendChild(poster);
    card.appendChild(title);
    card.appendChild(duration);
    
    return card;
}

// Render movies to the grid
function renderMovies(movies) {
    const grid = document.getElementById('movie-grid');
    grid.innerHTML = ''; // Clear current
    
    movies.forEach(movie => {
        grid.appendChild(createMovieCard(movie));
    });
}

// Load manifest
async function loadManifest() {
    try {
        const response = await fetch('/manifest.json');
        const manifest = await response.json();
        
        if (manifest.movies) {
            moviesData = manifest.movies;
            
            // Default sort: alphabetical
            sortAlphabetical();
        }
    } catch (error) {
        console.error("Error loading manifest:", error);
        document.getElementById('movie-grid').innerHTML = '<p style="color:red;">Failed to load catalog.</p>';
    }
}

// Sorting logic
function sortAlphabetical() {
    moviesData.sort((a, b) => a.name.localeCompare(b.name));
    renderMovies(moviesData);
}

function sortLength() {
    moviesData.sort((a, b) => (a.length || 0) - (b.length || 0));
    renderMovies(moviesData);
}

// Setup event listeners and init
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('sort-alpha').addEventListener('click', sortAlphabetical);
    document.getElementById('sort-length').addEventListener('click', sortLength);
    
    loadManifest();
});
