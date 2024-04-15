document.addEventListener('DOMContentLoaded', function () {
    const showOutputBtn = document.getElementById('show-output');
    const serverOutput = document.getElementById('serverOutput');

    showOutputBtn.addEventListener('click', function () {
        axios.get('/get-output')
            .then(response => {
                serverOutput.textContent = response.data.output.join('');  // Join array into a single string
                new bootstrap.Modal(document.getElementById('outputModal')).show();
            })
            .catch(error => console.error('Error:', error));
    });
});
