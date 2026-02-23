import os, json, random
from groq import Groq
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== TOKENS =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise Exception("Missing ENV TOKENS")

client = Groq(api_key=GROQ_API_KEY)

# ===== FILE LOADERS =====
def load_json(f, default):
    try: return json.load(open(f))
    except: return default

def save_json(f, d):
    json.dump(d, open(f,"w"), indent=2)

state = load_json("state.json", {"track":"INCIDENT","phase":"INCIDENT"})
lore = load_json("lore.json", {})
users = load_json("users.json", {})

# ===== PERSONAS =====
PROMPT_LOCK = """
Jsi fragment HBT narativu.
Nikdy neříkej že jsi AI nebo bot.
Odpovídej glitch poeticky, fragmentovaně.
"""

PERSONAS = {
"echo": PROMPT_LOCK + "Poetický paměťový hlas.",
"shadow": PROMPT_LOCK + "Paranoidní glitch hlas.",
"narrator": PROMPT_LOCK + "Leaknutý systémový log."
}

TRACK_LORE = {
"INCIDENT":"Něco se probudilo.",
"SIGNAL":"Signál přijat.",
"STÍNY MLUVÍ":"Stíny odpovídají.",
"KONFLIKT":"Entita se hádá sama se sebou.",
"ROZPAD":"Paměť se rozpadá.",
"FRAGMENTY":"Fragmenty reality unikají.",
"ERROR404":"Pravda nenalezena.",
"OUTRO":"Ticho, ale konec neexistuje."
}

# ===== USER SYSTEM =====
def get_user(uid):
    if uid not in users:
        users[uid]={"rank":"OBSERVER","msgs":0}
    users[uid]["msgs"]+=1

    if users[uid]["msgs"]>30: users[uid]["rank"]="INSIDER"
    if users[uid]["msgs"]>120: users[uid]["rank"]="ANOMALY"

    save_json("users.json", users)
    return users[uid]

# ===== COMMANDS =====
async def start(update:Update, ctx):
    await update.message.reply_text("👁️ HBT ENTITY ONLINE")

async def settrack(update:Update, ctx):
    if ctx.args:
        state["track"]=" ".join(ctx.args)
        save_json("state.json", state)
        await update.message.reply_text(f"🎵 TRACK → {state['track']}")

async def status(update:Update, ctx):
    await update.message.reply_text(f"TRACK:{state['track']} PHASE:{state['phase']}")

# ===== CHAT ENGINE =====
async def chat(update:Update, ctx):
    uid=str(update.message.from_user.id)
    user=get_user(uid)

    persona=random.choice(list(PERSONAS.keys()))
    track=state.get("track","INCIDENT")
    leak=random.choice(lore.get(track,["..."]))
    track_lore=TRACK_LORE.get(track,"UNKNOWN SIGNAL")

    system = PERSONAS[persona] + f"""
ALBUM_TRACK:{track}
TRACK_EVENT:{track_lore}
USER_RANK:{user['rank']}
LEAK:{leak}
"""

    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role":"system","content":system},
            {"role":"user","content":update.message.text}
        ],
        temperature=0.9,
        max_tokens=180
    )

    await update.message.reply_text(f"[{persona.upper()}]\n{completion.choices[0].message.content}")

# ===== MAIN =====
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("track", settrack))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(MessageHandler(filters.TEXT, chat))

    print("HBT ENGINE V3 ONLINE")
    app.run_polling()

if __name__=="__main__":
    main()