import os,sys,queue,threading,traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from core import WinscpTransport,UploadError,validate_folder,validate_connection,validate_name
from selection import collect_folder,collect_zip,destination
import settings

ROOT=(Path(getattr(sys,'_MEIPASS')) if getattr(sys,'frozen',False) else Path(__file__).resolve().parent.parent)
TRANSPORT=WinscpTransport(ROOT/'WinSCP'/'WinSCP.com')
RED='#b42332'; BG='#f6f7f9'
class Base(tk.Tk):
 def __init__(self,title):
  super().__init__();self.title(title);self.geometry('740x620');self.minsize(640,470);self.configure(bg=BG)
  self.q=queue.Queue();self.busy=False
  try:self.iconbitmap(str(ROOT/'assets'/('admin.ico' if 'Администратор' in title else 'upload.ico')))
  except (OSError,tk.TclError):pass
  self.protocol('WM_DELETE_WINDOW',self.destroy)
  self.after(100,self.poll)
  self.main=ttk.Frame(self,padding=20);self.main.pack(fill='both',expand=True)
  style=ttk.Style();style.theme_use('clam');style.configure('TButton',font=('Segoe UI',11),padding=10);style.configure('TLabel',font=('Segoe UI',10));style.configure('TEntry',font=('Segoe UI',11));style.configure('Heading.TLabel',font=('Segoe UI',17,'bold'))
  self.status=tk.StringVar(value='Готово')
  ttk.Label(self,textvariable=self.status,background=BG,wraplength=650).pack(fill='x',padx=20,pady=8)
 def launch(self,job,done):
  if self.busy:return
  self.busy=True;self.status.set('Выполняется операция…')
  def task():
   try: self.q.put((done,job(),None))
   except Exception as e:self.q.put((done,None,str(e)))
  threading.Thread(target=task,daemon=True).start()
 def poll(self):
  try:
   while True:
    done,result,error=self.q.get_nowait();self.busy=False
    if error:self.status.set('Ошибка: '+error[:250]);messagebox.showerror('Ошибка',error[:1000])
    else:self.status.set('Операция выполнена');done(result)
  except queue.Empty:pass
  self.after(100,self.poll)

class Admin(Base):
 def __init__(self):
  super().__init__('РКТМ — Администратор')
  ttk.Label(self.main,text='Настройка публикации',style='Heading.TLabel').pack(anchor='w',pady=10)
  self.vars={}
  for key,label,initial in [('host','Адрес сервера',''),('user','Пользователь SFTP',''),('port','Порт','22'),('password','Пароль',''),('hostkey','Отпечаток ключа сервера',''),('folder','Каталог на сервере','/')]:
   ttk.Label(self.main,text=label).pack(anchor='w')
   v=tk.StringVar(value=initial);self.vars[key]=v
   ttk.Entry(self.main,textvariable=v,show='•' if key=='password' else '').pack(fill='x',pady=(0,7))
  bar=ttk.Frame(self.main);bar.pack(fill='x',pady=5)
  ttk.Button(bar,text='Подключиться',command=self.connect).pack(side='left')
  ttk.Button(bar,text='На уровень выше',command=self.parent_folder).pack(side='left',padx=8)
  ttk.Button(bar,text='Сохранить эту папку',command=self.save).pack(side='right')
  self.folders=tk.Listbox(self.main,font=('Segoe UI',11),height=8);self.folders.pack(fill='both',expand=True,pady=7)
  self.folders.bind('<Double-1>',self.enter_folder)
  try:
   c=settings.load()
   if c:
    for k,v in c.items():
     if k in self.vars:self.vars[k].set(v)
  except Exception:pass
 def config(self):return {k:v.get() for k,v in self.vars.items()}
 def connect(self):
  c=self.config();p=c['folder'] or '/';c['folder']=p
  try:validate_connection(c);validate_folder(p)
  except Exception as e:messagebox.showerror('Проверьте данные',str(e));return
  self.launch(lambda:TRANSPORT.list_dir(c,p),self.show_folders)
 def show_folders(self,names):
  self.folders.delete(0,'end')
  for n in names:self.folders.insert('end',n)
  self.status.set(f'Папка открыта: {self.vars["folder"].get()}')
 def enter_folder(self,event=None):
  sel=self.folders.curselection()
  if not sel:return
  parent=self.vars['folder'].get().rstrip('/')
  self.vars['folder'].set(parent+'/'+self.folders.get(sel[0]));self.connect()
 def parent_folder(self):
  p=self.vars['folder'].get().rstrip('/');self.vars['folder'].set(p.rsplit('/',1)[0] or '/');self.connect()
 def save(self):
  try:
   c=self.config();validate_connection(c);c['folder']=validate_folder(c['folder']);settings.save(c);messagebox.showinfo('Сохранено','Папка публикации закреплена')
  except Exception as e:messagebox.showerror('Ошибка',str(e))

