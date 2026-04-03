import google.generativeai as genai
import urllib.request, json

# --- Test Gemini ---
print("=== GEMINI MODELS ===")
try:
    genai.configure(api_key='AIzaSyAh2Tt4yiQZi_qroN4iUvIN0-cc5Ht-U7g')
    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    for m in sorted(models):
        print(m)
except Exception as e:
    print("Error listing models:", e)

print("\n=== GEMINI TEST ===")
for model in ['models/gemini-1.5-flash', 'models/gemini-1.5-flash-latest', 'models/gemini-2.0-flash', 'models/gemini-2.0-flash-exp']:
    try:
        genai.configure(api_key='AIzaSyAh2Tt4yiQZi_qroN4iUvIN0-cc5Ht-U7g')
        m = genai.GenerativeModel(model)
        r = m.generate_content('say hi')
        print(f"OK [{model}]:", r.text[:30])
        break
    except Exception as e:
        print(f"FAIL [{model}]:", str(e)[:80])

print("\n=== OPENROUTER TEST ===")
OR_KEY = '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'
for model in ['mistralai/mistral-7b-instruct:free', 'google/gemma-2-9b-it:free', 'nousresearch/hermes-3-llama-3.1-405b:free', 'huggingfaceh4/zephyr-7b-beta:free']:
    payload = json.dumps({'model': model, 'messages': [{'role': 'user', 'content': 'say hi'}], 'max_tokens': 20}).encode()
    req = urllib.request.Request(
        'https://openrouter.ai/api/v1/chat/completions', data=payload,
        headers={'Authorization': f'Bearer {OR_KEY}', 'Content-Type': 'application/json',
                 'HTTP-Referer': 'http://localhost:8501', 'X-Title': 'AI Digital Twin'},
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
            print(f"OK [{model}]:", data['choices'][0]['message']['content'][:30])
            break
    except Exception as e:
        print(f"FAIL [{model}]:", str(e)[:80])
