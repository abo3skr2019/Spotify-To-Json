document.getElementById('fetchTracks').addEventListener('click', async () => {
    try {
        const response = await fetch('http://127.0.0.1:5000/unavailable_tracks', {
            credentials: 'include'  // Include credentials (cookies) with the request
        });

        const data = await response.json();

        if (response.status === 401 && data.redirect) {
            // Handle redirects by prompting the user to login
            window.location.href = data.redirect;
            return;
        }

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        displayTracks(data);
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