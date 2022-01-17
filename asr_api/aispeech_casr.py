#!/usr/bin/env python

import asyncio
from email.mime import audio
import websockets
import json
import argparse
import logging
import os.path as path
import urllib.parse as urlparse

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

LOGIN = "secret"
URL = urlparse.urlparse("wss://asr.dui.ai/runtime/v2/recognize")

QUERY = {
    "productId": "",  # 客户编号，唯一
    "apikey": "",  # apikey
    "res": "aiuniversal",  # 一路模型资源名称，区分大小写，需要和资源名称完全一致
    "lang": "zh-CN",  # Optional, 不传此参数时默认使用中文
}

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
    params = json.dumps(PARAMS)
    await websocket.send(params)
    logger.info(f"Request parameters:{params}")
    return


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
    while True:
        response = await websocket.recv()
        response= json.loads(response)
        errno = response.get('eof')
        if errno == 0:
            logger.info(f"{response.get('result')}")  # for extension
        elif errno == 1:
            logger.info(f"{response.get('result')}")
            return
        else:
            logger.error(f"{response}\nService exception.")
            return


async def test(audio, url):
    """Entry of asr test.

    Args:
        audio (str): audio file path.
        url (str): target url.
    """
    async with websockets.connect(url) as websocket:
        await start(websocket)
        task1 = asyncio.create_task(feed(audio, websocket))
        task2 = asyncio.create_task(get(websocket))

        await task1   
        await task2

        logger.info(f"End.")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("audio", type=str, help="Input audio file.")
    parser.add_argument("--res", type=str, help="Select asr resource. Defaults to aiuniversal.")
    args = parser.parse_args()
    
    pid, key = get_login()
    PARAMS['context']['productId'] = pid
    set_url(productId=pid, apikey=key)
    if args.res:
        set_url(res=args.res)
    audio = args.audio
    url = URL.geturl()
    logger.info(f'URL:{url}')
    asyncio.run(test(audio, url))
