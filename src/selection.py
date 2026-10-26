"""Collect HTML for upload without executing archives or trusting archive paths."""
from pathlib import Path, PurePosixPath
from zipfile import ZipFile, BadZipFile
import tempfile

SECTIONS={'HTML','HTML_PREPS','HTML_AUDS'}
MAX_FILES=1000
MAX_SINGLE=20*1024*1024
MAX_TOTAL=150*1024*1024

def destination(name):
    pieces=[p for p in name.replace('\\','/').split('/') if p]
    if not pieces or any(p in ('.','..') for p in pieces):
        raise ValueError('Некорректный путь в архиве')
    if not pieces[-1].lower().endswith(('.html','.htm')):
        return None
    if len(pieces[-1])>180 or any(ord(x)<32 for x in pieces[-1]):
        raise ValueError('Недопустимое имя файла')
    sections=[p for p in pieces[:-1] if p in SECTIONS]
    if sections:
        return sections[-1]+'/'+pieces[-1]
    if len(pieces)==1:
        return pieces[-1]
    # Unknown folder layouts cannot be mapped safely: reject instead of guessing.
    return None

def collect_folder(folder):
    base=Path(folder)
    if not base.is_dir():raise ValueError('Папка не найдена')
    result=[]
    for p in sorted(base.rglob('*')):
        if not p.is_file() or p.is_symlink():continue
        rel=p.relative_to(base).as_posix()
        if base.name in SECTIONS:rel=base.name+'/'+rel
        target=destination(rel)
        if target:
            if p.stat().st_size>MAX_SINGLE:raise ValueError('HTML слишком большой')
            result.append((str(p),target))
        if len(result)>MAX_FILES:raise ValueError('Слишком много HTML-файлов')
    return result

def collect_zip(archive):
    temp=tempfile.TemporaryDirectory(prefix='rktm-html-')
    result=[]
    try:
        with ZipFile(archive) as z:
            total=0
            for info in z.infolist():
                if info.is_dir():continue
                target=destination(info.filename)
                if not target:continue
                if info.file_size>MAX_SINGLE:raise ValueError('Слишком большой HTML-файл в ZIP')
                total+=info.file_size
                if total>MAX_TOTAL or len(result)>=MAX_FILES:
                    raise ValueError('Превышен лимит файлов архива')
                # Do not use original archive path as an extraction destination.
                output=Path(temp.name)/('f'+str(len(result))+'.html')
                with z.open(info) as src,output.open('wb') as dst:
                    copied=0
                    while True:
                        chunk=src.read(65536)
                        if not chunk:break
                        copied+=len(chunk)
                        if copied>MAX_SINGLE:raise ValueError('Слишком большой распакованный файл')
                        dst.write(chunk)
                result.append((str(output),target))
        if not result:raise ValueError('В ZIP нет подходящих HTML-файлов')
        return temp,result
    except Exception:
        temp.cleanup()
        raise
