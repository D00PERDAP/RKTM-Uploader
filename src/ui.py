import os,sys,queue,threading,traceback
from concurrent.futures import ThreadPoolExecutor,as_completed
from pathlib import Path
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
from core import WinscpTransport,UploadError,validate_folder,validate_connection,validate_name
from selection import collect_folder,collect_zip,destination
import settings
from brand_widgets import icon,action_button,RED,YELLOW,INK,BG

ROOT=(Path(getattr(sys,'_MEIPASS')) if getattr(sys,'frozen',False) else Path(__file__).resolve().parent.parent)
TRANSPORT=WinscpTransport(ROOT/'WinSCP'/'WinSCP.com')
PANEL='#F4F4F4'
class Base(tk.Tk):
 def __init__(self,title):
  super().__init__();self.title(title);self.geometry('980x700');self.minsize(820,560);self.configure(bg=BG)
  self.q=queue.Queue();self.busy=False
  try:self.iconbitmap(str(ROOT/'assets'/('admin.ico' if 'Администратор' in title else 'upload.ico')))
  except (OSError,tk.TclError):pass
  self.protocol('WM_DELETE_WINDOW',self.destroy)
  self.after(100,self.poll)
  self.main=ttk.Frame(self,padding=20);self.main.pack(fill='both',expand=True)
  style=ttk.Style();style.theme_use('clam');style.configure('TFrame',background=BG);style.configure('TLabel',background=BG,foreground=INK,font=('Segoe UI',10));style.configure('TButton',font=('Segoe UI',11),padding=(13,11));style.map('TButton',background=[('active','#e8e9ed')]);style.configure('TEntry',font=('Segoe UI',11),padding=6);style.configure('Heading.TLabel',font=('Segoe UI',20,'bold'),foreground=INK);style.configure('Primary.TButton',font=('Segoe UI',12,'bold'),padding=(14,15),foreground='white',background=RED);style.map('Primary.TButton',background=[('active','#BD171A'),('disabled','#aab0b6')]);style.configure('Horizontal.TProgressbar',background=RED,troughcolor='#E5E4E4',thickness=14)
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
  # Brandbook desktop layout: restrained red navigation, white content area.
  shell=self.main
  sidebar=tk.Frame(shell,bg=RED,width=173)
  sidebar.pack(side='left',fill='y',padx=(0,16))
  sidebar.pack_propagate(False)
  tk.Label(sidebar,text='РКТМ',bg=RED,fg='white',font=('Segoe UI',23,'bold'),anchor='w').pack(fill='x',padx=17,pady=(24,4))
  tk.Label(sidebar,text='ЗАГРУЗЧИК\nРАСПИСАНИЙ',bg=RED,fg='white',font=('Segoe UI',9,'bold'),anchor='w',justify='left').pack(fill='x',padx=18,pady=(0,30))
  self.side_items=[]
  for name,glyph,number in (('Выбор файлов','folder',1),('Проверка','check',2),('Публикация','upload',3)):
   cell=tk.Frame(sidebar,bg=RED,cursor='hand2')
   cell.pack(fill='x',pady=2)
   picture=icon(cell,glyph,20,'white',RED);picture.pack(side='left',padx=(17,8),pady=11)
   lbl=tk.Label(cell,text=name,bg=RED,fg='white',font=('Segoe UI',10),cursor='hand2',anchor='w')
   lbl.pack(side='left',fill='x',expand=True)
   self.side_items.append((cell,lbl,picture,number))
   def navigate(n=number):
    if self.busy:return
    if n==1:self.show_stage(1)
    elif n==2:self.review()
    else:
     if self.stage_num==2:self.publish()
     else:self.review()
   for elem in (cell,lbl,picture):elem.bind('<Button-1>',lambda e,f=navigate:f())
  tk.Label(sidebar,text='© Сорокин Д. Д.',bg=RED,fg='white',font=('Segoe UI',8)).pack(side='bottom',pady=16)
  self.main=ttk.Frame(shell,padding=(0,8,8,4))
  self.main.pack(side='left',fill='both',expand=True)
  brand=ttk.Frame(self.main);brand.pack(fill='x',pady=(2,14))
  # Prefer the college's official logo when provided in assets; keep Win7-compatible PNG.
  self.brand_logo=None
  logo_path=ROOT/'assets'/'rktm-logo.png'
  if logo_path.is_file():
   try:
    img=tk.PhotoImage(file=str(logo_path))
    factor=max(1,(img.width()+159)//160,(img.height()+63)//64)
    self.brand_logo=img.subsample(factor,factor)
    logo=tk.Label(brand,image=self.brand_logo,bg=BG,padx=4,pady=4)
   except tk.TclError:
    logo=tk.Label(brand,text='РКТМ',font=('Segoe UI',16,'bold'),fg='white',bg=RED,padx=18,pady=12)
  else:
   logo=tk.Label(brand,text='РКТМ',font=('Segoe UI',16,'bold'),fg='white',bg=RED,padx=18,pady=12)
  logo.pack(side='left',padx=(0,16))
  header=ttk.Frame(brand);header.pack(side='left',fill='x',expand=True)
  ttk.Label(header,text='Загрузка расписания',style='Heading.TLabel').pack(anchor='w')
  ttk.Label(header,text='Без лишних действий: выберите, проверьте, опубликуйте.').pack(anchor='w')
  self.steps_frame=ttk.Frame(self.main);self.steps_frame.pack(fill='x',pady=(0,12))
  self.step_labels=[]
  for i,label in enumerate(('01  Выбор файлов','02  Проверка','03  Публикация'),1):
   cell=ttk.Frame(self.steps_frame);cell.pack(side='left',fill='x',expand=True,padx=3)
   widget=tk.Label(cell,text=label,font=('Segoe UI',10,'bold'),padx=8,pady=10,bd=0)
   widget.pack(fill='x')
   self.step_labels.append(widget)
  try:self.cfg=settings.load()
  except Exception as e:self.cfg=None;self.status.set(str(e))
  ttk.Label(self.main,text='Куда будет загружено: '+(self.cfg.get('folder','—') if self.cfg else 'не настроено'),wraplength=700).pack(anchor='w',pady=(0,12))
  self.entries=[];self.temps=[]
  self.stage=tk.StringVar(value='ШАГ 1 ИЗ 3  ·  ВЫБОР ФАЙЛОВ')
  ttk.Label(self.main,textvariable=self.stage,font=('Segoe UI',11,'bold'),foreground='#a71f30').pack(anchor='w',pady=(0,5))
  bar=tk.Frame(self.main,bg=BG);bar.pack(fill='x',pady=6)
  for label,glyph,callback in (('ZIP-архив','zip',self.add_zip),('Папка','folder',self.add_folder),('HTML-файлы','html',self.pick)):
   action_button(bar,label,glyph,callback).pack(side='left',padx=(0,8))

  ttk.Label(self.main,text='СПИСОК ПУБЛИКАЦИИ',font=('Segoe UI',10,'bold'),foreground='#60656C').pack(anchor='w',pady=(8,0))
  self.count=tk.StringVar(value='HTML-файлов для публикации: 0')
  self.count_label=ttk.Label(self.main,textvariable=self.count)
  self.count_label.pack(anchor='w',pady=6)
  self.items=tk.Listbox(self.main,font=('Segoe UI',10),borderwidth=1,relief='solid',highlightthickness=0,selectbackground=RED,selectforeground='white',background=BG,activestyle='none')
  self.items.pack(fill='both',expand=True,pady=6)
  self.progress=ttk.Progressbar(self.main,mode='determinate',maximum=1)
  self.progress.pack(fill='x',pady=6)
  self.current=tk.StringVar(value='Готово к выбору файлов')
  ttk.Label(self.main,textvariable=self.current,wraplength=650).pack(anchor='w',pady=5)
  nav=ttk.Frame(self.main);nav.pack(fill='x',pady=8)
  self.back_button=ttk.Button(nav,text='← Назад',command=self.go_back)
  self.back_button.pack(side='left',padx=(0,8))
  self.send_button=ttk.Button(nav,text='ДАЛЕЕ: ПРОВЕРИТЬ ФАЙЛЫ →',style='Primary.TButton',command=self.review)
  self.send_button.pack(side='left',fill='x',expand=True)
  self.selection_bar=bar
  ttk.Label(self.main,text='Разработчик ПО: Сорокин Дмитрий Денисович',font=('Segoe UI',9),foreground='#697180').pack(side='bottom',anchor='e',pady=(4,0))
  self.stage_num=1
  self.show_stage(1)
  self.progress_q=queue.Queue()
  self.after(100,self.progress_poll)
 def show_stage(self,number):
  self.stage_num=number
  labels={1:'ШАГ 1 ИЗ 3  ·  ВЫБОР ФАЙЛОВ',2:'ШАГ 2 ИЗ 3  ·  ПРОВЕРКА ПЕРЕД ОТПРАВКОЙ',3:'ШАГ 3 ИЗ 3  ·  ПУБЛИКАЦИЯ'}
  self.stage.set(labels[number])
  for cell,lbl,picture,n in self.side_items:
   active=(n==number)
   color='#B5181B' if active else RED
   cell.configure(bg=color)
   lbl.configure(bg=color,font=('Segoe UI',10,'bold' if active else 'normal'))
   picture.configure(bg=color)
  for i,widget in enumerate(self.step_labels,1):
   active=(i==number)
   widget.configure(bg=RED if active else '#E5E4E4',fg='white' if active else INK)
  if number==1:
   self.selection_bar.pack(fill='x',pady=6,before=self.count_label)
   self.back_button.state(['disabled'])
   self.send_button.configure(text='ДАЛЕЕ: ПРОВЕРИТЬ ФАЙЛЫ →',command=self.review)
   self.send_button.state(['!disabled'])
   self.current.set('Выберите HTML-файлы, папку или ZIP-архив')
  elif number==2:
   self.selection_bar.pack_forget()
   self.back_button.state(['!disabled'])
   self.send_button.configure(text='ОПУБЛИКОВАТЬ НА САЙТЕ',command=self.publish)
   self.send_button.state(['!disabled'])
   self.current.set('Только HTML и HTM. Все файлы попадут прямо в выбранный каталог, без подпапок.')
  else:
   self.selection_bar.pack_forget()
   self.back_button.state(['disabled'])
   self.send_button.state(['disabled'])
 def go_back(self):
  if self.busy:return
  self.show_stage(1)
 def review(self):
  if not self.entries:
   messagebox.showinfo('Нет файлов','Сначала выберите HTML-файлы, папку или ZIP')
   return
  if not self.cfg:
   messagebox.showerror('Не настроено','Попросите администратора настроить папку публикации')
   return
  self.show_stage(2)
 def refresh(self):
  self.items.delete(0,'end')
  for local,rel in self.entries:self.items.insert('end',rel)
  self.count.set(f'HTML-файлов для публикации: {len(self.entries)}')
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
     self.current.set(f'Готово {index} из {total} · Последний файл: {name}')
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
  if not messagebox.askyesno('Подтверждение',f'Опубликовать {len(self.entries)} HTML-файлов непосредственно в {self.cfg["folder"]}, без подпапок?'):return
  self.show_stage(3)
  entries=list(self.entries);c=self.cfg.copy();self.progress_q=queue.Queue()
  self.progress['value']=0
  self.progress['maximum']=len(entries)
  def job():
   # A few parallel SFTP connections accelerate many small HTML files.
   # Every file retains the transport's staged upload and backup behaviour.
   results=[]
   def send(entry):
    local,rel=entry
    try:return entry,TRANSPORT.publish(c,local,c['folder'])
    except Exception as e:return entry,{'error':str(e)}
   with ThreadPoolExecutor(max_workers=3) as pool:
    futures={pool.submit(send,e):e for e in entries}
    completed=0
    for future in as_completed(futures):
     entry,result=future.result()
     completed+=1
     results.append((entry,result))
     self.progress_q.put(('current',(completed,len(entries),entry[1])))
     self.progress_q.put(('completed',completed))
   return results
  def done(results):
   succeeded={rel for (_,rel),r in results if r.get('status')=='published'}
   self.entries=[e for e in self.entries if e[1] not in succeeded]
   self.refresh()
   self.show_stage(2 if self.entries else 1)
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
