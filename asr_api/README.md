# ASR云端服务调用工具
## AISpeech实时长语音转写
### 使用方式
需要安装websockets包。
```
pip install websockets
```
指定音频的scp列表文件和输出文件
```
aispeech_lasr_online.py wav.scp results.txt
```
其中scp列表文件由key和音频地址组成。
```
test-1 /home/test1.wav
test-2 /home/test2.wav
```
注意：第一次使用时需要按照提示，输入productId和apikey。
### 切换语种
修改脚本里，`QUERY`字典的lang字段。
```
QUERY = {
    "productId": "",  # 客户编号，唯一
    "apikey": "",  # apikey
    "deviceId": "",  # Optional, 本次连接所使用的设备ID，建议唯一，以方便界定问题（deviceId和device_id设置其中一个）
    "forward_addresses": "",  # Optional, 当参数不为空时，启动转发模式。 当有转写结果时，会往注册的WebSocket地址实时推送转写结果。支持多个转写websocket服务地址，多个地址中间用英文逗号 , 隔开。格式： ws://xxxx:port,ws://xxxx:port,ws://xxxx:port
    "res": "aitranson",  # Optional, 默认aitranson长语音实时在线
    "lang": "cn",  # Optional, ce(中英文混合)/en(英文在线)/cn(中文在线)/sichuantone-mix(中川)/cantonese-mix(中粤)，不设置时使用中文在线.
    "product_source": "dui"  # Optional, 渠道分类，默认dui
}
```
### 切换ASR配置
修改`PARAMS`字典里对应字段的值。
```
PARAMS = {
    "command": "start",
    "params": {
    "env": {
    "use_txt_smooth": 1,  # 口语顺滑
    "use_tprocess": 1,  # 逆文本
    "use_sensitive_wds_norm": 0,  # 内置敏感词
    "use_stream_sp": 0,  # 流式标点,（默认为0），为1时，返回识别结果回退的长度:back_pos
    "use_alignment": 0,  # 输出词级别时间对齐信息
    "use_nn_emotion": 1,  # 情绪识别
    "use_confidence":0,  # 句级别置信度（默认为0），为1时会在rec中返回 ”conf"，浮点
    "use_word_confi":0,  # 词级别置信度（默认为0），为1时,返回"alignment"下的"conf"表示词级别的置信度。
    "use_volume_detection":1  # （默认为0），为1时，返回分贝数
    },
    "audio": {
    "audioType": "wav",  # 音频类型支持：pcm, wav, ogg-speex, opus, mp3
    "sampleRate": 16000,  # 音频采样率
    "sampleBytes": 2,  # 量化字节数
    "channel": 1  # 音频通道
    }
    },
    "lmId": "default",  # 二路资源ID。当lmId== “default”时，会使用在控制台绑定的默认语言模型
    "phraseFileId": "",  # 用户的Phrase热词ID。 当phraseFileId== “default”时，会使用在控制台绑定的默认Phrase热词ID
    "sensitiveFileId": "",  # 用户的敏感词ID。 当psensitiveFileId== “default”时，会使用在控制台绑定的默认敏感词ID
    "hotWords": [],  # 热词列表，最多2000个，每个热词最多7个中文词（不推荐）
    "phraseList":[  # 请求识别增强级热词列表（推荐使用）
    { "name" : "name", "words": ["Jerry",], "boost": 1 },  # 人名类热词
    { "name" : "location", "words": ["苏州",], "boost": 1 },  # 地名类热词
    { "name" : "common", "words": ["思必驰",], "boost": 3 }  # 其他类热词
    ]
}
```
## AISpeech短语音转写
### 使用方式
需要安装websockets包。
```
pip install websockets
```
指定音频的scp列表文件和输出文件
```
aispeech_casr.py wav.scp results.txt
```
其中scp列表文件由key和音频地址组成。
```
test-1 /home/test1.wav
test-2 /home/test2.wav
```
注意：第一次使用时需要按照提示，输入productId和apikey。
### 切换场景
修改脚本里`QUERY`字典的res字段。
```
QUERY = {
    "productId": "",  # 客户编号，唯一
    "apikey": "",  # apikey
    "res": "aiuniversal",  # 一路模型资源名称，区分大小写，需要和资源名称完全一致
    "lang": "zh-CN",  # Optional, 不传此参数时默认使用中文
}
```
或者调用时传参。
```
aispeech_casr.py --res aicar wav.scp results.txt
```
### 切换ASR配置
修改`PARAMS`字典里对应字段的值。
```
PARAMS = {
    "context": {
        "productId": "", # 必选
        "userId": "SERddeeeeeeee",    # 可选
        "deviceName": "EVICEdde",  # 可选, 同Device Name授权服务里的deviceName
        "sdkName": "dui-asr-android-sdk-6.1" # 可选
    },
    "request": {
        "requestId": "request-id-in-uuid", # 可选, 如果不存在则服务端会生成一个, 统一换成requestId
        "audio": {
            "audioType": "wav", # 必选，建议压缩，格式上支持ogg, wav,mp3,amr等
            "sampleRate": 16000, # 必选
            "channel": 1, # 必选
            "sampleBytes": 2, # 必选
            "url": "" # 可选, 服务端会自动下载此url的音频用作识别
        },
        "asr": {
            "wakeupWord": "你好, 小驰", # 唤醒词
            "enableRealTimeFeedback": True,
            "enableVAD": True,
            "enableTone": False,
            "enablePunctuation": True,
            "enableNumberConvert": True,
            "enableConfidence": True,
            "enableSNTime": True,
            "enableEmotion": True,
            "lmId": "", # 可选
            "lmList": ["lm-id","lm-id2"], # 可选
            "phraseHints": [{"type": "vocab", "name": "词库名", "data":["短语1", "短语2"]}] # 热词, 可选, 必须与lmId同时使用, 目前仅支持vocab类型
        }
    }
}
```
## AISpeech录音文件撰写
### 使用方式
需要安装requests包。
```
pip install requests
```
指定音频的scp列表文件和输出文件
```
aispeech_lasr_offline.py wav.scp results.txt
```
其中scp列表文件由key和音频地址组成。
```
test-1 /home/test1.wav
test-2 /home/test2.wav
```
注意：第一次使用时需要按照提示，输入productId和apikey。
### 切换语种
修改脚本里，全局变量`LANG`的值。