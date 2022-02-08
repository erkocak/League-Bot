import mwclient
import mwrogue
import mwcleric
import json
import time
import datetime as dt
from datetime import date, datetime, timedelta
import requests


# links
SCHEDULE = "https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US&leagueId={}"
NEXT = "https://esports-api.lolesports.com/persisted/gw/getSchedule?hl=en-US&leagueId={}&pageToken={}"
LEAGUES = "https://esports-api.lolesports.com/persisted/gw/getLeagues?hl=en-US"

# templates
START = """== {0} ==
{{{{SetPatch|patch= |disabled= |hotfix= |footnote=}}}}
{{{{MatchSchedule/Start|tab={0} |bestof={1} |shownname= }}}}\n"""
MATCH = """{{{{MatchSchedule|<!-- Do not change the order of team1 and team2!! -->|initialorder={initialorder}|team1={t1} |team2={t2} |team1score= |team2score= |winner={winner}
|date={date} |time={time} |timezone={timezone} |dst={dst} |pbp= |color= |vodinterview= |with= |stream={stream} |reddit=
{games}
}}}}\n"""
BO1_GAMES = """|game1={{MatchSchedule/Game\n|blue= |red= |winner= |ssel= |ff=\n|mh=\n|recap=\n|vodpb=\n|vodstart=\n|vodpost=\n|vodhl=\n|vodinterview=\n|with=\n|mvp=\n}}"""
BO2_GAMES = """|game1={{MatchSchedule/Game\n|blue= |red= |winner= |ssel= |ff=\n|mh=\n|recap=\n|vodpb=\n|vodstart=\n|vodpost=\n|vodhl=\n|vodinterview=\n|with=\n|mvp=\n}}
|game2={{MatchSchedule/Game\n|blue= |red= |winner= |ssel= |ff=\n|mh=\n|recap=\n|vodpb=\n|vodstart=\n|vodpost=\n|vodhl=\n|vodinterview=\n|with=\n|mvp=\n}}"""
BO3_GAMES = """|game1={{MatchSchedule/Game\n|blue= |red= |winner= |ssel= |ff=\n|mh=\n|recap=\n|vodpb=\n|vodstart=\n|vodpost=\n|vodhl=\n|vodinterview=\n|with=\n|mvp=\n}}
|game2={{MatchSchedule/Game\n|blue= |red= |winner= |ssel= |ff=\n|mh=\n|recap=\n|vodpb=\n|vodstart=\n|vodpost=\n|vodhl=\n|vodinterview=\n|with=\n|mvp=\n}}
|game3={{MatchSchedule/Game\n|blue= |red= |winner= |ssel= |ff=\n|mh=\n|recap=\n|vodpb=\n|vodstart=\n|vodpost=\n|vodhl=\n|vodinterview=\n|with=\n|mvp=\n}}"""
BO5_GAMES = """|game1={{MatchSchedule/Game\n|blue= |red= |winner= |ssel= |ff=\n|mh=\n|recap=\n|vodpb=\n|vodstart=\n|vodpost=\n|vodhl=\n|vodinterview=\n|with=\n|mvp=\n}}
|game2={{MatchSchedule/Game\n|blue= |red= |winner= |ssel= |ff=\n|mh=\n|recap=\n|vodpb=\n|vodstart=\n|vodpost=\n|vodhl=\n|vodinterview=\n|with=\n|mvp=\n}}
|game3={{MatchSchedule/Game\n|blue= |red= |winner= |ssel= |ff=\n|mh=\n|recap=\n|vodpb=\n|vodstart=\n|vodpost=\n|vodhl=\n|vodinterview=\n|with=\n|mvp=\n}}
|game4={{MatchSchedule/Game\n|blue= |red= |winner= |ssel= |ff=\n|mh=\n|recap=\n|vodpb=\n|vodstart=\n|vodpost=\n|vodhl=\n|vodinterview=\n|with=\n|mvp=\n}}
|game5={{MatchSchedule/Game\n|blue= |red= |winner= |ssel= |ff=\n|mh=\n|recap=\n|vodpb=\n|vodstart=\n|vodpost=\n|vodhl=\n|vodinterview=\n|with=\n|mvp=\n}}"""
END = "{{MatchSchedule/End}}\n"


