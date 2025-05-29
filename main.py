import discord
import requests
from bs4 import BeautifulSoup
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TWITTER_BEARER_TOKEN = os.getenv("TWITTER_BEARER_TOKEN")
AIR_DROP_CHANNEL_ID = int(os.getenv("AIR_DROP_CHANNEL_ID"))
INSIDER_CHANNEL_ID = int(os.getenv("INSIDER_CHANNEL_ID"))

INSIDER_USERNAMES = ['whale_alert', 'cryptoleaks', 'lookonchain']
visited_airdrops = set()
last_tweets = {}

client = discord.Client(intents=discord.Intents.default())

async def fetch_airdrops_io():
    url = "https://airdrops.io/latest/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    links = soup.select("div.titledesc > h3 > a")
    new_drops = []
    for link in links:
        href = link['href']
        title = link.text.strip()
        if href not in visited_airdrops:
            visited_airdrops.add(href)
            new_drops.append((title, href))
    return new_drops

async def fetch_airdropsalert():
    url = "https://airdropsalert.com/latest-airdrops/"
    headers = {'User-Agent': 'Mozilla/5.0'}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    cards = soup.select('div.card-header a')
    new_drops = []
    for card in cards:
        href = 'https://airdropsalert.com' + card['href']
        title = card.text.strip()
        if href not in visited_airdrops:
            visited_airdrops.add(href)
            new_drops.append((title, href))
    return new_drops

async def airdrop_notifier():
    await client.wait_until_ready()
    channel = client.get_channel(AIR_DROP_CHANNEL_ID)
    while not client.is_closed():
        drops_io = await fetch_airdrops_io()
        drops_alert = await fetch_airdropsalert()
        all_drops = drops_io + drops_alert
        for name, link in all_drops:
            await channel.send(f"🪂 Nowy Airdrop: **{name}**\n🔗 {link}")
        await asyncio.sleep(3600)

async def update_status():
    await client.wait_until_ready()
    coins = ['bitcoin', 'ethereum', 'solana']
    names = ['BTC', 'ETH', 'SOL']
    while not client.is_closed():
        for coin, name in zip(coins, names):
            try:
                url = f'https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd'
                response = requests.get(url)
                data = response.json()
                price = data[coin]['usd']
                await client.change_presence(activity=discord.Game(name=f'{name}: ${price:.2f}'))
            except Exception as e:
                print(f'❌ Błąd ceny {name}:', e)
            await asyncio.sleep(10)

def get_user_id(username):
    url = f"https://api.twitter.com/2/users/by/username/{username}"
    headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
    r = requests.get(url, headers=headers)
    data = r.json()
    return data['data']['id']

def get_latest_tweet(user_id):
    url = f"https://api.twitter.com/2/users/{user_id}/tweets?max_results=5&tweet.fields=created_at"
    headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}
    r = requests.get(url, headers=headers)
    data = r.json()
    if "data" not in data:
        return None
    return data["data"][0]

async def twitter_monitor():
    await client.wait_until_ready()
    channel = client.get_channel(INSIDER_CHANNEL_ID)
    user_ids = {u: get_user_id(u) for u in INSIDER_USERNAMES}
    while not client.is_closed():
        for username, user_id in user_ids.items():
            try:
                tweet = get_latest_tweet(user_id)
                if not tweet:
                    continue
                tweet_id = tweet["id"]
                if last_tweets.get(username) != tweet_id:
                    last_tweets[username] = tweet_id
                    tweet_url = f"https://twitter.com/{username}/status/{tweet_id}"
                    await channel.send(f"🧠 Nowy tweet od **{username}**:\n🔗 {tweet_url}")
            except Exception as e:
                print(f"❌ Błąd Twittera ({username}): {e}")
        await asyncio.sleep(60)

@client.event
async def on_ready():
    print(f'✅ Zalogowano jako {client.user}')

client.loop.create_task(airdrop_notifier())
client.loop.create_task(update_status())
client.loop.create_task(twitter_monitor())
client.run(DISCORD_TOKEN)
