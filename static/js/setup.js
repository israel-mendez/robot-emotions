let currentStep = 1;
let selectedPort = null;
let isSimulated = false;

function setStepStatus(stepNum, statusText, badgeClass) {
    const badge = document.getElementById(`badge-step-${stepNum}`);
    if (badge) {
        badge.innerText = statusText;
        badge.className = `status-badge ${badgeClass}`;
    }
}

function unlockStep(stepNum) {
    const stepEl = document.getElementById(`step-${stepNum}`);
    if (stepEl) {
        stepEl.classList.remove('locked');
        stepEl.classList.add('active');
        setStepStatus(stepNum, 'Ready', 'badge-pending');
    }
}

function completeStep(stepNum) {
    const stepEl = document.getElementById(`step-${stepNum}`);
    if (stepEl) {
        stepEl.classList.remove('active');
        stepEl.classList.add('completed');
        setStepStatus(stepNum, 'Completed', 'badge-success');
    }
}

function completeStep1() {
    completeStep(1);
    unlockStep(2);
    scanPorts();
}

async function scanPorts() {
    const consoleBox = document.getElementById('port-console');
    const selectBox = document.getElementById('port-select');
    consoleBox.innerText = 'Scanning USB serial ports...';

    try {
        const res = await fetch('/api/ports');
        const data = await res.json();
        selectBox.innerHTML = '';

        if (!data.ports || data.ports.length === 0) {
            selectBox.innerHTML = '<option value="">No COM ports detected</option>';
            consoleBox.innerText = 'No COM ports detected. Plug in your VEX Brain or click "Use Simulation Mode".';
            return;
        }

        data.ports.forEach(p => {
            const opt = document.createElement('option');
            opt.value = p.port || p.device;
            opt.textContent = `${p.port || p.device} - ${p.description || 'Serial Device'}`;
            selectBox.appendChild(opt);
        });

        consoleBox.innerText = `Found ${data.ports.length} port(s). Select your VEX IQ port and click "Connect Port".`;
    } catch (err) {
        consoleBox.innerText = `Error scanning ports: ${err.message}`;
    }
}

async function connectPort() {
    const selectBox = document.getElementById('port-select');
    const consoleBox = document.getElementById('port-console');
    const port = selectBox.value;

    if (!port) {
        consoleBox.innerText = 'Please select a valid COM port from the list.';
        return;
    }

    consoleBox.innerText = `Connecting to ${port} at 115200 baud...`;

    try {
        const res = await fetch('/api/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ port })
        });
        const data = await res.json();

        if (data.status === 'success' || data.status === 'connected') {
            selectedPort = port;
            isSimulated = false;
            consoleBox.innerText = `Successfully connected to ${port}!`;
            completeStep(2);
            unlockStep(3);
        } else {
            consoleBox.innerText = `Connection failed: ${data.message || 'Unknown error'}`;
        }
    } catch (err) {
        consoleBox.innerText = `Network/Server error: ${err.message}`;
    }
}

function enableSimulationMode() {
    const consoleBox = document.getElementById('port-console');
    isSimulated = true;
    selectedPort = 'SIMULATOR';
    consoleBox.innerText = 'Simulation Mode enabled. Hardware commands will be emulated.';
    completeStep(2);
    unlockStep(3);
}

async function testPing() {
    const consoleBox = document.getElementById('ping-console');
    consoleBox.innerText = 'Sending ping command to robot...';

    try {
        const res = await fetch('/api/command', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ command: 'ping' })
        });
        const data = await res.json();

        if (data.status === 'success') {
            consoleBox.innerText = `Handshake verified! Reply: ${data.reply || 'PONG_OK'}`;
            completeStep(3);
            unlockStep(4);
        } else {
            consoleBox.innerText = `Ping failed: ${data.message || 'No response'}`;
        }
    } catch (err) {
        consoleBox.innerText = `Error sending ping: ${err.message}`;
    }
}