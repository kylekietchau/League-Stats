from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
import os
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

load_dotenv() 
api_key = os.getenv('API_KEY')

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return render_template('mastery.html')

def fetch_match_data(match_id, api_key, region):
    match_detail_url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}?api_key={api_key}"
    response = requests.get(match_detail_url)
    return response.json()

@app.route('/submit-data', methods=['POST'])
def submit_data():
    data = request.json 

    gameName = data["username"].replace(" ", "%20")
    tagLine = data["tagline"]
    region = data["region"].lower()
    numMatches = data["num"]

    api_url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{gameName}/{tagLine}?api_key={api_key}"

    account_response = requests.get(api_url)
    if account_response.status_code == 200: #If the account is fetched
        account_data = account_response.json()
        puuid = account_data["puuid"]

        match_id_url = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count={numMatches}&api_key={api_key}"
        match_id_response = requests.get(match_id_url)
        match_id_data = match_id_response.json()

        kills = 0
        deaths = 0
        damage = 0

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch_match_data, match_id, api_key, region) for match_id in match_id_data]
            for future in as_completed(futures):
                individual_match_data = future.result()
                inGameOrder = individual_match_data["metadata"]["participants"].index(f"{puuid}")
                player = individual_match_data["info"]["participants"][inGameOrder]
                kills += player["kills"]
                deaths += player["deaths"]
                damage += player["trueDamageDealtToChampions"]

        return jsonify({"status": "success", "api_data": account_data, "kills": kills, "deaths": deaths, "damage": damage})
    else:
        return jsonify({"status": "error", "message": "Failed to retrieve data from the API"}), account_response.status_code

if __name__ == '__main__':
    app.run(debug=True)

