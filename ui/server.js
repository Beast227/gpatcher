const http = require('http');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const PORT = 3000;
const PUBLIC_DIR = path.join(__dirname, 'public');

const mimeTypes = {
    '.html': 'text/html',
    '.css': 'text/css',
    '.js': 'text/javascript',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
    '.svg': 'image/svg+xml'
};

const server = http.createServer((req, res) => {
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        res.writeHead(200);
        res.end();
        return;
    }

    const parsedUrl = new URL(req.url, `http://${req.headers.host}`);
    const pathname = parsedUrl.pathname;

    // 1. API: Server-Sent Events to stream command execution
    if (pathname === '/api/stream') {
        const cmdArgs = parsedUrl.searchParams.get('args');
        if (!cmdArgs) {
            res.writeHead(400, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ error: 'Missing args query parameter' }));
            return;
        }

        res.writeHead(200, {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive'
        });

        // Split args by space, but respect double and single quotes
        const argsArray = [];
        const regex = /"([^"]*)"|'([^']*)'|([^\s]+)/g;
        let match;
        while ((match = regex.exec(cmdArgs)) !== null) {
            argsArray.push(match[1] || match[2] || match[3]);
        }

        const scriptPath = path.join(__dirname, '..', 'gpatcher.ps1');
        const childArgs = ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', scriptPath, ...argsArray];
        
        const child = spawn('powershell.exe', childArgs, {
            cwd: path.join(__dirname, '..')
        });

        const sendEvent = (event, data) => {
            res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
        };

        child.stdout.on('data', (data) => {
            sendEvent('stdout', data.toString());
        });

        child.stderr.on('data', (data) => {
            sendEvent('stderr', data.toString());
        });

        child.on('close', (code) => {
            sendEvent('exit', { code });
            res.end();
        });

        child.on('error', (err) => {
            sendEvent('error', err.message);
            res.end();
        });

        req.on('close', () => {
            child.kill();
        });
        return;
    }

    // 2. API: Browse Folder
    if (pathname === '/api/browse-folder') {
        const title = parsedUrl.searchParams.get('title') || 'Select Folder';
        const psCommand = `
            Add-Type -AssemblyName System.Windows.Forms
            $d = New-Object System.Windows.Forms.FolderBrowserDialog
            $d.Description = "${title}"
            $d.ShowNewFolderButton = $true
            $dialogResult = $d.ShowDialog()
            if ($dialogResult -eq 'OK') {
                Write-Output $d.SelectedPath
            }
        `;

        const child = spawn('powershell.exe', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', psCommand]);
        let selectedPath = '';

        child.stdout.on('data', (data) => {
            selectedPath += data.toString();
        });

        child.on('close', (code) => {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ path: selectedPath.trim() }));
        });
        return;
    }

    // 3. API: Browse File
    if (pathname === '/api/browse-file') {
        const title = parsedUrl.searchParams.get('title') || 'Select File';
        const filter = parsedUrl.searchParams.get('filter') || 'All Files (*.*)|*.*';
        const psCommand = `
            Add-Type -AssemblyName System.Windows.Forms
            $d = New-Object System.Windows.Forms.OpenFileDialog
            $d.Title = "${title}"
            $d.Filter = "${filter}"
            $dialogResult = $d.ShowDialog()
            if ($dialogResult -eq 'OK') {
                Write-Output $d.FileName
            }
        `;

        const child = spawn('powershell.exe', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', psCommand]);
        let selectedPath = '';

        child.stdout.on('data', (data) => {
            selectedPath += data.toString();
        });

        child.on('close', (code) => {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ path: selectedPath.trim() }));
        });
        return;
    }

    // 4. API: Doctor Status
    if (pathname === '/api/doctor') {
        const scriptPath = path.join(__dirname, '..', 'gpatcher.ps1');
        const child = spawn('powershell.exe', ['-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', scriptPath, 'doctor']);
        let output = '';

        child.stdout.on('data', (data) => {
            output += data.toString();
        });

        child.stderr.on('data', (data) => {
            output += data.toString();
        });

        child.on('close', (code) => {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ code, output }));
        });
        return;
    }

    // 5. Serve Static Files
    let filePath = path.join(PUBLIC_DIR, pathname === '/' ? 'index.html' : pathname);
    const extname = path.extname(filePath);
    let contentType = mimeTypes[extname] || 'application/octet-stream';

    fs.readFile(filePath, (err, content) => {
        if (err) {
            if (err.code === 'ENOENT') {
                res.writeHead(404, { 'Content-Type': 'text/html' });
                res.end('<h1>404 Not Found</h1>', 'utf-8');
            } else {
                res.writeHead(500);
                res.end(`Server Error: ${err.code}`);
            }
        } else {
            res.writeHead(200, { 'Content-Type': contentType });
            res.end(content, 'utf-8');
        }
    });
});

server.listen(PORT, () => {
    console.log(`\n==========================================`);
    console.log(`  gpatcher UI running at: http://localhost:${PORT}`);
    console.log(`==========================================\n`);
});
