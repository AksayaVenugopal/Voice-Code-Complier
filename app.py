from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
import subprocess
import speech_recognition as sr
import threading
import io
import sys

app = Flask(__name__)
socketio = SocketIO(app)

# Store the ongoing speech recognition thread
recognition_thread = None
recording = False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/execute', methods=['POST'])
def execute_code():
    code = request.json.get('code')
    try:
        # Redirect stdout to capture the output
        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output

        exec(code, {})

        sys.stdout = old_stdout
        output = redirected_output.getvalue()
    except Exception as e:
        output = str(e)

    return jsonify({'output': output})

@app.route('/start_recording', methods=['POST'])
def start_recording():
    global recording, recognition_thread
    if not recording:
        recording = True
        recognition_thread = threading.Thread(target=record_speech)
        recognition_thread.start()
        return jsonify({'status': 'recording started'})
    return jsonify({'status': 'already recording'})

@app.route('/stop_recording', methods=['POST'])
def stop_recording():
    global recording
    if recording:
        recording = False
        return jsonify({'status': 'recording stopped'})
    return jsonify({'status': 'not recording'})

def process_text(spoken_text):
    commands = spoken_text.split()
    processed_text = ""
    kw = ["And", "As", "Assert", "Async", "Await", "Break", "Class", "Continue", "Def", "Del", "Elif", "Else", "Except", "Finally", "For", "From", "Global", "If", "Import", "In", "Is", "Lambda", "Nonlocal", "Not", "Or", "Pass", "Raise", "Return", "Try", "While", "With", "Yield"]
    k = ["true", "false", "none"]
    s = {"comma": ",", "semicolon": ";", "colon": ":\n\t", "tab": "\t"}
    kb = ["input", "string", "print", "length", "range", "open", "tuple", "list", "dict", "set", "abs", "max", "min", "sum", "sorted", "type", "any", "all", "capitalize", "lower", "upper", "title", "strip", "lstrip", "rstrip", "isalnum", "isalpha", "isdigit", "islower", "isnumeric", "isspace", "istitle", "isupper", "startswith", "endswith", "replace", "find", "index", "count", "split", "join"]

    for i in range(len(commands)):
        if commands[i] == "open":
            if commands[i + 1] == "string":
                processed_text += "'"
            elif commands[i + 1] == "list":
                processed_text += "["
            elif commands[i + 1] == "tuple":
                processed_text += "("
            elif commands[i + 1] in ["dict", "dictionary"]:
                processed_text += "{"
        elif commands[i] == "close":
            if commands[i + 1] == "string":
                processed_text += "'"
            elif commands[i + 1] == "list":
                processed_text += "]"
            elif commands[i + 1] == "tuple":
                processed_text += ")"
            elif commands[i + 1] in ["off", "of", "up"]:
                processed_text += ")"
            elif commands[i + 1] in ["dict", "dictionary"]:
                processed_text += "}"
        elif commands[i] == "terminate":
            return
        elif commands[i] == "equals":
            processed_text += "="
        elif commands[i] in kw:
            processed_text += commands[i].lower()
        elif commands[i] in k:
            processed_text += commands[i].capitalize()
        elif commands[i] == "plus":
            processed_text += '+'
        elif commands[i] == "minus":
            processed_text += '-'
        elif commands[i] == "multiply":
            processed_text += '*'
        elif commands[i] == "divide":
            processed_text += '/'
        elif commands[i] == "floor":
            processed_text += '//'
        elif commands[i] == "power":
            processed_text += '**'
        elif commands[i] == "modulos" or commands[i] == "modulo":
            processed_text += '%'
        elif commands[i] == "next":
            processed_text += '\n'
        elif commands[i] == "space":
            processed_text += ' '
        elif commands[i] == "tab":
            processed_text += "\t"
        elif commands[i] == "int" or commands[i] == "integer":
            processed_text += "int("
        elif commands[i] in kb:
            processed_text += commands[i] + "("
        elif commands[i] in s:
            processed_text += s[commands[i]]
        else:
            processed_text += commands[i] + " "

    return processed_text

def record_speech():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()
    while recording:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)
            try:
                spoken_text = recognizer.recognize_google(audio).lower()
                processed_text = process_text(spoken_text)
                socketio.emit('speech_result', {'text': processed_text})
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                print(f"Speech recognition error: {e}")

if __name__ == "__main__":
    socketio.run(app, debug=True)
