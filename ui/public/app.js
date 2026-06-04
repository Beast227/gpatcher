// Active EventSource connection
let currentEventSource = null;

// Tab Configurations
const tabMeta = {
    dashboard: { title: "Dashboard", desc: "Overview of your game installations and patches." },
    create: { title: "Create Patch", desc: "Generate a delta patch bundle (.zip) between two game folders." },
    apply: { title: "Apply Patch", desc: "Upgrade a game installation using an existing patch bundle." },
    restore: { title: "Restore Backup", desc: "Revert a previously applied patch to restore original files." },
    archive: { title: "Internet Archive", desc: "Search and upload patches to Share with the community." },
    doctor: { title: "System Diagnostics", desc: "Run health diagnostic checks for required binaries." }
};

// Start when document loaded
document.addEventListener("DOMContentLoaded", () => {
    setupTabNavigation();
    setupBrowsers();
    setupForms();
    setupTerminalControls();
    runDoctorDiagnostic(true); // Initial load diagnostics
});

// Tab navigation handler
function setupTabNavigation() {
    const navItems = document.querySelectorAll(".nav-item");
    navItems.forEach(item => {
        item.addEventListener("click", () => {
            const tabId = item.getAttribute("data-tab");
            switchTab(tabId);
        });
    });
}

function switchTab(tabId) {
    // Toggle active navigation button
    document.querySelectorAll(".nav-item").forEach(btn => {
        if (btn.getAttribute("data-tab") === tabId) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    // Toggle active tab content pane
    document.querySelectorAll(".tab-content").forEach(pane => {
        if (pane.id === `tab-${tabId}`) {
            pane.classList.add("active");
        } else {
            pane.classList.remove("active");
        }
    });

    // Update Header
    const meta = tabMeta[tabId] || { title: tabId, desc: "" };
    document.getElementById("current-tab-title").textContent = meta.title;
    document.getElementById("current-tab-desc").textContent = meta.desc;

    // Custom actions per tab
    if (tabId === "doctor") {
        runDoctorDiagnostic(false);
    }
}

// Set up native Windows file/directory browser pickers
function setupBrowsers() {
    const browseButtons = document.querySelectorAll(".btn-browse");
    browseButtons.forEach(btn => {
        btn.addEventListener("click", async () => {
            const type = btn.getAttribute("data-type");
            const targetId = btn.getAttribute("data-target");
            const inputField = document.getElementById(targetId);
            
            // Set indicator status
            setSystemStatus("Opening file browser...", "busy");
            btn.disabled = true;

            try {
                let url = "";
                if (type === "folder") {
                    url = `/api/browse-folder?title=Select ${btn.closest('.form-group').querySelector('label').textContent}`;
                } else {
                    const filter = btn.getAttribute("data-filter") || "All Files (*.*)|*.*";
                    url = `/api/browse-file?title=Select File&filter=${encodeURIComponent(filter)}`;
                }

                const response = await fetch(url);
                const data = await response.json();
                
                if (data.path) {
                    inputField.value = data.path;
                }
            } catch (err) {
                console.error("Error browsing paths:", err);
                appendTerminalLine(`[system-err] Failed to browse: ${err.message}`);
            } finally {
                btn.disabled = false;
                setSystemStatus("System ready", "online");
            }
        });
    });
}

// Setup execution forms
function setupForms() {
    // Create Patch Form
    document.getElementById("form-create").addEventListener("submit", (e) => {
        e.preventDefault();
        const game = document.getElementById("create-game").value;
        const oldVer = document.getElementById("create-old-ver").value;
        const newVer = document.getElementById("create-new-ver").value;
        const oldDir = document.getElementById("create-old-dir").value;
        const newDir = document.getElementById("create-new-dir").value;
        const outDir = document.getElementById("create-out-dir").value;

        let args = `create --game "${game}" --old-ver "${oldVer}" --new-ver "${newVer}" --old "${oldDir}" --new "${newDir}"`;
        if (outDir) {
            args += ` --out "${outDir}"`;
        }

        executeCommand(args);
    });

    // Apply Patch Form
    document.getElementById("form-apply").addEventListener("submit", (e) => {
        e.preventDefault();
        const patch = document.getElementById("apply-patch").value;
        const target = document.getElementById("apply-target").value;
        const dryRun = document.getElementById("apply-dry-run").checked;
        const noBackup = document.getElementById("apply-no-backup").checked;
        const keepBackup = document.getElementById("apply-keep-backup").checked;

        let args = `apply --patch "${patch}" --target "${target}"`;
        if (dryRun) args += " --dry-run";
        if (noBackup) args += " --no-backup";
        if (keepBackup) args += " --keep-backup";

        executeCommand(args);
    });

    // Restore Backup Form
    document.getElementById("form-restore").addEventListener("submit", (e) => {
        e.preventDefault();
        const target = document.getElementById("restore-target").value;
        const backup = document.getElementById("restore-backup").value;
        const keepBackup = document.getElementById("restore-keep-backup").checked;

        let args = `restore --target "${target}"`;
        if (backup) args += ` --backup "${backup}"`;
        if (keepBackup) args += " --keep-backup";

        executeCommand(args);
    });

    // Upload Form
    document.getElementById("form-upload").addEventListener("submit", (e) => {
        e.preventDefault();
        const patch = document.getElementById("upload-patch").value;
        const creator = document.getElementById("upload-creator").value;
        const desc = document.getElementById("upload-desc").value;

        let args = `upload --patch "${patch}"`;
        if (creator) args += ` --creator "${creator}"`;
        if (desc) args += ` --description "${desc}"`;

        executeCommand(args);
    });

    // Search IA Button
    document.getElementById("btn-search").addEventListener("click", () => {
        const query = document.getElementById("search-query").value;
        if (!query) return;

        const resultsPanel = document.getElementById("search-results");
        resultsPanel.innerHTML = '<p class="search-results-placeholder">Searching Internet Archive database...</p>';

        let collectedOutput = "";
        executeCommand(`search "${query}"`, (line) => {
            collectedOutput += line;
        }, () => {
            // On complete, parse output
            parseSearchResults(collectedOutput);
        });
    });

    // Header Diagnostic Button
    document.getElementById("btn-run-doctor").addEventListener("click", () => {
        switchTab("doctor");
    });
}

// Parser for searching internet archive outputs
function parseSearchResults(output) {
    const resultsPanel = document.getElementById("search-results");
    resultsPanel.innerHTML = "";

    // Parse lines like: "Found: gpatcher-hades-1-0-to-1-1"
    const regex = /gpatcher-([a-zA-Z0-9\-]+)-([a-zA-Z0-9\.\-]+)-to-([a-zA-Z0-9\.\-]+)/g;
    let match;
    const items = [];

    while ((match = regex.exec(output)) !== null) {
        items.push({
            identifier: match[0],
            game: match[1].replace(/-/g, ' '),
            from: match[2],
            to: match[3]
        });
    }

    if (items.length === 0) {
        resultsPanel.innerHTML = '<p class="search-results-placeholder">No matching patch packages found on Internet Archive.</p>';
        return;
    }

    items.forEach(item => {
        const div = document.createElement("div");
        div.className = "search-item";
        div.innerHTML = `
            <div class="search-item-info">
                <h4>${capitalizeWords(item.game)}</h4>
                <p>Version ${item.from} → ${item.to}</p>
                <p style="color: var(--text-muted); font-size: 11px;">ID: ${item.identifier}</p>
            </div>
            <button class="btn btn-secondary btn-small btn-fetch-direct" data-id="${item.identifier}" data-game="${item.game}" data-from="${item.from}" data-to="${item.to}">Fetch Patch</button>
        `;
        resultsPanel.appendChild(div);
    });

    // Setup direct Fetch listeners
    document.querySelectorAll(".btn-fetch-direct").forEach(btn => {
        btn.addEventListener("click", () => {
            const id = btn.getAttribute("data-id");
            const game = btn.getAttribute("data-game");
            const from = btn.getAttribute("data-from");
            const to = btn.getAttribute("data-to");
            
            appendTerminalLine(`[system] Fetching metadata for ${game} (${from} to ${to})...`);
            
            // Auto switch to Apply Patch, configure URL as direct fetch download
            // (fetch downloaded files can be loaded via Internet Archive identifier)
            document.getElementById("apply-patch").value = `https://archive.org/download/${id}/${id}.patch.zip`;
            switchTab("apply");
        });
    });
}

function capitalizeWords(str) {
    return str.replace(/\b\w/g, c => c.toUpperCase());
}

// Doctor Diagnostic API Call
async function runDoctorDiagnostic(dashboardOnly = false) {
    const diagConsole = document.getElementById("diag-console");
    const summaryList = document.getElementById("doctor-summary-list");

    if (!dashboardOnly) {
        diagConsole.textContent = "Running diagnostic checks...";
    }
    summaryList.innerHTML = '<div class="doctor-summary-item loading">Running health checks...</div>';

    try {
        const response = await fetch("/api/doctor");
        const data = await response.json();

        if (!dashboardOnly) {
            diagConsole.textContent = data.output;
        }

        // Parse doctor output to list view
        summaryList.innerHTML = "";
        const lines = data.output.split("\n");
        let itemHtml = "";

        lines.forEach(line => {
            if (line.includes("[ok]")) {
                const text = line.replace("[ok]", "").trim();
                summaryList.innerHTML += `
                    <div class="doctor-item ok">
                        <span class="doctor-icon">✅</span>
                        <span>${text}</span>
                    </div>
                `;
            } else if (line.includes("[warn]")) {
                const text = line.replace("[warn]", "").trim();
                summaryList.innerHTML += `
                    <div class="doctor-item warn">
                        <span class="doctor-icon">⚠️</span>
                        <span>${text}</span>
                    </div>
                `;
            } else if (line.includes("[err]")) {
                const text = line.replace("[err]", "").trim();
                summaryList.innerHTML += `
                    <div class="doctor-item err">
                        <span class="doctor-icon">❌</span>
                        <span>${text}</span>
                    </div>
                `;
            }
        });

        if (summaryList.innerHTML === "") {
            summaryList.innerHTML = '<div class="doctor-item err"><span class="doctor-icon">❌</span><span>Diagnostics failed to run</span></div>';
        }

    } catch (err) {
        console.error("Error executing doctor:", err);
        if (!dashboardOnly) {
            diagConsole.textContent = `Error connecting to host process: ${err.message}`;
        }
        summaryList.innerHTML = `<div class="doctor-item err"><span class="doctor-icon">❌</span><span>Connection error: ${err.message}</span></div>`;
    }
}

// Execution stream backend connection
function executeCommand(argsString, onDataLine = null, onComplete = null) {
    // Clear terminal, set state
    const terminalBody = document.getElementById("terminal-body");
    terminalBody.innerHTML = `<div class="terminal-line system-line">[system] Launching: gpatcher ${argsString}</div>`;
    
    setSystemStatus("Executing command...", "busy");
    document.getElementById("btn-stop-execution").disabled = false;

    // Open Server-Sent Events stream connection
    const url = `/api/stream?args=${encodeURIComponent(argsString)}`;
    currentEventSource = new EventSource(url);

    currentEventSource.addEventListener("stdout", (event) => {
        const text = JSON.parse(event.data);
        const lines = text.split("\n");
        lines.forEach(line => {
            if (line.trim() === "") return;
            
            // Format color-coding based on line prefixes
            let cssClass = "stdout-line";
            if (line.includes("[info]")) cssClass = "stdout-info";
            else if (line.includes("[ok]")) cssClass = "stdout-ok";
            else if (line.includes("[warn]")) cssClass = "stdout-warn";
            else if (line.includes("[err]")) cssClass = "stdout-err";

            appendTerminalLine(line, cssClass);
            if (onDataLine) onDataLine(line);
        });
    });

    currentEventSource.addEventListener("stderr", (event) => {
        const text = JSON.parse(event.data);
        appendTerminalLine(text, "stderr-line");
    });

    currentEventSource.addEventListener("exit", (event) => {
        const data = JSON.parse(event.data);
        appendTerminalLine(`[system] Command finished with exit code ${data.code}`, "system-line");
        cleanupExecution();
        if (onComplete) onComplete();
        
        // Refresh doctor checks on completed run
        runDoctorDiagnostic(true);
    });

    currentEventSource.addEventListener("error", (event) => {
        appendTerminalLine(`[system-err] Stream connection lost or errored`, "stderr-line");
        cleanupExecution();
    });
}

function cleanupExecution() {
    if (currentEventSource) {
        currentEventSource.close();
        currentEventSource = null;
    }
    setSystemStatus("System ready", "online");
    document.getElementById("btn-stop-execution").disabled = true;
}

// Terminal helper utilities
function appendTerminalLine(text, cssClass = "system-line") {
    const terminalBody = document.getElementById("terminal-body");
    const div = document.createElement("div");
    div.className = `terminal-line ${cssClass}`;
    div.textContent = text;
    terminalBody.appendChild(div);
    terminalBody.scrollTop = terminalBody.scrollHeight;
}

function setupTerminalControls() {
    // Clear terminal
    document.getElementById("btn-clear-terminal").addEventListener("click", () => {
        document.getElementById("terminal-body").innerHTML = `<div class="terminal-line system-line">[system] Console log cleared. Ready.</div>`;
    });

    // Abort button
    document.getElementById("btn-stop-execution").addEventListener("click", () => {
        appendTerminalLine(`[system] Aborting running command...`, "stdout-warn");
        cleanupExecution();
    });
}

function setSystemStatus(text, type = "online") {
    const statusText = document.getElementById("system-status");
    const statusDot = statusText.previousElementSibling;

    statusText.textContent = text;
    statusDot.className = `status-dot ${type}`;
}
