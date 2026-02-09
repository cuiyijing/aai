"""
Gradio Demo App - Interactive AI Interface
Run with: python demo_app.py
"""

import gradio as gr
from datetime import datetime


def greet(name: str, intensity: int) -> str:
    """Generate a personalized greeting"""
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        time_greeting = "Good morning"
    elif 12 <= current_hour < 18:
        time_greeting = "Good afternoon"
    else:
        time_greeting = "Good evening"
    
    emojis = "😀" * intensity
    return f"{time_greeting}, {name}! {emojis}"


def analyze_sentiment(text: str) -> dict:
    """Simple sentiment analysis demo"""
    positive_words = ['good', 'great', 'love', 'amazing', 'excellent', 'happy', 'awesome']
    negative_words = ['bad', 'terrible', 'hate', 'awful', 'poor', 'sad', 'worst']
    
    text_lower = text.lower()
    pos_count = sum(1 for word in positive_words if word in text_lower)
    neg_count = sum(1 for word in negative_words if word in text_lower)
    
    if pos_count > neg_count:
        sentiment = "Positive 😊"
        confidence = min(0.95, 0.5 + (pos_count - neg_count) * 0.15)
    elif neg_count > pos_count:
        sentiment = "Negative 😞"
        confidence = min(0.95, 0.5 + (neg_count - pos_count) * 0.15)
    else:
        sentiment = "Neutral 😐"
        confidence = 0.5
    
    return {"sentiment": sentiment, "confidence": round(confidence, 2)}


def text_to_emoji(text: str) -> str:
    """Convert text keywords to emojis"""
    replacements = {
        'hello': '👋', 'hi': '👋',
        'love': '❤️', 'heart': '❤️',
        'happy': '😊', 'smile': '😊',
        'sad': '😢', 'cry': '😢',
        'fire': '🔥', 'hot': '🔥',
        'cool': '😎', 'awesome': '😎',
        'star': '⭐', 'like': '⭐',
        'computer': '💻', 'code': '💻',
        'python': '🐍', 'snake': '🐍',
        'party': '🎉', 'celebrate': '🎉',
        'music': '🎵', 'song': '🎵',
    }
    
    result = text
    for word, emoji in replacements.items():
        result = result.replace(word, emoji)
        result = result.replace(word.capitalize(), emoji)
    return result


# Theme configuration
theme = gr.themes.Soft(
    primary_hue="indigo",
    secondary_hue="purple",
    neutral_hue="slate",
)

with gr.Blocks(title="AI Demo App") as demo:
    gr.Markdown(
        """
        # 🚀 Gradio Demo App
        *Interactive AI/ML Interface Demo*
        
        Explore three interactive demos below!
        """
    )
    
    with gr.Tabs():
        with gr.TabItem("👋 Greeting Generator"):
            gr.Markdown("Enter your name and choose intensity for a personalized greeting!")
            with gr.Row():
                name_input = gr.Textbox(
                    label="Your Name",
                    placeholder="Enter your name...",
                    scale=2
                )
                intensity_slider = gr.Slider(
                    minimum=1,
                    maximum=10,
                    value=5,
                    label="Emoji Intensity",
                    scale=1
                )
            greet_btn = gr.Button("Generate Greeting 🎉", variant="primary")
            greet_output = gr.Textbox(label="Your Greeting", interactive=False)
            
            greet_btn.click(
                fn=greet,
                inputs=[name_input, intensity_slider],
                outputs=greet_output
            )
        
        with gr.TabItem("🎭 Sentiment Analyzer"):
            gr.Markdown("Type some text to analyze its sentiment!")
            sentiment_input = gr.Textbox(
                label="Enter Text",
                placeholder="Try: I love this amazing product! or This is terrible...",
                lines=3
            )
            analyze_btn = gr.Button("Analyze Sentiment 🔍", variant="secondary")
            
            with gr.Row():
                sentiment_output = gr.Label(label="Sentiment Result")
                confidence_output = gr.Number(label="Confidence Score")
            
            analyze_btn.click(
                fn=analyze_sentiment,
                inputs=sentiment_input,
                outputs=[sentiment_output, confidence_output]
            )
        
        with gr.TabItem("😀 Emoji Converter"):
            gr.Markdown("Type text and convert keywords to emojis!")
            emoji_input = gr.Textbox(
                label="Enter Text",
                placeholder="Type: I love Python and code!",
                lines=3
            )
            emoji_btn = gr.Button("Convert to Emojis ✨", variant="primary")
            emoji_output = gr.Textbox(label="Emoji Version", interactive=False)
            
            emoji_btn.click(
                fn=text_to_emoji,
                inputs=emoji_input,
                outputs=emoji_output
            )
    
    gr.Markdown(
        """
        ---
        *Built with ❤️ using Gradio*
        """
    )


if __name__ == "__main__":
    demo.launch()
