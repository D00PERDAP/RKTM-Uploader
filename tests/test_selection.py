import sys,zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pytest
from selection import destination,collect_folder,collect_zip

def test_routes():
 assert destination('HTML/1.html')=='1.html'
 assert destination('Для сайта/HTML_PREPS/m1.htm')=='m1.htm'
 assert destination('HTML_AUDS/a.html')=='a.html'
 assert destination('readme.txt') is None

def test_folder(tmp_path):
 p=tmp_path/'HTML';p.mkdir()
 (p/'1.html').write_text('<html>1</html>')
 (p/'x.txt').write_text('ignore')
 assert [x[1] for x in collect_folder(p)]==['1.html']

def test_zip_html_only(tmp_path):
 p=tmp_path/'test.zip'
 with zipfile.ZipFile(p,'w') as z:
  z.writestr('Для сайта/HTML/1.html',b'<html>test</html>')
  z.writestr('Для сайта/HTML_PREPS/m1.html',b'<html>teach</html>')
  z.writestr('extra.txt',b'ignored')
 temp,items=collect_zip(p)
 try:
  assert [rel for _,rel in items]==['1.html','m1.html']
  assert all(Path(local).is_file() for local,_ in items)
 finally:temp.cleanup()

def test_zip_traversal(tmp_path):
 p=tmp_path/'bad.zip'
 with zipfile.ZipFile(p,'w') as z:z.writestr('../HTML/1.html','test')
 with pytest.raises(ValueError):collect_zip(p)
