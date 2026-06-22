import speech_recognition as sr
import pyttsx3
import datetime
import wikipedia
import webbrowser
import time
import pywhatkit
import os
import requests
import threading 
import psutil
import pyautogui
import pyjokes
import re
import spacy

engine = pyttsx3.init("sapi5")

voices = engine.getProperty("voices")
engine.setProperty("voice", voices[0].id)   # male voice
engine.setProperty("rate", 170)

nlp = spacy.load("en_core_web_sm")

def understand_command(command):

    command = command.lower()

    intents = {
        "youtube": [
            "youtube",
            "open youtube",
            "launch youtube"
        ],

        "spotify": [
            "spotify",
            "open spotify",
            "launch spotify"
        ],

        "weather": [
            "weather",
            "temperature",
            "climate"
        ],

        "time": [
            "time",
            "current time"
        ],

        "date": [
            "date",
            "today date"
        ],

        "calculator": [
            "calculator",
            "calc"
        ],

        "notepad": [
            "notepad",
            "note pad",
            "open note"
        ]
    }

    text = command.lower()

    for intent, words in intents.items():

        for phrase in words:

            if phrase in text:
                return intent

    return ""

def reminder(seconds, message):
    time.sleep(seconds)
    speak(message)
    
speech_lock = threading.Lock()      
is_speaking = False

def speak(text):

    global is_speaking

    with speech_lock:

        is_speaking = True

        print("Lumira:", text)

        engine.stop()
        engine.say(text)
        engine.runAndWait()

        is_speaking = False

        time.sleep(0.3)
       
listener = sr.Recognizer()
listener.energy_threshold = 300
listener.pause_threshold = 1
listener.dynamic_energy_threshold = True

waiting_for_city = False

def get_weather(city):
    global waiting_for_city
    api_key = "28dd88e299fb89999842fd65ab0ec9b2"

    url = (
        f"https://api.openweathermap.org/data/2.5/weather"
        f"?q={city}&appid={api_key}&units=metric"
    )

    try:
        data = requests.get(url).json()

        if str(data["cod"]) != "200":
           speak("I could not find that city.")
           return

        temp = data["main"]["temp"]
        description = data["weather"][0]["description"]

        speak(
            f"The temperature in {city} is {temp} degrees Celsius with {description}."
        )

    except:
        speak("Unable to get weather information.")   
        
def take_command():
    
    global is_speaking

    while is_speaking:
        time.sleep(0.1)
        
    with sr.Microphone() as source:
        print("Listening...")
        listener.adjust_for_ambient_noise(source, duration=0.3)

        try:
            audio = listener.listen(
                source,
                timeout=5,
                phrase_time_limit=8
            )

        except sr.WaitTimeoutError:
            return ""

    try:
        command = listener.recognize_google(audio,
                                            language="en-IN"
                                            )
        command = command.lower()
        print("You:", command)
        return command

    except Exception as e:
       print(e)
       return ""

speak("Hello Sharmi. I am Lumira, your personal voice assistant. How can I help you today?")

mode = input(
    "Choose mode:\n"
    "v = Voice Mode\n"
    "t = Type Mode\n"
    "Your choice: "
).lower()

failed_attempts = 0

