#!/usr/bin/env python3
"""Local Apple Silicon transcription with genuine word timestamps."""
import argparse,json,pathlib
p=argparse.ArgumentParser(description=__doc__);p.add_argument('audio');p.add_argument('output');p.add_argument('--language',default='zh');p.add_argument('--prompt',default='');p.add_argument('--model',default='mlx-community/whisper-large-v3-turbo');a=p.parse_args()
import mlx_whisper
r=mlx_whisper.transcribe(a.audio,path_or_hf_repo=a.model,language=a.language,word_timestamps=True,condition_on_previous_text=False,initial_prompt=a.prompt or None,verbose=False)
out=pathlib.Path(a.output);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,ensure_ascii=False,indent=2))
print(out)
