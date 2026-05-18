import zipfile
import xml.etree.ElementTree as ET
import sys

def read_docx(file_path):
    try:
        with zipfile.ZipFile(file_path) as docx:
            xml_content = docx.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            
            ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            text = []
            for paragraph in tree.findall('.//w:p', ns):
                para_text = []
                for run in paragraph.findall('.//w:r', ns):
                    t = run.find('w:t', ns)
                    if t is not None and t.text:
                        para_text.append(t.text)
                if para_text:
                    text.append(''.join(para_text))
            
            # Write to output txt
            out_path = file_path + '.txt'
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(text))
            print(f"Successfully extracted text to {out_path}")
            
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

if __name__ == '__main__':
    read_docx(sys.argv[1])
