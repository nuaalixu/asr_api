#!/usr/bin/env python3

import uuid
import os
import sys
import requests
import json
import argparse
import logging
import time
import concurrent.futures
from os import path


PRODUCT_ID  = ''
API_KEY     = ''
LASR_TASK_URL = 'http://lasr.duiopen.com/lasr-file-api/v2'
LOGIN = "secret"  # file to save pid & apikey

SAMPLE_RATE = 16000  # 采样率
USE_TXT_SMOOTH = 0  # 顺滑开关
USE_INVERSE_TXT = 0  # 逆文本开关 
SPEAK_NUMBER = 0  # 说话人，-1代表盲分
USE_SEGMENT = 0  # 是否按分词输出
USE_AUX = 0 # 是否开启情绪
LANG= 'cn'
LM_ID=''

SLICE_LEN   = 2 * 1024 * 1024
TMP_FOLDER  = ".slices"


def get_login():
    """Get and store pid&apikey.
    """
    if path.exists(LOGIN) and path.getsize(LOGIN) != 0:
        with open(LOGIN, 'r', encoding='utf8') as f:
            pid = f.readline().rstrip()
            key = f.readline().rstrip()
        logging.info(f'Use previous productId {pid} and apikey {key}.')
    else:
        pid = input("PID: ")
        key = input("KEY: ")
        with open(LOGIN, 'w', encoding='utf8') as f:
            f.write(pid + "\n")
            f.write(key + "\n")
    return pid, key


def abort(step, reason):
    logging.error("[ %s ] %s", step ,reason)
    raise RuntimeError


def empty_tmp_folder():
    if not os.path.exists(TMP_FOLDER):
        os.mkdir(TMP_FOLDER)
    else:
        for f in os.listdir(TMP_FOLDER):
            os.remove(os.path.join(TMP_FOLDER, f))


def upload_audio(audio, audio_type, path):
    AUDIO_API_URL = '{}/audio'.format(LASR_TASK_URL)

    audio_file = open(path, 'rb')
    x_session_id = ''.join(str(uuid.uuid4()).split('-'))[0]
    audio_file.seek(0, 2)
    size = audio_file.tell()
    slice_num, other = divmod(size, SLICE_LEN)
    if other > 0: slice_num += 1
    params  = dict(audio_type = audio_type, slice_num = slice_num)
    headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Connection": "close",
            "x-sessionId": x_session_id
        }

    resp = requests.post(
            str.format("{}?productId={}&apiKey={}", AUDIO_API_URL, PRODUCT_ID, API_KEY),
            data = params,
            headers = headers)

    audio_id = None

    if resp.status_code == 200:
        json = resp.json()

        if json:
            errno = json["errno"]
            if errno:
                abort('upload', 'failed create audio. res: {}'.format(resp.text))
            else:
                audio_id = json['data']["audio_id"]
        else:
            abort('upload', 'failed create audio. res: {}'.format(resp.text))
    else:
        abort('upload', 'failed create audio. code: {}, res: {}'.format(resp.status_code, resp.text))

    if audio_id:
        slice_index = 0

        while slice_index < slice_num:
            audio_file.seek(slice_index * SLICE_LEN)

            slice_file_path = os.path.join(TMP_FOLDER, audio + "." + str(slice_index))
            slice_f = open(slice_file_path, 'wb')
            slice_data = audio_file.read(SLICE_LEN)
            slice_f.write(slice_data)
            slice_f.close()

            url = str.format('{}/{}/slice/{}?productId={}&apiKey={}', AUDIO_API_URL, audio_id, slice_index, PRODUCT_ID, API_KEY)
            files = { 'file': open(slice_file_path, 'rb') }

            headers = {
                "x-sessionId": x_session_id,
            }
            resp = requests.post(url, files = files, headers = headers)

            if resp.status_code == 200:
                json = resp.json()

                if json:
                    errno = json["errno"]
                    if errno:
                        abort('upload', 'failed upload audio slice. res: {}'.format(resp.text))
                    else:
                        logging.info('audio: %s, id: %s, slice %d uploaded.', audio, audio_id, slice_index)
                        slice_index += 1
                else:
                    abort('upload', 'failed upload audio slice. res: {}'.format(resp.text))
            else:
                abort('upload', 'failed upload audio slice. code: {}, res: {}'.format(resp.status_code, resp.text))

    return audio_id