while True:

    if mode == "t":

        command = input("You: ").lower()

    else:

        command = take_command()

        if command == "":

            failed_attempts += 1

            print(
                f"No speech detected. Attempt {failed_attempts}/3"
            )

            if failed_attempts >= 3:

                command = input(
                    "Please type your command: "
                ).lower()

                failed_attempts = 0

        else:
            failed_attempts = 0
    
    intent = understand_command(command)
    
    if intent == "youtube":
        speak("Opening YouTube")
        webbrowser.open("https://youtube.com")
        continue

    elif intent == "spotify":
        speak("Opening Spotify")
        os.startfile(
            r"C:\Users\sharm\AppData\Roaming\Spotify\Spotify.exe"
        )
        continue
    
    elif intent == "calculator":
        speak("Opening Calculator")
        os.system("calc")
        continue

    elif intent == "notepad":
        speak("Opening Notepad")
        os.system("notepad")
        continue
    
    if  command in ["hello", "hi", "hey"]:
        speak("Hello Sharmi. Nice to meet you.")
        
    elif "good morning" in command:
        speak("Good morning Sharmi. Have a wonderful day.")
        
    elif "good evening" in command:
        speak("Good evening Sharmi. I hope you enjoy this evening to the fullest")
        
    elif ("how are you" in command or"how are u" in command):
        speak("I am doing well. Thank you for asking.")
        
    elif "time" in command:
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        speak("The time is " + current_time)

    elif "date" in command:
        today = datetime.date.today()
        speak("Today's date is " + str(today))
        
    elif "play" in command:

        song = command.replace("play", "")
        song = song.replace("can you", "")
        song = song.strip()

        if song == "":
            speak("What should I play?")

        else:
            speak("Playing " + song)
            pywhatkit.playonyt(song)

    elif "song" in command:
       speak("Playing " + command)
       pywhatkit.playonyt(command)
        
    elif ("chat" in command and "g" in command) or "chat gpt" in command:
       speak("Opening ChatGPT")
       webbrowser.open("https://chatgpt.com")  
    
    elif ("gmail" in command or"email" in command or"mail" in command):
       speak("Opening Gmail")
       webbrowser.open("https://mail.google.com")
          
    elif "joke" in command:
        speak(pyjokes.get_joke())
    
    elif "weather in" in command:

        city = command.split("weather in")[-1]

        city = city.replace("what's", "")
        city = city.replace("what is", "")
        city = city.strip()

        if city == "":
            speak("Please tell me the city name.")
            waiting_for_city = True

        else:
            get_weather(city)
    
    elif waiting_for_city:
        get_weather(command)
        waiting_for_city = False
        
    elif ("weather" in command or"temperature" in command):
        speak("Please tell me the city name.")
        waiting_for_city = True
    
    elif (
        "remind" in command or
        "reminder" in command
    ):

        numbers = re.findall(r'\d+', command)

        if numbers:
            minutes = int(numbers[0])

            speak(
                f"Reminder set for {minutes} minutes."
            )

            threading.Thread(
                target=reminder,
                args=(minutes*60,
                      "Your reminder time is over."),
                daemon=True
            ).start()

        else:
            speak(
                "Please tell me the number of minutes."
            )
    
    elif (
        "take screenshot" in command or
        "take a screenshot" in command
    ):
        image = pyautogui.screenshot()

        path = os.path.join(
            os.getcwd(),
            "screenshot.png"
        )
  
        image.save(path)
        print(path) 

        speak("Screenshot saved.")
    
    elif "battery" in command:
        battery = psutil.sensors_battery()
        if battery:
            speak(f"Battery is {battery.percent} percent.")
        else:
            speak("Battery information is unavailable.") 
    
    elif "shutdown computer" in command:
        speak("Shutting down your computer.")
        os.system("shutdown /s /t 5")
    
    elif "restart computer" in command:
        speak("Restarting your computer.")
        os.system("shutdown /r /t 5")
        
    elif "lock computer" in command:
        os.system("rundll32.exe user32.dll,LockWorkStation")
    
    elif "open chrome" in command:
        speak("Opening Chrome")
        os.system("start chrome")

    elif "open vscode" in command or "open vs code" in command:
       speak("Opening Visual Studio Code")
       os.system("code")

    elif "day" in command:
        day = datetime.datetime.now().strftime("%A")
        speak("Today is " + day)
    
    elif "take note" in command:
        speak("What should I write?")

        note = take_command()

        with open("notes.txt", "a") as file:
            file.write(note + "\n")

        speak("Note saved.")
    
    elif "cpu" in command:
        cpu = psutil.cpu_percent()
        speak(f"CPU usage is {cpu} percent.")
    
    elif "google" in command:
        speak("Opening Google")
        webbrowser.open("https://www.google.com")
        
    elif "search" in command:
        query = command.replace("search", "")
        query = query.replace("for", "")
        query = query.strip()

        if query == "":
           speak("What should I search?")
        else:
           speak("Searching for " + query)
           webbrowser.open(
            f"https://www.google.com/search?q={query}"
        )      
        
    elif "who is" in command or "what is" in command:
        query = command.replace("who is", "")
        query = query.replace("what is", "")

        try:
            info = wikipedia.summary(query, sentences=2)
            speak(info)

        except wikipedia.DisambiguationError:
            speak(
            "Please say the full name."
        )

        except wikipedia.PageError:
            speak(
                "I could not find information."
            )

    elif "help" in command:
        speak(
        "You can ask me the time, date, search Google, ask who is someone, or ask what is something."
    )
        
    elif "thank" in command:
        speak("You are welcome Sharmi.")
        time.sleep(1)
        
    elif ("exit" in command or
          "bye" in command or
          "bye bye" in command or
          "goodbye" in command):
        
        speak("Goodbye Sharmi.")
        break

    elif command != "":
        speak("Sorry, I did not understand.")