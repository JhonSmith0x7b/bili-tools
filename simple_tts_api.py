import sys
sys.path.append("./bert_vits2")
import os
import torch
from bert_vits2 import utils
from bert_vits2.infer import infer, latest_version, get_net_g, get_text
from bert_vits2.tools.sentence import split_by_language
import numpy
import flask
import json
import requests
import io
import datetime
import scipy.io.wavfile
import logging
import common
import numpy as np
from dotenv import load_dotenv
from bert_vits2.oldVersion.V220.clap_wrapper import get_clap_text_feature
load_dotenv(override=True)


device = (
        "cuda:0"
        if torch.cuda.is_available()
        else (
            "mps"
            if sys.platform == "darwin" and torch.backends.mps.is_available()
            else "cpu"
        )
    )
if device == "mps":
    # os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
    # device = "cpu"
    pass
os.environ["TOKENIZERS_PARALLELISM"] = "false"
print(device)
model_path = os.environ.get("TTS_MODEL_PATH")
hps = utils.get_hparams_from_file(os.environ.get("TTS_CONFIG_PATH"))
version = hps.version if hasattr(hps, "version") else latest_version
net_g = get_net_g(
    model_path=model_path, version=version, device=device, hps=hps
)

convert_map = {
    "A": "厄",
    "B": "闭",
    "C": "啬",
    "D": "迪",
    "E": "衣",
    "F": "福",
    "G": "记",
    "H": "吃",
    "I": "爱",
    "J": "这",
    "K": "客",
    "L": "捱",
    "M": "慕",
    "N": "嗯",
    "O": "鸥",
    "P": "屁",
    "Q": "秋",
    "R": "啊",
    "S": "斯",
    "T": "踢",
    "U": "呦",
    "V": "喂",
    "W": "大",
    "X": "斯",
    "Y": "歪",
    "Z": "贼"
}

def en2cn(text: str):
    new_text = ""
    for c in text:
        new_text += convert_map.get(c.upper(), c)
    return new_text


def process_auto(text):
    _text, _lang = [], []
    for slice in text.split("|"):
        if slice == "":
            continue
        temp_text, temp_lang = [], []
        sentences_list = split_by_language(slice, target_languages=["zh", "ja", "en"])
        for sentence, lang in sentences_list:
            if sentence == "":
                continue
            temp_text.append(sentence)
            temp_lang.append(lang.upper())
        _text.append(temp_text)
        _lang.append(temp_lang)
    return _text, _lang


def infer_multilang(
    text,
    sdp_ratio,
    noise_scale,
    noise_scale_w,
    length_scale,
    sid,
    language,
    hps,
    net_g,
    device,
    reference_audio=None,
    emotion=None,
    skip_start=False,
    skip_end=False,
):
    bert, ja_bert, en_bert, phones, tones, lang_ids = [], [], [], [], [], []
    # emo = get_emo_(reference_audio, emotion, sid)
    # if isinstance(reference_audio, np.ndarray):
    #     emo = get_clap_audio_feature(reference_audio, device)
    # else:
    #     emo = get_clap_text_feature(emotion, device)
    # emo = torch.squeeze(emo, dim=1)
    for idx, (txt, lang) in enumerate(zip(text, language)):
        _skip_start = (idx != 0) or (skip_start and idx == 0)
        _skip_end = (idx != len(language) - 1) or skip_end
        (
            temp_bert,
            temp_ja_bert,
            temp_en_bert,
            temp_phones,
            temp_tones,
            temp_lang_ids,
        ) = get_text(txt, lang, hps, device)
        if _skip_start:
            temp_bert = temp_bert[:, 3:]
            temp_ja_bert = temp_ja_bert[:, 3:]
            temp_en_bert = temp_en_bert[:, 3:]
            temp_phones = temp_phones[3:]
            temp_tones = temp_tones[3:]
            temp_lang_ids = temp_lang_ids[3:]
        if _skip_end:
            temp_bert = temp_bert[:, :-2]
            temp_ja_bert = temp_ja_bert[:, :-2]
            temp_en_bert = temp_en_bert[:, :-2]
            temp_phones = temp_phones[:-2]
            temp_tones = temp_tones[:-2]
            temp_lang_ids = temp_lang_ids[:-2]
        bert.append(temp_bert)
        ja_bert.append(temp_ja_bert)
        en_bert.append(temp_en_bert)
        phones.append(temp_phones)
        tones.append(temp_tones)
        lang_ids.append(temp_lang_ids)
    bert = torch.concatenate(bert, dim=1)
    ja_bert = torch.concatenate(ja_bert, dim=1)
    en_bert = torch.concatenate(en_bert, dim=1)
    phones = torch.concatenate(phones, dim=0)
    tones = torch.concatenate(tones, dim=0)
    lang_ids = torch.concatenate(lang_ids, dim=0)
    with torch.no_grad():
        x_tst = phones.to(device).unsqueeze(0)
        tones = tones.to(device).unsqueeze(0)
        lang_ids = lang_ids.to(device).unsqueeze(0)
        bert = bert.to(device).unsqueeze(0)
        ja_bert = ja_bert.to(device).unsqueeze(0)
        en_bert = en_bert.to(device).unsqueeze(0)
        # emo = emo.to(device).unsqueeze(0)
        x_tst_lengths = torch.LongTensor([phones.size(0)]).to(device)
        del phones
        speakers = torch.LongTensor([hps.data.spk2id[sid]]).to(device)
        if version == '2.2.2':
            emotion = "Happy"
            emo = get_clap_text_feature(emotion, device)
            emo = torch.squeeze(emo, dim=1)
            audio = (
                net_g.infer(
                    x_tst,
                    x_tst_lengths,
                    speakers,
                    tones,
                    lang_ids,
                    bert,
                    ja_bert,
                    en_bert,
                    emo=emo,
                    sdp_ratio=sdp_ratio,
                    noise_scale=noise_scale,
                    noise_scale_w=noise_scale_w,
                    length_scale=length_scale,
                )[0][0, 0]
                .data.cpu()
                .float()
                .numpy()
            )
            del (
                x_tst,
                tones,
                lang_ids,
                bert,
                x_tst_lengths,
                speakers,
                ja_bert,
                en_bert,
            ) 
        else:
            audio = (
                net_g.infer(
                    x_tst,
                    x_tst_lengths,
                    speakers,
                    tones,
                    lang_ids,
                    bert,
                    ja_bert,
                    en_bert,
                    sdp_ratio=sdp_ratio,
                    noise_scale=noise_scale,
                    noise_scale_w=noise_scale_w,
                    length_scale=length_scale,
                )[0][0, 0]
                .data.cpu()
                .float()
                .numpy()
            )
            del (
                x_tst,
                tones,
                lang_ids,
                bert,
                x_tst_lengths,
                speakers,
                ja_bert,
                en_bert,
            )  # , emo
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        return audio