def create_task(audio, audio_type, audio_id):
    data = dict(
        #debug = 1,
		lang = LANG,
        audio_type = audio_type,
        audio_id = audio_id,
        sample_rate = SAMPLE_RATE,
        speaker_number = SPEAK_NUMBER,
        use_txt_smooth = USE_TXT_SMOOTH,
        use_inverse_txt = USE_INVERSE_TXT,
        use_segment = USE_SEGMENT,
        use_aux = USE_AUX,
        enableConfidence = True,
		lmid = LM_ID
        )

    resp = requests.post(LASR_TASK_URL + "/task?productId={0}&apiKey={1}".format(PRODUCT_ID, API_KEY), data=data)
    if resp.status_code == 200:
        jsonr = resp.json()
        errno = jsonr.get('errno', 1)
        if errno == 0:
            data = jsonr['data']
            return data['task_id']
        else:
            abort('task', 'failed create task. audio: {}, errno: {}, error: {}'.format(audio, errno, jsonr['error']))
    else:
        abort('task', 'failed create task. audio: {}, status code: {}, error: {}'.format(audio, resp.status_code, resp.text))


def query_progress(audio, task_id):
    resp = requests.get("{0}/task/{1}/progress?productId={2}&apiKey={3}".format(LASR_TASK_URL, task_id, PRODUCT_ID, API_KEY))

    if resp.status_code == 200:
        jsonr = resp.json()
        errno = jsonr.get('errno', 1)
        if errno == 0:
            data = jsonr['data']
            return data['progress']
        else:
            abort('task', 'failed query progress. audio: {}, task: {}, errno: {}, error: {}'.format(audio, task_id, errno, jsonr['error']))
    else:
        abort('task', 'failed query progress. audio: {}, task: {}, status code: {}, error: {}'.format(audio, task_id, resp.status_code, resp.text))


def get_result(audio, task_id):
    resp = requests.get("{0}/task/{1}/result?productId={2}&apiKey={3}".format(LASR_TASK_URL, task_id, PRODUCT_ID, API_KEY))

    if resp.status_code == 200:
        jsonr = resp.json()
        errno = jsonr.get('errno', 1)
        if errno == 0:
            data = jsonr['data']['result']
            data = [rec['onebest'] for rec in data]
        else:
            abort('task', 'failed save result. audio: {}, task: {}, errno: {}, error: {}'.format(audio, task_id, errno, jsonr['error']))
    else:
        abort('task', 'failed save result. audio: {}, task: {}, status code: {}, error: {}'.format(audio, task_id, resp.status_code, resp.text))
    
    return "".join(data)


def run(record):
    key, audio = record.rstrip().split(maxsplit=1)
    try:
        logging.info("Begin translate audio: %s, path: %s", key, audio)
        audio_type = audio.rsplit('.')[-1]

        audio_id = upload_audio(key, audio_type, audio)
        logging.info("Finished uploaded. audio: %s, path: %s, audio id: %s", key, audio, audio_id)
        task_id = create_task(key, audio_type, audio_id)

        while True:
            progress = query_progress(key, task_id)
            logging.info("Translating audio: %s, task id: %s, progress: %d", key, task_id, progress)

            if progress >= 100:
                result = get_result(audio, task_id)
                logging.info("Finished translate audio: %s, task id: %s", key, task_id)
                return f'{key}\t{result}\n'
            else:
                time.sleep(1)
    except RuntimeError:
        return 0


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s][%(levelname)-5s] %(message)s - %(filename)s[line:%(lineno)d]'
    )

    parser = argparse.ArgumentParser()
    parser.add_argument('-nproc', '--nproc', dest='nproc', type=int, default=1, help='number of parallel jobs')
    parser.add_argument('in_scp', help='Input scp file which consisit of key and value.')
    parser.add_argument('out_trans', help='Output asr transcription.')

    args = parser.parse_args()
    in_scp = args.in_scp
    out_trans = args.out_trans
    nproc = args.nproc

    pid, key = get_login()
    PRODUCT_ID = pid
    API_KEY = key
    try:
        audio_list_fd = open(in_scp, 'r', encoding='utf8')
        trans_file_fd = open(out_trans, 'w', encoding='utf8')
        empty_tmp_folder()
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=nproc)
        tasks = [executor.submit(run, record) for record in audio_list_fd]
        for future in concurrent.futures.as_completed(tasks):
            data = future.result()
            trans_file_fd.write(data)
            trans_file_fd.flush()
    finally:
        audio_list_fd.close()
        trans_file_fd.close()
