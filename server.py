import http.server
import socketserver
import urllib.request
import urllib.error
import json
import os
import csv
import mimetypes

PORT = 3000
TARGET_API = 'https://api.typesafe.ai/v1/systemone'
FIELDS = ['Q6', 'Q7', '#10', '#11', '#12', '#13', '#14', '#15', '#16', '#17']

def parse_header_col(col):
    if col is None: return None, None
    col = str(col).strip()
    side = None
    if '左' in col or col.endswith('L') or col.startswith('L') or '左-' in col:
        side = 'left'
    elif '右' in col or col.endswith('R') or col.startswith('R') or '右-' in col:
        side = 'right'
    for f in FIELDS:
        if f in col:
            return f, side
    return None, None

def parse_csv_file(filepath):
    raw = open(filepath, 'rb').read()
    text = None
    for enc in ['utf-8-sig', 'cp950', 'big5', 'gb18030', 'latin1']:
        try:
            text = raw.decode(enc)
            break
        except Exception:
            continue
    if not text:
        raise ValueError('無法識別檔案編碼')
    
    lines = [l for l in text.splitlines() if l.strip()]
    reader = csv.reader(lines)
    header = next(reader)
    col_map = {}
    for idx, col in enumerate(header):
        f, side = parse_header_col(col)
        if f and side:
            col_map[idx] = (f, side)
            
    rows = []
    for r in reader:
        if not r or not any(r): continue
        name = str(r[0]).strip()
        data = {}
        for idx, (f, side) in col_map.items():
            if idx < len(r) and str(r[idx]).strip():
                try:
                    val = float(str(r[idx]).replace(',', '').strip())
                    if f not in data: data[f] = {}
                    data[f][side] = val
                except ValueError:
                    pass
        if data:
            rows.append({'name': name, 'data': data})
    return rows

def parse_xlsx_file(filepath):
    import openpyxl
    wb = openpyxl.load_workbook(filepath, data_only=True)
    sheet = wb.active
    rows_iter = list(sheet.iter_rows(values_only=True))
    if not rows_iter:
        return []
    header = rows_iter[0]
    col_map = {}
    for idx, col in enumerate(header):
        f, side = parse_header_col(col)
        if f and side:
            col_map[idx] = (f, side)
            
    result = []
    for r in rows_iter[1:]:
        if not r or not any(r): continue
        name = str(r[0]).strip() if r[0] is not None else ''
        data = {}
        for idx, (f, side) in col_map.items():
            if idx < len(r) and r[idx] is not None:
                try:
                    val = float(r[idx])
                    if f not in data: data[f] = {}
                    data[f][side] = val
                except ValueError:
                    pass
        if data:
            result.append({'name': name, 'data': data})
    return result

def parse_file(filename):
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    if not os.path.exists(filepath):
        raise FileNotFoundError(f'找不到檔案: {filename}')
    ext = os.path.splitext(filename)[1].lower()
    if ext in ['.xlsx', '.xls']:
        return parse_xlsx_file(filepath)
    else:
        return parse_csv_file(filepath)

class ProxyHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        if self.path == '/api/list-local-files':
            current_dir = os.path.dirname(os.path.abspath(__file__))
            files = []
            for f in os.listdir(current_dir):
                if f.lower().endswith(('.csv', '.xlsx', '.tsv')):
                    files.append(f)
            files.sort()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps({'files': files}, ensure_ascii=False).encode('utf-8'))
            return
            
        if self.path == '/' or self.path == '':
            self.path = '/JEV刀柄判斷系統.html'
        return super().do_GET()

    def do_POST(self):
        # 1. 本機檔案 Python 讀取 API
        if self.path == '/api/read-local-file':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8')
            try:
                params = json.loads(body)
                filename = params.get('filename')
                if not filename:
                    raise ValueError('未提供檔名')
                rows = parse_file(filename)
                resp_data = {'success': True, 'count': len(rows), 'filename': filename, 'rows': rows}
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(resp_data, ensure_ascii=False).encode('utf-8'))
            except Exception as e:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'success': False, 'error': str(e)}, ensure_ascii=False).encode('utf-8'))
            return

        # 2. JEV 雲端轉發 API
        if self.path == '/api/jev':
            content_length = int(self.headers.get('Content-Length', 0))
            body_bytes = self.rfile.read(content_length)
            try:
                # 確保包含 model 參數
                body_json = json.loads(body_bytes.decode('utf-8'))
                if not body_json.get('model'):
                    body_json['model'] = 'jev-latest'
                forward_bytes = json.dumps(body_json).encode('utf-8')

                req = urllib.request.Request(TARGET_API, data=forward_bytes, method='POST')
                req.add_header('Content-Type', 'application/json')
                auth = self.headers.get('Authorization')
                if auth:
                    req.add_header('Authorization', auth)

                with urllib.request.urlopen(req) as response:
                    res_body = response.read()
                    self.send_response(response.status)
                    self.send_header('Content-Type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(res_body)
            except urllib.error.HTTPError as e:
                err_body = e.read()
                self.send_response(e.code)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(err_body)
            except Exception as err:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({'error': f'Python Proxy Error: {str(err)}'}, ensure_ascii=False).encode('utf-8'))
            return

        self.send_response(404)
        self.end_headers()

if __name__ == '__main__':
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(('', PORT), ProxyHandler) as httpd:
        print(f'========================================================')
        print(f'  JEV Python 地端服務已啟動: http://localhost:{PORT}')
        print(f'  支援自動讀取公司加密檔案 (.csv / .xlsx)')
        print(f'========================================================')
        httpd.serve_forever()
