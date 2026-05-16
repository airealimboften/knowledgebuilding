# -*- coding: utf-8 -*-
"""重新生成已有的故事页面（加入密码门和Giscus）"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config, html_builder

stories_dir = config.STORIES_DIR
for filename in sorted(os.listdir(stories_dir)):
    if not filename.endswith('.html'):
        continue
    filepath = os.path.join(stories_dir, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    parts = filename.replace('.html', '').split('_', 1)
    num = int(parts[0])
    name = parts[1] if len(parts) > 1 else '?'

    field_match = re.search(r'class="field-tag[^"]*">([^<]+)</span>', content)
    field = field_match.group(1).strip() if field_match else '?'

    date_match = re.search(r'datetime="(\d{4}-\d{2}-\d{2})"', content)
    date_str = date_match.group(1) if date_match else '2026-05-15'

    body_match = re.search(r'<section class="fable-body[^"]*">(.*?)</section>', content, re.DOTALL)
    fable_content = body_match.group(1).strip() if body_match else ''

    new_html = html_builder.generate_story_html(
        story_number=num,
        concept_name=name,
        field=field,
        fable_content=fable_content,
        date_str=date_str,
    )
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_html)
    print(f'Regenerated: {filename}')

print('All stories regenerated with password gate + Giscus')
