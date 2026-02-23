import json

def load(f, d):
    try: return json.load(open(f))
    except: return d

tracks = load("tracks.json", {})
state = load("state.json", {"track":"INCIDENT"})

def current_track():
    return state["track"], tracks.get(state["track"], {})

def set_track(t):
    if t in tracks:
        state["track"] = t
        json.dump(state, open("state.json","w"), indent=2)
        return True
    return False