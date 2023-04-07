import os
import logging
import sys
import openai 
from time import sleep
import sys
import logging
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

languages = {"en": "English", "fr": "French", "es": "Spanish", "nl": "Dutch", "gr": "Greek", "it": "Italian", "pt": "Portuguese", "ja": "Japanese", "zh": "Chinese"}

def check_api_key():
    """
    Check that the OPENAI_API_KEY environment variable is set.    
    """
    load_dotenv()
    openai.api_key = os.getenv('OPENAI_API_KEY')
    if not openai.api_key:
        logging.info("OPENAI_API_KEY environment variable not found. Exiting the app.")
        logging.info("Please set the OPENAI_API_KEY environment variable in the .env file.  See the README for more details.")
        sys.exit(1)


def summarize_text(text):
    """
    Summarize the given text using OpenAI's GPT-3 API.
    """
    messages = [
        {"role": "system", "content": "You are a translator expert."},
        {"role": "user", "content": f"Summarize the following text into two sentences : {text}, only return the summary text"}
    ];
    return call_chat_gpt(messages)    
    


def translate_text(text, source_lang, target_lang):     
    """
    Translate the given text to French using OpenAI's GPT-3 API.
    """    
    messages = [
        {"role": "system", "content": "You are a translator expert."},
        {"role": "user", "content": f"Translate this text from {languages[source_lang]} to {languages[target_lang]}, only return the translated text : {text}"}
    ];
    return call_chat_gpt(messages)    
    
    
def call_chat_gpt(messages):
    """
    Call the OpenAI Chat GPT API.
    """
    max_retry = 5
    sleep_duration_in_seconds = 1
    
    while True:
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo-0301",
                messages=messages
            )

            return response["choices"][0]["message"]["content"]
        
        except Exception as oops:
            logging.error(oops)
            
            retry += 1

            if retry >= max_retry:
                return None
            
            logging.error(f"GPT3 error: {oops} ... Retrying in 1 second") 
            sleep(sleep_duration_in_seconds)
