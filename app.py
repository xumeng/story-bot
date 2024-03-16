import streamlit as st
import os
import json
import requests
import azure.cognitiveservices.speech as speechsdk

# LLM model config
MODEL_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
MODEL_NAME = "glm-3-turbo"
MODEL_TOKEN = os.getenv("GLM_MODEL_TOKEN")
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {MODEL_TOKEN}",
}
MAX_TOKENS = 1000

# tts config
speech_key = os.getenv("AZURE_SPEECH_KEY")
service_region = os.getenv("AZURE_REGION")
if not speech_key or not service_region:
    st.error("Missing speech key or region in configuration")
speech_config = speechsdk.SpeechConfig(subscription=speech_key, region=service_region)
speech_config.speech_synthesis_voice_name = "zh-CN-XiaoyouNeural"
speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config)

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
    "故事主题:", placeholder="在这里写下你的故事主题梗概，如奥特曼大战怪兽"
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

story_length = st.slider("故事长度(大约字数):", max_value=500, min_value=100, step=50)


def tts(text: str):
    result = speech_synthesizer.speak_text_async(text).get()
    # Check result
    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("Speech synthesized for text [{}]".format(text))
    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = result.cancellation_details
        print("Speech synthesis canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            print("Error details: {}".format(cancellation_details.error_details))


if "gen_story_content" not in st.session_state:
    st.session_state.gen_story_content = ""
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
                "content": f"故事主题:{story_topic}故事类型:{story_type_str},内容{story_length}字左右",
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
        else:
            st.write("request failed ", response.status_code)
if "gen_story_content" in st.session_state:
    st.write(st.session_state.gen_story_content)

if st.button("朗读故事"):
    if st.session_state.gen_story_content:
        with st.spinner("朗读故事中.."):
            tts(st.session_state.gen_story_content)
    else:
        st.write("还没有生成故事")
