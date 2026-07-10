let releasesData = [];

// Helper to format track count
function formatTrackCount(count) {
    if (!count) return '0 Tracks';
    return count === 1 ? '1 Track' : `${count} Tracks`;
}

// Function to create a music card element
function createReleaseCard(release) {
    const card = document.createElement('div');
    card.className = 'media-card';
    
    // Poster image (cover or placeholder)
    const cover = document.createElement('img');
    cover.className = 'album-cover'; // Square cover class
    if (release.cover) {
        cover.src = release.cover;
    } else {
        cover.src = '../asset/placeholder.png'; // Fallback placeholder
    }
    cover.alt = release.name;
    
    // Title
    const title = document.createElement('div');
    title.className = 'media-title';
    title.textContent = release.name;
    
    // Track count
    const tracks = document.createElement('div');
    tracks.className = 'media-duration'; // Reuse style for consistency
    tracks.textContent = formatTrackCount(release.songs ? release.songs.length : 0);
    
    // Add click event to navigate to release.html?id=<release_id>
    card.addEventListener('click', () => {
        window.location.href = `release.html?id=${release.id}`;
    });

    card.appendChild(cover);
    card.appendChild(title);
    card.appendChild(tracks);
    
    return card;
}

// Render releases to the grid
function renderReleases(releases) {
    const grid = document.getElementById('music-grid');
    grid.innerHTML = ''; // Clear current
    
    releases.forEach(release => {
        grid.appendChild(createReleaseCard(release));
    });
}

// Load manifest
async function loadManifest() {
    try {
        const response = await fetch('../manifest.json');
        const manifest = await response.json();
        
        if (manifest.releases) {
            releasesData = manifest.releases;
            
            // Default sort: alphabetical
            sortAlphabetical();
        }
    } catch (error) {
        console.error("Error loading manifest:", error);
        document.getElementById('music-grid').innerHTML = '<p style="color:red;">Failed to load catalog.</p>';
    }
}

// Sorting logic
function sortAlphabetical() {
    releasesData.sort((a, b) => a.name.localeCompare(b.name));
    renderReleases(releasesData);
}

function sortTracks() {
    releasesData.sort((a, b) => ((a.songs ? a.songs.length : 0) - (b.songs ? b.songs.length : 0)));
    renderReleases(releasesData);
}

// Setup event listeners and init
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('sort-alpha').addEventListener('click', sortAlphabetical);
    document.getElementById('sort-tracks').addEventListener('click', sortTracks);
    
    loadManifest();
});
