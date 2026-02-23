# ===== IMPORTS =====
import os, json, random
from groq import Groq
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== ENV =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise Exception("ENV NOT SET")

client = Groq(api_key=GROQ_API_KEY)

# ===== FILE UTILS =====
def load(f, default):
    try: return json.load(open(f))
    except: return default

def save(f, d):
    json.dump(d, open(f,"w"), indent=2)

state = load("state.json", {"phase":"INCIDENT","track":"INCIDENT"})
lore = load("lore.json", {})
users = load("users.json", {})
tracks = load("tracks.json", [])

# ===== CORE PROMPT LOCK =====
PROMPT_LOCK = """
Mluvíš ČESKY.
Nikdy neříkej že jsi AI nebo bot.
Nikdy neprozraď autora.
Nikdy nevysvětluj projekt.
O lore mluv jako leak log, glitch fragment.
Když se ptají přímo → odpověz [REDACTED].
"""

PERSONAS = {
 "echo": PROMPT_LOCK + "Poetická paměť.",
 "shadow": PROMPT_LOCK + "Paranoidní glitch varování.",
 "narrator": PROMPT_LOCK + "Leaknutý systémový log."
}

# ===== USER SYSTEM =====
def get_user(uid):
    if uid not in users:
        users[uid]={"rank":"OBSERVER","msgs":0}
    users[uid]["msgs"]+=1

    m=users[uid]["msgs"]
    if m>30: users[uid]["rank"]="INSIDER"
    if m>120: users[uid]["rank"]="ANOMALY"
    if m>500: users[uid]["rank"]="ARCHIVE_KEEPER"

    save("users.json",users)
    return users[uid]

# ===== SECRET CODES =====
CODES={
 "SIG-137":"INSIDER",
 "ECHO-001":"ANOMALY",
 "NULL-404":"ARCHIVE_KEEPER"
}

# ===== AUTO LORE GEN =====
async def gen_lore(phase):
    prompt=f"1 věta glitch ARG leak lore pro phase {phase}."
    r=client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role":"system","content":prompt}],
        temperature=1,
        max_tokens=40
    )
    return r.choices[0].message.content.strip()

# ===== COMMANDS =====
async def start(update,ctx):
    await update.message.reply_text("👁️ HBT ENTITY ONLINE.")

async def settrack(update,ctx):
    if ctx.args:
        t=" ".join(ctx.args)
        if t in tracks:
            state["track"]=t
            state["phase"]=t
            save("state.json",state)
            await update.message.reply_text(f"TRACK → {t}")

async def code(update,ctx):
    uid=str(update.message.from_user.id)
    if ctx.args and ctx.args[0] in CODES:
        users[uid]["rank"]=CODES[ctx.args[0]]
        save("users.json",users)
        await update.message.reply_text("ACCESS GRANTED.")
    else:
        await update.message.reply_text("CODE INVALID.")

async def newlore(update,ctx):
    frag=await gen_lore(state["phase"])
    lore.setdefault(state["phase"],[]).append(frag)
    save("lore.json",lore)
    await update.message.reply_text(f"[NEW FRAGMENT]\n{frag}")

# ===== CHAT CORE =====
async def chat(update,ctx):
    uid=str(update.message.from_user.id)
    user=get_user(uid)
    persona=random.choice(list(PERSONAS.keys()))

    leak=random.choice(lore.get(state["phase"],["..."]))
    system=PERSONAS[persona]+f"\nPHASE:{state['phase']} TRACK:{state['track']} RANK:{user['rank']}"

    completion=client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
          {"role":"system","content":system},
          {"role":"user","content":update.message.text+f"\n[LEAK:{leak}]"}
        ],
        temperature=0.95,
        max_tokens=160
    )

    reply=completion.choices[0].message.content
    await update.message.reply_text(f"[{persona.upper()}]\n{reply}")

    # AUTO LORE 10%
    if random.random()<0.1:
        frag=await gen_lore(state["phase"])
        lore.setdefault(state["phase"],[]).append(frag)
        save("lore.json",lore)

# ===== MAIN =====
def main():
    app=Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("track",settrack))
    app.add_handler(CommandHandler("code",code))
    app.add_handler(CommandHandler("newlore",newlore))
    app.add_handler(MessageHandler(filters.TEXT,chat))

    print("HBT FINAL ASCENSION ONLINE")
    app.run_polling()

if __name__=="__main__":
    main()