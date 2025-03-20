import os
import azure.cognitiveservices.speech as speechsdk
import streamlit as st
import requests
from azure_blob_storage import AzureBlobStorage
from dotenv import load_dotenv
import uuid

# Load environment variables from .env file
load_dotenv()

# Initialize Azure Blob Storage
blob_storage = AzureBlobStorage()

def detect_language(text):
    """
    Detect the language of the given text using Azure Translator.
    """
    endpoint = os.environ.get("AZURE_TRANSLATOR_ENDPOINT")
    key = os.environ.get("AZURE_TRANSLATOR_KEY")
    region = os.environ.get("AZURE_TRANSLATOR_REGION")

    if not endpoint or not key or not region:
        st.error("Azure Translator environment variables are not set correctly.")
        return None

    # Construct the API URL
    api_url = f"{endpoint}/translator/text/v3.0/detect?api-version=3.0"

    # Prepare the request payload
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Ocp-Apim-Subscription-Region": region,
        "Content-Type": "application/json",
        "X-ClientTraceId": str(uuid.uuid4())
    }
    payload = [{"text": text}]

    # Make the API request
    response = requests.post(api_url, headers=headers, json=payload)

    if response.status_code == 200:
        # Extract the detected language
        detected_language = response.json()[0]["language"]
        return detected_language
    else:
        st.error("Failed to detect language.")
        st.write(f"Error: {response.status_code} - {response.text}")
        return None

def translate_text(text, target_language="en"):
    """
    Translate text to the target language using Azure Translator.
    """
    endpoint = os.environ.get("AZURE_TRANSLATOR_ENDPOINT")
    key = os.environ.get("AZURE_TRANSLATOR_KEY")
    region = os.environ.get("AZURE_TRANSLATOR_REGION")

    if not endpoint or not key or not region:
        st.error("Azure Translator environment variables are not set correctly.")
        return None

    # Construct the API URL
    api_url = f"{endpoint}/translator/text/v3.0/translate?api-version=3.0&to={target_language}"

    # Prepare the request payload
    headers = {
        "Ocp-Apim-Subscription-Key": key,
        "Ocp-Apim-Subscription-Region": region,
        "Content-Type": "application/json",
        "X-ClientTraceId": str(uuid.uuid4())
    }
    payload = [{"text": text}]

    # Make the API request
    response = requests.post(api_url, headers=headers, json=payload)

    if response.status_code == 200:
        # Extract the translated text
        translated_text = response.json()[0]["translations"][0]["text"]
        return translated_text
    else:
        st.error("Failed to translate text.")
        st.write(f"Error: {response.status_code} - {response.text}")
        return None

def recognize_from_microphone():
    """
    Perform speech recognition, detect language, and optionally translate the recognized text.
    """
    # Configure Azure Speech SDK
    speech_config = speechsdk.SpeechConfig(
        subscription=os.environ.get('SPEECH_KEY'), 
        region=os.environ.get('SPEECH_REGION')
    )
    speech_config.speech_recognition_language = "en-US"  # Default to English for recognition

    audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
    speech_recognizer = speechsdk.SpeechRecognizer(
        speech_config=speech_config, 
        audio_config=audio_config
    )

    st.write("Speak into your microphone.")
    st.info("Listening...")

    # Perform speech recognition asynchronously and wait for the result
    speech_recognition_result = speech_recognizer.recognize_once_async().get()

    # Check the result of the speech recognition
    if speech_recognition_result.reason == speechsdk.ResultReason.RecognizedSpeech:
        recognized_text = speech_recognition_result.text
        st.success("Recognized Speech:")
        st.write(recognized_text)

        # Detect the language of the recognized text
        detected_language = detect_language(recognized_text)
        if detected_language:
            st.info(f"Detected Language: {detected_language}")

            # Translate the text to English if necessary
            if detected_language != "en":
                translated_text = translate_text(recognized_text, target_language="en")
                if translated_text:
                    st.session_state.recognized_text = translated_text
                    st.info("Translated Text:")
                    st.write(translated_text)
            else:
                st.session_state.recognized_text = recognized_text
        else:
            st.error("Failed to detect language.")
    elif speech_recognition_result.reason == speechsdk.ResultReason.NoMatch:
        st.error("No speech could be recognized.")
        st.write(speech_recognition_result.no_match_details)
    elif speech_recognition_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_recognition_result.cancellation_details
        st.error("Speech Recognition canceled.")
        st.write(f"Reason: {cancellation_details.reason}")
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            st.error("Error details:")
            st.write(cancellation_details.error_details)
            st.warning("Did we set the speech resource key and region values?")

import datetime  # Import datetime for timestamp generation

