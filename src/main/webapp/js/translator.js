const startButton = document.getElementById('start');
const stopButton = document.getElementById('stop');
const sourceLangSelect = document.getElementById('source-lang');
const targetLangSelect = document.getElementById('target-lang');
const translatedTextElement = document.getElementById('translatedText'); 

let ws; // Declare the WebSocket variable
let mediaRecorder;
let chunks = [];
let recordingInterval;
let langInfo
let audioBlob;
let sendInterval = 20 * 1000;   // Send audio every 20 seconds
let isRecording = false;

function setTranslatedText(text) {
    translatedTextElement.innerHTML = text;
}

async function startRecording() {

    console.warn("> Starting recording...");

    isRecording = true;
    stopButton.disabled = !isRecording;
    startButton.disabled = isRecording;
    
    setupWebSocket();

    startMediaRecorder();

    setInterval(sendAudio, sendInterval);
}

function sendAudio() {
    if (isRecording) {
        mediaRecorder.stop();         // MediaRecorder using slicing doesn't work, so we stop it and start it again
        mediaRecorder.start();        // And lets start the recording again for the next audio chunk
    } 
}

function setupWebSocket() {
    // Initialize the WebSocket connection
    ws = new WebSocket("ws://localhost:8000");

    ws.onopen = () => {
        console.warn(">> WebSocket connection established.");
        setTranslatedText("Recording started...");
    };
    
    ws.onmessage = (event) => {
        console.warn(">>>>> Received translated text:", event);
        setTranslatedText(event.data); 
    };

    ws.onclose = () => {
        console.warn(">>>>> WebSocket connection closed."); 
        setTranslatedText("Recording stopped...");
        isRecording = false;
        startButton.disabled = false;
        stopButton.disabled = !startButton.disabled;
    };

    ws.onerror = (error) => {
        isRecording = false;
        console.error("WebSocket error:", error);
        setTranslatedText("Error: " + error);
    };
}

//
// Start recording audio from the user's microphone
// 
async function startMediaRecorder() {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(mediaStream);
    mediaRecorder.start(); 
    isRecording = true;

    mediaRecorder.ondataavailable = (event) => {
        console.warn(">>>>> Received audio data, add to chunks", event);
        chunks.push(event.data);
    };

    mediaRecorder.onstop = (event) => {
        console.warn(">>>>> MediaRecorder stopped", event);
        
        console.log(">>>>> Sending language data to the WebSocket server...");
        ws.send(getLanguageInfo());    
        
        console.log(">>>>> Sending audio blob to the WebSocket server...");
        const audioBlob = new Blob(chunks, { type: 'audio/mpeg' });
        ws.send(audioBlob);

        chunks = [];
    }
}

function getLanguageInfo() {
    // Send the source and target languages to the WebSocket server as a JSON string
    return JSON.stringify({
        sourceLang: sourceLangSelect.value,
        targetLang: targetLangSelect.value
    });
}

async function stopRecording() {
    isRecording = false;
    startButton.disabled = isRecording;
    stopButton.disabled = !isRecording;

    mediaRecorder.stop();
    mediaStream.getTracks().forEach(track => track.stop());
    ws.close();
}

startButton.addEventListener('click', startRecording);
stopButton.addEventListener('click', stopRecording);
