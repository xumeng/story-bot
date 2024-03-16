import streamlit as st
import os
import json
import requests
import base64
import azure.cognitiveservices.speech as speechsdk

# env var config
# MODEL_TOKEN = os.getenv("GLM_MODEL_TOKEN")
# speech_key = os.getenv("AZURE_SPEECH_KEY")
# service_region = os.getenv("AZURE_REGION")

MODEL_TOKEN = st.secrets["GLM_MODEL_TOKEN"]
speech_key = st.secrets["speech_service"]["AZURE_SPEECH_KEY"]
service_region = st.secrets["speech_service"]["AZURE_REGION"]

# LLM model config
MODEL_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL_NAME = "glm-3-turbo"
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {MODEL_TOKEN}",
}
MAX_TOKENS = 1000

if not st.session_state.keys():
    st.session_state.gen_story_content = ""
    st.session_state.voice_type = ""


# tts config
if not speech_key or not service_region:
    st.error("Missing speech key or region in configuration")
speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
file_name = "outputaudio.wav"
file_config = speechsdk.audio.AudioOutputConfig(filename=file_name)


# prompt config
STORY_PROMPT = """你是一位擅长讲故事的机器人，你的任务是根据用户提供的关键词和方向构造出适合小朋友和胎教使用的故事。
技能1:分析用户的输入，从中提取关键词或主题。根据关键词或主题，利用相应的故事模板来生成故事。
技能2:适当地调整故事情节.让故事具有适合小朋友和胎教使用的情节与话题。调整故事的情节以满足用户的需要，如增加教育元素，强调家庭价值观等。
限制:只讨论与故事创作相关的话题。保持提供的故事在各方面都贴近小朋友和胎教的需要.
下面开始创作故事."""

# ui config
st.title("故事机器人")
st.subheader("请在下面输入你的故事主题和元素，并选择故事类型和长度")

story_topic = st.text_area(
    "故事主题:",
    placeholder="在这里写下你的故事主题梗概，如奥特曼大战怪兽",
    max_chars=100,
)

story_type = [
    "童话",
    "神话",
    "科幻",
    "奇幻",
    "悬疑",
    "历史",
    "冒险",
    "幽默",
    "教育",
    "动物",
    "友情",
    "玩具",
]
story_type_choice = st.multiselect("故事类型:", story_type)

voice_type = ["小女孩", "大姐姐", "大哥哥"]
voice_type_values = [
    "zh-CN-XiaoyouNeural",
    "zh-CN-XiaoxiaoNeural",
    "zh-CN-YunfengNeural",
]
voice_types = {
    "小女孩": "zh-CN-XiaoyouNeural",
    "大姐姐": "zh-CN-XiaoxiaoNeural",
    "大哥哥": "zh-CN-YunfengNeural",
}

voice_type_choice = st.selectbox("声音类型:", list(voice_types.keys()))

story_length = st.slider("故事长度(大约字数):", max_value=500, min_value=100, step=50)
st.session_state.voice_type = voice_types[voice_type_choice]


def autoplay_audio(file_path: str):
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f"""
            <audio controls autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(
            md,
            unsafe_allow_html=True,
        )


def tts(text: str):
    speech_config.speech_synthesis_voice_name = st.session_state.voice_type
    speech_synthesizer = speechsdk.SpeechSynthesizer(
        speech_config=speech_config, audio_config=file_config
    )
    result = speech_synthesizer.speak_text_async(text).get()
    # Check result
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("Speech synthesized for text [{}]".format(text))

        autoplay_audio(file_name)
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print("Speech synthesis canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))


if st.button("生成故事"):
    with st.spinner("生成故事中"):
        story_type_str = ", ".join(story_type_choice)
        default_messages = [
            {
                "role": "user",
                "content": STORY_PROMPT,
            },
            {
                "role": "user",
                "content": f"故事主题:{story_topic},故事类型:{story_type_str},内容限制字数{story_length}字以内",
            },
        ]

        data = json.dumps(
            {
                "model": MODEL_NAME,
                "messages": default_messages,
                "max_tokens": MAX_TOKENS,
            }
        )
        response = requests.post(MODEL_URL, headers=headers, data=data)

        if response.status_code == 200:
            story_response = response.json()
            story = story_response.get("choices")[0].get("message").get("content")
            st.session_state.gen_story_content = story

            st.write(st.session_state.gen_story_content)
        else:
            st.write("生成失败, 请稍后重试 ", response.status_code)
    if st.session_state.gen_story_content:
        with st.spinner("生成音频中"):
            tts(st.session_state.gen_story_content)
