document.getElementById('add-server').addEventListener('click', function () {
    fetch('/load-server-content')
        .then(response => response.json())
        .then(data => {
            const contentArea = document.getElementById('content-area');
            const noServersText = document.getElementById('no-servers');

            // Create a new div for each instance
            const div = document.createElement('div');
            div.className = 'server-instance';
            div.innerHTML = data.html;

            // Append the new div to the content area
            contentArea.appendChild(div);

            // Hide the 'no servers' text if it's visible
            if (noServersText) {
                noServersText.style.display = 'none';
            }

            // Add event listener to the new "Remove" button within this div
            div.querySelector('.remove-btn').addEventListener('click', function () {
                div.remove(); // This will remove the specific div
                // Check if there are no more servers, and show the 'no servers' text if true
                if (contentArea.getElementsByClassName('server-instance').length === 0) {
                    noServersText.style.display = 'block';
                }
            });
        });
});

// Initial check to see if the 'no servers' text should be displayed
document.addEventListener('DOMContentLoaded', function () {
    const contentArea = document.getElementById('content-area');
    const noServersText = document.getElementById('no-servers');
    if (contentArea.getElementsByClassName('server-instance').length === 0) {
        noServersText.style.display = 'block';
    } else {
        noServersText.style.display = 'none';
    }
});