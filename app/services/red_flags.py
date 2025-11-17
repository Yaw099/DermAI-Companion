RED_FLAGS = ["rapid growth", "bleeding", "severe pain", "rapid swelling", "oozing", "fever", "infected", "won't stop bleeding", ""]

def check_red_flags(text):
    text = text.lower()
    found = [flag for flag in RED_FLAGS if flag in text]

    if found:
        return "Warning: Your symptoms may warrant immediate medical attention. Please alert your healthcare provider, visit urgent care, or call 911 if you believe this is an emergecy."

    return None
