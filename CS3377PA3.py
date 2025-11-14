from flask import Flask
app = Flask("Derm AI Companion")

@app.route('/')
def home():
    return "Hello, Flask is working!"

if __name__ == '__main__':
    app.run(debug=True)