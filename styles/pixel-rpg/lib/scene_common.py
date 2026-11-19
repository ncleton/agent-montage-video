"""Primitives graphiques du film. Tout est éditable et déterministe."""
from html import escape
from pathlib import Path
import textwrap
COLORS=dict(bg='#0A1411',ivory='#EEF4F0',panel='#11201B',muted='#9CB0A6',mint='#5FF2A8',gold='#F5C56B',green='#2FBF83',orange='#F5B97A',red='#FF8A7A')
def color(c): return COLORS.get(c,c)
def esc(t): return escape(str(t),quote=True)
def label(id,x,y,text,size=32,color='ivory'):
 return f'<text id="{esc(id)}" x="{x}" y="{y}" font-size="{size}" fill="{COLORS.get(color,color)}" font-family="Montserrat" font-weight="600">{esc(text)}</text>'
def path(id,d,color='ivory',width=3):
 return f'<path id="{esc(id)}" d="{esc(d)}" fill="none" stroke="{COLORS.get(color,color)}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>'
def svg(content):
 return f'<svg viewBox="0 0 1920 1080" class="diagram" xmlns="http://www.w3.org/2000/svg" data-layout-allow-overlap="true">{content}</svg>'
def paper(id,x,y,w,h,title,lines,accent='ivory'):
 if isinstance(lines,str): lines=lines.split('\n')
 cols=max(8,int((w-70)/16.5))
 rows=[]
 for line in lines: rows+=textwrap.wrap(str(line),cols,break_long_words=False,break_on_hyphens=False) or ['']
 title_rows=textwrap.wrap(title,max(8,int((w-64)/19)),break_long_words=False,break_on_hyphens=False)
 content=f'<g id="{esc(id)}"><path d="M{x+6} {y+9}H{x+w-20}L{x+w+6} {y+35}V{y+h+9}H{x+6}Z" fill="#000" opacity=".32"/><path d="M{x} {y}L{x+w-28} {y-2}L{x+w} {y+28}L{x+w-2} {y+h}L{x+2} {y+h+2}Z" fill="#EEF4F0"/><path d="M{x+w-28} {y-2}V{y+28}H{x+w}" fill="#BDB6AB"/>'
 for i,t in enumerate(title_rows): content+=label('',x+30,y+52+i*40,t,34,'#0F2924')
 yy=y+58+len(title_rows)*40
 for i,t in enumerate(rows):
  content+=label('',x+30,yy+i*39,t,30,'#43544D')
 content+=f'<path d="M{x+30} {y+h-29}H{x+w-30}" stroke="{color(accent)}" stroke-width="4"/></g>'
 return content

def node(id,x,y,text,accent='mint'):
 return f'<g id="{esc(id)}"><rect x="{x-90}" y="{y-70}" width="180" height="140" rx="25" fill="#11201B" stroke="{color(accent)}" stroke-width="3"/><path d="M{x-25} {y-22}H{x+24}M{x-25} {y}H{x+8}M{x-25} {y+22}H{x+24}" stroke="{color(accent)}" stroke-width="4" stroke-linecap="round"/>{label("",x-110,y+123,text,32,accent)}</g>'
def box(id,x,y,w,h,title,lines,accent='mint'):
 if isinstance(lines,str):lines=lines.split('\n')
 c=color(accent)
 content=f'<g id="{esc(id)}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="#11201B" stroke="{c}" stroke-width="2"/><path d="M{x+22} {y+64}H{x+w-22}" stroke="{c}" opacity=".3"/>{label("",x+25,y+45,title,32,accent)}'
 cols=max(8,int((w-50)/17))
 rows=[]
 for line in lines:rows+=textwrap.wrap(str(line),cols,break_long_words=False,break_on_hyphens=False) or ['']
 for i,t in enumerate(rows):content+=label('',x+25,y+111+i*42,t,30,'ivory')
 return content+'</g>'
def reveal(id,when='0',dur=.65):
 return f"tl.fromTo('#{id}',{{opacity:0}},{{opacity:1,duration:{dur},ease:'power3.out'}},{when});"