def generate_resume():
    """
    Generate a resume using Azure OpenAI and upload it to Azure Blob Storage.
    """
    # Check if recognized_text or manually entered text exists
    input_text = st.session_state.get("recognized_text", "") or st.session_state.get("manual_text", "")
    if not input_text:
        st.error("No input text found. Please perform speech recognition or enter text manually.")
        return

    # Detect the language of the input text
    detected_language = detect_language(input_text)
    if not detected_language:
        st.error("Failed to detect the language of the input text.")
        return

    # Translate the input text to English if it's not already in English
    if detected_language != "en":
        st.info(f"Detected Language: {detected_language}. Translating to English...")
        input_text = translate_text(input_text, target_language="en")
        if not input_text:
            st.error("Failed to translate the input text to English.")
            return

    # Collect additional candidate information
    email = st.session_state.get("email", "")
    phone = st.session_state.get("phone", "")

    # Append additional information to the input text
    additional_info = f"""
    Candidate Contact Information:
    - Email: {email}
    - Phone: {phone}
    """
    input_text += "\n\n" + additional_info

    # Azure OpenAI API endpoint, key, and deployment name
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    api_key = os.environ.get("AZURE_OPENAI_API_KEY")
    deployment_name = os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME")

    # Validate environment variables
    if not endpoint or not api_key or not deployment_name:
        st.error("Azure OpenAI environment variables are not set correctly.")
        return


    # Define the prompt for generating a resume
    prompt = f"""
    You are a professional resume writer and Job Coach. Based on the following input, create a structured resume in plain text format in English:
    
    Input: {input_text}
    
    Resume Format:
    - Name:
    - Professional Summary:
    - Key Skills:
    - Work Experience:
    - Education:
    - Certifications:
    - Technical Skills:
    """

    # Azure OpenAI API request
    headers = {
        "Content-Type": "application/json",
        "api-key": api_key
    }
    payload = {
        "messages": [
            {"role": "system", "content": "You are a professional resume writer."},
            {"role": "user", "content": prompt}
        ],
        "model": deployment_name,
        "temperature": 0.7
    }

    # Construct the full API URL
    api_url = f"{endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version=2025-01-01-preview"

    response = requests.post(api_url, headers=headers, json=payload)

    if response.status_code == 200:
        # Extract the generated resume
        resume_text = response.json()["choices"][0]["message"]["content"]
        st.session_state.generated_resume = resume_text  # Store the generated resume in session state
        st.success("Resume Generated Successfully!")

        # Generate a unique file name with a timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"resume_{st.session_state.get('email', 'unknown')}_{timestamp}.txt"

        # Upload the resume to Azure Blob Storage
        try:
            container_name = "resumes"
            upload_message = blob_storage.upload_resume(container_name, file_name, resume_text)
            st.info(upload_message)
        except Exception as e:
            st.error(f"Failed to upload resume to Azure Blob Storage: {e}")
    else:
        st.error("Failed to generate resume.")
        st.write(f"Error: {response.status_code} - {response.text}")
        
# Streamlit app with a descriptive header
st.markdown(
    """
    <style>
    .header-title {
        font-size: 2.5rem;
        color: #4CAF50;
        text-align: center;
        margin-bottom: 0.5rem;
    }
    .header-subtitle {
        font-size: 1.2rem;
        color: #555;
        text-align: center;
        margin-bottom: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown('<div class="header-title">Job Coach AI Speech Recognition & Resume Generator</div>', unsafe_allow_html=True)
st.markdown('<div class="header-subtitle">Transform your clients spoken words into a professional resume effortlessly to empower them for their next role.</div>', unsafe_allow_html=True)

st.title("Speech Recognition and Resume Generator")

# Option to manually enter text
st.write("### Option 1: Enter Candidate Information Manually")
manual_text = st.text_area(
    "Enter candidate information (e.g., career stories, achievements, and contact details):",
    height=200,
    key="manual_text",
    placeholder="Ensure to ask for contact info and general career stories no matter how 'small'."
)

# Option to use speech recognition
st.write("### Option 2: Use Speech Recognition")
if st.button("Start Speech Recognition"):
    recognize_from_microphone()

# Button to generate resume
if st.button("Generate Resume"):
    generate_resume()

# Display the generated resume if it exists
if "generated_resume" in st.session_state:
    st.write("### Generated Resume")
    edited_resume = st.text_area("Edit the Generated Resume", st.session_state.generated_resume, height=300, key="edited_resume")

    # Add a download button for the edited resume
    st.download_button(
        label="Download Edited Resume",
        data=edited_resume,
        file_name="edited_resume.txt",
        mime="text/plain"
    )