class Upload(Base):
 def __init__(self):
  super().__init__('РКТМ — Загрузка расписания')
  ttk.Label(self.main,text='Обновление расписания',style='Heading.TLabel').pack(anchor='w',pady=10)
  try:self.cfg=settings.load()
  except Exception as e:self.cfg=None;self.status.set(str(e))
  ttk.Label(self.main,text='Папка на сайте: '+(self.cfg.get('folder','—') if self.cfg else 'не настроена')).pack(anchor='w',pady=8)
  self.entries=[];self.temps=[]
  bar=ttk.Frame(self.main);bar.pack(fill='x',pady=6)
  ttk.Button(bar,text='Выбрать HTML',command=self.pick).pack(side='left',expand=True,fill='x',padx=3)
  ttk.Button(bar,text='Добавить папку',command=self.add_folder).pack(side='left',expand=True,fill='x',padx=3)
  ttk.Button(bar,text='Добавить ZIP',command=self.add_zip).pack(side='left',expand=True,fill='x',padx=3)
  self.count=tk.StringVar(value='Выбрано файлов: 0')
  ttk.Label(self.main,textvariable=self.count).pack(anchor='w',pady=6)
  self.items=tk.Listbox(self.main,font=('Segoe UI',10))
  self.items.pack(fill='both',expand=True,pady=6)
  self.progress=ttk.Progressbar(self.main,mode='determinate',maximum=1)
  self.progress.pack(fill='x',pady=6)
  self.current=tk.StringVar(value='Ожидание выбора файлов')
  ttk.Label(self.main,textvariable=self.current,wraplength=650).pack(anchor='w',pady=5)
  self.send_button=ttk.Button(self.main,text='Опубликовать на сайте',command=self.publish)
  self.send_button.pack(fill='x',pady=8)
  self.progress_q=queue.Queue()
  self.after(100,self.progress_poll)
 def refresh(self):
  self.items.delete(0,'end')
  for local,rel in self.entries:self.items.insert('end',rel)
  self.count.set(f'Выбрано файлов: {len(self.entries)}')
 def append(self,new):
  known={rel.casefold() for _,rel in self.entries}
  for local,rel in new:
   if rel.casefold() in known:
    messagebox.showerror('Повтор имени','Повторяется файл назначения: '+rel)
    return
   known.add(rel.casefold())
  self.entries.extend(new)
  self.refresh()
 def pick(self):
  if self.busy:return
  paths=filedialog.askopenfilenames(title='Выберите HTML-файлы',filetypes=[('HTML','*.html *.htm')])
  self.append([(p,Path(p).name) for p in paths])
 def add_folder(self):
  if self.busy:return
  folder=filedialog.askdirectory(title='Выберите папку с расписанием')
  if not folder:return
  try:self.append(collect_folder(folder))
  except Exception as e:messagebox.showerror('Папка',str(e))
 def add_zip(self):
  if self.busy:return
  filename=filedialog.askopenfilename(title='Выберите ZIP с HTML',filetypes=[('ZIP','*.zip')])
  if not filename:return
  try:
   temp,files=collect_zip(filename)
   self.temps.append(temp)
   self.append(files)
  except Exception as e:messagebox.showerror('ZIP',str(e))
 def progress_poll(self):
  try:
   while True:
    kind,value=self.progress_q.get_nowait()
    if kind=='current':
     index,total,name=value
     self.progress['maximum']=total
     self.progress['value']=index-1
     self.current.set(f'Файл {index} из {total}: {name}')
    elif kind=='completed':
     self.progress['value']=value
  except queue.Empty:pass
  self.after(100,self.progress_poll)
 def publish(self):
  if self.busy:return
  if not self.cfg:messagebox.showerror('Не настроено','Обратитесь к администратору');return
  if not self.entries:messagebox.showinfo('Нет файлов','Сначала добавьте HTML-файлы');return
  try:
   validate_folder(self.cfg['folder'])
   for p,rel in self.entries:
    validate_name(Path(rel).name)
    if not Path(p).is_file():raise UploadError('Файл не найден: '+rel)
  except Exception as e:messagebox.showerror('Проверка',str(e));return
  if not messagebox.askyesno('Подтверждение',f'Опубликовать {len(self.entries)} HTML-файлов? Вложенные HTML, HTML_PREPS, HTML_AUDS будут направлены в соответствующие каталоги.'):return
  entries=list(self.entries);c=self.cfg.copy();self.progress_q=queue.Queue()
  self.progress['value']=0
  self.progress['maximum']=len(entries)
  self.send_button.state(['disabled'])
  def job():
   results=[]
   for i,(local,rel) in enumerate(entries,1):
    self.progress_q.put(('current',(i,len(entries),rel)))
    try:
     sections=rel.split('/')[:-1]
     folder=TRANSPORT.ensure_subfolders(c,c['folder'],sections)
     result=TRANSPORT.publish(c,local,folder)
    except Exception as e:
     result={'error':str(e)}
    results.append(((local,rel),result))
    self.progress_q.put(('completed',i))
   return results
  def done(results):
   self.send_button.state(['!disabled'])
   succeeded={rel for (_,rel),r in results if r.get('status')=='published'}
   self.entries=[e for e in self.entries if e[1] not in succeeded]
   self.refresh()
   ok=len(succeeded);failed=len(results)-ok
   self.current.set(f'Готово. Успешно: {ok}, ошибок: {failed}')
   self.status.set(f'Опубликовано: {ok}. Осталось в списке: {len(self.entries)}')
   errors=[f'{rel}: {r.get("error")}' for (_,rel),r in results if r.get('status')!='published']
   if errors:
    messagebox.showwarning('Итог публикации',f'Успешно: {ok}; ошибок: {failed}.\n'+'\n'.join(errors)[:1800])
   else:messagebox.showinfo('Готово',f'Все {ok} HTML-файлов опубликованы.')
  self.launch(job,done)

if __name__=='__main__':
 (Admin if '--admin' in sys.argv else Upload)().mainloop()
