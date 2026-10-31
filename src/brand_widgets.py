"""Lightweight, brandbook-aligned RKTM iconography for Tkinter (Windows 7 compatible)."""
import tkinter as tk
RED='#E51F22'
YELLOW='#FFDB57'
INK='#171717'
MUTED='#60656C'
BG='#FFFFFF'
PALE='#F4F4F4'

def icon(parent,name,size=24,color=RED,bg=BG):
    c=tk.Canvas(parent,width=size,height=size,bg=bg,highlightthickness=0,bd=0)
    s=size/24.0
    def line(*xy,**kw): return c.create_line(*[round(v*s) for v in xy],fill=color,width=max(2,int(2*s)),capstyle='round',joinstyle='round',**kw)
    def rect(x1,y1,x2,y2,**kw): return c.create_rectangle(x1*s,y1*s,x2*s,y2*s,outline=color,width=max(2,int(2*s)),**kw)
    def oval(x1,y1,x2,y2,**kw): return c.create_oval(x1*s,y1*s,x2*s,y2*s,outline=color,width=max(2,int(2*s)),**kw)
    if name=='zip':
        rect(5,2,19,22);line(12,3,12,13);line(10,5,14,5);line(10,9,14,9);rect(10,15,14,19)
    elif name=='folder':
        line(2,7,2,20,22,20,22,9,10,9,8,5,2,5,2,7)
    elif name=='html':
        line(6,2,16,2,21,7,21,22,6,22,6,2);line(16,2,16,7,21,7);line(11,11,8,14,11,17);line(16,11,19,14,16,17)
    elif name=='upload':
        line(12,17,12,3);line(6,9,12,3,18,9);line(4,16,4,21,20,21,20,16)
    elif name=='check':
        oval(3,3,21,21);line(7,12,11,16,18,8)
    elif name=='warning':
        line(12,3,22,21,2,21,12,3);line(12,9,12,14);oval(11,17,13,19,fill=color)
    elif name=='back':
        line(19,12,5,12);line(11,6,5,12,11,18)
    elif name=='gear':
        oval(4,4,20,20);oval(9,9,15,15);line(12,1,12,5);line(12,19,12,23);line(1,12,5,12);line(19,12,23,12)
    elif name=='search':
        oval(3,3,16,16);line(15,15,22,22)
    elif name=='shield':
        line(12,2,21,6,20,16,12,22,4,16,3,6,12,2);line(8,12,11,15,16,9)
    elif name=='info':
        oval(3,3,21,21);line(12,11,12,17);oval(11,7,13,9,fill=color)
    elif name=='clock':
        oval(3,3,21,21);line(12,6,12,12,17,15)
    else:
        oval(7,7,17,17)
    return c

def action_button(parent,label,ico,command,primary=False):
    bg=RED if primary else BG
    fg='white' if primary else INK
    frame=tk.Frame(parent,bg=bg,highlightbackground=RED if primary else '#DDDDDD',
                   highlightthickness=1,bd=0,cursor='hand2')
    glyph=icon(frame,ico,26,'white' if primary else RED,bg)
    glyph.pack(side='left',padx=(12,7),pady=10)
    text=tk.Label(frame,text=label,bg=bg,fg=fg,font=('Segoe UI',10,'bold'),cursor='hand2')
    text.pack(side='left',padx=(0,12),pady=10)
    for w in (frame,glyph,text):w.bind('<Button-1>',lambda event: command())
    return frame
