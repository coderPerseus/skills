# 执行细节

## 环境与目录

优先复用可用环境；没有时在任务 `work/` 中建立 venv。不要依赖某次聊天的绝对路径，也不要把模型、视频或虚拟环境放进 skill。

```sh
uv venv work/video-venv --python 3.12
uv pip install --python work/video-venv/bin/python numpy pillow mlx-whisper opencc-python-reimplemented
```

要求 ffmpeg（含 libass）、ffprobe。Apple Silicon 使用 MLX Whisper；其他平台换为本地 faster-whisper，并保留同等逐词结构。不要把音频上传第三方服务作为隐含默认。

`PYTHON` 表示上述 venv Python；`SKILL` 表示本 skill 文件夹。给路径加引号。每次任务使用独立 `work/job/`，不要用 `inspect.py` 等标准库名称给脚本命名。

## 分析、剪辑和字幕数据

```sh
ffmpeg -y -i "$SOURCE" -vn -ac 1 -ar 16000 work/job/asr.wav
ffmpeg -i work/job/asr.wav -af silencedetect=noise=-35dB:d=0.4 -f null - 2> work/job/silence.log
"$PYTHON" "$SKILL/scripts/transcribe.py" work/job/asr.wav work/job/transcript.json
```

转录模型首次需要下载，使用 `mlx-community/whisper-large-v3-turbo`。提示词可含视频中已核实的术语，不能把上一个视频的品牌词典自动应用到新视频。

`decisions.json`（时间单位秒，均对应原视频）：

```json
{
  "cuts": [[12.4, 14.8]],
  "protect": [[30.0, 37.0]],
  "silence_min": 0.72,
  "padding": 0.16
}
```

上述时间只是格式示例，不能直接套用。`cuts` 是审核后的删除内容，`protect` 仅阻止自动静音压缩。无须用户再次审批。

```sh
"$PYTHON" "$SKILL/scripts/media.py" plan --source "$SOURCE" --silence work/job/silence.log --decisions work/job/decisions.json --output work/job/plan.json
```

字幕先按有意义短语组织，中文单行一般不超过约 28 字，英文按实际宽度。适当合并小于 0.7 秒的孤立尾词，不能把型号末尾 `Flash` 一类拆成一闪而过的一屏。尽量让每条停留 1–6 秒，短句可更短，不以牺牲同步为代价。

`source-cues.json`：`[[原开始秒, 原结束秒, "修订后的字幕"], ...]`。每条内容必须只包含保留的原话，不可凭字幕脚本推断被删除的字。示范片段可添加“生成效果 · 第一版”等中性说明。

```sh
"$PYTHON" "$SKILL/scripts/media.py" map-cues --plan work/job/plan.json --cues work/job/source-cues.json --output work/job/cues.json
"$PYTHON" "$SKILL/scripts/soft_captions.py" --cues work/job/cues.json --ass work/job/captions.ass --srt outputs/视频名_精修字幕.srt --width 1920 --height 1240
```

宽高必须与导出一致。先按源比例计算偶数尺寸。若脚本报告字幕超宽，按实际词时间拆句，不按字数均分时间。

## 已验收的字幕样式

基准为 1920×1240 的录屏：

- 字体：macOS `Hiragino Sans GB` 常规 W3，36 px，不加粗。其他系统选择可用的思源黑体/Noto Sans CJK 常规体，并通过 `--font` 与 `--font-name` 指定匹配字体。
- 文字：RGB `#454B53`，ASS alpha `08`，约 97% 不透明。
- 背景：RGB `#D8DBDF`，ASS alpha `30`，约 81% 不透明。
- 底框高度 62 px，左右留白各 24 px，圆角 11 px；位置 x 居中，顶部 y=1136（底边距 42 px）。宽度随文字实际测量。
- 无描边、阴影、粗体或高亮。圆角框与文字用 ASS 独立图层，避免 BorderStyle=3 的硬黑框。
- 其他分辨率按画面高度缩放，先验证最长字幕及内容遮挡；源画面底部若有重要按钮，可以略上移或留出字幕带，保持整体低存在感。

预览应使用素材截图和真实字幕时间；使用 `setpts=字幕时刻/TB` 后加载 ASS 可以快速检查某一条。

## 导出

```sh
"$PYTHON" "$SKILL/scripts/media.py" render --source "$SOURCE" --plan work/job/plan.json --ass work/job/captions.ass --workdir work/job/render --output outputs/视频名_精修柔和字幕版.mp4 --width 1920 --height 1240
```

默认 H.264：macOS VideoToolbox 10 Mbps，其他平台 libx264 CRF 18；硬件编码不可用时用 `--encoder libx264`。AAC 256 kbps/48 kHz，按原声道数处理（最多双声道）。使用帧索引选择视频并统一 30 fps；音频按完全相同的量化区间截取，接点约 5 ms 淡入淡出。响度起点 `highpass=f=65,loudnorm=I=-16:TP=-1.5:LRA=11`，如明显改变音色则调整。

输出文件必须是新路径；脚本拒绝覆盖旧成片。不使用 `-c copy` 任意切视频，避免非关键帧切割导致黑帧、跳帧与音画漂移。

## 验收

- 完整阅读剪后复核转录；新接点重点检查，遇到可疑词对照源片，不靠一次 ASR 猜测。
- ffprobe 检查实际输出尺寸、30 fps、48 kHz、时长与计划一致；音画结束差小于 0.12 秒。
- 用 `ffmpeg -v error -i "$FINAL" -map 0:v -map 0:a -f null -` 做完整解码。
- 抽查不同背景、最宽字幕、演示区、开头结尾，检查底框宽度、对齐与字形。
- 保留对应 SRT、原素材和已交付版本；中间文件留在 work，不擅自删除源文件或用户已有资产。

## 来源

流程参考了 VideoCLip-AI 的逐词审查和时间戳驱动剪辑思想：https://github.com/CocoLayuan/videoclip-ai-skill 。具体灰底字幕和无中途确认偏好来自用户已验收的成片。参考项目要求的字体选择/确认环节不适用于这个用户已授权的标准流程。
