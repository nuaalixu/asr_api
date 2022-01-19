#!/usr/bin/env python

import asyncio
from hmac import trans_36
import websockets
import json
import argparse
import logging
import os.path as path
import urllib.parse as urlparse
import concurrent


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


MAX_WORKER = 10
LOGIN = "secret"
URL = urlparse.urlparse("wss://lasr.duiopen.com/live/ws2")

QUERY = {
    "productId": "",  # 客户编号，唯一
    "apikey": "",  # apikey
    "deviceId": "",  # Optional, 本次连接所使用的设备ID，建议唯一，以方便界定问题（deviceId和device_id设置其中一个）
    "forward_addresses": "",  # Optional, 当参数不为空时，启动转发模式。 当有转写结果时，会往注册的WebSocket地址实时推送转写结果。支持多个转写websocket服务地址，多个地址中间用英文逗号 , 隔开。格式： ws://xxxx:port,ws://xxxx:port,ws://xxxx:port
    "res": "aitranson",  # Optional, 默认aitranson长语音实时在线
    "lang": "cn",  # Optional, ce(中英文混合)/en(英文在线)/cn(中文在线)/sichuantone-mix(中川)/cantonese-mix(中粤)，不设置时使用中文在线.
    "product_source": "dui"  # Optional, 渠道分类，默认dui
}

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

def get_login():
    """Get and store pid*apikey.
    """
    if path.exists(LOGIN) and path.getsize(LOGIN) != 0:
        with open(LOGIN, 'r', encoding='utf8') as f:
            pid = f.readline().rstrip()
            key = f.readline().rstrip()
        logger.info(f'Use previous productId {pid} and apikey {key}.')
    else:
        pid = input("PID: ")
        key = input("KEY: ")
        with open(LOGIN, 'w', encoding='utf8') as f:
            f.write(pid + "\n")
            f.write(key + "\n")
    return pid, key


def set_url(**kargs):
    """Set url parameters.
    """
    global QUERY
    for k, v in kargs.items():
        if QUERY.get(k, None) is None:
            logger.error(f"Query parameter {k} is not defined.")
        else:
            QUERY[k] = v

    global URL
    URL = URL._replace(query=urlparse.urlencode(QUERY))


def set_params(**kargs):
    """Set request parameters.
    """
    global PARAMS
    for k, v in kargs.items():
        if PARAMS.get(k, None) is None:
            logger.error(f"Request parameter {k} is not defined.")
        else:
            PARAMS[k] = v


async def start(websocket):
    """Start a new ASR task."""
    PARAMS["command"] =  "start"
    params = json.dumps(PARAMS)
    await websocket.send(params)
    logger.info(f"Request parameters:{params}")
    greeting = json.loads(await websocket.recv())
    if greeting['errno'] == 7:
        logger.info(f"Start transcription.")
    else:
        logger.error(f"{greeting}\nConnection failed.")


async def feed(audio, websocket, stride=0.04, size=1280):
    """Read and Send audio data streamly.

    Args:
        audio (str): audio file path.
        websocket ([type]): webSocket client connection.
        stride (float, optional): interval for sending data. Defaults to 0.04.
        size (int, optional): bytes of data to send every time. Defaults to 1280.
    """
    with open(audio, 'rb') as f:
        while True:
            data = f.read(size)
            if data: 
                await websocket.send(data)
                await asyncio.sleep(stride)
            else:
                await websocket.send(b'')   
                return


async def get(websocket):
    """Fetch and display ASR transciption."""
    data = []
    while True:
        response = await websocket.recv()
        response= json.loads(response)
        errno = response.get('errno')
        if errno == 8:
            logger.info(f"{response.get('data')}")  # for extension
        elif errno == 0:
            logger.info(f"{response.get('data')}")
            data.append(response.get('data').get('onebest'))
        elif errno == 9:
            logger.info(f"{response.get('data')}")
            data.append(response.get('data').get('onebest'))
            return data
        elif errno == 10:
            logger.error(f"Data format error.")
            raise
        else:
            logger.error(f"{response}\nService exception.")
            raise


async def request(audio, url):
    """Entry of a request of ASR.

    Args:
        audio (str): audio file path.
        url (str): target url.
    """
    async with websockets.connect(url) as websocket:
        await start(websocket)
        task1 = asyncio.create_task(feed(audio, websocket))
        task2 = asyncio.create_task(get(websocket))

        await task1   
        data = await task2

        return "".join(data)


def run(record):
    """ A running thread for ASR.

    Args:
        record (str): a record which consist of key and value.

    Returns:
        str: ASR transcription.
    """
    url = URL.geturl()
    key, audio = record.rstrip().split(maxsplit=1)
    result = asyncio.run(request(audio, url))
    return f'{key}\t{result}\n'
    

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("in_scp", type=str, help="Input scp file which consisit of key and value.")
    parser.add_argument("out_trans", type=str, help="Output asr transcription.")
    parser.add_argument("--params", type=str, help="switch request parameters string in JSON.")
    parser.add_argument("--lang", type=str, help="switch language. Defaults to cn.")
    args = parser.parse_args()
    
    if args.params:
        my_params = json.loads(args.params)
        set_params(**my_params)
    
    if args.lang:
        set_url(lang=args.lang)
    
    pid, key = get_login()
    set_url(productId=pid, apikey=key)
    
    in_scp = args.in_scp
    out_trans = args.out_trans
    url = URL.geturl()
    logger.info(f'URL:{url}')
    
    try:
        audio_list_fd = open(in_scp, 'r', encoding='utf8')
        trans_file_fd = open(out_trans, 'w', encoding='utf8')
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKER)
        tasks = [executor.submit(run, record) for record in audio_list_fd]
        for future in concurrent.futures.as_completed(tasks):
            data = future.result()
            trans_file_fd.write(data)
    finally:
        audio_list_fd.close()
        trans_file_fd.close()
    

