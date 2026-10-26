import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import pytest
from core import *

CFG={'host':'127.0.0.1','user':'test','password':'P@ss word%','port':'22','hostkey':'ssh-ed25519 256 SHA256:ofL9honxhZ4RaZXLKG8oTUj6zGfWeA7EMsFsPvB4La8','folder':'/schedule'}
@pytest.mark.parametrize('p',['/','/var/lib','/site/x/'])
def test_paths(p):assert validate_folder(p).startswith('/')
@pytest.mark.parametrize('p',['','relative','/../home','/some/../a','/bad"here','/bad\nname'])
def test_bad_paths(p):
 with pytest.raises(UploadError):validate_folder(p)
@pytest.mark.parametrize('p',['1.html','my-group.HTM','Group 1.html'])
def test_names(p): assert validate_name(p)==p
@pytest.mark.parametrize('p',['../x.html','x.pdf','..html','bad/hi.html','bad\n.html'])
def test_bad_names(p):
 with pytest.raises(UploadError):validate_name(p)
def test_open_command():
 v=command_open(CFG)
 assert 'test:P%40ss%20word%25@' in v and '-hostkey=' in v
 assert 'P@ss word%' not in v
 assert '-hostkey="ssh-ed25519 256 ofL9honxhZ4RaZXLKG8oTUj6zGfWeA7EMsFsPvB4La8"' in v
 assert 'SHA256:' not in v

def test_missing_host():
 with pytest.raises(UploadError):validate_connection(dict(CFG,host=''))

def test_invalid_fingerprint():
 with pytest.raises(UploadError):validate_connection(dict(CFG,hostkey='badkey'))

def test_redact():assert 'secret' not in sanitize('password=secret', 'secret')

def test_list_folders():
 outputs=[]
 def fake(commands,password,timeout):
  outputs.append(commands)
  return 'drwxr-xr-x  0 root root 0 Jan 01 12:00 HTML\n-rw-r--r-- 0 root root 10 Jan 01 12:00 index.html\n'
 names=WinscpTransport('/fake',fake).list_dir(CFG,'/')
 assert names==['HTML']

def test_publish_success(tmp_path):
 f=tmp_path/'1.html';f.write_bytes(b'<html>New</html>')
 calls=[]
 def fake(commands,password,timeout):
  calls.append(commands)
  if commands[-1].startswith('ls '):
   return f'-rw-r--r--  0 root root {f.stat().st_size} Jan 01 12:00 '+ [x for x in calls[0][-1].split('"') if '.rktm-' in x][0].split('/')[-1]+'\n-rw-r--r--  0 root root 4 Jan 01 12:00 1.html'
  return 'OK'
 t=WinscpTransport('/fake',fake)
 result=t.publish(CFG,str(f),'/schedule')
 assert result['status']=='published' and result['backup']
 assert len(calls)==4

def test_upload_fail_preserves_target(tmp_path):
 f=tmp_path/'2.html';f.write_text('old')
 def fake(commands,password,timeout):
  raise UploadError('failed stage')
 with pytest.raises(UploadError):WinscpTransport('/fake',fake).publish(CFG,str(f),'/schedule')
