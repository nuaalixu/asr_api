#!/usr/bin/env python

import asyncio
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
URL = urlparse.urlparse("wss://asr.dui.ai/runtime/v2/recognize")

QUERY = {
    "productId": "",  # 客户编号，唯一
    "apikey": "",  # apikey
    "res": "aiuniversal",  # 一路模型资源名称，区分大小写，需要和资源名称完全一致
    "lang": "zh-CN",  # Optional, 不传此参数时默认使用中文
}

PARAMS = {
    "context": {
        "productId": "", # 客户编号，唯一
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
            "enableRealTimeFeedback": False,
            "enableVAD": True,
            "enableTone": False,
            "enablePunctuation": False,
            "enableNumberConvert": False,
            "enableConfidence": True,
            "enableSNTime": True,
            "enableEmotion": True,
            "lmId": "aisichuan-mix_gwm_20220329_v01_rs2", # 可选
            "lmList": ["lm-id","lm-id2"], # 可选
            "phraseHints": [{"type": "vocab", "name": "词库名", "data":["短语1", "短语2"]}] # 热词, 可选, 必须与lmId同时使用, 目前仅支持vocab类型
        }
    }
}


def get_login():
    """Get and store pid&apikey.
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
    data = []
    while True:
        response = await websocket.recv()
        response= json.loads(response)
        errno = response.get('eof')
        if errno == 0:
            logger.info(f"{response.get('result')}")  # for extension
            if response.get('result').get('rec', None) is not None:
                data.append(response.get('result').get('rec'))
        elif errno == 1:
            logger.info(f"{response.get('result')}")
            data.append(response.get('result').get('rec'))
            return data
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
    try:
        result = asyncio.run(request(audio, url))
    except:
        logging.exception(f'Task {key} failed.')
        return None
    else:
        return f'{key}\t{result}\n'


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("in_scp", type=str, help="Input scp file which consisit of key and value.")
    parser.add_argument("out_trans", type=str, help="Output asr transcription.")
    parser.add_argument("--res", type=str, help="Select asr resource. Defaults to aiuniversal.")
    args = parser.parse_args()
    
    pid, key = get_login()
    PARAMS['context']['productId'] = pid
    set_url(productId=pid, apikey=key)
    if args.res:
        set_url(res=args.res)
    
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
            if data := future.result()
                trans_file_fd.write(data)
                trans_file_fd.flush()
    finally:
        audio_list_fd.close()
        trans_file_fd.close()
