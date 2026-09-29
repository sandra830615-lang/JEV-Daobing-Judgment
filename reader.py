import sys
import os
import json
import csv

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

def main():
    if len(sys.argv) < 2:
        print(json.dumps({'success': False, 'error': '未提供檔案名稱'}, ensure_ascii=False))
        return
    filename = sys.argv[1]
    filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), filename)
    if not os.path.exists(filepath):
        print(json.dumps({'success': False, 'error': f'找不到檔案: {filename}'}, ensure_ascii=False))
        return
    try:
        ext = os.path.splitext(filename)[1].lower()
        if ext in ['.xlsx', '.xls']:
            rows = parse_xlsx_file(filepath)
        else:
            rows = parse_csv_file(filepath)
        print(json.dumps({'success': True, 'count': len(rows), 'filename': filename, 'rows': rows}, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({'success': False, 'error': str(e)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
