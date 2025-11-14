# app.py
from flask import render_template
from project import create_app

print("🔥 USING THIS APP.PY:", __file__)

# Use the REAL create_app inside project/__init__.py
app = create_app()

app.config['PROPAGATE_EXCEPTIONS'] = True

@app.route('/', methods=['GET'])
def Home():
    print(">>> HOME ROUTE REACHED <<<")
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
