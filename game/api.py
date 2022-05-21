from os import stat_result
from datetime import date as d
import httpx

from datetime import date
from fastapi import FastAPI, Depends, Response, HTTPException, status
from pydantic import BaseModel, BaseSettings, Field

class Settings(BaseSettings):
    STARTDATE: str

    class Config:
        env_file = "./.env"

settings = Settings()
app = FastAPI()

@app.get("/")
def index():
    return "in game"

# Get new game, using other API in game-state from Project 4
@app.post("/game/new")
def newGame(username):
    stats_url = 'http://localhost:9999/api/stats/username/' + username
    res = httpx.get(stats_url)
    user_id = res.json()["user_id"]
    default_start_date = d(2022, 5, 5)
    today = d.today()
    date_idx = (today - default_start_date).days
    
    newgame_url = 'http://localhost:9999/api/game-state/game-state/newgame'
    params = {"user_id": user_id, "game_id": date_idx}
    gamestate_res = httpx.post(newgame_url, params=params)
    print(params)
    if (gamestate_res.status_code == 200):
        res = {"status:": "welcome"}
        res.update(params)
        return res
    elif (gamestate_res.status_code == 409):
        res = {"status:": "playing"}
        
        game_status_url = "http://localhost:9999/api/game-state/game-state/" + str(user_id) + "/" + str(date_idx)
        t = httpx.get(game_status_url)
        res.update(params)
        res.update({"remain: " : t.json()["remaining"]})
        
        guesses = []
        if (len(t.json()) > 1):
            for i in range(1, len(t.json())):
                guesses.append(t.json()[str(i)])
        # Add to the response
        res.update({"guesses": guesses})
        selected_letters = {"correct": [], "present": []}
        if (guesses):
            new_guess = guesses[-1]
            check_answerurl = 'http://localhost:9999/api/answer-checking/answer/check/reach' + new_guess
            u = httpx.get(check_answerurl)
            for i in range(0, 5):
                score_list = u.json()["accuracy"][i]
                if (score_list == 1):
                    selected_letters["present"].append(new_guess[i])
                if (score_list == 2):
                    selected_letters["correct"].append(new_guess[i])
        #toss it on the response object
        res.update({"selected_letters": selected_letters})
        #done
        return res
    
    # return NOW only for testing
    return "passed"

# Make a guess using POST request
@app.post("/game")
def makeGuess(game_id: int, user_guess: str, user_id: str):
    word_validate_url = 'http://127.0.0.1:9999/api/word-validation/word/isvalid/' + user_guess
    game_state_check_url = "http://localhost:9999/api/game-state/game-state/" + str(user_id) + "/" + str(game_id)

    #make sure that the word is in the word dict
    #check the number of remaining user_guess
    v = httpx.get(word_validate_url)
    g = httpx.get(game_state_check_url)
    guesses = g.json()

    #Record the user_guess and update the number of guesses
    if int(guesses['remaining']) > 0 and v.json()['valid'] is 'true':
        updated_guesses = int(guesses['remaining']) - 1
        game_state_check_url = 'http://127.0.0.1:9999/api/game-state/game-state/newguess'
        params = {"user_id": user_id, "game_id": game_id, "user_guess": user_guess}
        r = httpx.post(game_state_check_url, params=params)
        res = {"remaining": updated_guesses}
        #If the user_guess is correct
        if (r.status_code == 200):
            check_answerurl = 'http://127.0.0.1:9999/api/answer-checking/answer/check/' + user_guess
            u = httpx.get(check_answerurl)
            selected_letters = {"correct": [], "present": []}
            for i in range(0, 5):
                score_list = u.json()["accuracy"][i]
                if (score_list == 1):
                    selected_letters["present"].append(user_guess[i])
                if (score_list == 2):
                    selected_letters["correct"].append(user_guess[i])
            # User got all 5 selected_letters
            if len(selected_letters['correct']) == 5:
                win_url = 'http://127.0.0.1:9999/api/stats/stats/' 
                guesses = 6 - updated_guesses 
                params = {"user_id": user_id, "game_id": game_id, "finished": d.today(), "guesses": guesses, "won": True} 
                s = httpx.post(win_url, params=params) 
                res.update({"status": "win", "remaining": updated_guesses}) 
                # Get their score
                scoreurl = 'http://localhost:9999/api/stats/stats/user/' + user_id 
                scores = httpx.get(scoreurl) 
                res.update(scores.json()) 
                return res 
            #Out of guesses
            elif len(selected_letters['correct']) < 5 and updated_guesses == 0:
                return "wrong"
            else:
                res.update({"status": "incorrect", "selected_letters": selected_letters})
                return res
    return "You are out of guesses"
