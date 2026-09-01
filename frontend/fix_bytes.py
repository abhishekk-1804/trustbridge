with open('src/pages/CommandCenter.tsx', 'rb') as f:
    content = f.read()

# Replace common UTF-8 encoded special characters with ASCII equivalents
replacements = {
    b'\xe2\x80\x94': b'--',   # em dash —
    b'\xe2\x80\x93': b'-',    # en dash –
    b'\xe2\x80\x9c': b'"',    # left double quote "
    b'\xe2\x80\x9d': b'"',    # right double quote "
    b'\xe2\x80\x98': b"'",    # left single quote '
    b'\xe2\x80\x99': b"'",    # right single quote '
    b'\xe2\x80\xa6': b'...',  # ellipsis …
}

for old, new in replacements.items():
    content = content.replace(old, new)

with open('src/pages/CommandCenter.tsx', 'wb') as f:
    f.write(content)

print('Fixed!')