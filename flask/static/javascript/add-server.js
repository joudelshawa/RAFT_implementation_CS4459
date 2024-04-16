let serverCount = 0;
let serverIntervals = {};
const logUpdateIntervals = {};


document.getElementById('add-server').addEventListener('click', function () {
    const noServersText = document.getElementById('no-servers');

    addServer()

    // Hide the 'no servers' text if it's visible
    if (noServersText) {
        noServersText.style.display = 'none';
    }
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
                <div class="d-flex flex-row gap-5 pt-3 align-items-center justify-content-center">
                        <ul class="list-group list-group-horizontal list-group-radio list-unstyled gap-2 border-0">
                        <!-- Dynamically created radio buttons and labels -->
                        ${[1, 2, 3].map(num => `
                            <li class="position-relative">
                                <input class="form-check-input position-absolute top-50 end-0 me-3 fs-5" 
                                       type="radio" name="listGroupRadioGrid${serverId}" 
                                       id="listGroupRadioGrid${num}_${serverId}" 
                                       onclick="getLog(${num}, '${serverId}')">
                                <label class="list-group-item rounded-3" 
                                       for="listGroupRadioGrid${num}_${serverId}">
                                    <strong class="fw-semibold pe-4">${num === 1 ? 'Log' : num === 2 ? 'Heartbeat' : 'Output'}</strong>
                                </label>
                            </li>
                        `).join('')}

                    </ul>

                </div>
                <div data-bs-spy="scroll" data-bs-smooth-scroll="true" style="overflow: auto; display: none" 
                     tabindex="0" class="bg-body-tertiary rounded-2 mt-3" id="log-container-${serverId}">
                    <pre class="text-start mb-2 p-2 " id="server-log_${serverId}"></pre>
                </div>
                <div class="d-flex justify-content-between align-items-center mt-3">
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

    serverIntervals[serverId] = setInterval(() => checkServerStatus(serverId), 3000);

}

function checkServerStatus(serverId) {
    axios.post('/check-logs', {server_id: serverId})
        .then(response => {
            document.getElementById(`status-${serverId}`).textContent = response.data.status;
            document.getElementById(`status-${serverId}`).className = response.data.status === 'Connected' ? 'text-success' : 'text-warning';
        })
        .catch(error => {
            console.error('Error checking logs:', error);
            const statusElement = document.getElementById(`status-${serverId}`);
            statusElement.textContent = 'Error';
            statusElement.className = 'text-danger';
        });
}

function fetchLogContent(serverId, logType, serverLog) {
    axios.post('/get-log', {server_id: serverId, log_type: logType})
        .then(response => {
            serverLog.textContent = response.data.content;
        })
        .catch(error => {
            console.error('Error fetching log:', error);
            serverLog.textContent = 'Failed to fetch log data.';
        });
}

function getLog(num, serverId) {
    const logType = num === 1 ? 'log' : num === 2 ? 'heartbeat' : 'output';
    const logContainer = document.getElementById(`log-container-${serverId}`);
    const serverLog = document.getElementById(`server-log_${serverId}`);

    logContainer.style.display = 'block'; // Make the log container visible
    serverLog.textContent = 'Loading...'; // Temporary loading text

    // Clear any existing interval for this server to avoid multiple fetches
    if (logUpdateIntervals[serverId]) {
        clearInterval(logUpdateIntervals[serverId]);
    }

    // Immediately fetch log content, then start an interval to update it
    fetchLogContent(serverId, logType, serverLog);
    logUpdateIntervals[serverId] = setInterval(() => {
        fetchLogContent(serverId, logType, serverLog);
    }, 1000); // Update every 1 seconds, adjust as needed
}


function killServer(serverId) {
    document.getElementById(`status-${serverId}`).textContent = 'Killing... Please Wait';
    document.getElementById(`status-${serverId}`).className = 'text-danger'
    axios.post('/send-command', {command: "stop server " + serverId})
        .then(response => {
            // Remove the server card from the UI
            const element = document.getElementById(`server-${serverId}`);
            if (element) {
                element.parentNode.removeChild(element);
            }

            // Stop the interval for this server
            clearInterval(serverIntervals[serverId]);
            delete serverIntervals[serverId];

            if (logUpdateIntervals[serverId]) {
                clearInterval(logUpdateIntervals[serverId]);
                delete logUpdateIntervals[serverId];
            }

            // Check if there are no more servers, and show the 'no servers' text if true
            const serversContainer = document.getElementById('servers-container');
            const noServersText = document.getElementById('no-servers');
            if (!serversContainer.getElementsByClassName('server-instance').length) {
                noServersText.style.display = 'block';
            }

        })
        .catch(error => console.error('Error stopping server:', error));
}

window.killAllServers = function () {
    const serverCards = document.getElementsByClassName('server-instance');
    for (let i = 0; i < serverCards.length; i++) {
        const serverId = serverCards[i].getAttribute('data-server-id');
        killServer(serverId);
    }
}
