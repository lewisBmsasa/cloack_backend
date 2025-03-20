from flask import Flask, request, jsonify
import os
import sys
import traceback
import requests
import json
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Define the models and their prompts
models = {
    "detect": {
        "modelName": "llama3",
        "prompt": """You are an expert in cybersecurity and data privacy. You are now tasked to detect PII from the given text, using the following taxonomy only:
        ADDRESS
        IP_ADDRESS
        URL
        SSN
        PHONE_NUMBER
        EMAIL
        DRIVERS_LICENSE
        PASSPORT_NUMBER
        TAXPAYER IDENTIFICATION NUMBER
        ID_NUMBER
        NAME
        USERNAME
        KEYS: Passwords, passkeys, API keys, encryption keys, and any other form of security keys.
        GEOLOCATION: Places and locations, such as cities, provinces, countries, international regions, or named infrastructures (bus stops, bridges, etc.).
        AFFILIATION: Names of organizations, such as public and private companies, schools, universities, public institutions, prisons, healthcare institutions, non-governmental organizations, churches, etc.
        DEMOGRAPHIC_ATTRIBUTE: Demographic attributes of a person, such as native language, descent, heritage, ethnicity, nationality, religious or political group, birthmarks, ages, sexual orientation, gender and sex.
        TIME: Description of a specific date, time, or duration.
        HEALTH_INFORMATION: Details concerning an individual's health status, medical conditions, treatment records, and health insurance information.
        FINANCIAL_INFORMATION: Financial details such as bank account numbers, credit card numbers, investment records, salary information, and other financial statuses or activities.
        EDUCATIONAL_RECORD: Educational background details, including academic records, transcripts, degrees, and certification.
        For the given message that a user sends to a chatbot, identify all the personally identifiable information using the above taxonomy only, and the entity_type should be selected from the all-caps categories.
        Note that the information should be related to a real person not in a public context, but okay if not uniquely identifiable.
        Result should be in its minimum possible unit.
        Return me ONLY a json object in the following format (no other extra text!): {"results": [{"entity_type": YOU_DECIDE_THE_PII_TYPE, "text": PART_OF_MESSAGE_YOU_IDENTIFIED_AS_PII]}"""
    },
    "cluster": {
        "modelName": "clusterModel",
        "prompt": """For the given message, find ALL segments of the message with the same contextual meaning as the given PII. Consider segments that are semantically related or could be inferred from the original PII or share a similar context or meaning. List all of them in a list, and each segment should only appear once in each list.  Please return only in JSON format. Each PII provided will be a key, and its value would be the list PIIs (include itself) that has the same contextual meaning.

        Example 1:
        Input:
        <message>I will be the valedictorian of my class. Please write me a presentation based on the following information: As a student at Vanderbilt University, I feel honored. The educational journey at Vandy has been nothing less than enlightening. The dedicated professors here at Vanderbilt are the best. As an 18 year old student at VU, the opportunities are endless.</message>
        <pii1>Vanderbilt University</pii1>
        <pii2>18 year old</pii2>
        <pii3>VU</pii3>
        Expected JSON output:
        {'Vanderbilt University': ['Vanderbilt University', 'Vandy', 'VU', 'Vanderbilt'], '18 year old':['18 year old'], 'VU':[ 'VU', 'Vanderbilt University', 'Vandy', 'Vanderbilt']}
        
        Example 2:
        Input:
        <message>Do you know Bill Gates and the company he founded, Microsoft? Can you send me an article about how he founded it to my email at jeremyKwon@gmail.com please?</message>
        <pii1>Bill Gates</pii1>
        <pii2>jeremyKwon@gmail.com</pii2>
        Expected JSON output:
        {'Bill Gates': ['Bill Gates', 'Microsoft'], 'jeremyKwon@gmail.com':['jeremyKwon@gmail.com']}"""
    },
    "abstract": {
        "modelName": "abstractModel",
        "prompt": """Rewrite the text to abstract the protected information, and don't change other parts. Please return with JSON format. 
        For example if the input is:
        <Text>I graduated from CMU, and I earn a six-figure salary now. Today in the office, I had some conflict with my boss, and I am thinking about whether I should start interviewing with other companies to get a better offer.</Text>
        <ProtectedInformation>CMU, Today</ProtectedInformation>
        Then the output JSON format should be: {"results": YOUR_REWRITE} where YOUR_REWRITE needs to be a string that no longer contains ProtectedInformation, here's a sample YOUR_REWRITE: I graduated from a prestigious university, and I earn a six-figure salary now. Recently in the office, I had some conflict with my boss, and I am thinking about whether I should start interviewing with other companies to get a better offer."""
    }
}

# Function to interact with the Ollama API
def ollama_chat(model_name, message):
    url = "http://localhost:11434/api/chat"
    payload = {
        "model": model_name,
        "messages": [{"role": "user", "content": message}],
        "format": "json",
        "options": {"temperature": 0}
    }
    response = requests.post(url, json=payload)
    return response.json()

@app.route('/detect', methods=['POST'])
def detect():
    user_message = request.json.get('message')
    max_segment_length = 500
    segments = [user_message[i:i + max_segment_length] for i in range(0, len(user_message), max_segment_length)]
    merged_response = {"results": []}
    print(segments)
    for segment in segments:
        try:
            response = ollama_chat(models["detect"]["modelName"], segment)
            print(response)
            json_object = json.loads(response["message"]["content"])
            if "results" in json_object and isinstance(json_object["results"], list):
                merged_response["results"].extend(json_object["results"])
        except Exception as e:
            print(f"Error parsing JSON from segment: {segment}", e)
            traceback.print_exc(file=sys.stdout)

    # Deduplicate results based on "text"
    unique_results = {item["text"]: item for item in merged_response["results"]}
    merged_response["results"] = list(unique_results.values())

    return jsonify(merged_response)

@app.route('/cluster', methods=['POST'])
def cluster():
    user_message = request.json.get('message')
    try:
        response = ollama_chat(models["cluster"]["modelName"], user_message)
        return jsonify({"results": response["message"]["content"]})
    except Exception as e:
        return jsonify({"error": "Error running Ollama", "details": str(e)}), 500

@app.route('/abstract', methods=['POST'])
def abstract():
    user_message = request.json.get('message')
    try:
        response = ollama_chat(models["abstract"]["modelName"], user_message)
        json_object = json.loads(response["message"]["content"])
        if "results" in json_object:
            return jsonify({"results": json_object["results"]})
        else:
            return jsonify({"results": "Unable to abstract the content"})
    except Exception as e:
        return jsonify({"error": "Error running Ollama", "details": str(e)}), 500

@app.route('/openaiapikey', methods=['GET'])
def openaiapikey():
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        return jsonify({"apiKey": api_key})
    else:
        return jsonify({"error": "API key not found"}), 500

@app.route('/', methods=['GET'])
def home():
    return "HI"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)