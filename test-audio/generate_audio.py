"""Generate test audio files using Edge TTS."""
import asyncio
import edge_tts

SCRIPTS = {
    "01_beginner.mp3": (
        "Hello, my name is John. I am from India. "
        "I like reading books and watching movies. "
        "Yesterday I visitted my friend and we eated dinner together. "
        "It was very enjoyful."
    ),
    "02_intermediate.mp3": (
        "Good morning everyone. Today I want to talk about healthy lifestyle. "
        "People should excercise every day and eat vegetables regularly. "
        "Many peoples thinks that sleeping five hour is enough, but it is not. "
        "If you take care of your body, your life become much better."
    ),
    "03_advanced.mp3": (
        "Artificial intelligence is changing the world very fast. "
        "Many companies are investing heavily in machine learning and automation. "
        "However, it is important to use these technologies responsible. "
        "Sometimes peoples depends too much on AI without checking the information carefully. "
        "I believes that AI should assist humans instead of replacing them completely."
    ),
    "04_phoneme_difficult.mp3": (
        "The squirrel quietly climbed through the rural neighborhood. "
        "She bought a comfortable pair of clothes at the jewelry store. "
        "The sixth athlete successfully solved the statistical problem. "
        "The brewery produced three hundred fresh beverages. "
        "The architecture of the library is extraordinary."
    ),
}

# Use a voice with slight non-native accent feel for realism
# en-IN (Indian English) works well for beginner/intermediate
# en-US for the phoneme-difficult one
VOICE_MAP = {
    "01_beginner.mp3": "en-IN-PrabhatNeural",
    "02_intermediate.mp3": "en-IN-NeerjaNeural",
    "03_advanced.mp3": "en-US-GuyNeural",
    "04_phoneme_difficult.mp3": "en-US-JennyNeural",
}


async def generate_all():
    for filename, text in SCRIPTS.items():
        voice = VOICE_MAP[filename]
        print(f"Generating {filename} with voice {voice}...")
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(filename)
        print(f"  Done: {filename}")


if __name__ == "__main__":
    asyncio.run(generate_all())
