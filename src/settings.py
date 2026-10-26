"""DPAPI CurrentUser secrets. This means two apps must run as same Windows user."""
import sys, json, ctypes, base64, os
from pathlib import Path
from ctypes import wintypes
from core import UploadError
APP=Path(os.environ.get('APPDATA',str(Path.home()))) / 'RKTM-Rebuild'
CFG=APP/'config.json'

class BLOB(ctypes.Structure):
    _fields_=[('cbData',wintypes.DWORD),('pbData',ctypes.POINTER(ctypes.c_byte))]

def _crypt(data, decrypt):
    if sys.platform!='win32': raise UploadError('Хранилище DPAPI поддерживается только Windows')
    raw=ctypes.create_string_buffer(data)
    inp=BLOB(len(data),ctypes.cast(raw,ctypes.POINTER(ctypes.c_byte)))
    out=BLOB()
    fn=ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    if decrypt:
        ok=fn(ctypes.byref(inp),None,None,None,None,0,ctypes.byref(out))
    else:
        ok=fn(ctypes.byref(inp),None,None,None,None,0,ctypes.byref(out))
    if not ok: raise UploadError('Не удалось защитить/расшифровать пароль Windows')
    try: return ctypes.string_at(out.pbData,out.cbData)
    finally: ctypes.windll.kernel32.LocalFree(out.pbData)

def save(c):
    APP.mkdir(parents=True,exist_ok=True)
    d={k:c.get(k,'') for k in ('host','user','port','hostkey','folder')}
    d['protected']=base64.b64encode(_crypt(c['password'].encode(),False)).decode()
    tmp=CFG.with_suffix('.tmp');tmp.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(CFG)

def load():
    if not CFG.exists(): return None
    d=json.loads(CFG.read_text(encoding='utf-8'))
    d['password']=_crypt(base64.b64decode(d.pop('protected')),True).decode()
    return d
