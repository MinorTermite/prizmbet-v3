import re

html_path = 'c:/Users/GravMix/Desktop/prizmbet-v2-main/frontend/index.html'
css_path = 'c:/Users/GravMix/Desktop/prizmbet-v2-main/frontend/css/base.min.css'

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

def repl_title(m):
    original = m.group(0)
    if 'aria-label' in original:
        return original
    title = m.group(1)
    return original.replace('title=', f'aria-label="{title}" title=')

html = re.sub(r'<button[^>]+title=\"([^\"]+)\"[^>]*>', repl_title, html)
html = re.sub(r'(<button class="modal-close"[^>]*)>', r'\1 aria-label="Закрыть">', html)
html = re.sub(r'(<button class="bet-slip-close"[^>]*)>', r'\1 aria-label="Закрыть">', html)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)

css_append = """
@media (prefers-reduced-motion: reduce) {
  *, ::before, ::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
:focus-visible {
  outline: 2px solid var(--accent-bright);
  outline-offset: 2px;
}
"""

with open(css_path, 'a', encoding='utf-8') as f:
    f.write(css_append)

print("Accessibility updates applied.")
