// Start, stop and summary buttons
const startButton = document.getElementById('start');
const stopButton = document.getElementById('stop');

// Language select elements
const sourceLangSelect = document.getElementById('source-lang');
const targetLangSelect = document.getElementById('target-lang');

// Translated text element
const translatedTextElement = document.getElementById('translatedText'); 

let ws; // Declare the WebSocket variable
let mediaRecorder;
let chunks = [];
let recordingInterval;
let langInfo
let audioBlob;
let sendInterval = 20 * 1000;   // Send audio every 20 seconds
let isRecording = false;
let processSummary = false;


/**
 * Set the translated text in the HTML element
 * @param {*} text 
 */
function setTranslatedText(text) {
    translatedTextElement.innerHTML = text;
}

/**
 * Start websocket, media recorder and interval to send audio to server
 */
async function startRecording(event) {

    console.warn("> Starting recording...");

    isRecording = true;
    
    setActionButtons();

    setupWebSocket();

    startMediaRecorder();

    setInterval(sendAudio, sendInterval);

    event.stopPropagation(); // Stop event propagation
}

/**
 * Stop/Start media recorder, this will trigger the audio to be send to the WebSocket server
 */
function sendAudio() {
    if (isRecording) {
        mediaRecorder.stop();         // MediaRecorder using slicing doesn't work, so we stop it and start it again
        mediaRecorder.start();        // And lets start the recording again for the next audio chunk
    } 
}

function setActionButtons() {
    startButton.disabled = isRecording;
    stopButton.disabled = !startButton.disabled;
}

/**
 * Setup the WebSocket connection
 */
function setupWebSocket() {
    // Initialize the WebSocket connection
    ws = new WebSocket("ws://localhost:8000");

    ws.onopen = () => {
        console.warn(">> WebSocket connection established.");
        setTranslatedText("Recording started...");
    };
    
    ws.onmessage = (event) => {
        console.warn(">>>>> Received translated text:", event);
        if (processSummary) {
            createAudioAndPlay(event.data);            
        } else {
            setTranslatedText(event.data); 
        }
    };

    ws.onclose = () => {
        console.warn(">>>>> WebSocket connection closed."); 
        setTranslatedText("Recording stopped...");
        isRecording = false;
        setActionButtons();    
    };

    ws.onerror = (error) => {
        isRecording = false;
        console.error("WebSocket error:", error);
        setTranslatedText("Error: " + error);
    };
}

/**
 * Start recording audio from the user's microphone
 */
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

/**
 * Get the source and target languages
 * @returns a JSON string with the source and target languages
 */
function getLanguageInfo() {
    return JSON.stringify({
        sourceLang: sourceLangSelect.value,
        targetLang: targetLangSelect.value
    });
}

/**
 * Stop recording audio from the user's microphone
 */
async function stopRecording(event) {
    isRecording = false;
    setActionButtons();

    mediaRecorder.stop();
    mediaStream.getTracks().forEach(track => track.stop());
    ws.close();

    event.stopPropagation(); // Stop event propagation
}

/**
 * Process the summary of the transcript and play it.
 * This method will be called every second until the summary slide is displayed.
 */
function checkForSummarySlide() {
    // Wait for the summary slide to be displayed then process the summary of the transcript and play it
    setInterval(function() {
        // This is the Keynote slide ID of the summary slide
        const summarySlide = document.getElementById('A0F2796350957B06BF8095A489AD6E72');
        if (summarySlide && !processSummary) {                                
            processSummary = true;       
            console.warn("Summary slide detected, process summary and play audio");
            ws.send(JSON.stringify({
                sourceLang: "summary",
                targetLang: targetLangSelect.value
            }));
        }
    }, 1000); // 1 second wait

}

/**
 * Create an audio from the summary and play it
 * @param {*} summary 
 */
function createAudioAndPlay(summary) {
    console.warn("Create audio from : " + summary);

    // Call elevenLabs API
    const apiKey = config.audioKey;
    const voiceId = 'gUSxfaE7egCWuKIqUd4J'; // Antonio's voice (almost) :)

    // The body of the request is the text to be synthesized
    const requestOptions = {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'xi-api-key': apiKey
    },
    body: JSON.stringify({ text: summary })
    };

    // Call the API
    fetch(`https://api.elevenlabs.io/v1/text-to-speech/${voiceId}`, requestOptions)
    .then(response => response.blob())
    .then(blob => {
        // Use the audio blob to play the audio
        const audioUrl = URL.createObjectURL(blob);
        console.warn("Summary audio URL: " + audioUrl);
        
        const audio = new Audio(audioUrl);
        audio.play().then(() => {
            console.warn("Audio played");
            processSummary = false;
        });
    })
    .catch(error => {
        console.error('Error:', error);
        alert("Something went wrong during audio creation: " + error);
    });
}

startButton.addEventListener('click', startRecording);
stopButton.addEventListener('click', stopRecording);

sourceLangSelect.addEventListener('click', (event) => {
    console.warn("Source language changed to: " + event.target.value);
    event.stopPropagation();
});

targetLangSelect.addEventListener('click', (event) => {
    console.warn("Target language changed to: " + event.target.value);
    event.stopPropagation();
});

checkForSummarySlide();