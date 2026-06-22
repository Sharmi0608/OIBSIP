import pyttsx3

engine = pyttsx3.init()

engine.setProperty('rate', 170)

voices = engine.getProperty('voices')
engine.setProperty('voice', voices[0].id)

engine.say("Testing one.")
engine.say("Testing two.")
engine.say("Testing three.")

engine.runAndWait()

engine.stop()