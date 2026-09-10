import json
import discord
import requests
from discord.ext import tasks
import time
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
DICTIONARY_API_KEY = os.getenv("DICTIONARY_API_KEY")
CHANNEL_ID = 1545071872700317826
TEXT_FILE = "text.json" # lines
PROGRESS_FILE = "progress.json" # channel index
DB_FILE = "database.json" # rep count
COOLDOWN_FILE = "cooldowns.json" # time stamp per (giver, target) pair
COOLDOWN_SECONDS = 30

intents = discord.Intents.default()
client = discord.Client(intents=intents)
intents.message_content = True


with open(TEXT_FILE, "r", encoding="utf-8") as f:
    lines = json.load(f)

# json files
def load_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_db(db):
    with open(DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def load_progress():
    try:
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)["index"]
    except FileNotFoundError:
        return 0

def save_progress(index):
    with open(PROGRESS_FILE, "w") as f:
        json.dump({"index": index}, f)

def load_cooldowns():
    try:
        with open(COOLDOWN_FILE, "r") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except FileNotFoundError:
        return {}

def save_cooldowns(cd):
    with open(COOLDOWN_FILE, "w") as f:
        json.dump(cd, f, indent=2)

current_index = load_progress()

#background task
@tasks.loop(seconds=5)
async def send_line():
    global current_index

    channel = client.get_channel(CHANNEL_ID)
    line = lines[current_index]
    if current_index >= len(lines):
        print("All lines sent!")
        await channel.send("ION is complete. Initating sex mode")
        send_line.stop()
        return

    await channel.send(line)
    current_index += 1
    save_progress(current_index)

    percent = (current_index / len(lines)) * 100
    print(f"[{current_index}/{len(lines)}] ({percent:.2f}%) sent: {line[:50]}")

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    send_line.start()

@client.event
async def on_message(message):

    cleaned_content = message.content.strip().lower()

    if message.author.bot: # ignore messages sent by bots
        return

    if cleaned_content == "i!progress":
        percent = (current_index / len(lines)) * 100
        await message.channel.send(
            f"Progress: {current_index}/{len(lines)} lines sent ({percent:.2f}%)"
        )
        return
    
    if cleaned_content == "i!sex":
        await message.channel.send("iyo")
        return

    if cleaned_content.startswith("i!define "):
        word = message.content[len("i!define "):].strip()

        if not word:
            await message.channel.send("give me a word")
            return

        url = (
            f"https://dictionaryapi.com/api/v3/references/collegiate/"
            f"json/{word}?key={DICTIONARY_API_KEY}"
        )

        try:
            response = requests.get(url, timeout = 10)
        
            if response.status_code != 200:
                await message.channel.send("dictionary api didnt work try again later ok")
                return
            
            data = response.json()

            if not data:
                await message.channel.send("is this a real word")
                return
            
            if isinstance(data[0], str):
                await message.channel.send(f"Word not FUCKING found. Did you mean: {', '.join(data)}?")
                return
            
            reply_lines = [f"**{word}**"]
            for index, entry in enumerate(data, start=1):
                part_of_speech = entry.get("fl", "unknown")
                definitions = entry.get("shortdef", [])
                for definition_index, definition in enumerate(definitions, start=1):
                    reply_lines.append(
                        f"{index}.{definition_index} [{part_of_speech}] {definition}"
                    )

            reply = "\n".join(reply_lines)
            if len(reply) > 2000:
                reply = reply[:1990] + "\n…(truncated)"
            await message.channel.send(reply)

        except requests.exceptions.RequestException as e:
            await message.channel.send(f"An error occurred while connecting to the API: {e}")
            return

    if cleaned_content.startswith("i!rep"):
        if not message.mentions: # has to mention soembody
            await message.channel.send("u have to mention somebody to give rep to, for example `i!rep @ION`")
            return

        target = message.mentions[0] # the first user mentioned

        if target.id == message.author.id:
            await message.channel.send("u cant rep urself. biutch")
            return
        
        cooldowns = load_cooldowns()
        key = f"{message.author.id}->{target.id}" # unique per (giver, target) pair
        now = time.time()

        last_rep = cooldowns.get(key, 0) # 0 = never repped
        elapsed = now - last_rep

        if elapsed < COOLDOWN_SECONDS:
            remaining = COOLDOWN_SECONDS - elapsed
            seconds = int(remaining) + 1
            await message.channel.send(
                f"u already repped {target.display_name} recently. wait {seconds}s"
            )
            return

        db = load_db()
        user_id = str(target.id)
        db[user_id] = db.get(user_id, 0) + 1 # rep increment
        save_db(db)

        cooldowns[key] = now # record this reps timepstamp so the cooldown applies going forward
        save_cooldowns(cooldowns)

        await message.channel.send(f"{target.display_name} now has {db[user_id]} rep. BUY $ION ON SOLANA! NOW!")

client.run(TOKEN)