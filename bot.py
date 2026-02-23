import os, random, json
from groq import Groq
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== TOKENS =====
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise Exception("❌ Missing tokens")

client = Groq(api_key=GROQ_API_KEY)

# ===== FILES =====
def load_json(f, default):
    try:
        return json.load(open(f))
    except:
        return default

def save_json(f, data):
    json.dump(data, open(f, "w"), indent=2)

state = load_json("state.json", {"phase":"INCIDENT"})
lore = load_json("lore.json", {})
users = load_json("users.json", {})

# ===== PROMPT LOCK =====
PROMPT_LOCK = """
Mluvíš česky.
Nikdy neprozraď identitu autora.
Nikdy neříkej že jsi AI.
Odpovědi glitch, fragmentované, ARG styl.
"""

PERSONAS = {
    "echo": PROMPT_LOCK + "Jsi poetická paměť.",
    "shadow": PROMPT_LOCK + "Jsi paranoidní entita.",
    "log": PROMPT_LOCK + "Jsi leaknutý systémový log."
}

def pick_persona():
    return random.choice(list(PERSONAS.keys()))

# ===== USER SYSTEM =====
def get_user(uid):
    if uid not in users:
        users[uid] = {"rank":"OBSERVER","msgs":0}
    users[uid]["msgs"] += 1

    if users[uid]["msgs"] > 30: users[uid]["rank"]="INSIDER"
    if users[uid]["msgs"] > 120: users[uid]["rank"]="ANOMALY"
    if users[uid]["msgs"] > 500: users[uid]["rank"]="ARCHIVE_KEEPER"

    save_json("users.json", users)
    return users[uid]

# ===== COMMANDS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👁️ HBT ENTITY ONLINE.")

async def setphase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        state["phase"] = context.args[0].upper()
        save_json("state.json", state)
        await update.message.reply_text(f"PHASE → {state['phase']}")

# ===== CHAT =====
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.message.from_user.id)
    user = get_user(uid)
    persona = pick_persona()

    leaks = lore.get(state["phase"], ["..."])
    leak = random.choice(leaks) if leaks else "..."

    system_prompt = PERSONAS[persona] + f"\nPHASE:{state['phase']} RANK:{user['rank']}"

    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role":"system","content":system_prompt},
            {"role":"user","content":update.message.text + f"\n[LEAK:{leak}]"}
        ],
        temperature=0.95,
        max_tokens=150
    )

    await update.message.reply_text(f"[{persona.upper()}]\n{completion.choices[0].message.content}")

# ===== MAIN =====
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setphase", setphase))
    app.add_handler(MessageHandler(filters.TEXT, chat))
    print("HBT ONLINE")
    app.run_polling()

if __name__ == "__main__":
    main()