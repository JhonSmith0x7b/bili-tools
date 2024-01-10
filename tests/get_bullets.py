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
import multiprocessing
from collections.abc import Callable


LOOP = asyncio.get_event_loop()
Q = multiprocessing.Queue()


def process_play_audio(q: multiprocessing.Queue):
    common.init_log("audio_sub")
    logging.info("audio process start")
    while True:
        audio = q.get()
        try:
            temp_audio = io.BytesIO(audio)
            rate, data = scipy.io.wavfile.read(temp_audio)
            data = data * float(os.environ.get('VOLUME'))
            sd.play(data, rate, blocking=True)
        except Exception as e:
            traceback.print_exc()
            logging.error(f"paly audio error {e}")


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


@common.wrap_log_ts_async
async def tts(text: str) -> None:
    url = os.environ.get("TTS_ENDPOINT")
    resp = await LOOP.run_in_executor(
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
    Q.put(resp.content)


def llm_clo() -> str:
    simple_gpt_bk = []
    gpt = gpt_clo(simple_gpt_bk)
    simple_gemini_bk = []
    gemini = gemini_clo(simple_gemini_bk)
    @common.wrap_log_ts_async
    async def llm_inner(text: str) -> str:
        common.lru_pop(simple_gpt_bk, simple_gemini_bk)
        if (text.startswith("::") or text.startswith("：：")): return await gpt(text)
        if (text.startswith("--") or text.startswith("——")): return await gemini(text)
        return None
    return llm_inner


def gpt_clo(bk: list[dict[str, str]]) -> Callable:
    endpoint = os.environ.get("AZURE_ENDPOINT")
    api_key = os.environ.get("AZURE_API_KEY")
    model = os.environ.get("AZURE_MODEL")
    url = f"{endpoint}/openai/deployments/{model}/chat/completions?api-version=2023-03-15-preview"
    init_prompt = open("./prompts/bullet_init.txt").read()
    error_prompt = open("./prompts/bullet_error.txt").read()
    async def gpt_inner(text) -> str:
        messages = [
            {
                "role": "system",
                "content": init_prompt
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
        resp = await LOOP.run_in_executor(
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
            return error_prompt
        re_message = resp.json()['choices'][0]['message']
        bk.append(new_message)
        bk.append(
            {
                "role": re_message['role'],
                "content": re_message['content']
            }
        )
        return resp.json()['choices'][0]['message']['content']
    return gpt_inner


def gemini_clo(bk: list[dict[str, str]]) -> Callable:
    endpoint = "https://generativelanguage.googleapis.com/"
    model = "gemini-pro:generateContent"
    api_key = os.environ.get("GEMINI_API_KEY")
    url = f"{endpoint}v1/models/{model}?key={api_key}"
    init_prompt = open("./prompts/bullet_init.txt").read()
    error_prompt = open("./prompts/bullet_error.txt").read()
    async def gemini_inner(text: str) -> str:
        contents = [
            {
                "role": "user",
                "parts": [
                    {
                        "text": init_prompt
                    }
                ]
            },
            {
                "role": "model",
                "parts": [
                    {
                        "text": "我一定遵守."
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
        resp = await LOOP.run_in_executor(
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
        try:
            re_message = resp.json()['candidates'][0]['content']
        except Exception as e:
            logging.error(f"gemini error, response is {resp.text}")
            return error_prompt
        bk.append(new_message)
        bk.append(re_message)
        return re_message['parts'][0]['text']
    return gemini_inner



async def loop_main() -> None:
    simple_bk = []
    llm = llm_clo()
    while True:
        start_ts = common.now_ts()
        try:
            re = get_bullets(os.environ.get("ROOM_ID"))
            start = 0 if len(re)-5<0 else len(re)-5
            for i in range(start, len(re)):
                text = re[i][1]
                if text in simple_bk: continue
                try:
                    task_audio = asyncio.ensure_future(tts(text))
                    task_llm = asyncio.ensure_future(llm(text))
                    results = await asyncio.gather(task_audio, task_llm)
                    for result in results:
                        if result is None: continue
                        await tts(result[:120])
                except Exception as e:
                    logging.error(e)
                    traceback.print_exc()
                simple_bk.append(text)
            simple_bk = simple_bk[-100:]
        except Exception as e:
            logging.error(e)
            traceback.print_exc()
        sleep_second = 5 - int(common.now_ts() - start_ts)
        if sleep_second<0:sleep_second=0
        logging.info(f"next loop after {sleep_second}s")
        time.sleep(sleep_second)


def main() -> None:
    multiprocessing.Process(target=process_play_audio, args=(Q,)).start()
    LOOP.run_until_complete(loop_main())


def test() -> None:
    gpt = gpt_clo(bk=[])
    re = gpt("::测试弹幕")
    tts(re)



if __name__ == '__main__':
    common.init_log("bullets_")
    main()
    # test()