def get_headers():
    api_key = "0TvQnueqKa5mxJntVWt0w4LpLfEkrV1Ta8rQBb9Z"
    headers = {"x-api-key": api_key}
    return headers


def get_json(json_type, headers):
    request = requests.get(json_type, headers=headers)
    json_file = json.loads(request.text)
    return json_file


def get_all_jsons(first_json, league_id, headers):
    jsons = [first_json]
    next_token = filter_json(first_json, "data", "schedule", "pages", "newer")
    while next_token is not None:
        next_json = get_json(NEXT.format(league_id, next_token), headers)
        jsons.append(next_json)
        next_token = filter_json(next_json, "data", "schedule", "pages", "newer")
    return jsons


def get_league(league_name, headers):
    json_leagues = get_json(LEAGUES, headers)
    json_leagues = filter_json(json_leagues, "data", "leagues")
    league_dict = next((league_dict for league_dict in json_leagues if league_dict["name"] == league_name), None)
    league_id = league_dict["id"]
    return league_id


def filter_json(json_file, *args):
    new_json = json_file
    for arg in args:
        try:
            new_json = new_json[arg]
        except KeyError:
            print("Couldn't find '{}'. Original json returned.".format(arg))
            return json_file
    return new_json


def parse_schedule(jsons, timezone="CET", dst="no", stream=""):
    counter = 0
    values = {}
    
    initialorder = 1
    schedule, current_tab = "", ""
    for json_file in jsons:
        json_schedule = filter_json(json_file, "data", "schedule", "events")
        for game in json_schedule:
            date_time = game["startTime"]
            date = date_time[:10]
            time = date_time[11:16]
            time_obj = datetime.strptime(time, "%H:%M")
            hour = timedelta(hours=1)
            time_obj = time_obj + hour
            time = time_obj.strftime("%H:%M")
            team1 = game["match"]["teams"][0]["name"]
            team2 = game["match"]["teams"][1]["name"]
            bestof = game["match"]["strategy"]["count"]
            
            team1_wins_int = 0
            team2_wins_int = 0
            if game["match"]["teams"][0]["result"] is None:
                team1_wins_int = 0  
            else:
                team1_wins_str = game["match"]["teams"][0]["result"]["gameWins"]
                team1_wins_int = int(team1_wins_str)       

            if game["match"]["teams"][1]["result"] is None:
                team2_wins_int = 0 
            else:
                team2_wins_str = game["match"]["teams"][1]["result"]["gameWins"]
                team2_wins_int = int(team2_wins_str)    
        
            if team1_wins_int > team2_wins_int:
                winner = game["match"]["teams"][0]["name"]
            elif team2_wins_int > team1_wins_int:
                winner = game["match"]["teams"][1]["name"]
            else:
                winner = "None"

            t1_series_score = 0
            t2_series_score = 0
            series_score = "0-0"
            if game["match"]["teams"][0]["result"] is not None and game["match"]["teams"][1]["result"] is not None:
                t1_series_score = game["match"]["teams"][0]["result"]["gameWins"]
                t2_series_score = game["match"]["teams"][1]["result"]["gameWins"]
                series_score = str(t1_series_score) + "-" + str(t2_series_score)

            values[counter] = {'team1': team1, 'team2': team2, 'winner': winner, 'score': series_score, 'date': date, 'time': time, 'timezone': timezone, 'bestof': bestof}
            counter = counter + 1

    return values


def run(league_name):
    headers = get_headers()
    league_id = get_league(league_name, headers)
    json_schedule = get_json(SCHEDULE.format(league_id), headers)
    jsons = get_all_jsons(json_schedule, league_id, headers)
    schedule = parse_schedule(jsons)
    return schedule
    