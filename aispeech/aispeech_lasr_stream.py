#!/usr/bin/env python

import asyncio
from pathlib import Path
import websockets
import json
import yaml
from yaml import SafeLoader
import argparse
import logging
import urllib.parse as urlparse
import concurrent
import uuid

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s:%(levelname)s:%(message)s", datefmt='%Y-%m-%d %H:%M:%S')


MAX_WORKER = 10
URL = urlparse.urlparse("wss://lasr.duiopen.com/live/ws2")


def parse_config(conf):
    with open(conf) as f:
        data = yaml.load(f, Loader=SafeLoader)
    try:
        query = data['query']
        msg = data['msg']
    except KeyError:
        logger.error(f"Parsing config failed, please check the yaml file.")
        raise
    return query, msg


class ASRTask:
    def __init__(self, name, url, params, audio: Path, chunk_size=1280, stride=0.04):
        self.name = name
        self.url = url
        self.params = params
        self.audio = audio
        self.stride = stride
        self.chunk_size = chunk_size

    async def _start(self, websocket):
        """Start a new ASR task."""
        params = json.dumps(self.params)
        await websocket.send(params)
        logger.info(f"Requset params:{params}")
        greeting = json.loads(await websocket.recv())
        if greeting['errno'] == 7:
            logger.info(f"Start transcription.")
        else:
            logger.error(f"{greeting}\nConnection failed.")

    async def _feed(self, websocket):
        """Read and Send audio data streamly.

        Args:
            audio (str): audio file path.
            websocket ([type]): webSocket client connection.
            stride (float, optional): interval for sending data. Defaults to 0.04.
            size (int, optional): bytes of data to send every time. Defaults to 1280.
        """
        with open(self.audio, 'rb') as f:
            while True:
                data = f.read(self.chunk_size)
                if data: 
                    await websocket.send(data)
                    await asyncio.sleep(self.stride)
                else:
                    await websocket.send(b'')   
                    return
    
    async def _get(self, websocket):
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

    async def naive_task(self):
        """Run a naive task.
        """
        async with websockets.connect(self.url) as websocket:
            await self._start(websocket)
            task1 = asyncio.create_task(self._feed(websocket))
            task2 = asyncio.create_task(self._get(websocket))

            await task1   
            data = await task2
            return "".join(data)
    
    def run(self, task: str="naive"):
        if task == "naive":
            self.result = asyncio.run(self.naive_task())
        else:
            raise NotImplementedError(f'task type {task} is not supported yet.')
        return self


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("in_scp", type=str, help="Input scp file which consisit of key and value.")
    parser.add_argument("out_trans", type=str, help="Output asr transcription.")
    parser.add_argument("-c", dest="conf", required=True, type=str, help="Yaml file of configuration.")
    args = parser.parse_args()

    query, params = parse_config(args.conf)
    url = URL._replace(query=urlparse.urlencode(query)).geturl()
    in_scp = args.in_scp
    out_trans = args.out_trans
    logger.info(f'URL:{url}')

    audio_list_fd = open(in_scp, 'r', encoding='utf8')
    trans_file_fd = open(out_trans, 'w', encoding='utf8')   
    try:

        executor = concurrent.futures.ProcessPoolExecutor(max_workers=MAX_WORKER)
        tasks = []
        for record in audio_list_fd:
            try:
                key, audio = record.rstrip().split(maxsplit=1)
            except ValueError:
                audio = record.rstrip()
                key=uuid.uuid1()
            asr_task = ASRTask(key, url, params, audio)
            tasks.append(executor.submit(asr_task.run, "naive"))

        for future in concurrent.futures.as_completed(tasks):
            asr_task = future.result()
            trans_file_fd.write(f'{asr_task.name}\t{asr_task.result}\n')
    finally:
        audio_list_fd.close()
        trans_file_fd.close()
