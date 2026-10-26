import os,sys,queue,threading,traceback
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from core import WinscpTransport,UploadError,validate_folder,validate_connection,validate_name
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
  ttk.Label(self.main,text='Папка на сайте: '+(self.cfg.get('folder','—') if self.cfg else 'не настроена')).pack(anchor='w',pady=10)
  self.paths=[]
  ttk.Button(self.main,text='Выбрать HTML-файлы',command=self.pick).pack(fill='x',pady=6)
  self.items=tk.Listbox(self.main,font=('Segoe UI',11));self.items.pack(fill='both',expand=True,pady=10)
  ttk.Button(self.main,text='Опубликовать на сайте',command=self.publish).pack(fill='x',pady=8)
 def pick(self):
  paths=filedialog.askopenfilenames(title='Выбрать HTML-файлы',filetypes=[('HTML','*.html *.htm')])
  self.paths=list(paths);self.items.delete(0,'end')
  for p in self.paths:self.items.insert('end',Path(p).name)
 def publish(self):
  if not self.cfg:messagebox.showerror('Не настроено','Обратитесь к администратору');return
  if not self.paths:messagebox.showinfo('Нет файлов','Сначала выберите HTML-файлы');return
  try:
   for p in self.paths:validate_name(Path(p).name)
   names=[Path(p).name.lower() for p in self.paths]
   if len(names)!=len(set(names)):raise UploadError('Есть файлы с одинаковым именем')
  except Exception as e:messagebox.showerror('Проверка',str(e));return
  if not messagebox.askyesno('Подтверждение',f'Заменить {len(self.paths)} файлов на сайте в папке {self.cfg["folder"]}?'):return
  paths=list(self.paths);c=self.cfg.copy()
  def job():
   results=[]
   for p in paths:
    try:results.append((Path(p).name,TRANSPORT.publish(c,p,c['folder'])))
    except Exception as e:results.append((Path(p).name,{'error':str(e)}))
   return results
  def done(results):
   lines=[f'{n}: '+('опубликован' if r.get('status')=='published' else 'ОШИБКА — '+r.get('error','')) for n,r in results]
   messagebox.showinfo('Результат публикации','\n'.join(lines)[:3000])
  self.launch(job,done)

if __name__=='__main__':
 (Admin if '--admin' in sys.argv else Upload)().mainloop()
