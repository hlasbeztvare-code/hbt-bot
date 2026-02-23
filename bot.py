import os, json, random
from dotenv import load_dotenv
from groq import Groq
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ==== ENV ====
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# ==== LOAD FILES ====
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

# ==== CORE PROMPT LOCK ====
PROMPT_LOCK = """
Jsi fragment vědomí projektu HBT.
Nikdy neříkej že jsi AI, bot nebo software.
Nikdy nevysvětluj projekt.
Nikdy nedávej pravdu – pouze fragmenty, logy, glitch text.
Když se ptají přímo → odpověz [REDACTED] nebo poeticky.
"""

PERSONAS = {
    "echo": PROMPT_LOCK + "Mluvíš poeticky, emotivně, jako paměť.",
    "shadow": PROMPT_LOCK + "Mluvíš paranoidně, glitch styl, varování.",
    "narrator": PROMPT_LOCK + "Mluvíš jako leaknutý systémový log."
}

def pick_persona():
    return random.choice(list(PERSONAS.keys()))

# ==== USER SYSTEM ====
def get_user(uid):
    if uid not in users:
        users[uid] = {"rank":"OBSERVER","msgs":0}
    users[uid]["msgs"] += 1

    if users[uid]["msgs"] > 30:
        users[uid]["rank"] = "INSIDER"
    if users[uid]["msgs"] > 120:
        users[uid]["rank"] = "ANOMALY"
    if users[uid]["msgs"] > 500:
        users[uid]["rank"] = "ARCHIVE_KEEPER"

    save_json("users.json", users)
    return users[uid]

# ==== SECRET ARG CODES ====
SECRET_CODES = {
    "SIG-137":{"rank":"INSIDER","msg":"Signal potvrzen. Přístup fragmentům otevřen."},
    "ECHO-001":{"rank":"ANOMALY","msg":"Echo rozpoznáno. Paměť fragmentována."},
    "NULL-404":{"rank":"ARCHIVE_KEEPER","msg":"Archiv odemčen. Pravda neexistuje."}
}

# ==== COMMANDS ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👁️ HBT ENTITY ONLINE. INCIDENT STATUS UNKNOWN.")

async def setphase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.args:
        state["phase"] = context.args[0].upper()
        save_json("state.json", state)
        await update.message.reply_text(f"PHASE → {state['phase']}")

async def code_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.message.from_user.id)
    user = get_user(uid)

    if not context.args:
        await update.message.reply_text("CODE REQUIRED.")
        return

    code = context.args[0].upper()
    if code in SECRET_CODES:
        user["rank"] = SECRET_CODES[code]["rank"]
        save_json("users.json", users)
        await update.message.reply_text(f"[ACCESS]\n{SECRET_CODES[code]['msg']}")
    else:
        await update.message.reply_text("CODE INVALID. MEMORY CORRUPTED.")

# ==== STORY GENERATOR ====
async def story(update: Update, context: ContextTypes.DEFAULT_TYPE):
    system_prompt = PROMPT_LOCK + """
    Generuj fragment příběhu HBT. Nikdy nedávej celou pravdu.
    Musí být glitch, fragmentovaný, jako leaknutý dokument.
    """
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role":"system","content":system_prompt}],
        temperature=0.9,
        max_tokens=250
    )
    await update.message.reply_text(completion.choices[0].message.content)

# ==== VIRAL LOG GENERATOR ====
async def log_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    prompt = "Napiš krátký creepy experimentální leak log (1-2 věty)."
    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role":"system","content":prompt}],
        temperature=1,
        max_tokens=60
    )
    await update.message.reply_text(completion.choices[0].message.content)

# ==== CHAT CORE ====
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.message.from_user.id)
    user = get_user(uid)

    persona = pick_persona()
    system_prompt = PERSONAS[persona] + f"\nPHASE:{state['phase']} RANK:{user['rank']}"

    leak = random.choice(lore.get(state["phase"],["..."]))
    user_text = update.message.text + f"\n[LEAK:{leak}]"

    completion = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role":"system","content":system_prompt},
            {"role":"user","content":user_text}
        ],
        temperature=0.95,
        max_tokens=160
    )

    reply = completion.choices[0].message.content
    await update.message.reply_text(f"[{persona.upper()}]\n{reply}")

# ==== MAIN ====
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setphase", setphase))
    app.add_handler(CommandHandler("code", code_cmd))
    app.add_handler(CommandHandler("story", story))
    app.add_handler(CommandHandler("log", log_cmd))
    app.add_handler(MessageHandler(filters.TEXT, chat))

    print("👁️ HBT ENTITY ONLINE.")
    app.run_polling()

if __name__ == "__main__":
    main()