from flask import Flask, render_template, request, redirect, url_for, session
from joblib import load
import re

app = Flask(__name__)
app.secret_key = 'YOUR_SECRET_KEY'  # Required for session usage!

# Load your pre-trained model and scaler
model = load('model.pkl')
scaler = load('scaler.pkl')

# Tier mapping dictionary
tier_mapping = {
    'iron': 0,
    'bronze': 1,
    'silver': 2,
    'gold': 3,
    'platinum': 4,
    'diamond': 5,
    'ascendant': 6,
    'immortal': 7
}

inv_tier_mapping = {v: k for k, v in tier_mapping.items()}
rank_icons = {
    'iron': 'iron.png',
    'bronze': 'bronze.png',
    'silver': 'silver.png',
    'gold': 'gold.png',
    'platinum': 'platinum.png',
    'diamond': 'diamond.png',
    'ascendant': 'ascendant.png',
    'immortal': 'immortal.png'
}
def parse_valorant_data(raw_text):
    """
    Parse the raw text block and return a dict of extracted fields.
    We'll assume the stats appear as e.g.:
        "Assists/Match\n4.7"
        "Damage Received\n1,336,758"
        "Headshots\n3,905"
        etc.
    This function uses simple regex or text splitting to find them.
    """
    # We define a dictionary of the fields we want:
    # keys are the "labels" we expect, values are the default or None if not found
    # The left side is exactly how it appears in the text.
    fields_map = {
        "Assists/Match": None,
        "Damage Received": None,
        "Headshots": None,
        "Rounds Traded": None,
        "Kills/Match": None,
        "Deaths/Match": None,
        "Damage/Match": None,
        "Matches Played": None
    }

    # We'll split by lines and look for lines that match a label in fields_map
    lines = raw_text.splitlines()
    for i, line in enumerate(lines):
        line_clean = line.strip()
        if line_clean in fields_map:
            # The next line should be the numeric value
            if i + 1 < len(lines):
                value_line = lines[i + 1].strip()
                # Remove commas if present, convert to float
                value_line = value_line.replace(",", "")
                try:
                    numeric_val = float(value_line)
                except ValueError:
                    numeric_val = None
                fields_map[line_clean] = numeric_val

    return fields_map
@app.route('/')
def home():
    # Redirect from root URL to step1
    return redirect(url_for('extract'))
@app.route('/extract', methods=['GET', 'POST'])
def extract():
    """
    Page 1: 
    - Presents a textarea for user to paste raw stats 
    - On POST, parse the text, store in session, redirect to /show_data
    """
    if request.method == 'POST':
        raw_text = request.form['raw_text']
        parsed = parse_valorant_data(raw_text)

        # Store in session so we can show on next page
        session['parsed_stats'] = parsed
        return redirect(url_for('show_data'))
    return render_template('extract.html')

@app.route('/show_data', methods=['GET', 'POST'])
def show_data():
    """
    Page 2:
    - Displays the extracted stats from session 
    - Has a "Predict" button that triggers final prediction
    """
    parsed_stats = session.get('parsed_stats', {})
    if request.method == 'POST':
        # We'll do the final prediction here
        # Extract the 8 needed fields from parsed_stats
        a = parsed_stats.get("Assists/Match", 0.0)   # e.g. 4.7
        dmg_received = parsed_stats.get("Damage Received", 0.0)
        hs = parsed_stats.get("Headshots", 0.0)
        tr = parsed_stats.get("Rounds Traded", 0.0)
        k = parsed_stats.get("Kills/Match", 0.0)
        d = parsed_stats.get("Deaths/Match", 0.0)
        dmg = parsed_stats.get("Damage/Match", 0.0)
        mp = parsed_stats.get("Matches Played", 1.0)

        if mp == 0:
            mp = 1.0  # Avoid divide by zero if something is weird

        # Build the feature vector
        new_data = [[
            a,                 # Assist/Match
            dmg_received,      # Damage Received
            hs,                # Headshots
            tr,                # Rounds Traded
            k,                 # Kills/Match
            d,                 # Deaths/Match
            dmg,               # Damage/Match
            k/d if d != 0 else 0.0  # K/D ratio
        ]]

        # For stats with indices 1,2,3, divide by matches
        for idx in [1, 2, 3]:
            new_data[0][idx] /= mp

        # Scale the data
        new_data_scaled = scaler.transform(new_data)

        # Predict
        prediction = model.predict(new_data_scaled)
        predicted_tier = inv_tier_mapping.get(prediction[0], "Unknown Tier")

        # Store in session or pass via query param
        session['predicted_tier'] = predicted_tier
        return redirect(url_for('result'))

    # If GET, just display the extracted data
    return render_template('show_data.html', parsed_stats=parsed_stats)

@app.route('/result')
def result():
    predicted_tier = session.get('predicted_tier', None)
    
    # Our rank icon mapping
    rank_icons = {
        'iron': 'iron.png',
        'bronze': 'bronze.png',
        'silver': 'silver.png',
        'gold': 'gold.png',
        'platinum': 'platinum.png',
        'diamond': 'diamond.png',
        'ascendant': 'ascendant.png',
        'immortal': 'immortal.png'
    }

    # In case predicted_tier is None or something unexpected, we provide a fallback image
    if predicted_tier:
        icon_filename = rank_icons.get(predicted_tier.lower(), 'unknown_tier.png')
    else:
        icon_filename = 'unknown_tier.png'

    # Pass both the tier and icon filename to the template
    return render_template('result.html',
                           predicted_tier=predicted_tier,
                           icon_filename=icon_filename)


if __name__ == '__main__':
    app.run(debug=True)
