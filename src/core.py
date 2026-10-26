"""RKTM WinSCP transport. No secrets in command-line arguments or files."""
import os, re, sys, json, time, uuid, queue, subprocess, hashlib
from pathlib import Path
from urllib.parse import quote

class UploadError(Exception): pass

HOSTKEY_RE = re.compile(r'^(?:ssh-(?:ed25519|rsa)|ecdsa-sha2-[\w-]+)\s+\d+\s+SHA256:[A-Za-z0-9+/]{40,44}=?$')
NAME_RE = re.compile(r'^[^/\\\x00-\x1f\"<>|:*?]+\.html?$', re.I)


def validate_folder(p):
    if not p or not p.startswith('/') or any(x in p for x in ('\n','\r','"','\\','\x00')) or '..' in p.split('/'):
        raise UploadError('Неверный путь к папке')
    return '/' + '/'.join(x for x in p.split('/') if x)


def validate_name(n):
    if not NAME_RE.fullmatch(n) or n.startswith('.') or n in ('.','..'):
        raise UploadError('Недопустимое имя HTML-файла')
    return n


def validate_hostkey(k):
    k=k.strip()
    if k.startswith('SHA256:'):
        k='ssh-ed25519 256 '+k
    if not HOSTKEY_RE.fullmatch(k):
        raise UploadError('Проверьте отпечаток ключа SSH')
    return k


def validate_connection(c):
    h=c.get('host','').strip(); u=c.get('user','').strip()
    if not h or not re.fullmatch(r'[A-Za-z0-9.:-]+',h) or not re.fullmatch(r'[A-Za-z0-9._-]+',u):
        raise UploadError('Укажите адрес сервера и имя пользователя')
    port=int(c.get('port',22))
    if not 1<=port<=65535: raise UploadError('Неверный SSH-порт')
    validate_hostkey(c.get('hostkey',''))
    if not c.get('password'): raise UploadError('Укажите пароль')
    return h,u,port


def sanitize(message, password):
    message=message.replace(password,'[СКРЫТО]') if password else message
    return re.sub(r'(?i)(password|passwd|pass)\s*[=:]\s*\S+',r'\1=[СКРЫТО]',message)


def command_open(c):
    h,u,port=validate_connection(c)
    # WinSCP scripting commands are delivered via stdin, never process arguments.
    pwd=quote(c['password'],safe='')
    return 'open "sftp://%s:%s@%s:%d/" -hostkey="%s" -timeout=12' % (quote(u,safe=''), pwd,h,port,validate_hostkey(c['hostkey']).replace(' SHA256:', ' '))


def quote_remote(path):
    if any(x in path for x in ('\n','\r','"','\x00')): raise UploadError('Недопустимый путь')
    return '"'+path+'"'


class WinscpTransport:
    def __init__(self, exe, run=None):
        self.exe=Path(exe)
        self.run=run or self._run
    def _run(self, commands, password, timeout=25):
        if not self.exe.exists(): raise UploadError('WinSCP.com отсутствует в комплекте')
        payload='option batch abort\noption confirm off\n'+ '\n'.join(commands) +'\nexit\n'
        startup = {'args':[str(self.exe),'/ini=nul'], 'stdin':subprocess.PIPE,'stdout':subprocess.PIPE,'stderr':subprocess.STDOUT,'text':True,'encoding':'utf-8','errors':'replace', 'creationflags':getattr(subprocess,'CREATE_NO_WINDOW',0)}
        proc=subprocess.Popen(**startup)
        try: out,_=proc.communicate(payload,timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.communicate();raise UploadError('Сервер не ответил вовремя (тайм-аут)')
        clean=sanitize(out,password)
        clean=clean.replace(quote(password,safe=''),'[СКРЫТО]') if password else clean
        if proc.returncode: raise UploadError('Ошибка SFTP: '+clean[-1000:])
        return clean
    def execute(self,c, commands, timeout=25):
        return self.run([command_open(c)]+commands,c['password'],timeout)
    def list_dir(self,c,p):
        p=validate_folder(p)
        out=self.execute(c,['ls '+quote_remote(p)])
        # WinSCP ls listing: permission bit begins 'd' for directory.
        dirs=[]
        for line in out.splitlines():
            line=line.strip()
            if not re.match(r'^d[rwxstST-]{9}\s',line): continue
            # last column follows metadata; use fixed-width column splitting where possible
            seg=re.split(r'\s{2,}',line)
            name=line.split()[-1].strip()
            if name not in ('.','..') and '/' not in name and name: dirs.append(name)
        return sorted(set(dirs),key=str.casefold)
    def ensure_subfolders(self,c,base,parts):
        """Create only selected relative subfolders under the locked publishing root."""
        base=validate_folder(base)
        current=base
        for part in parts:
            if part not in ('HTML','HTML_PREPS','HTML_AUDS'):
                raise UploadError('Неизвестный раздел расписания: '+part)
            current=current.rstrip('/')+'/'+part
            # WinSCP mkdir returns an error when directory exists, so test first.
            parent=current.rsplit('/',1)[0] or '/'
            known=self.list_dir(c,parent)
            if part not in known:
                self.execute(c,['mkdir '+quote_remote(current)],timeout=30)
        return current

    def publish(self,c,local_path,folder):
        folder=validate_folder(folder)
        path=Path(local_path); name=validate_name(path.name)
        if not path.is_file(): raise UploadError('Локальный файл отсутствует')
        remote=folder.rstrip('/')+'/'+name
        temp=folder.rstrip('/')+'/.rktm-'+uuid.uuid4().hex+'.tmp'
        backup=folder.rstrip('/')+'/.rktm-backup-'+name+'-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
        # Upload to staging first. Failed staging never touches the published file.
        self.execute(c,['put -resumesupport=off '+quote_remote(str(path))+' '+quote_remote(temp)],timeout=120)
        # Confirm remote byte size via the server listing before commit.
        listing=self.execute(c,['ls '+quote_remote(folder)],timeout=30)
        if not any(temp.split('/')[-1] in ln and str(path.stat().st_size) in ln for ln in listing.splitlines()):
            raise UploadError('Размер загруженного файла не подтверждён. Исходный файл не изменён, проверьте временный файл: '+temp)
        # Determine if old version exists from a fresh listing; false positives avoided by final column match.
        existing=any(re.search(r'(^|\s)'+re.escape(name)+r'\s*$',ln) for ln in listing.splitlines())
        if existing:
            self.execute(c,['mv '+quote_remote(remote)+' '+quote_remote(backup)],timeout=30)
        try:
            self.execute(c,['mv '+quote_remote(temp)+' '+quote_remote(remote)],timeout=30)
        except Exception as e:
            if existing:
                try: self.execute(c,['mv '+quote_remote(backup)+' '+quote_remote(remote)],timeout=30)
                except Exception: raise UploadError('Публикация не подтверждена; восстановление не удалось. Обратитесь к администратору. '+str(e)) from e
            raise UploadError('Публикация не завершена, исходный файл восстановлен или не менялся. '+str(e)) from e
        return {'status':'published','target':remote,'backup':backup if existing else None,'sha256_local':hashlib.sha256(path.read_bytes()).hexdigest()}
