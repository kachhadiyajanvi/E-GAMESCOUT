import re

file_path = 'web/templates/web/Admin/admin_analytics.html'

with open(file_path, 'r') as f:
    text = f.read()

# Pattern to find the progress bar divs
# <div class="h-full bg-... " style="...">
def replacer(match):
    div_start = match.group(1)
    tag_content = match.group(2)
    
    # We strip any styling that was there and replace w-[var(--progress)] with js-progress-bar
    new_class = div_start.replace('w-[var(--progress)]', '').strip()
    if 'js-progress-bar' not in new_class:
        new_class = new_class.replace('class="', 'class="js-progress-bar ')
        
    return f'{new_class}" data-width="{tag_content.strip()}%"'

# First let's do a broad regex for the lines
lines = text.split('\n')
for i, line in enumerate(lines):
    if 'class="h-full bg-gradient' in line or 'class="h-full bg-' in line:
        if 'style=' in line:
            # extract the template tag
            tag_match = re.search(r'style="[^"]*(\{\{[^}]+\}\})[^"]*"', line)
            
            if tag_match:
                tag = tag_match.group(1)
                
                # replace class
                line = re.sub(r'w-\[var\(--progress\)\]', '', line)
                line = line.replace('class="', 'class="js-progress-bar ')
                
                # remove style entirely
                line = re.sub(r'\s*style="[^"]+"', '', line)
                
                # Add data-width right before the closing bracket if it's on the same line
                if '">' in line:
                    line = line.replace('">', f'" data-width="{tag}%">')
                elif ' ' in line:
                     # Just append it
                     line += f' data-width="{tag}%"'
                lines[i] = line
        elif '--progress:' in line:
            # It might be split across lines
            pass

# Let's write a stronger regex for the whole text instead of line by line
text = '\n'.join(lines)

# Find all 
# <div class="h-full ... " style="--progress: {{ ... }}%;">
# <div class="h-full ..." style="width: {{ ... }}%">
patt = r'(<div\s+class="[^"]*h-full\s+bg-[^"]*")[^>]*style="[^"]*(\{\{[^}]+\}\})[^"]*"[^>]*>'

def re_replacer(m):
    cls = m.group(1)
    tag = m.group(2)
    cls = cls.replace('w-[var(--progress)]', '')
    if 'js-progress-bar' not in cls:
        cls = cls.replace('class="', 'class="js-progress-bar ')
    return f'{cls}" data-width="{tag}%">'

text = re.sub(patt, re_replacer, text)

# Let's fix the user's messy syntax line 48 manually just in case
text = re.sub(r'style="width--progress:\s*(\{\{.*?\}\})%', r'data-width="\1%"', text)

# JS Snippet
js = """
            // Initialize progress bars
            document.querySelectorAll('.js-progress-bar').forEach(bar => {
                const width = bar.getAttribute('data-width');
                if (width) {
                    bar.style.width = width;
                }
            });
"""
if "document.querySelectorAll('.js-progress-bar')" not in text:
    text = text.replace('// User Distribution Chart', js + '\n            // User Distribution Chart')

with open(file_path, 'w') as f:
    f.write(text)

