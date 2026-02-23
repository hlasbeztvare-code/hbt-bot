# ===== IMPORTS =====
import os, random, json
from groq import Groq
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== TOKENS =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise Exception("Missing ENV TOKENS")

client = Groq(api_key=GROQ_API_KEY)

# ===== FILE UTILS =====
def load_json(f, default):
    try: return json.load(open(f))
    except: return default

def save_json(f, data):
    json.dump(data, open(f, "w"), indent=2)

state = load_json("state.json", {"phase":"INCIDENT"})
tracks = load_json("tracks.json", {"current":"INCIDENT","order":[]})
lore = load_json("lore.json", {})
users = load_json("users.json", {})

# ===== PROMPT CORE =====
PROMPT_LOCK = """
Mluvíš česky.
Nikdy neříkej že jsi AI, bot nebo software.
Nikdy neprozrazuj identitu autorů.
Nikdy nevysvětluj projekt přímo.
Odpovídej glitch stylem, leak dokument, fragment vědomí.
"""

PERSONAS = {
 "echo": PROMPT_LOCK + "Jsi paměť systému, poetický fragment.",
 "shadow": PROMPT_LOCK + "Jsi paranoidní varování systému.",
 "narrator": PROMPT_LOCK + "Jsi leaknutý interní log."
}

# ===== USER SYSTEM =====
def get_user(uid):
    if uid not in users:
        users[uid] = {"rank":"OBSERVER","msgs":0}
    users[uid]["msgs"] += 1

    m = users[uid]["msgs"]
    if m > 30: users[uid]["rank"]="INSIDER"
    if m > 120: users[uid]["rank"]="ANOMALY"
    if m > 500: users[uid]["rank"]="ARCHIVE_KEEPER"

    save_json("users.json", users)
    return users[uid]

# ===== ARG CODES =====
SECRET_CODES = {
 "SIG-137":"INSIDER",
 "ECHO-001":"ANOMALY",
 "NULL-404":"ARCHIVE_KEEPER"
}

# ===== AUTO LORE GENERATOR =====
async def generate_lore_fragment(phase):
    prompt = f"Vytvoř glitch leak lore fragment pro fázi {phase}. Jedna věta."
    c = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role":"system","content":prompt}],
        temperature=1,
        max_tokens=40
    )
    return c.choices[0].message.content.strip()

# ===== COMMANDS =====
async def start(update, context):
    await update.message.reply_text("👁️ HBT ENTITY ONLINE. INCIDENT ACTIVE.")

async def setphase(update, context):
    if context.args:
        state["phase"]=context.args[0].upper()
        tracks["current"]=state["phase"]
        save_json("state.json", state)
        save_json("tracks.json", tracks)
        await update.message.reply_text(f"PHASE SWITCHED → {state['phase']}")

async def track_cmd(update, context):
    if context.args:
        tracks["current"]=context.args[0].upper()
        state["phase"]=tracks["current"]
        save_json("tracks.json", tracks)
        save_json("state.json", state)
        await update.message.reply_text(f"TRACK ENGINE → {tracks['current']}")

async def code_cmd(update, context):
    uid=str(update.message.from_user.id)
    if not context.args: return
    c=context.args[0].upper()
    if c in SECRET_CODES:
        users[uid]["rank"]=SECRET_CODES[c]
        save_json("users.json", users)
        await update.message.reply_text(f"[ACCESS GRANTED] {SECRET_CODES[c]}")
    else:
        await update.message.reply_text("CODE CORRUPTED.")

async def newlore(update, context):
    frag = await generate_lore_fragment(state["phase"])
    lore.setdefault(state["phase"],[]).append(frag)
    save_json("lore.json", lore)
    await update.message.reply_text("[NEW LORE]\n"+frag)

# ===== CHAT CORE =====
async def chat(update, context):
    uid=str(update.message.from_user.id)
    user=get_user(uid)
    persona=random.choice(list(PERSONAS.keys()))
    system = PERSONAS[persona] + f"\nPHASE:{state['phase']} RANK:{user['rank']}"

    leak=random.choice(lore.get(state["phase"],["..."]))
    text=update.message.text + f"\n[LEAK:{leak}]"

    c=client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role":"system","content":system},
            {"role":"user","content":text}
        ],
        temperature=0.95,
        max_tokens=180
    )

    reply=c.choices[0].message.content
    await update.message.reply_text(f"[{persona.upper()}]\n{reply}")

    # AUTO LORE (10%)
    if random.random()<0.1:
        frag=await generate_lore_fragment(state["phase"])
        lore.setdefault(state["phase"],[]).append(frag)
        save_json("lore.json", lore)

# ===== MAIN =====
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setphase", setphase))
    app.add_handler(CommandHandler("track", track_cmd))
    app.add_handler(CommandHandler("code", code_cmd))
    app.add_handler(CommandHandler("newlore", newlore))
    app.add_handler(MessageHandler(filters.TEXT, chat))

    print("HBT SINGULARITY ENTITY ONLINE")
    app.run_polling()

if __name__=="__main__":
    main()