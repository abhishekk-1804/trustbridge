with open('src/pages/CommandCenter.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the corrupted characters
content = content.replace('\u00e2\u20ac\u201d', '--')  # em dash to double dash
content = content.replace('\u201d', '"')  # smart quote to regular quote

with open('src/pages/CommandCenter.tsx', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed!')