"""Unified native desktop interface. Standard-library only, Python 3.8 / Tk 8.6."""
import os
import sys
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from core import WinscpTransport, UploadError, validate_folder, validate_connection, validate_name
from selection import collect_folder, collect_zip
from brand_widgets import icon, RED, YELLOW, INK
import settings
import history

ROOT=Path(getattr(sys, '_MEIPASS')) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent
TRANSPORT=WinscpTransport(ROOT/'WinSCP'/'WinSCP.com')
BG='#F4F4F4'
WHITE='#FFFFFF'
GRAY='#60656C'
BORDER='#DADDE1'


class App(tk.Tk):
    def __init__(self, initial_tab='schedule'):
        super().__init__()
        self.title('РКТМ — Расписание')
        self.geometry('{}x{}'.format(min(1080, self.winfo_screenwidth()-40), min(760, self.winfo_screenheight()-100)))
        self.minsize(900, 640)
        self.configure(bg=BG)
        self.busy=False
        self.entries=[]
        self.temps=[]
        self.stage_num=1
        self.q=queue.Queue()
        self.progress_q=queue.Queue()
        self.cfg=None
        self.status=tk.StringVar(value='Готово к работе')
        try:
            self.iconbitmap(str(ROOT/'assets'/'upload.ico'))
        except (OSError, tk.TclError):
            pass
        self._styles()
        self.protocol('WM_DELETE_WINDOW', self.close)
        tk.Frame(self, bg=RED, height=4).pack(fill='x')
        self._header()
        footer=tk.Frame(self, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
        footer.pack(side='bottom', fill='x')
        tk.Label(footer, textvariable=self.status, bg=WHITE, fg=GRAY, font=('Segoe UI', 9), anchor='w').pack(side='left', padx=16, pady=8)
        tk.Label(footer, text='Сорокин Дмитрий Денисович', bg=WHITE, fg=GRAY, font=('Segoe UI', 9)).pack(side='right', padx=16)
        self.body=tk.Frame(self, bg=BG)
        self.body.pack(fill='both', expand=True, padx=28, pady=10)
        self.pages={}
        for name in ('schedule', 'history', 'settings'):
            self.pages[name]=tk.Frame(self.body, bg=WHITE, highlightbackground=BORDER, highlightthickness=1)
        self._schedule()
        self._history()
        self._settings()
        try:
            self.cfg=settings.load()
        except Exception:
            self.status.set('Не удалось прочитать настройки. Откройте «Настройки».')
        if self.cfg:
            for key, var in self.vars.items():
                var.set(self.cfg.get(key, ''))
        self.update_destination()
        self.show_stage(1)
        self.show_page(initial_tab)
        self.poll_id=self.after(100, self.poll)

    def _styles(self):
        self.option_add('*Font', ('Segoe UI', 10))
        s=ttk.Style(self)
        s.theme_use('clam')
        s.configure('TFrame', background=WHITE)
        s.configure('TLabel', background=WHITE, foreground=INK)
        s.configure('TButton', font=('Segoe UI', 10), padding=(14, 10), background=WHITE, foreground=INK, bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER, relief='flat', borderwidth=1, focusthickness=2)
        s.map('TButton', background=[('active', '#F0F1F3')])
        s.configure('Primary.TButton', background=RED, foreground=WHITE, bordercolor=RED, font=('Segoe UI', 11, 'bold'))
        s.map('Primary.TButton', background=[('disabled', '#BBBBBB'), ('active', '#C7191C')], foreground=[('disabled', WHITE)])
        s.configure('Import.TButton', padding=(10, 12), font=('Segoe UI', 11, 'bold'), borderwidth=0, relief='flat')
        for name, color, hover in (('ImportRed.TButton', '#FFF1F1', '#FFE0E0'), ('ImportGold.TButton', '#FFF8DF', '#FFECB2')):
            s.configure(name, padding=(10, 12), font=('Segoe UI', 11, 'bold'), borderwidth=0, relief='flat', background=color)
            s.map(name, background=[('active', hover), ('disabled', '#F4F4F4')])
        s.configure('TEntry', padding=7, fieldbackground=WHITE, bordercolor=BORDER)
        s.configure('Treeview', background=WHITE, fieldbackground=WHITE, foreground=INK, rowheight=28, bordercolor=BORDER, font=('Segoe UI', 10))
        s.configure('Treeview.Heading', background='#F1F2F4', foreground=GRAY, font=('Segoe UI', 10), padding=(8, 6), relief='flat', borderwidth=1, lightcolor=BORDER, darkcolor=BORDER)
        s.map('Treeview', background=[('selected', '#FCE5E5')], foreground=[('selected', INK)])
        s.configure('Horizontal.TProgressbar', background=RED, troughcolor='#ECEDEF', borderwidth=0, thickness=8)

    def _header(self):
        header=tk.Frame(self, bg=WHITE, height=84, highlightbackground=BORDER, highlightthickness=1)
        header.pack(fill='x')
        self.logo=None
        try:
            raw=tk.PhotoImage(file=str(ROOT/'assets'/'rktm-logo.png'))
            self.logo=raw.subsample(max(1, (raw.height()+51)//52))
            tk.Label(header, image=self.logo, bg=WHITE).pack(side='left', padx=(22, 12), pady=12)
        except (OSError, tk.TclError):
            tk.Label(header, text='РКТМ', fg=RED, bg=WHITE, font=('Segoe UI', 19, 'bold')).pack(side='left', padx=22, pady=20)
        tk.Label(header, text='РКТМ — Расписание', bg=WHITE, fg=INK, font=('Segoe UI', 15, 'bold')).pack(side='left', padx=(0, 20))
        self.tabs={}
        for key, title in (('schedule', 'Расписание'), ('history', 'История'), ('settings', 'Настройки')):
            cell=tk.Frame(header, bg=WHITE)
            cell.pack(side='left', fill='y', padx=8)
            b=tk.Button(cell, text=title, command=lambda n=key:self.show_page(n), bg=WHITE, fg=INK, activebackground=WHITE, activeforeground=RED, bd=0, relief='flat', font=('Segoe UI', 11), padx=10, pady=20, cursor='hand2', takefocus=True)
            b.pack(fill='both', expand=True)
            line=tk.Frame(cell, bg=WHITE, height=3)
            line.pack(fill='x')
            self.tabs[key]=(b, line)

    def show_page(self, name):
        if self.busy:
            return
        for key, frame in self.pages.items():
            frame.pack_forget()
            self.tabs[key][1].configure(bg=RED if key==name else WHITE)
            self.tabs[key][0].configure(fg=RED if key==name else GRAY, bg='#FFF1F1' if key==name else WHITE)
        self.pages[name].pack(fill='both', expand=True)
        self.current_page=name
        if name=='history':
            self.refresh_history()

    def title_block(self, page, title, subtitle):
        tk.Label(page, text=title, bg=WHITE, fg=RED, font=('Segoe UI', 20, 'bold'), anchor='w').pack(fill='x', padx=24, pady=(12, 3))
        tk.Label(page, text=subtitle, bg=WHITE, fg=GRAY, anchor='w').pack(fill='x', padx=24, pady=(0, 10))

    def table(self, parent, columns, widths):
        frame=ttk.Frame(parent)
        frame.pack(fill='both', expand=True)
        tree=ttk.Treeview(frame, columns=columns, show='headings', selectmode='extended', height=5)
        for name, width in zip(columns, widths):
            tree.heading(name, text=name, anchor='w')
            tree.column(name, width=width, minwidth=65, anchor='w')
        sb=ttk.Scrollbar(frame, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side='left', fill='both', expand=True)
        sb.pack(side='right', fill='y')
        return tree

    def _schedule(self):
        page=self.pages['schedule']
        self.title_block(page, 'Публикация расписания', 'Выберите файлы, проверьте и отправьте на сайт')
        steps=tk.Frame(page, bg=WHITE)
        steps.pack(fill='x', padx=24, pady=(0, 10))
        self.step_widgets=[]
        for i, title in enumerate(('Выбор файлов', 'Проверка', 'Публикация'), 1):
            circle=tk.Label(steps, text=str(i), bg='#E5E4E4', fg=INK, font=('Segoe UI', 12, 'bold'), width=3, pady=5)
            circle.pack(side='left')
            label=tk.Label(steps, text=title, bg=WHITE, fg=GRAY, padx=9)
            label.pack(side='left')
            self.step_widgets.append((circle, label))
            if i<3:
                tk.Frame(steps, bg=BORDER, height=1).pack(side='left', fill='x', expand=True, padx=(4, 14))
        self.import_bar=tk.Frame(page, bg=WHITE)
        self.import_bar.pack(fill='x', padx=24, pady=(0, 14))
        self.import_buttons=[]
        for col, (title, glyph, fn) in enumerate((('ZIP-архив', 'zip', self.add_zip), ('Папка', 'folder', self.add_folder), ('HTML-файлы', 'html', self.pick))):
            self.import_bar.columnconfigure(col, weight=1, uniform='import')
            tile_color='#FFF8DF' if col==1 else '#FFF1F1'
            box=tk.Frame(self.import_bar, bg=tile_color, highlightbackground='#EED5B0' if col==1 else '#F0C3C3', highlightthickness=1)
            box.grid(row=0, column=col, sticky='ew', padx=(0 if col==0 else 6, 0 if col==2 else 6))
            icon(box, glyph, 30, bg=tile_color).pack(side='left', padx=(18, 6), pady=10)
            b=ttk.Button(box, text=title, command=fn, style='ImportGold.TButton' if col==1 else 'ImportRed.TButton')
            b.pack(side='left', fill='both', expand=True)
            self.import_buttons.append(b)
        container=tk.Frame(page, bg=WHITE)
        container.pack(fill='both', expand=True, padx=24)
        self.items=self.table(container, ('Файл', 'Размер', 'Состояние'), (420, 110, 210))
        self.items.bind('<Delete>', lambda e:self.remove_selected())
        self.count=tk.StringVar(value='Выбрано файлов: 0')
        tk.Label(page, textvariable=self.count, bg=WHITE, fg=GRAY, anchor='w').pack(fill='x', padx=24, pady=(9, 3))
        self.progress=ttk.Progressbar(page, maximum=1)
        self.progress.pack(fill='x', padx=24, pady=(3, 5))
        self.current=tk.StringVar(value='Добавьте файлы расписания')
        self.current_label=tk.Label(page, textvariable=self.current, bg=WHITE, fg=GRAY, anchor='w')
        self.current_label.pack(fill='x', padx=24, pady=(0, 5))
        bottom=tk.Frame(page, bg=WHITE)
        bottom.pack(fill='x', padx=24, pady=(5, 18))
        self.remove_button=ttk.Button(bottom, text='Убрать выбранное', command=self.remove_selected)
        self.remove_button.pack(side='left')
        self.back_button=ttk.Button(bottom, text='Назад', command=lambda:self.show_stage(1))
        self.back_button.pack(side='left', padx=8)
        self.send_button=ttk.Button(bottom, text='Проверить файлы →', command=self.review, style='Primary.TButton')
        self.send_button.pack(side='right')
        self.destination=tk.StringVar()
        self.destination_label=tk.Label(page, textvariable=self.destination, bg=WHITE, fg=GRAY, anchor='w', wraplength=850)
        self.destination_label.pack(fill='x', padx=24, pady=(0, 12))
        # Reserve the action area before the expanding table, even on 768px displays.
        widgets=page.pack_slaves()
        options={w:w.pack_info() for w in widgets}
        for w in widgets:w.pack_forget()
        for w in (self.destination_label, bottom, self.current_label, self.progress, widgets[-5]):
            opts=dict(options[w]);opts.pop('in', None);opts['side']='bottom'
            w.pack(**opts)
        for w in widgets[:4]:
            opts=dict(options[w]);opts.pop('in', None);w.pack(**opts)
        opts=dict(options[container]);opts.pop('in', None);container.pack(**opts)

    def update_destination(self):
        folder=self.cfg.get('folder', '') if self.cfg else ''
        self.destination.set('Папка публикации: '+folder if folder else 'Подключение не настроено — откройте «Настройки»')

    def refresh(self):
        self.items.delete(*self.items.get_children())
        for i, (local, rel) in enumerate(self.entries):
            try:
                size='{:,} КБ'.format(max(1, (Path(local).stat().st_size+1023)//1024)).replace(',', ' ')
            except OSError:
                size='—'
            self.items.insert('', 'end', iid=str(i), values=(rel, size, 'Проверен' if self.stage_num==2 else 'Выбран'))
        self.count.set('Выбрано файлов: '+str(len(self.entries)))

    def show_stage(self, number):
        if self.busy:
            return
        self.stage_num=number
        if number==3:
            self.progress.pack(side='bottom', fill='x', padx=24, pady=(3, 5), after=self.current_label)
        else:
            self.progress.pack_forget()
        for i, (circle, label) in enumerate(self.step_widgets, 1):
            circle.configure(bg=YELLOW if i==number else '#E5E4E4')
            label.configure(fg=INK if i==number else GRAY, font=('Segoe UI', 10, 'bold' if i==number else 'normal'))
        for b in self.import_buttons:
            b.state(['!disabled'] if number==1 else ['disabled'])
        self.remove_button.state(['!disabled'] if number==1 else ['disabled'])
        self.back_button.state(['!disabled'] if number==2 else ['disabled'])
        self.send_button.configure(text='Опубликовать на сайте' if number==2 else 'Проверить файлы →', command=self.publish if number==2 else self.review)
        self.send_button.state(['disabled'] if number==3 else ['!disabled'])
        self.refresh()
        self.current.set({1:'Добавьте файлы расписания', 2:'Проверка пройдена. Файлы будут опубликованы без подпапок.', 3:'Публикация выполняется. Дождитесь завершения.'}[number])

    def append(self, new):
        if self.busy or self.stage_num!=1:
            return
        known={rel.casefold() for _, rel in self.entries}
        for local, rel in new:
            validate_name(rel)
            if rel.casefold() in known:
                raise UploadError('Повторяется имя назначения: '+rel)
            known.add(rel.casefold())
        self.entries.extend(new)
        self.refresh()

    def remove_selected(self):
        if self.busy or self.stage_num!=1:
            return
        selected=set(self.items.selection())
        self.entries=[e for i, e in enumerate(self.entries) if str(i) not in selected]
        self.refresh()

    def pick(self):
        if self.busy or self.stage_num!=1:return
        files=filedialog.askopenfilenames(title='Выберите HTML-файлы', filetypes=[('HTML', '*.html *.htm')])
        try:self.append([(p, Path(p).name) for p in files])
        except Exception as e:messagebox.showerror('Выбор файлов', str(e))

    def add_folder(self):
        if self.busy or self.stage_num!=1:return
        folder=filedialog.askdirectory(title='Выберите папку с расписанием')
        if not folder:return
        try:self.append(collect_folder(folder))
        except Exception as e:messagebox.showerror('Выбор папки', str(e))

    def add_zip(self):
        if self.busy or self.stage_num!=1:return
        filename=filedialog.askopenfilename(title='Выберите ZIP с расписанием', filetypes=[('ZIP', '*.zip')])
        if not filename:return
        temp=None
        try:
            temp, files=collect_zip(filename)
            self.append(files)
            self.temps.append(temp)
        except Exception as e:
            if temp:temp.cleanup()
            messagebox.showerror('Выбор ZIP', str(e))

    def validate_entries(self):
        if not self.entries:raise UploadError('Сначала выберите HTML-файлы, папку или ZIP-архив.')
        if not self.cfg:raise UploadError('Сначала сохраните подключение в разделе «Настройки».')
        validate_connection(self.cfg)
        validate_folder(self.cfg['folder'])
        for local, rel in self.entries:
            validate_name(rel)
            if not Path(local).is_file():raise UploadError('Файл не найден: '+rel)

    def review(self):
        if self.busy:return
        try:self.validate_entries()
        except Exception as e:
            messagebox.showerror('Проверка файлов', str(e));return
        self.show_stage(2)

    def publish(self):
        if self.busy or self.stage_num!=2:return
        try:self.validate_entries()
        except Exception as e:
            messagebox.showerror('Проверка файлов', str(e));return
        if not messagebox.askyesno('Публикация', 'Отправить {} файлов в {}?\nСуществующие файлы будут заменены с резервной копией.'.format(len(self.entries), self.cfg['folder'])):return
        self.show_stage(3)
        entries=list(self.entries)
        cfg=self.cfg.copy()
        self.progress['value']=0
        self.progress['maximum']=len(entries)
        def job():
            def send(entry):
                try:return entry, TRANSPORT.publish(cfg, entry[0], cfg['folder'])
                except Exception as e:return entry, {'error':str(e)}
            results=[]
            with ThreadPoolExecutor(max_workers=3) as pool:
                futures=[pool.submit(send, e) for e in entries]
                for future in as_completed(futures):
                    item=future.result()
                    results.append(item)
                    self.progress_q.put((len(results), len(entries), item[0][1]))
            return results
        def done(results):
            succeeded={rel for (_, rel), r in results if r.get('status')=='published'}
            self.entries=[e for e in self.entries if e[1] not in succeeded]
            receipt_error=False
            try:history.record(len(results), len(succeeded))
            except Exception:receipt_error=True
            self.show_stage(2 if self.entries else 1)
            self.current.set('Опубликовано: {}. Ошибок: {}.'.format(len(succeeded), len(results)-len(succeeded)))
            self.status.set(self.current.get()+(' Журнал не сохранён.' if receipt_error else ''))
            errors=['{}: {}'.format(e[1], r.get('error', 'Не подтверждено')) for e, r in results if r.get('status')!='published']
            if errors:messagebox.showwarning('Результат публикации', '\n'.join(errors)[:1800])
            else:
                for temp in self.temps:temp.cleanup()
                self.temps.clear()
                messagebox.showinfo('Готово', 'Все {} файлов опубликованы.'.format(len(succeeded)))
        self.launch(job, done)

    def _history(self):
        page=self.pages['history']
        self.title_block(page, 'История публикаций', 'Результаты загрузок с этого компьютера')
        table=tk.Frame(page, bg=WHITE)
        table.pack(fill='both', expand=True, padx=24, pady=(0, 10))
        self.history_items=self.table(table, ('Дата', 'Файлов', 'Результат'), (250, 110, 420))
        self.history_items.tag_configure('ok', foreground='#207743')
        bottom=ttk.Frame(page)
        bottom.pack(fill='x', padx=24, pady=(0, 20))
        ttk.Button(bottom, text='Обновить', command=self.refresh_history).pack(side='left')
        ttk.Button(bottom, text='Сохранить журнал…', command=self.export_history).pack(side='left', padx=10)
        self.history_note=tk.StringVar(value='')
        ttk.Label(bottom, textvariable=self.history_note).pack(side='right')

    def refresh_history(self):
        self.history_items.delete(*self.history_items.get_children())
        try:
            rows=history.recent()
            for date, total, ok in rows:
                from datetime import datetime
                stamp=datetime.fromisoformat(date).strftime('%d.%m.%Y, %H:%M')
                result='Опубликовано' if total==ok else 'Успешно: {}, ошибок: {}'.format(ok, total-ok)
                self.history_items.insert('', 'end', values=(stamp, total, result), tags=('ok',) if total==ok else ())
            self.history_note.set('Записей: '+str(len(rows)) if rows else 'Публикаций пока нет')
        except Exception:
            self.history_note.set('Не удалось открыть журнал')

    def export_history(self):
        filename=filedialog.asksaveasfilename(title='Сохранить журнал', defaultextension='.txt', filetypes=[('Текст', '*.txt')])
        if not filename:return
        try:
            rows=history.recent()
            text='РКТМ — История публикаций\n\n'+'\n'.join('{} | Файлов: {} | Успешно: {}'.format(*r) for r in rows)
            Path(filename).write_text(text, encoding='utf-8-sig')
        except Exception as e:messagebox.showerror('Журнал', str(e))

    def _settings(self):
        page=self.pages['settings']
        self.title_block(page, 'Настройки подключения', 'Настраивается один раз администратором')
        form=ttk.Frame(page)
        form.pack(fill='x', padx=24)
        form.columnconfigure(1, weight=1)
        self.vars={}
        for row, (key, label, default) in enumerate((('host', 'SFTP-сервер', ''), ('port', 'Порт', '22'), ('user', 'Пользователь', ''), ('password', 'Пароль', ''), ('hostkey', 'Отпечаток ключа сервера', ''), ('folder', 'Папка публикации', '/'))):
            ttk.Label(form, text=label).grid(row=row, column=0, sticky='w', padx=(0, 20), pady=7)
            var=tk.StringVar(value=default)
            self.vars[key]=var
            ttk.Entry(form, textvariable=var, show='•' if key=='password' else '').grid(row=row, column=1, sticky='ew', pady=7)
        ttk.Label(page, text='Отпечаток SSH: ssh-ed25519 256 SHA256:… (не путь к файлу ключа)', foreground=GRAY).pack(anchor='w', padx=24, pady=(8, 14))
        actions=ttk.Frame(page)
        actions.pack(fill='x', padx=24, pady=10)
        self.connect_button=ttk.Button(actions, text='Проверить связь', command=self.connect)
        self.connect_button.pack(side='left')
        self.browse_button=ttk.Button(actions, text='Выбрать папку на сервере', command=self.browse)
        self.browse_button.pack(side='left', padx=10)
        self.save_button=ttk.Button(actions, text='Сохранить', command=self.save, style='Primary.TButton')
        self.save_button.pack(side='right')
        ttk.Label(page, text='Пароль защищён средствами Windows и доступен текущему пользователю.', foreground=GRAY).pack(anchor='w', padx=24, pady=14)

    def config(self):return {k:v.get().strip() if k!='password' else v.get() for k, v in self.vars.items()}

    def checked_config(self):
        c=self.config()
        validate_connection(c)
        c['folder']=validate_folder(c['folder'])
        return c

    def save(self):
        if self.busy:return
        try:
            c=self.checked_config()
            settings.save(c)
            self.cfg=c
            self.update_destination()
            if self.stage_num==2:self.show_stage(1)
            self.status.set('Настройки сохранены')
            messagebox.showinfo('Готово', 'Подключение сохранено. Можно загружать расписание.')
        except Exception as e:messagebox.showerror('Настройки', str(e))

    def connect(self):
        if self.busy:return
        try:c=self.checked_config()
        except Exception as e:messagebox.showerror('Подключение', str(e));return
        self.launch(lambda:TRANSPORT.list_dir(c, c['folder']), lambda names:self.status.set('Подключение успешно. Подпапок: '+str(len(names))))

    def browse(self):
        if self.busy:return
        try:c=self.checked_config()
        except Exception as e:messagebox.showerror('Папка на сервере', str(e));return
        win=tk.Toplevel(self)
        win.title('Выбор папки публикации')
        win.geometry('620x440')
        win.configure(bg=WHITE)
        win.transient(self)
        win.grab_set()
        path=tk.StringVar(value=c['folder'])
        ttk.Label(win, textvariable=path, wraplength=570).pack(fill='x', padx=20, pady=15)
        folders=tk.Listbox(win, font=('Segoe UI', 11), activestyle='none')
        folders.pack(fill='both', expand=True, padx=20)
        def show(names):
            if not win.winfo_exists():return
            folders.delete(0, 'end')
            for name in names:folders.insert('end', name)
        def load():
            if self.busy:return
            location=path.get()
            folders.delete(0, 'end')
            self.launch(lambda:TRANSPORT.list_dir(c, location), show)
        def enter(event=None):
            if self.busy or not folders.curselection():return
            path.set(path.get().rstrip('/')+'/'+folders.get(folders.curselection()[0]))
            load()
        def up():
            if self.busy:return
            path.set(path.get().rstrip('/').rsplit('/', 1)[0] or '/')
            load()
        def choose():
            if self.busy:return
            self.vars['folder'].set(path.get())
            win.destroy()
        def close():
            if not self.busy:win.destroy()
        win.protocol('WM_DELETE_WINDOW', close)
        folders.bind('<Double-1>', enter)
        bar=ttk.Frame(win)
        bar.pack(fill='x', padx=20, pady=14)
        ttk.Button(bar, text='На уровень выше', command=up).pack(side='left')
        ttk.Button(bar, text='Выбрать эту папку', command=choose, style='Primary.TButton').pack(side='right')
        load()

    def launch(self, job, done):
        if self.busy:return
        self.busy=True
        self.status.set('Выполняется операция…')
        def task():
            try:self.q.put((done, job(), None))
            except Exception as e:self.q.put((done, None, str(e)))
        threading.Thread(target=task, daemon=True).start()

    def poll(self):
        try:
            while True:
                count, total, name=self.progress_q.get_nowait()
                self.progress['value']=count
                self.current.set('Обработано {} из {} · {}'.format(count, total, name))
        except queue.Empty:pass
        try:
            while True:
                done, result, error=self.q.get_nowait()
                self.busy=False
                if error:
                    self.status.set('Операция не завершена')
                    if self.stage_num==3:self.show_stage(2)
                    messagebox.showerror('Ошибка', error[:1600])
                else:
                    self.status.set('Операция выполнена')
                    done(result)
        except queue.Empty:pass
        self.poll_id=self.after(100, self.poll)

    def close(self):
        if self.busy:
            messagebox.showinfo('Выполняется операция', 'Дождитесь завершения перед закрытием программы.')
            return
        self.after_cancel(self.poll_id)
        for temp in self.temps:temp.cleanup()
        self.destroy()


# Backwards-compatible entry points for existing shortcuts and imports.
class Upload(App):
    pass


class Admin(App):
    def __init__(self):super().__init__('settings')


if __name__=='__main__':
    App('settings' if '--admin' in sys.argv else 'schedule').mainloop()
