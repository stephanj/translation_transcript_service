import asyncio
import websockets
import whisper
import os
import logging
import sys
import glob
import json

from chatgpt import check_api_key, translate_text, summarize_text

global recording_path 
recording_path = "recording"

global file_number
file_number = 0


logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

def remove_old_files():
    """
    Remove the old files from the recording folder.
    """
    file_pattern = recording_path + '/*.*'
    files_to_remove = glob.glob(file_pattern)

    for file in files_to_remove:
        try:
            os.remove(file)
            logging.info(f"Removed file: {file}")
        except OSError as e:
            logging.error(f"Error removing file {file}: {e}")


async def websocket_handler(websocket, model):
    """
    Handle the websocket connection requests.
    """
    
    while True:
        # Receive the JSON string containing source and target languages
        logging.info("--------------------------------------------------------------------")
        
        logging.info("Waiting for source/target language info...")
        lang_info_json = await websocket.recv()        
        lang_info = json.loads(lang_info_json)
        source_lang = lang_info['sourceLang']
        target_lang = lang_info['targetLang']

        full_transcript_file_path = os.path.join(recording_path, "full_transcript.txt")
                
        logging.info(f"Translate from '{source_lang}' to '{target_lang}'") 
                
        # Browser requested summary of the transcript
        if source_lang == "summary":
            await create_summary(websocket, full_transcript_file_path)
        else:
            await handle_translation(websocket, model, source_lang, target_lang, full_transcript_file_path);


def get_file_number():
    global file_number
    file_number = file_number + 1
    return file_number
    

async def handle_translation(websocket, model, source_lang, target_lang, full_transcript_file_path):
    """
    Handle the translation of the audio file.
    """
    logging.info("Waiting for client to request audio file")
    audio_data = await websocket.recv()

    file_name = "recording_{}".format(get_file_number())
    audio_file = "{}.webm".format(file_name)
    audio_file_path = os.path.join(recording_path, audio_file)

    write_to_file(audio_file_path, audio_data, "wb")
    logging.info(f"Received audio file: {audio_file}")

    # Transcribe the audio file    
    try:
        text = model.transcribe(audio_file_path)['text']

        logging.info(f"Transcribed text: {text}")

        if len(text.strip()) > 3:        
            # Save the original text to a file                
            transcript_file = f"{file_name}.txt"
            transcript_file_path = os.path.join(recording_path, transcript_file)
            write_to_file(transcript_file_path, text)

            # Save the translated text to a file            
            translated_text = translate_text(text, source_lang, target_lang)

            translated_file = f"{file_name}_{target_lang}.txt"
            translated_file_path = os.path.join(recording_path, translated_file)
            write_to_file(translated_file_path, translated_text)
            
            # Append translation to transcript
            write_to_file(full_transcript_file_path, text + "\n", "a")

            await websocket.send(translated_text)
        else:
            logging.info(">>>> No text to translate")         
    except Exception as e:
        logging.error(" >>>> Error transcribing audio file: {}".format(e))
        

async def create_summary(websocket, full_transcript_file_path):
    """
    Create a summary of the transcript and send it to the browser.
    """    
    with open(full_transcript_file_path, "r") as transcript_file:
        transcript = transcript_file.read()
    
    summary_text = summarize_text(transcript)
    logging.info(f"Summary: {summary_text}")

    summary_file_path = os.path.join(recording_path, "summary.txt")
    write_to_file(summary_file_path, summary_text)

    await websocket.send(summary_text)


def load_model():
    """
    Load the model from the model folder.
    """
    logging.info("Loading 'base' whisper model...")
    model = whisper.load_model("base")
    return model


def write_to_file(file_path, text, mode="w"):
    """
    Write the given text to the given file.
    """
    with open(file_path, mode) as f:
        f.write(text)


def run_websocket_server(model):
    """
    Run the websocket server on port 8000
    """
    
    while True:
        try:
            logging.info("Starting WebSocket server...")

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

    # Remove the recording_*.* files before running this script
    remove_old_files()

    if not os.path.exists(recording_path):
        os.mkdir(recording_path)

    model = load_model()

    # Load the model outside the websocket_handler function to avoid reloading the model for each connection    
    run_websocket_server(model)