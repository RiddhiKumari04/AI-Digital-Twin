lines = open('frontend/app.py', encoding='utf-8', errors='replace').readlines()
hits = [(i+1, l.rstrip()) for i, l in enumerate(lines) if 'BACKEND_URL' in l or 'requests.' in l]
with open('/tmp/api_calls.txt', 'w', encoding='utf-8') as f:
    for ln, text in hits:
        f.write(f'{ln}|{text}\n')
print(f"Found {len(hits)} lines")
