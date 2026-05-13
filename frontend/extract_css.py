import os

file_path = r"c:\Users\GravMix\Desktop\prizmbet-v2-main\frontend\index.html"
css_path = r"c:\Users\GravMix\Desktop\prizmbet-v2-main\frontend\css\base.css"

with open(file_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

style_start = -1
style_end = -1
for i, line in enumerate(lines):
    if "<style>" in line and style_start == -1:
        style_start = i
    if "</style>" in line and style_end == -1:
        style_end = i

if style_start != -1 and style_end != -1:
    css_lines = lines[style_start+1:style_end]
    
    os.makedirs(os.path.dirname(css_path), exist_ok=True)
    with open(css_path, "w", encoding="utf-8") as f:
        f.writelines(css_lines)

    link_tags = '    <link rel="preload" href="css/base.css" as="style">\n    <link rel="stylesheet" href="css/base.css">\n'
    new_lines = lines[:style_start] + [link_tags] + lines[style_end+1:]
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    print("CSS extracted successfully")
else:
    print("Could not find <style> or </style> tags")
