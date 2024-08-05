document.getElementById('fetchTracks').addEventListener('click', async () => {
    const source = document.getElementById('source').value;
    const availability = document.getElementById('availability').value;
    const currentUrl = window.location.href;

    const queryParams = new URLSearchParams({
        source: source,
        availability: availability
    });

    try {
        const response = await fetch(`http://127.0.0.1:5000/unavailable_tracks?${queryParams.toString()}`, {
            credentials: 'include'  // Include credentials (cookies) with the request
        });

        const data = await response.json();

        if (response.status === 401 && data.redirect) {
            // Append the next parameter to the redirect URL
            const redirectUrl = new URL(data.redirect);
            redirectUrl.searchParams.set('next', currentUrl);
            window.location.href = redirectUrl.toString();
            return;
        }

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        displayTracks(data);
        createDownloadButton(data);
    } catch (error) {
        console.error('There was a problem with the fetch operation:', error);
    }
});

function displayTracks(tracks) {
    const trackList = document.getElementById('trackList');
    trackList.innerHTML = '';

    if (tracks.length === 0) {
        trackList.innerHTML = '<p>No unavailable tracks found.</p>';
        return;
    }

    tracks.forEach(track => {
        const trackElement = document.createElement('div');
        trackElement.classList.add('track');
        trackElement.innerHTML = `
            <p><strong>Track:</strong> ${track.name}</p>
            <p><strong>Artist:</strong> ${track.artists.map(artist => artist.name).join(', ')}</p>
            <p><strong>Album:</strong> ${track.album.name}</p>
        `;
        trackList.appendChild(trackElement);
    });
}

function createDownloadButton(data) {
    const downloadButton = document.createElement('button');
    downloadButton.textContent = 'Download Data';
    downloadButton.addEventListener('click', () => downloadData(data));
    document.body.appendChild(downloadButton);
}

function downloadData(data) {
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(data));
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", "unavailable_tracks.json");
    document.body.appendChild(downloadAnchorNode); // required for firefox
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
}