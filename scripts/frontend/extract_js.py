import os
import re

html_path = 'c:/Users/GravMix/Desktop/prizmbet-v2-main/frontend/index.html'
js_path = 'c:/Users/GravMix/Desktop/prizmbet-v2-main/frontend/js/app.js'

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

script_match = re.search(r'<script>\s*(.*?)\s*</script>\s*</body>', html, flags=re.DOTALL | re.IGNORECASE)

if script_match:
    os.makedirs(os.path.dirname(js_path), exist_ok=True)
    with open(js_path, 'w', encoding='utf-8') as f:
        f.write(script_match.group(1).strip() + '\n')
    
    html = html.replace(script_match.group(0), '<script src="js/app.js" defer></script>\n</body>')
    html = html.replace('<script src="api.js"></script>', '<script src="api.js" defer></script>')
    html = html.replace('<script src="tests.js"></script>', '<script src="tests.js" defer></script>')
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print("JS extracted successfully.")
else:
    print("Could not find inline script matching pattern.")
