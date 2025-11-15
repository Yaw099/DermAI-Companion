RED_FLAGS = ["rapid growth", "bleeding", "pain"]

def check_red_flags(text):
    text = text.lower()
    found = [t for t in RED_FLAGS if t in text]
    return found if found else None
