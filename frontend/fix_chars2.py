with open('src/pages/CommandCenter.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace common UTF-8 encoded special characters with ASCII equivalents
replacements = {
    '\xe2\x80\x94': '--',   # em dash —
    '\xe2\x80\x93': '-',    # en dash –
    '\xe2\x80\x9c': '"',    # left double quote "
    '\xe2\x80\x9d': '"',    # right double quote "
    '\xe2\x80\x98': "'",    # left single quote '
    '\xe2\x80\x99': "'",    # right single quote '
    '\xe2\x80\xa6': '...',  # ellipsis …
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open('src/pages/CommandCenter.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed!')