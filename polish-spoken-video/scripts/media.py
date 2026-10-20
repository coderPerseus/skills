#!/usr/bin/env python3
"""Frame-aligned spoken-video planning, cue mapping and rendering."""
import argparse,json,math,pathlib,re,shutil,subprocess,sys,wave

def read(p): return json.loads(pathlib.Path(p).read_text())
def save(p,d):
 p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2))
def probe(p): return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(p)]))
def intervals(xs,d):
 out=[]
 for a,b in xs:
  if not (math.isfinite(a) and math.isfinite(b) and 0<=a<b<=d+.1):raise ValueError(f'Invalid interval {a,b}')
  out.append((a,min(b,d)))
 return out

def plan(args):
 source=pathlib.Path(args.source).resolve();info=probe(source);d=float(info['format']['duration']);cfg=read(args.decisions)
 manual=intervals(cfg.get('cuts',[]),d);protect=intervals(cfg.get('protect',[]),d)
 padding=float(cfg.get('padding',.16));minimum=float(cfg.get('silence_min',.72))
 if not (0<=padding and minimum>2*padding):raise ValueError('silence_min must exceed twice padding')
 cuts=[];start=None
 for line in pathlib.Path(args.silence).read_text().splitlines():
  m=re.search(r'silence_start: ([0-9.]+)',line)
  if m:start=float(m[1])
  m=re.search(r'silence_end: ([0-9.]+)',line)
  if m and start is not None:
   end=min(d,float(m[1]));parts=[(start+padding,end-padding)] if end-start>=minimum else []
   for u,v in protect:
    new=[]
    for a,b in parts:
     if v<=a or u>=b:new.append((a,b))
     else:
      if a<u:new.append((a,u))
      if v<b:new.append((v,b))
    parts=new
   cuts+=parts;start=None
 if start is not None:raise ValueError('Unclosed silence: rerun full silencedetect')
 cuts+=manual;fps=30;total=math.floor(d*fps)
 merged=[]
 for a,b in sorted((max(0,round(a*fps)),min(total,round(b*fps))) for a,b in cuts):
  if b<=a:continue
  if merged and a<=merged[-1][1]:merged[-1][1]=max(b,merged[-1][1])
  else:merged.append([a,b])
 keep=[];pos=0
 for a,b in merged:
  if pos<a:keep.append([pos/fps,a/fps])
  pos=b
 if pos<total:keep.append([pos/fps,total/fps])
 if not keep:raise ValueError('Edits remove all footage')
 save(args.output,{'source':str(source),'fps':fps,'source_duration':d,'keep':keep,'duration':sum(b-a for a,b in keep),'decisions':cfg})
 print(f'{d:.3f}s -> {sum(b-a for a,b in keep):.3f}s; {len(keep)} retained spans')

def validate(p):
 fps=p['fps'];prev=0
 if fps!=30 or not p['keep']:raise ValueError('Expected nonempty 30 fps plan')
 for a,b in p['keep']:
  if not (math.isfinite(a) and math.isfinite(b) and 0<=prev<=a<b):raise ValueError('Invalid keep timeline')
  if any(abs(t*fps-round(t*fps))>1e-5 for t in (a,b)):raise ValueError('Timeline not frame aligned')
  prev=b
 if abs(sum(b-a for a,b in p['keep'])-p['duration'])>1e-5:raise ValueError('Duration mismatch')

def map_cues(args):
 p=read(args.plan);validate(p);out=[]
 for a,b,text in read(args.cues):
  if not (0<=a<b and isinstance(text,str) and text.strip()):raise ValueError('Invalid cue')
  spans=[];offset=0
  for x,y in p['keep']:
   lo=max(a,x);hi=min(b,y)
   if hi>lo:spans.append([offset+lo-x,offset+hi-x])
   offset+=y-x
  if spans:out.append([spans[0][0],spans[-1][1],text.strip()])
 out.sort()
 for i,c in enumerate(out):
  if i and out[i-1][1]>c[0]+.001:raise ValueError('Mapped cues overlap: fix source cues')
 save(args.output,out)

