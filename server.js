const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 3000;
const TARGET_API = 'https://api.typesafe.ai/v1/systemone';

const MIME_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.csv': 'text/csv; charset=utf-8',
    '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
};

const server = http.createServer(async (req, res) => {
    // 允許 CORS
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type, Authorization');

    if (req.method === 'OPTIONS') {
        res.writeHead(204);
        res.end();
        return;
    }

    const url = new URL(req.url, `http://${req.headers.host}`);

    // JEV API 代理轉發
    if (url.pathname === '/api/jev' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', async () => {
            try {
                const headers = { 'Content-Type': 'application/json' };
                if (req.headers['authorization']) {
                    headers['Authorization'] = req.headers['authorization'];
                }

                // 確保包含必要欄位 model
                let payload = body;
                try {
                    const parsed = JSON.parse(body);
                    if (!parsed.model) parsed.model = 'jev-latest';
                    payload = JSON.stringify(parsed);
                } catch (e) {}

                const response = await fetch(TARGET_API, {
                    method: 'POST',
                    headers: headers,
                    body: payload
                });

                const data = await response.text();
                res.writeHead(response.status, { 'Content-Type': 'application/json; charset=utf-8' });
                res.end(data);
            } catch (err) {
                res.writeHead(500, { 'Content-Type': 'application/json; charset=utf-8' });
                res.end(JSON.stringify({ error: 'Proxy error: ' + err.message }));
            }
        });
        return;
    }

    // 列出本機目錄下的 CSV / XLSX
    if (url.pathname === '/api/list-local-files' && req.method === 'GET') {
        const files = fs.readdirSync(__dirname).filter(f => {
            const ext = path.extname(f).toLowerCase();
            return ext === '.csv' || ext === '.xlsx' || ext === '.tsv';
        });
        res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ files }));
        return;
    }

    // 使用公司 Python 讀取並解密本地檔案
    if (url.pathname === '/api/read-local-file' && req.method === 'POST') {
        let body = '';
        req.on('data', chunk => { body += chunk; });
        req.on('end', () => {
            try {
                const { filename } = JSON.parse(body);
                const { execFile } = require('child_process');
                execFile('python', [path.join(__dirname, 'reader.py'), filename], { encoding: 'utf-8' }, (error, stdout, stderr) => {
                    if (error) {
                        res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
                        res.end(JSON.stringify({ success: false, error: stderr || error.message }));
                        return;
                    }
                    res.writeHead(200, { 'Content-Type': 'application/json; charset=utf-8' });
                    res.end(stdout);
                });
            } catch (err) {
                res.writeHead(400, { 'Content-Type': 'application/json; charset=utf-8' });
                res.end(JSON.stringify({ success: false, error: err.message }));
            }
        });
        return;
    }

    // 靜態檔案服務
    let reqPath = decodeURIComponent(url.pathname);
    if (reqPath === '/' || reqPath === '') reqPath = '/JEV刀柄判斷系統.html';
    const filePath = path.join(__dirname, reqPath);

    fs.readFile(filePath, (err, content) => {
        if (err) {
            res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8' });
            res.end('File Not Found');
            return;
        }
        const ext = path.extname(filePath).toLowerCase();
        res.writeHead(200, { 'Content-Type': MIME_TYPES[ext] || 'application/octet-stream' });
        res.end(content);
    });
});

server.listen(PORT, () => {
    console.log(`JEV 本機代理伺服器已啟動: http://localhost:${PORT}`);
    console.log(`開啟系統首頁: http://localhost:${PORT}/JEV刀柄判斷系統.html`);
});
