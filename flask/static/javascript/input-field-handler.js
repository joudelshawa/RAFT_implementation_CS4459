document.getElementById('inputField').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') {
        axios.post('/send-command', {command: 'input ' + this.value})
            .then(response => {
                console.log('Command sent:', this.value);
                this.value = '';  // Clear the input field after sending the command
            })
            .catch(error => console.error('Error:', error));
    }
});