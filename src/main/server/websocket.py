import asyncio
import websockets
import os
import logging
import sys
import glob
import openai 
import whisper 
import json

from dotenv import load_dotenv

recording_path = "recording"
DELAY_BETWEEN_AUDIO_CHUNKS = 20     # in seconds

languages = {"en": "English", "fr": "French", "es": "Spanish", "nl": "Dutch"}

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

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


def remove_old_files():
    """
    Remove the old files from the recording folder.
    """
    file_pattern = recording_path + '/recording_*.*'
    files_to_remove = glob.glob(file_pattern)

    for file in files_to_remove:
        try:
            os.remove(file)
            logging.info(f"Removed file: {file}")
        except OSError as e:
            logging.error(f"Error removing file {file}: {e}")


def load_model():
    """
    Load the model from the model folder.
    """
    logging.info("Loading 'base' whisper model...")
    model = whisper.load_model("base")
    return model

def translate(text, source_lang, target_lang):     
    """
    Translate the given text to French using OpenAI's GPT-3 API.
    """           
    messages = [
        {"role": "system", "content": "You are a translator expert."},
        {"role": "user", "content": f"Translate this text from {languages[source_lang]} to {languages[target_lang]}, only return the translated text : {text}"}
    ];
    
    logging.info("messages: " + str(messages));
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-0301",
        messages=messages
    )

    translation_txt = response["choices"][0]["message"]["content"]
    logging.info("Translating text: " + text + " to " + translation_txt)
    
    return translation_txt


async def websocket_handler(websocket, model):
    """
    Handle the websocket connection.
    """
    file_number = 1
    

    while True:
        # Receive the JSON string containing source and target languages
        logging.info("--------------------------------------------------------------------")
        logging.info("Waiting for source/target language info...")
        lang_info_json = await websocket.recv()
        lang_info = json.loads(lang_info_json)
        source_lang = lang_info['sourceLang']
        target_lang = lang_info['targetLang']

        logging.info(f"Translate from {languages[source_lang]} to {languages[target_lang]}") 
                
        logging.info("Waiting for client to request audio file")
        audio_data = await websocket.recv()

        file_name = "recording_{}".format(file_number)
        audio_file = "{}.webm".format(file_name)
        audio_file_path = os.path.join("recording", audio_file)

        with open(audio_file_path, "wb") as f:
            f.write(audio_data)

        logging.info(f"Received audio file: {audio_file}")

        # Transcribe the audio file    
        try:
            text = model.transcribe(audio_file_path)

            logging.info(f"Transcribed text: {text['text']}")

            if len(text['text']) > 0:        
                transcript_file = f"{file_name}.txt"
                transcript_file_path = os.path.join("recording", transcript_file)

                # Save the original text to a file
                with open(transcript_file_path, "w") as f:
                    f.write(text['text'])        
                
                # Translate the text
                translated_text = translate(text['text'], source_lang, target_lang)
                logging.info(f"Translated text: {translated_text}")

                # Save the translated text to a file
                translated_file = f"{file_name}_{target_lang}.txt"
                translated_file_path = os.path.join("recording", translated_file)

                with open(translated_file_path, "w") as f:
                    f.write(translated_text)        
                
                await websocket.send(translated_text)
            else:
                logging.info(">>>> No text to translate")         
        except Exception as e:
            logging.error(" >>>> Error transcribing audio file: {}".format(e))
        
        # Increment the file_number after processing each audio file
        file_number += 1

        await asyncio.sleep(DELAY_BETWEEN_AUDIO_CHUNKS)  # Adjust the delay between file reads as needed


def run_websocket_server(model):
    """
    Run the websocket server on port 8000
    """
    
    while True:
        try:
            logging.info("Starting WebSocket server...")
            # start_server = websockets.serve(websocket_handler, "localhost", 8000)
            start_server = websockets.serve(lambda ws: websocket_handler(ws, model), "localhost", 8000)
            
            loop = asyncio.get_event_loop()
            loop.run_until_complete(start_server)
            loop.run_forever()
        except Exception as e:
            logging.info(f"WebSocket server encountered an error: {e}")
            logging.info("Restarting WebSocket server...")
            # Add a delay to prevent the server from restarting too quickly if the error is persistent
            asyncio.sleep(5)


if __name__ == "__main__":
    check_api_key()

    # Remove the recording_?.txt files before running this script
    remove_old_files()

    if not os.path.exists(recording_path):
        os.mkdir(recording_path)

    # Load the model outside the websocket_handler
    model = load_model()

    run_websocket_server(model)