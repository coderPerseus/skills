#!/usr/bin/env python3
"""Render the user's approved understated gray rounded subtitles."""
import argparse,json,math,pathlib
from PIL import ImageFont

def stamp(t,ass=False):
 den=100 if ass else 1000;n=round(t*den);h=n//(3600*den);m=n//(60*den)%60;s=n//den%60;f=n%den
 return f'{h}:{m:02}:{s:02}.{f:02}' if ass else f'{h:02}:{m:02}:{s:02},{f:03}'
def rounded(w,h,r):
 k=.55228475*r
 return f'm {r} 0 l {w-r} 0 b {w-r+k:.2f} 0 {w} {r-k:.2f} {w} {r} l {w} {h-r} b {w} {h-r+k:.2f} {w-r+k:.2f} {h} {w-r} {h} l {r} {h} b {r-k:.2f} {h} 0 {h-r+k:.2f} 0 {h-r} l 0 {r} b 0 {r-k:.2f} {r-k:.2f} 0 {r} 0'

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ['cues','ass','srt']:p.add_argument('--'+name,required=True)
 p.add_argument('--width',type=int,required=True);p.add_argument('--height',type=int,required=True)
 p.add_argument('--font',default='/System/Library/Fonts/Hiragino Sans GB.ttc');p.add_argument('--font-name',default='Hiragino Sans GB');p.add_argument('--font-index',type=int,default=0)
 a=p.parse_args();cues=json.loads(pathlib.Path(a.cues).read_text());scale=a.height/1240;size=round(36*scale);font=ImageFont.truetype(a.font,size,index=a.font_index)
 if min(a.width,a.height)<2:raise ValueError('Invalid dimensions')
 lines=[];srt=[];last=0
 for i,(start,end,text) in enumerate(cues):
  if not (math.isfinite(start) and math.isfinite(end) and 0<=last<=start<end and text.strip()):raise ValueError(f'Invalid or overlapping cue {i}')
  if any(c in text for c in '{}\\\n\r'):raise ValueError('Plain single-line subtitles only; remove ASS control characters')
  last=end;w=round(font.getlength(text))+round(48*scale);h=round(62*scale);radius=round(11*scale);left=round((a.width-w)/2);top=a.height-round(104*scale)
  if w>a.width*.92:raise ValueError(f'Cue {i} is too wide; split at real word timestamps')
  lines.append(f'Dialogue: 0,{stamp(start,True)},{stamp(end,True)},Box,,0,0,0,,{{\\an7\\pos({left},{top})\\p1}}'+rounded(w,h,radius)+'{\\p0}')
  lines.append(f'Dialogue: 1,{stamp(start,True)},{stamp(end,True)},Text,,0,0,0,,{{\\an5\\pos({a.width/2},{top+h/2})}}'+text)
  srt.append(f'{i+1}\n{stamp(start)} --> {stamp(end)}\n{text}')
 header=f'''[Script Info]
ScriptType: v4.00+
PlayResX: {a.width}
PlayResY: {a.height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Text,{a.font_name},{size},&H08534B45,&H000000FF,&HFF000000,&HFF000000,0,0,0,0,100,100,0,0,1,0,0,5,20,20,40,1
Style: Box,{a.font_name},{size},&H30DFDBD8,&H000000FF,&HFF000000,&HFF000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
 for dest,content in [(a.ass,header+'\n'.join(lines)),(a.srt,'\n\n'.join(srt)+'\n')]:
  path=pathlib.Path(dest);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(content)
 print(f'{len(cues)} cues generated')
if __name__=='__main__':main()
