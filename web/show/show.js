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

// Function to format season and episode numbers (e.g., S01E05 or just S1E5)
function formatEpisodeCode(seasonNum, epIndex) {
    return `S${seasonNum}E${epIndex + 1}`;
}

async function loadShowDetails() {
    const urlParams = new URLSearchParams(window.location.search);
    const showId = urlParams.get('id');

    if (!showId) {
        showError("No Show ID specified in the URL.");
        return;
    }

    try {
        const response = await fetch('/manifest.json');
        const manifest = await response.json();

        if (!manifest || !manifest.shows) {
            showError("Manifest is empty or corrupted.");
            return;
        }

        // Find the show matching the decoded ID (show name)
        const show = manifest.shows.find(s => s.name === showId || encodeURIComponent(s.name) === encodeURIComponent(showId));

        if (!show) {
            showError(`Show '${showId}' was not found in the manifest.`);
            return;
        }

        // Display basic show info
        document.getElementById('show-header-title').textContent = show.name;
        document.getElementById('show-title-display').textContent = show.name;
        
        const totalEps = countEpisodes(show);
        document.getElementById('show-episodes-count').textContent = `${totalEps} Episode${totalEps !== 1 ? 's' : ''}`;

        const coverImg = document.getElementById('show-cover-img');
        if (show.thumbnail) {
            coverImg.src = show.thumbnail;
        } else {
            coverImg.src = '../asset/placeholder.png';
        }
        coverImg.alt = show.name;

        // Render seasons
        const seasonsContainer = document.getElementById('seasons-container');
        seasonsContainer.innerHTML = '';

        if (show.seasons && show.seasons.length > 0) {
            // Sort seasons in ascending order
            const sortedSeasons = [...show.seasons].sort((a, b) => a.season - b.season);

            sortedSeasons.forEach(season => {
                const accordion = document.createElement('div');
                accordion.className = 'season-accordion';

                // Header
                const header = document.createElement('div');
                header.className = 'season-header';
                
                const headerTitle = document.createElement('span');
                headerTitle.textContent = `Season ${season.season}`;
                header.appendChild(headerTitle);

                // Content
                const content = document.createElement('div');
                content.className = 'season-episodes';

                const epList = document.createElement('ul');
                epList.className = 'episode-list';

                if (season.episodes && season.episodes.length > 0) {
                    season.episodes.forEach((episode, index) => {
                        const epItem = document.createElement('li');
                        epItem.className = 'episode-item';

                        const numSpan = document.createElement('span');
                        numSpan.className = 'episode-num';
                        numSpan.textContent = formatEpisodeCode(season.season, index);

                        const titleSpan = document.createElement('span');
                        titleSpan.style.flex = '1';
                        titleSpan.textContent = episode.name;

                        epItem.appendChild(numSpan);
                        epItem.appendChild(titleSpan);

                        // Clicking episode navigates to watch.html
                        epItem.addEventListener('click', () => {
                            window.location.href = `watch.html?show=${encodeURIComponent(show.name)}&season=${season.season}&episode=${index}`;
                        });

                        epList.appendChild(epItem);
                    });
                } else {
                    const emptyItem = document.createElement('li');
                    emptyItem.className = 'episode-item';
                    emptyItem.style.color = '#888';
                    emptyItem.textContent = "No episodes in this season.";
                    epList.appendChild(emptyItem);
                }

                content.appendChild(epList);
                accordion.appendChild(header);
                accordion.appendChild(content);

                // Collapsible smooth click event
                header.addEventListener('click', () => {
                    const isExpanded = content.style.display === 'block';
                    if (isExpanded) {
                        content.style.display = 'none';
                        header.classList.remove('active');
                    } else {
                        content.style.display = 'block';
                        header.classList.add('active');
                    }
                });

                seasonsContainer.appendChild(accordion);
            });
        } else {
            seasonsContainer.innerHTML = '<p style="color: #666; padding: 10px;">No seasons recorded for this show.</p>';
        }

        document.getElementById('show-content').style.display = 'flex';

    } catch (err) {
        console.error("Error loading show:", err);
        showError("Failed to fetch or parse the manifest.json file.");
    }
}

function showError(msg) {
    document.getElementById('show-header-title').textContent = "Error";
    document.getElementById('error-message').textContent = msg;
    document.getElementById('error-view').style.display = 'block';
}

document.addEventListener('DOMContentLoaded', loadShowDetails);
