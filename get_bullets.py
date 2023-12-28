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
import asyncio
import functools
from concurrent.futures import ProcessPoolExecutor


loop = asyncio.get_event_loop()
process_executor = ProcessPoolExecutor(max_workers=1)


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
async def tts(text: str) -> None:
    url = os.environ.get("TTS_ENDPOINT")
    resp = await loop.run_in_executor(
        None,
        functools.partial(
            requests.get,
            url,
            params={
                "text": requests.utils.quote(text),
                "sdp_ratio": 0.2,
                "noise_scale": 0.6,
                "noise_scale_w": 0.8,
                "length_scale": 1.0
            }))
    temp_audio = io.BytesIO(resp.content)
    rate, data = scipy.io.wavfile.read(temp_audio)
    data = data * float(os.environ.get('VOLUME'))
    await loop.run_in_executor(
        process_executor,
        functools.partial(
            sd.play,
            data,
            rate,
            blocking=True
        )
    )


@common.wrap_log_ts
async def gpt(text: str, bk: list[dict[str, str]]) -> str:
    if not (text.startswith("::") or text.startswith("：：")): return None
    endpoint = os.environ.get("AZURE_ENDPOINT")
    api_key = os.environ.get("AZURE_API_KEY")
    model = os.environ.get("AZURE_MODEL")
    url = f"{endpoint}/openai/deployments/{model}/chat/completions?api-version=2023-03-15-preview"
    messages = [
        {
            "role": "system",
            "content": "你是个中文助手, 同时是个万能的女仆, 你的名字叫做小鸣, 说话要像木之本櫻一样可爱, 需要保证你的回复少于一百字. "
        },
        {
            "role": "user",
            "content": text
        }
    ]
    messages.extend(bk)
    new_message = {
        "role": "user",
        "content": text
    }
    messages.append(new_message)
    resp = await loop.run_in_executor(
        None, 
        functools.partial(requests.post, 
        url=url,
        headers={"Content-Type": "application/json", "api-key": api_key},
        json={
            "messages": messages
        }
        )
    )
    if resp.json()['choices'][0]['finish_reason'] == "content_filter":
        return "呼呼呼!!!小鸣决定不回答这个问题!"
    re_message = resp.json()['choices'][0]['message']
    bk.append(new_message)
    bk.append(
        {
            "role": re_message['role'],
            "content": re_message['content']
        }
    )
    return resp.json()['choices'][0]['message']['content']

@common.wrap_log_ts
async def gemini(text: str, bk: list[dict[str, str]]) -> str:
    if not (text.startswith("--") or text.startswith("——")): return None
    endpoint = "https://generativelanguage.googleapis.com/"
    model = "gemini-pro:generateContent"
    api_key = os.environ.get("GEMINI_API_KEY")
    url = f"{endpoint}v1/models/{model}?key={api_key}"
    contents = [
        {
            "role": "user",
            "parts": [
                {
                    "text": "你是个中文助手, 同时是个万能的女仆, 你的名字叫做小鸣, 说话要像木之本櫻一样可爱, 需要保证你的回复少于一百字."
                }
            ]
        },
        {
            "role": "model",
            "parts": [
                {
                    "text": "小鸣一定遵守."
                }
            ]
        },
    ]
    contents.extend(bk)
    new_message = {
        "role": "user",
        "parts": [
                {
                    "text": text
                }
        ]
    }
    contents.append(new_message)
    resp = await loop.run_in_executor(
        None,
        functools.partial(
            requests.post,
            url=url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": contents
            }
        )
    )
    re_message = resp.json()['candidates'][0]['content']
    bk.append(new_message)
    bk.append(re_message)
    return re_message['parts'][0]['text']



async def loop_main() -> None:
    simple_bk = []
    simple_gpt_bk = []
    simple_gemini_bk = []
    while True:
        start_ts = common.now_ts()
        try:
            re = get_bullets(os.environ.get("ROOM_ID"))
            start = 0 if len(re)-5<0 else len(re)-5
            for i in range(start, len(re)):
                text = re[i][1]
                if text in simple_bk: continue
                try:
                    await tts(text)
                    simple_gpt_bk = simple_gpt_bk[-10:]
                    gpt_re = await gpt(text, bk=simple_gpt_bk)
                    if gpt_re != None: await tts(gpt_re[:120])
                    simple_gemini_bk = simple_gemini_bk[-10:]
                    gemini_re = await gemini(text, bk=simple_gemini_bk)
                    if gemini_re != None: await tts(gemini_re[:120])
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
    loop.run_until_complete(loop_main())
    # test()