def render(args):
 import numpy as np
 source=pathlib.Path(args.source).resolve();output=pathlib.Path(args.output).resolve();p=read(args.plan);validate(p)
 if source!=pathlib.Path(p['source']).resolve():raise ValueError('Plan belongs to another source')
 if output.exists():raise FileExistsError('Choose a new output name; existing video retained')
 if args.width%2 or args.height%2 or min(args.width,args.height)<2:raise ValueError('Output dimensions must be positive even numbers')
 wd=pathlib.Path(args.workdir).resolve();wd.mkdir(parents=True,exist_ok=True);output.parent.mkdir(parents=True,exist_ok=True)
 info=probe(source);track=next(s for s in info['streams'] if s['codec_type']=='audio');channels=min(2,int(track['channels']))
 # first_pts=0 preserves any positive audio start offset relative to the video.
 subprocess.run(['ffmpeg','-y','-v','error','-i',str(source),'-map','0:a:0','-vn','-af','aresample=48000:async=1:first_pts=0','-ac',str(channels),'-c:a','pcm_s16le',str(wd/'source.wav')],check=True)
 with wave.open(str(wd/'source.wav')) as f:rate=f.getframerate();raw=np.frombuffer(f.readframes(f.getnframes()),dtype=np.int16).reshape(-1,channels)
 with wave.open(str(wd/'edited.wav'),'w') as f:
  f.setnchannels(channels);f.setsampwidth(2);f.setframerate(rate)
  for a,b in p['keep']:
   n0=round(a*rate);n1=round(b*rate);y=raw[n0:n1].astype(np.float64)
   if len(y)<n1-n0:y=np.pad(y,((0,n1-n0-len(y)),(0,0)))
   n=min(round(.005*rate),len(y)//2)
   if n:y[:n]*=np.linspace(0,1,n)[:,None];y[-n:]*=np.linspace(1,0,n)[:,None]
   f.writeframes(y.astype(np.int16).tobytes())
 ass=pathlib.Path(args.ass).resolve()
 if ass!=wd/'captions.ass':shutil.copyfile(ass,wd/'captions.ass')
 select='+'.join(f'between(n,{round(a*30)},{round(b*30)-1})' for a,b in p['keep'])
 vf=f"fps=30,select='{select}',setpts=N/(30*TB),scale={args.width}:{args.height}:flags=lanczos,ass=captions.ass"
 (wd/'filter.txt').write_text(vf)
 encoder=args.encoder if args.encoder!='auto' else ('h264_videotoolbox' if sys.platform=='darwin' else 'libx264')
 quality=['-b:v','10M'] if encoder=='h264_videotoolbox' else ['-crf','18','-preset','medium']
 cmd=['ffmpeg','-n','-hide_banner','-i',str(source),'-i','edited.wav','-map','0:v:0','-map','1:a:0','-filter_script:v','filter.txt','-af','highpass=f=65,loudnorm=I=-16:TP=-1.5:LRA=11','-c:v',encoder,*quality,'-pix_fmt','yuv420p','-c:a','aac','-b:a','256k','-ar','48000','-movflags','+faststart','-shortest','-progress','progress.txt',str(output)]
 with (wd/'render.log').open('w') as log:subprocess.run(cmd,cwd=wd,stdout=log,stderr=log,check=True)
 result=probe(output);v=next(s for s in result['streams'] if s['codec_type']=='video');a=next(s for s in result['streams'] if s['codec_type']=='audio')
 if abs(float(v['duration'])-float(a['duration']))>=.12 or abs(float(v['duration'])-p['duration'])>.07:raise ValueError('Output duration/sync check failed')
 print(str(output))

def main():
 ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest='mode',required=True)
 p=sub.add_parser('plan')
 for name in ['source','silence','decisions','output']:p.add_argument('--'+name,required=True)
 p.set_defaults(fn=plan)
 p=sub.add_parser('map-cues')
 for name in ['plan','cues','output']:p.add_argument('--'+name,required=True)
 p.set_defaults(fn=map_cues)
 p=sub.add_parser('render')
 for name in ['source','plan','ass','workdir','output']:p.add_argument('--'+name,required=True)
 p.add_argument('--width',type=int,required=True);p.add_argument('--height',type=int,required=True);p.add_argument('--encoder',choices=['auto','libx264','h264_videotoolbox'],default='auto');p.set_defaults(fn=render)
 args=ap.parse_args();args.fn(args)
if __name__=='__main__':main()
