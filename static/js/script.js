document.getElementById('fetchTracks').addEventListener('click', async () => {
    const source = document.getElementById('source').value;
    const availability = document.getElementById('availability').value;
    const currentUrl = window.location.href;

    const queryParams = new URLSearchParams({
        source: source,
        availability: availability
    });

    console.log('Query Parameters:', queryParams.toString()); // Log query parameters

    const url = new URL('/unavailable_tracks', window.location.origin);
    url.search = queryParams.toString();

    try {
        const response = await fetch(url.toString(), {
            credentials: 'include'  // Include credentials (cookies) with the request
        });

        const data = await response.json();

        if (response.status === 401 && data.redirect) {
            // Append the next parameter to the redirect URL
            const redirectUrl = new URL(data.redirect, window.location.origin);
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
    downloadButton.addEventListener('click', () => downloadDataAsCSV(data));
    document.body.appendChild(downloadButton);
}

function downloadDataAsCSV(data) {
    const csvRows = [];
    const headers = ['Artist', 'Title', 'Album', 'Length'];
    csvRows.push(headers.join(','));

    data.forEach(track => {
        const artistNames = track.artists.map(artist => artist.name).join(', ');
        const title = track.name;
        const album = track.album.name;
        const length = track.duration_ms / 1000;
        const row = [artistNames, title, album, length];
        csvRows.push(row.join(','));
    });

    const csvString = csvRows.join('\n');
    const dataStr = "data:text/csv;charset=utf-8," + encodeURIComponent(csvString);
    const downloadAnchorNode = document.createElement('a');
    downloadAnchorNode.setAttribute("href", dataStr);
    downloadAnchorNode.setAttribute("download", "unavailable_tracks.csv");
    document.body.appendChild(downloadAnchorNode); // required for firefox
    downloadAnchorNode.click();
    downloadAnchorNode.remove();
}