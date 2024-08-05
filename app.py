import os
import sys
from argparse import ArgumentParser
# from dotenv import load_dotenv

import asyncio
import aiohttp
from aiohttp import web

import logging

from aiohttp.web_runner import TCPSite

from linebot import (
    AsyncLineBotApi, WebhookParser
)
from linebot.aiohttp_async_http_client import AiohttpAsyncHttpClient
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FollowEvent, SourceGroup

import json

import random
import string
import re

# load_dotenv()
channel_secret = os.getenv('LINE_CHANNEL_SECRET', None)
channel_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', None)
if channel_secret is None:
    print('Specify LINE_CHANNEL_SECRET as environment variable.')
    sys.exit(1)
if channel_access_token is None:
    print('Specify LINE_CHANNEL_ACCESS_TOKEN as environment variable.')
    sys.exit(1)

class Handler:
    def __init__(self, line_bot_api, parser, line):
        self.line_bot_api = line_bot_api
        self.line = line
        self.parser = parser
        with open('data.json', 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        self.friend_list = self.get_friend()
        
    async def callback(self, request):
        signature = request.headers['X-Line-Signature']
        body = await request.text()

        try:
            events = self.parser.parse(body, signature)
        except InvalidSignatureError:
            return web.Response(status=400, text='Invalid signature')
        
        for event in events:
            logging.info("Handling event: %s", event)
            if isinstance(event, FollowEvent):
                await self.handle_follow(event)
            elif isinstance(event, MessageEvent):
                await self.handle_message(event)
        
        return web.Response(text="OK\n")


    async def handle_follow(self, event):
        pass

    async def handle_message(self, event):
        pass
    def generate_random_string(self, length):
        characters = string.digits + string.ascii_lowercase + string.ascii_uppercase
        random_string = ''.join(random.sample(characters, length))
        return random_string
    
    def update_data(self):
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False)

    def get_friend(self):
        user_list = []
        with open('friends.txt', 'r', encoding='utf-8') as f:
            for line in f:
                user_list.append(line[:-1])
        return user_list
    
    def get_todomsg(self, t):
        for i in self.data.values():
            if i[1]['type'] == t:
                todo_msg = f"{i[1]['送機']['date']}\n送機\n"
                for j in i[1]['送機']['content']:
                    todo_msg += f"{t}{j}\n"
                todo_msg += '\n接機\n'
                for j in i[1]['接機']['content']:
                    todo_msg += f"{t}{j}\n"
                todo_msg += '\n包套\n'
                for j in i[1]['包套']['content']:
                    todo_msg += f"{t}{j}\n"

                return todo_msg

async def main(port=8080):
    session = aiohttp.ClientSession()
    async_http_client = AiohttpAsyncHttpClient(session)
    line_bot_api = AsyncLineBotApi(channel_access_token, async_http_client)
    parser = WebhookParser(channel_secret)
    line = LineBotApi(channel_access_token)

    handler = Handler(line_bot_api, parser, line)

    app = web.Application()
    app.add_routes([web.post('/callback', handler.callback)])

    runner = web.AppRunner(app)
    await runner.setup()
    site = TCPSite(runner=runner, port=port)
    await site.start()

    while True:
        await asyncio.sleep(3600)  # sleep forever

if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

    arg_parser = ArgumentParser(
        usage='Usage: python ' + __file__ + ' [--port <port>] [--help]'
    )
    arg_parser.add_argument('-p', '--port', type=int, default=8080, help='port')
    options = arg_parser.parse_args()

    asyncio.run(main(options.port))