@common.wrap_log_ts
def simple_audio(
    text: str,
    language: str = 'ZH',
    sdp_ratio: float = 0.2,
    noise_scale: float = 0.6,
    noise_scale_w: float = 0.8,
    length_scale: float = 1.0
) -> tuple[numpy.ndarray, int]:
    text = en2cn(text)
    bert, ja_bert, en_bert, phones, tones, lang_ids = get_text(text, language, hps, device)
    x_tst = phones.to(device).unsqueeze(0)
    tones = tones.to(device).unsqueeze(0)
    lang_ids = lang_ids.to(device).unsqueeze(0)
    bert = bert.to(device).unsqueeze(0)
    ja_bert = ja_bert.to(device).unsqueeze(0)
    en_bert = en_bert.to(device).unsqueeze(0)
    x_tst_lengths = torch.LongTensor([phones.size(0)]).to(device)
    del phones
    sid = list(hps.data.spk2id.keys())[0]
    speakers = torch.LongTensor([hps.data.spk2id[sid]]).to(device)
    audio = infer(
        text=text,
        sdp_ratio=sdp_ratio,
        noise_scale=noise_scale,
        noise_scale_w=noise_scale_w,
        length_scale=length_scale,
        sid=sid,
        language=language,
        hps=hps,
        net_g=net_g,
        device=device,
        reference_audio=None,
        emotion="Happy",
        skip_start=False,
        skip_end=False
    )
    # audio = (
    #     net_g.infer(
    #         x_tst,
    #         x_tst_lengths,
    #         speakers,
    #         tones,
    #         lang_ids,
    #         bert,
    #         sdp_ratio=sdp_ratio,
    #         noise_scale=noise_scale,
    #         noise_scale_w=noise_scale_w,
    #         length_scale=length_scale,
    #     )[0][0, 0]
    #     .data.cpu()
    #     .float()
    #     .numpy()
    # )
    del x_tst, tones, lang_ids, bert, x_tst_lengths, speakers, ja_bert, en_bert
    return (audio, hps.data.sampling_rate)

@common.wrap_log_ts
def simple_audio_v2(
    text: str,
    sdp_ratio: float = 0.2,
    noise_scale: float = 0.6,
    noise_scale_w: float = 0.8,
    length_scale: float = 1.0
) -> tuple[numpy.ndarray, int]:
    _text, _lang = process_auto(text)
    sid = list(hps.data.spk2id.keys())[0]
    audio_list = []
    for idx, piece in enumerate(_text):
        skip_start = idx != 0
        skip_end = idx != len(_text) - 1
        audio = infer_multilang(
            piece,
            reference_audio=None,
            emotion=None,
            sdp_ratio=sdp_ratio,
            noise_scale=noise_scale,
            noise_scale_w=noise_scale_w,
            length_scale=length_scale,
            sid=sid,
            language=_lang[idx],
            hps=hps,
            net_g=net_g,
            device=device,
            skip_start=skip_start,
            skip_end=skip_end,
        )
        audio_list.append(audio)
    audio_concat = np.concatenate(audio_list)
    del audio_list, _text, _lang
    return (audio_concat, hps.data.sampling_rate)


app = flask.Flask(__name__)


@app.route("/simple-tts")
def simple_tts() -> flask.Response:
    text = flask.request.args.get("text")
    try:
        sdp_ratio = float(flask.request.args.get('sdp_ratio'))
        noise_scale = float(flask.request.args.get('noise_scale'))
        noise_scale_w = float(flask.request.args.get('noise_scale_w'))
        length_scale = float(flask.request.args.get('length_scale'))
    except:
        sdp_ratio = 0.2
        noise_scale = 0.6
        noise_scale_w = 0.8
        length_scale = 1.0
    text = requests.utils.unquote(text)
    if int(version.replace(".", "")) < 23:
        audio, rate = simple_audio(text, sdp_ratio=sdp_ratio, noise_scale=noise_scale, noise_scale_w=noise_scale_w, length_scale=length_scale)
    else:
        audio, rate = simple_audio_v2(text, sdp_ratio=sdp_ratio, noise_scale=noise_scale, noise_scale_w=noise_scale_w, length_scale=length_scale)
    audio_buffer = io.BytesIO()
    scipy.io.wavfile.write(audio_buffer, rate, audio)
    return flask.send_file(
        audio_buffer,
        mimetype="audio/wav"
    )


if __name__ == '__main__':
    common.init_log("tts_")
    app.run("0.0.0.0", "12300")
