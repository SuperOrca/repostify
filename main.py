import json
import math
import os
import random
import textwrap

import praw
import subtitle_parser
from dotenv import load_dotenv
import pyttsx3
from moviepy.editor import AudioFileClip, CompositeVideoClip, TextClip, VideoFileClip
from subsai import SubsAI

load_dotenv()


with open("config.json") as file:
    CONFIG = json.load(file)

reddit = praw.Reddit(
    client_id=CONFIG["reddit"]["id"],
    client_secret=CONFIG["reddit"]["secret"],
    user_agent="python 3.11",
)


def get_filtered_posts():
    subreddit = reddit.subreddit(random.choice(CONFIG["reddit"]["subreddits"]))
    return [
        post
        for post in subreddit.top(
            time_filter=CONFIG["reddit"]["time_filter"], limit=100
        )
        if CONFIG["reddit"]["length"]["min"]
        <= len(post.selftext)
        <= CONFIG["reddit"]["length"]["max"]
        and not post.over_18
    ]


post = random.choice(get_filtered_posts())
text = post.selftext

tts = pyttsx3.init()
tts.setProperty("rate", 160)
tts.setProperty("volume", 1.0)
voices = tts.getProperty("voices")
tts.setProperty("voice", voices[0].id)
tts.save_to_file(text, "temp.mp3")
tts.runAndWait()

subs_ai = SubsAI()
model = subs_ai.create_model("openai/whisper", {"model_type": "base"})
subs = subs_ai.transcribe("temp.mp3", model)
subs.save("temp.srt")

with open("temp.srt", "r") as file:
    parser = subtitle_parser.SrtParser(file)
    parser.parse()

time = lambda t: t[1] * 60 + t[2] + t[3] / 1000

text_clips = []
duration = 0
for subtitle in parser.subtitles:
    start = time(subtitle.start)
    end = time(subtitle.end)

    text_clips.append(
        TextClip(
            "\n".join(textwrap.wrap(subtitle.text, width=CONFIG["text"]["width"])),
            fontsize=CONFIG["text"]["size"],
            color="white",
            font=CONFIG["text"]["font"],
        )
        .set_position(("center", CONFIG["text"]["height"]))
        .set_duration(end - start)
        .set_start(start)
    )

duration = sum(t.duration for t in text_clips)

audio_clip = AudioFileClip("temp.mp3")
audio_clip.set_duration(audio_clip.duration)

background_clip = VideoFileClip(CONFIG["background"])
start = random.randint(
    0, math.floor(background_clip.duration - duration - CONFIG["excess"])
)
background_clip = background_clip.subclip(
    start, start + duration + CONFIG["excess"]
).set_audio(audio_clip)

video = CompositeVideoClip([background_clip, *text_clips])
video.write_videofile(f"output/{post.id}.mp4", codec="libx264")

audio_clip.close()
background_clip.close()
os.remove("temp.srt")
os.remove("temp.mp3")

print(
    f"""
r/{post.subreddit}
-
u/{post.author}
-
#aita #reddit #amitheasshole #yta #nta #esh #redditstories #redditposts #redditmeme #rslash #redditadvice #advice #nah #daily #redditopinions #opinion #reels
"""
)
