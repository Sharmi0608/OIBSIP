import customtkinter as ctk
import datetime
import webbrowser
import pyttsx3
from PIL import Image

engine = pyttsx3.init()

def speak(text):
    engine.say(text)
    engine.runAndWait()
    
app = ctk.CTk()

app.title("Lumira AI Assistant")
app.geometry("500x600")

title = ctk.CTkLabel(
    app,
    text="LUMIRA",
    font=("Arial",30)
)

title.pack(pady=20)

img = ctk.CTkImage(
    light_image=Image.open("assistant.png"),
    size=(180,180)
)

label = ctk.CTkLabel(
    app,
    image=img,
    text=""
)

label.pack(pady=10)

textbox = ctk.CTkTextbox(
    app,
    width=400,
    height=250
)

textbox.pack(pady=20)

entry = ctk.CTkEntry(
    app,
    width=300,
    placeholder_text="Type your command"
)

entry.pack(pady=10)

def send_message():

    command = entry.get().lower()

    if command == "":
        return

    textbox.insert("end", f"You: {command}\n")

    if "hello" in command:
        response = "Hello Sharmi."

    elif "how are you" in command or "how are u" in command:
        response = "I am doing well."

    elif "time" in command:
        response = datetime.datetime.now().strftime("%I:%M %p")

    elif "date" in command:
        response = str(datetime.date.today())

    elif "youtube" in command:
        response = "Opening YouTube"
        webbrowser.open("https://youtube.com")

    elif "google" in command:
        response = "Opening Google"
        webbrowser.open("https://google.com")

    elif "weather" in command:
        response = "Weather feature available in voice mode."

    elif "joke" in command:
        response = "Why do programmers prefer dark mode? Because light attracts bugs."

    elif "thank" in command:
        response = "You are welcome."

    elif "bye" in command:
        response = "Goodbye."

    else:
        response = "Sorry, I did not understand."

    textbox.insert("end", f"Lumira: {response}\n")

    speak(response)

    entry.delete(0, "end")

    textbox.see("end")
    
entry.bind(
    "<Return>",
    lambda event: send_message()
)

button = ctk.CTkButton(
    app,
    text="Send",
    command=send_message
)

button.pack(pady=10)


    
app.mainloop()