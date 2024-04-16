document.addEventListener('DOMContentLoaded', function () {
    const toggle = document.getElementById('toggle-server-manager');
    const confirmToggleOff = document.getElementById('confirmToggleOff');
    const serverStatus = document.getElementById('server-status');
    const inputField = document.getElementById('inputField');
    const addServer = document.getElementById('add-server');
    const showOutputBtn = document.getElementById('show-output');
    let lastCheckedState = toggle.checked;

    function updateUI(isOn) {
        serverStatus.textContent = isOn ? 'Manager Process Is Running' : 'Manager Process Is Not Running';
        serverStatus.className = isOn ? 'text-success' : 'text-danger';
        inputField.disabled = !isOn;
        addServer.disabled = !isOn;
        toggle.checked = isOn;
        showOutputBtn.style.display = isOn ? 'block' : 'none';
    }

    updateUI(toggle.checked);

    toggle.addEventListener('click', function (event) {
        if (toggle.checked !== lastCheckedState) {
            if (!toggle.checked) {
                event.preventDefault();
                var modal = new bootstrap.Modal(document.getElementById('confirmationModal'));
                modal.show();
            } else {
                axios.post('/toggle-server-manager', {status: 'on'})
                    .then(response => {
                        console.log(response.data.message);
                        lastCheckedState = true;
                        updateUI(true);
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        toggle.checked = false; // Reset toggle to off if the request fails
                        updateUI(false);
                    });
            }
        }
    });

    confirmToggleOff.addEventListener('click', function () {
        console.log('Confirming toggle off');
        axios.post('/toggle-server-manager', {status: 'off'})
            .then(response => {
                console.log(response.data.message);
                lastCheckedState = false;
                updateUI(false);
                var modal = bootstrap.Modal.getInstance(document.getElementById('confirmationModal'));
                modal.hide();
            })
            .catch(error => {
                console.error('Error:', error);
                toggle.checked = true; // Keep toggle on if the request fails
                lastCheckedState = true;
                updateUI(true);
            });
    });
});