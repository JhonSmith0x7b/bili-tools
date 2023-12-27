import requests
import json
import sounddevice as sd
import numpy
import json
import time
import traceback
import os
import io
import scipy.io.wavfile
from dotenv import load_dotenv
load_dotenv()
import datetime
import logging
import common


def get_bullets(room_id:str) -> list[tuple[str, str]]:
    url = f"https://api.live.bilibili.com/xlive/web-room/v1/dM/gethistory?roomid={room_id}&room_type=0"
    # api return ten bullets
    headers = {
        "authority": "api.live.bilibili.com",
        "accept": "application/json",
        "accept-language": "zh-CN",
        "origin": "https://live.bilibili.com",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    }
    resp = requests.get(url, headers=headers)
    data = json.loads(resp.text)
    re = []
    room = data['data']['room']
    for line in room:
        re.append((line['nickname'], line['text']))
    return re


@common.wrap_log_ts
def tts(text: str) -> None:
    url = os.environ.get("TTS_ENDPOINT")
    resp = requests.get(url, params={
        "text": requests.utils.quote(text),
        "sdp_ratio": 0.2,
        "noise_scale": 0.6,
        "noise_scale_w": 0.8,
        "length_scale": 1.0
    })
    temp_audio = io.BytesIO(resp.content)
    rate, data = scipy.io.wavfile.read(temp_audio)
    data = data * 3
    sd.play(data, rate, blocking=True)


@common.wrap_log_ts
def gpt(text: str) -> str:
    if not (text.startswith("::") or text.startswith("：：")): return None
    endpoint = os.environ.get("AZURE_ENDPOINT")
    api_key = os.environ.get("AZURE_API_KEY")
    model = os.environ.get("AZURE_MODEL")
    url = f"{endpoint}/openai/deployments/{model}/chat/completions?api-version=2023-03-15-preview"
    resp = requests.post(
        url=url,
        headers={"Content-Type": "application/json", "api-key": api_key},
        json={
            "messages": [
                {
                    "role": "system",
                    "content": "你是个中文助手, 同时是个万能的女仆, 说话要像木之本櫻一样可爱, 需要保证你的回复少于30字. "
                },
                {
                    "role": "user",
                    "content": text
                }
            ]
        }
    )
    if resp.json()['choices'][0]['finish_reason'] == "content_filter":
        return "呼呼呼!!!小鸣决定不回答这个问题!"
    return resp.json()['choices'][0]['message']['content']


def loop_main() -> None:
    simple_bk = []
    while True:
        start_ts = common.now_ts()
        try:
            re = get_bullets(os.environ.get("ROOM_ID"))
            start = 0 if len(re)-5<0 else len(re)-5
            for i in range(start, len(re)):
                text = re[i][1]
                if text in simple_bk: continue
                try:
                    tts(text)
                    gpt_re = gpt(text)
                    if gpt_re != None: tts(gpt_re[:30])
                except Exception as e:
                    print(e)
                    traceback.print_exc()
                simple_bk.append(text)
            simple_bk = simple_bk[len(simple_bk)-100:]
        except Exception as e:
            print(e)
            traceback.print_exc()
        sleep_second = 5 - int(common.now_ts() - start_ts)
        if sleep_second<0:sleep_second=0
        logging.info(f"next loop after {sleep_second}s")
        time.sleep(sleep_second)


def test() -> None:
    re = gpt("::测试弹幕")
    tts(re)



if __name__ == '__main__':
    common.init_log("bullets_")
    loop_main()
    # test()

