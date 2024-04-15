let serverCount = 0;

document.getElementById('add-server').addEventListener('click', function () {
    const noServersText = document.getElementById('no-servers');

    addServer()

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

function addServer() {
    serverCount++; // Increment to get a unique ID for the new server
    const serverId = serverCount; // Local variable to use in the template literal

    // HTML block for the server with dynamic IDs
    const serverHTML = `
    <div class="col" id="server-${serverId}">
        <div class="card shadow-sm">
            <div class="card-body text-center">
                <h2 class="text-center">Server ${serverId}</h2>
                <span id="status-${serverId}" class="text-warning">Connecting...</span>
                <div class="d-flex flex-column flex-md-row gap-4 py-md-3 align-items-center justify-content-center">
                    <div class="list-group list-group-radio d-grid gap-2 border-0">
                        <!-- Dynamically created radio buttons and labels -->
                        ${[1, 2, 3].map(num => `
                            <div class="position-relative">
                                <input class="form-check-input position-absolute top-50 end-0 me-3 fs-5" 
                                       type="radio" name="listGroupRadioGrid${serverId}" 
                                       id="listGroupRadioGrid${num}_${serverId}" 
                                       onclick="getLog(${num}, '${serverId}')">
                                <label class="list-group-item rounded-3" 
                                       for="listGroupRadioGrid${num}_${serverId}">
                                    <strong class="fw-semibold">${num === 1 ? 'Server Logs' : num === 2 ? 'Heartbeat Log' : 'Output Log'}</strong>
                                </label>
                            </div>
                        `).join('')}
                        <div data-bs-spy="scroll" data-bs-smooth-scroll="true" class="bg-body-tertiary p-3 rounded-2" tabindex="0">
                        <pre class="text-start" id="server-log_${serverId}"></pre>
                        </div>
                    </div>
                </div>
                <div class="d-flex justify-content-between align-items-center">
                    <div class="btn-group">
                        <button type="button" class="btn btn-sm btn-danger" onclick="killServer(${serverId})">Kill Server</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    `;

    const serversContainer = document.getElementById('servers-container');

    const div = document.createElement('div');
    div.className = 'server-instance';
    div.innerHTML = serverHTML;

    // Append the new server HTML to a container div
    serversContainer.appendChild(div);

    axios.post('/start-server', {server_id: serverId})
        .then(response => console.log('Server started:', response.data.message))
        .catch(error => console.error('Error starting server:', error));

    setInterval(() => checkServerStatus(serverId), 3000)
}

function checkServerStatus(serverId) {
    axios.post('/check-logs', {server_id: serverId})
        .then(response => {
            document.getElementById(`status-${serverId}`).textContent = response.data.status;
            document.getElementById(`status-${serverId}`).className = response.data.status === 'Connected' ? 'text-success' : 'text-danger';
        })
        .catch(error => {
            console.error('Error checking logs:', error);
            const statusElement = document.getElementById(`status-${serverId}`);
            statusElement.textContent = 'Error';
            statusElement.className = 'text-danger';
        });
}

function getLog(num, serverId) {
    // Determine the log type based on the radio number
    const logType = num === 1 ? 'log' : num === 2 ? 'heartbeat' : 'output'

    // Fetch the log content based on the server ID and log type
    axios.post('/get-log', {server_id: serverId, log_type: logType})
        .then(response => {
            document.getElementById(`server-log_${serverId}`).textContent = response.data.content;
        })
        .catch(error => console.error('Error fetching log:', error));
}

function killServer(serverId) {
    // Additional functionality to kill the server
    console.log('Kill server:', serverId);
    // Optionally remove the server div
    document.getElementById(`server-${serverId}`).remove();
}
