import re

file_path = 'web/templates/web/Admin/admin_analytics.html'

with open(file_path, 'r') as f:
    text = f.read()

# 1. Remove w-[var(--progress)]
text = text.replace(" w-[var(--progress)]", " js-progress-bar")

# 2. Replace style="--progress: {{...}}%;" with data-width="{{...}}%"
text = re.sub(r'style="--progress:\s*(\{\{.*?\}\})%;"', r'data-width="\1%"', text)

# 3. Replace style="width: {{...}}%" with data-width="{{...}}%" js-progress-bar class
# First, let's catch the divs
def fix_div(match):
    prefix = match.group(1)
    style_content = match.group(2)
    # Extract the template tag
    tag_match = re.search(r'(\{\{.*?\}\})', style_content)
    if not tag_match:
        return match.group(0)
    tag = tag_match.group(1)
    
    # Ensure js-progress-bar is in the class
    new_prefix = prefix
    if 'js-progress-bar' not in new_prefix:
        new_prefix = new_prefix.replace('class="', 'class="js-progress-bar ')
    
    return f'{new_prefix} data-width="{tag}%"'

# Match <div class="..." style="width: ...">
text = re.sub(r'(<div\s+class="h-full[^>]*?)"\s+style="(?:width|width--progress):.*?%?;?"', fix_div, text)

# Handle the one specific to the screenshot if it's messed up
# style="width--progress: {{ player_conversion }}%"
text = text.replace('style="width--progress:', 'style="width:')
text = re.sub(r'(<div\s+class="h-full[^>]*?)"\s+style="width:\s*\{\{.*?\}\}%?"', fix_div, text)

# 4. In case there is an existing one that got missed, let's do a more robust pass.
# Find any <div class="h-full ...">...
lines = text.split('\n')
for i, line in enumerate(lines):
    if 'class="h-full bg-' in line and 'style="' in line:
        # It's an inline style progress bar
        tag_match = re.search(r'(\{\{[^}]+\}\})', line)
        if tag_match:
            tag = tag_match.group(1)
            # Remove style attribute
            line = re.sub(r'\s*style="[^"]+"', '', line)
            # Add data-width
            line = line.replace('class="', 'class="js-progress-bar ')
            line = line.replace('">', f'" data-width="{tag}%">')
            lines[i] = line

text = '\n'.join(lines)

# 5. Add the JS snippet at the end if not present
js_snippet = """
            // Initialize progress bars
            document.querySelectorAll('.js-progress-bar').forEach(bar => {
                const width = bar.getAttribute('data-width');
                if (width) {
                    bar.style.width = width;
                }
            });
"""
if "document.querySelectorAll('.js-progress-bar')" not in text:
    text = text.replace('// User Distribution Chart', js_snippet + '\n            // User Distribution Chart')

with open(file_path, 'w') as f:
    f.write(text)

print("Done")
