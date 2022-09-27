# AISpeech云端服务调用工具
## 实时长语音转写
### 使用方式
需要安装websockets包。
```
pip install websockets
```
编辑配置文件，填写有效的productId和apikey。
```
---
query:
  productId: ''  # 客户编号，唯一
  apikey: ''   # apikey
  deviceId: ''  # Optional, 本次连接所使用的设备ID，建议唯一，以方便界定问题（deviceId和device_id设置其中一个）
  forward_addresses: ''  # # Optional, 当参数不为空时，启动转发模式。 当有转写结果时，会往注册的WebSocket地址实时推送转写结果。
  res: aitranson
  lang: cn  # Optional, ce(中英文混合)/en(英文在线)/cn(中文在线)/sichuantone-mix(中川)/cantonese-mix(中粤)，不设置时使用中文在线.
  product_source: dui  # Optional, 渠道分类，默认dui
```
可根据需要，自定义识别功能。
指定配置文件、音频的scp列表文件和输出文件
```
aispeech_lasr_stream.py -c lasr_stream.yaml wav.scp results.txt
```
其中scp列表文件由key和音频地址组成。
```
test-1 /home/test1.wav
test-2 /home/test2.wav
```
## 短语音转写
### 使用方式
需要安装websockets包。
```
pip install websockets
```
编辑配置文件，填写有效的productId和apikey。
指定配置文件、音频的scp列表文件和输出文件。
```
aispeech_casr.py -c casr.yaml wav.scp results.txt
```
其中scp列表文件由key和音频地址组成。
```
test-1 /home/test1.wav
test-2 /home/test2.wav
```
### 切换场景
修改配置文件中的`res`字段。
```
query:
  productId: ''  # 必填，客户编号，唯一
  apikey: ''  # 必填，apikey
  res: aiuniversal  # 一路模型资源名称，区分大小写，需要和资源名称完全一致
  lang: zh-CN
...
```
## 录音文件转写
### 使用方式
需要安装requests包。
```
pip install requests
```
修改脚本中的配置项，必须填写pid和apikey，识别功能可自行选择。
```
PRODUCT_ID  = '' # 必填
API_KEY     = '' # 必填

SAMPLE_RATE = 16000  # 采样率
USE_TXT_SMOOTH = 0  # 顺滑开关
USE_INVERSE_TXT = 0  # 逆文本开关 
SPEAK_NUMBER = 0  # 说话人，-1代表盲分
USE_SEGMENT = 0  # 是否按分词输出
USE_AUX = 0 # 是否开启情绪
LANG= 'cn' # 语种
LM_ID='' # 二路语言模型ID
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
### 切换语种
修改脚本里，全局变量`LANG`的值。