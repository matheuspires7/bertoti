import ollama
from smolagents import CodeAgent, tool
from tools.final_answer import FinalAnswerTool
from Gradio_UI import GradioUI
import yaml
from transformers import pipeline
from itertools import islice
from youtube_comment_downloader import *


class OllamaModelWrapper:
    def __init__(self, model_name: str):
        self.model_name = model_name

    def generate(self, prompt: str, **kwargs):
        response = ollama.chat(
            model=self.model_name,
            messages=[{"role": "user", "content": str(prompt)}]
        )
        
        print(response)

        if 'text' in response:
            return response['text']
        elif 'message' in response:
            return response['message']
        else:
            return "Unexpected response format"

    def __call__(self, prompt: str, **kwargs):
        return self.generate(prompt, **kwargs)

# Initialize the model
model = OllamaModelWrapper(model_name="qwen2.5:3b")

final_answer = FinalAnswerTool()

# Initialize the sentiment analyzer
sentiment_analyzer = pipeline("sentiment-analysis")

@tool
def get_yt_comment(link: str, max_comments: int = 50) -> str:
    """A tool that fetches comments from a YouTube video and returns them as a single string with a descriptive context.
    Args:
        link: The YouTube video URL.
        max_comments: The maximum number of comments to retrieve.
    """
    try:
        downloader = YoutubeCommentDownloader()  # type: ignore
        comments = []
        for comment in downloader.get_comments_from_url(link, sort_by=SORT_BY_POPULAR):  # type: ignore
            comments.append(comment['text'])
            if len(comments) >= max_comments:
                break
        
        # Prepend a descriptive sentence and join the comments into a single string
        comment_string = "\n".join(comments)
        return f"These are the top {len(comments)} comments from the video:\n{comment_string}"
    except Exception as e:
        return f"Error fetching comments: {str(e)}"
    
@tool
def analyze_sentiment_of_comments(comments: str) -> str:
    """
    Analyzes the sentiment of YouTube comments to determine the overall reception.
    
    Args:
        comments (str): A string containing the YouTube comments.
    
    Returns:
        str: A summary of the sentiment analysis (positive, negative, or neutral).
    """
    try:
        comment_list = comments.split("\n")
        sentiments = [sentiment_analyzer(comment)[0] for comment in comment_list if len(comment.strip()) > 0]
        positive_count = sum(1 for sentiment in sentiments if sentiment['label'] == 'POSITIVE')
        negative_count = sum(1 for sentiment in sentiments if sentiment['label'] == 'NEGATIVE')
        if positive_count > negative_count:
            return f"The overall reception is positive. Positive comments: {positive_count}, Negative comments: {negative_count}."
        elif negative_count > positive_count:
            return f"The overall reception is negative. Positive comments: {positive_count}, Negative comments: {negative_count}."
        else:
            return f"The overall reception is neutral. Positive comments: {positive_count}, Negative comments: {negative_count}."
    except Exception as e:
        return f"Error during sentiment analysis: {str(e)}"

with open("prompts.yaml", 'r') as stream:
    prompt_templates = yaml.safe_load(stream)

agent = CodeAgent(
    model=model,
    tools=[final_answer, get_yt_comment, analyze_sentiment_of_comments],
    max_steps=6,
    verbosity_level=1,
    prompt_templates=prompt_templates
)

GradioUI(agent).launch()
