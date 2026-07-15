let showsData = [];

// Helper to count total episodes in a show
function countEpisodes(show) {
    let total = 0;
    if (show.seasons) {
        show.seasons.forEach(season => {
            if (season.episodes) {
                total += season.episodes.length;
            }
        });
    }
    return total;
}

// Function to create a show card element
function createShowCard(show) {
    const card = document.createElement('div');
    card.className = 'media-card';
    
    // Cover artwork (thumbnail or placeholder)
    const poster = document.createElement('img');
    poster.className = 'media-poster';
    if (show.thumbnail) {
        poster.src = show.thumbnail;
    } else {
        poster.src = '../asset/placeholder.png';
    }
    poster.alt = show.name;
    
    // Title
    const title = document.createElement('div');
    title.className = 'media-title';
    title.textContent = show.name;
    
    // Episode count
    const totalEps = countEpisodes(show);
    const episodesCount = document.createElement('div');
    episodesCount.className = 'media-duration';
    episodesCount.textContent = `${totalEps} Episode${totalEps !== 1 ? 's' : ''}`;
    
    // Click event to navigate to dedicated show page
    card.addEventListener('click', () => {
        window.location.href = `show.html?id=${encodeURIComponent(show.name)}`;
    });

    card.appendChild(poster);
    card.appendChild(title);
    card.appendChild(episodesCount);
    
    return card;
}

// Render shows to the grid
function renderShows(shows) {
    const grid = document.getElementById('show-grid');
    grid.innerHTML = '';
    
    shows.forEach(show => {
        grid.appendChild(createShowCard(show));
    });
}

// Helper to extract S#E# display from season number and episode index
function formatS00E00(seasonNum, epIndex) {
    return `S${seasonNum}E${epIndex + 1}`;
}

// Render "Continue Watching" section
function renderContinueWatching(manifestShows) {
    const continuePanel = document.getElementById('continue-watching-panel');
    const continueGrid = document.getElementById('continue-grid');
    
    continueGrid.innerHTML = '';
    
    // Load saved single item from localStorage
    let entry = null;
    try {
        const stored = localStorage.getItem('lms_continue_watching');
        if (stored) {
            entry = JSON.parse(stored);
        }
    } catch (e) {
        console.error("Error reading continue watching data:", e);
    }
    
    if (!entry || !entry.showName) {
        continuePanel.style.display = 'none';
        return;
    }
    
    // Find matching show in manifest to get thumbnail
    const matchedShow = manifestShows.find(s => s.name === entry.showName);
    if (!matchedShow) {
        continuePanel.style.display = 'none';
        return;
    }
    
    const card = document.createElement('div');
    card.className = 'media-card';
    
    // Poster image
    const poster = document.createElement('img');
    poster.className = 'media-poster';
    if (matchedShow.thumbnail) {
        poster.src = matchedShow.thumbnail;
    } else {
        poster.src = '../asset/placeholder.png';
    }
    poster.alt = entry.showName;
    
    // Show Title
    const showTitle = document.createElement('div');
    showTitle.className = 'media-title';
    showTitle.textContent = entry.showName;
    
    // S#E# label
    const epLabel = document.createElement('div');
    epLabel.className = 'media-duration';
    epLabel.style.fontWeight = 'bold';
    epLabel.textContent = formatS00E00(entry.seasonNumber, entry.episodeIndex);
    
    // Episode Title
    const epTitle = document.createElement('div');
    epTitle.className = 'media-duration';
    epTitle.style.textAlign = 'center';
    epTitle.style.whiteSpace = 'nowrap';
    epTitle.style.overflow = 'hidden';
    epTitle.style.textOverflow = 'ellipsis';
    epTitle.style.width = '100%';
    epTitle.textContent = entry.episodeTitle;
    
    // Navigation on click
    card.addEventListener('click', () => {
        window.location.href = `watch.html?show=${encodeURIComponent(entry.showName)}&season=${entry.seasonNumber}&episode=${entry.episodeIndex}&resume=1`;
    });
    
    card.appendChild(poster);
    card.appendChild(showTitle);
    card.appendChild(epLabel);
    card.appendChild(epTitle);
    
    continueGrid.appendChild(card);
    continuePanel.style.display = 'block';
}

// Load manifest and initialize
async function loadManifest() {
    try {
        const response = await fetch('../manifest.json');
        const manifest = await response.json();
        
        if (manifest.shows) {
            showsData = manifest.shows;
            
            // Render Continue Watching
            renderContinueWatching(showsData);
            
            // Render shows as defined in the manifest
            renderShows(showsData);
        }
    } catch (error) {
        console.error("Error loading manifest:", error);
        document.getElementById('show-grid').innerHTML = '<p style="color:red;">Failed to load catalog.</p>';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadManifest();
});
