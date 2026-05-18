import urllib.request, re

url = 'https://airealimboften.github.io/knowledgebuilding/index.html'
raw = urllib.request.urlopen(url).read().decode('utf-8')

# Find where script tag is relative to page-content div
script_pos = raw.find('<script>')
page_content_pos = raw.find('id="page-content"')
auth_overlay_pos = raw.find('id="auth-overlay"')

print('Script position:', script_pos)
print('auth-overlay position:', auth_overlay_pos)
print('page-content position:', page_content_pos)
print()
print('Script comes BEFORE auth-overlay?', script_pos < auth_overlay_pos)
print('Script comes BEFORE page-content?', script_pos < page_content_pos)
print()
# Print 200 chars around the script start and the body structure  
body_start = raw.find('<body>')
print('--- BODY STRUCTURE (first 1000 chars after body) ---')
print(raw[body_start:body_start+1000])
