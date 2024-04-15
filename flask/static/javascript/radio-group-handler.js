let lastClickedRadio = null;  // Store the last clicked radio

function toggleRadio(radio, serverId) {
    let lastClickedRadio = window[`lastClickedRadio_${serverId}`]; // Use a dynamic property to track the last clicked radio
    let serverLog = document.getElementById(`server-log_${serverId}`);

    if (radio === lastClickedRadio) {
        radio.checked = false;
        radio.blur();
        serverLog.style.display = 'none';  // Hide the server log textarea when no radio is selected
        window[`lastClickedRadio_${serverId}`] = null;
    } else {
        if (lastClickedRadio) {
            lastClickedRadio.blur();
        }
        window[`lastClickedRadio_${serverId}`] = radio;
        radio.checked = true;
        serverLog.style.display = 'block';  // Show the server log textarea when a radio is selected
        updateLogContent(radio, serverId);  // Pass the server ID to updateLogContent
    }
}

function updateLogContent(radio, serverId) {
    let serverLog = document.getElementById(`server-log_${serverId}`);
    switch (radio.id) {
        case `listGroupRadioGrid1_${serverId}`:
            serverLog.value = 'Details for Server Logs...';
            break;
        case `listGroupRadioGrid2_${serverId}`:
            serverLog.value = 'Details for Heartbeat Log...';
            break;
        case `listGroupRadioGrid3_${serverId}`:
            serverLog.value = 'Details for Output Log...';
            break;
        default:
            serverLog.value = '';
    }
}

// Initial state setup for the textarea
document.addEventListener('DOMContentLoaded', function () {
    let serverLog = document.getElementById('server-log');
    let radios = document.querySelectorAll('input[type="radio"][name="listGroupRadioGrid"]');
    let anyChecked = Array.from(radios).some(radio => radio.checked);

    serverLog.style.display = anyChecked ? 'block' : 'none';  // Initial display based on radio state
    if (anyChecked) {
        let checkedRadio = Array.from(radios).find(radio => radio.checked);
        updateLogContent(checkedRadio);  // Initialize content if there's a checked radio
    }
});
