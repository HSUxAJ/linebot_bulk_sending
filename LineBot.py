import os
import sys
from argparse import ArgumentParser
from dotenv import load_dotenv

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

# from .mention import Mention
# from .mentionee import Mentionee

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FollowEvent, SourceGroup

import multiprocessing
import requests
import json

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

import random
import string
import re

from openpyxl import load_workbook

load_dotenv()
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
        self.scheduler = BackgroundScheduler()
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
        user_id = event.source.user_id
        if user_id not in self.friend_list:
            self.friend_list.append(user_id)
            print('new friend!!')
            with open('friends.txt', 'w', encoding='utf-8') as f:
                for i in self.friend_list:
                    f.write(i + '\n')

    async def handle_message(self, event):
        user_id = event.source.user_id
        profile = self.line.get_profile(user_id)
        user_name = profile.display_name
        content_message = event.message.text
        if event.message.type == 'text':
            #取得群發身分
            if isinstance(event.source, SourceGroup) and event.source.group_id == 'C27c109614ab240ea15638e3f95ad7a26' and content_message == 'get':
                self.data[user_id] = [{},
                                      {"type": chr(ord('a')+len(self.data)-1),
                                       "送機": { "date": "", "content": [] },
                                       "接機": { "date": "", "content": [] },
                                       "包套": { "date": "", "content": [] }}]
                self.update_data()
                self.line.push_message(user_id, TextMessage(text=f"{user_name} 啟用成功!"))
                
                return
            #查詢小幫手數量
            if user_id == "Uf588c46a23189172c99e95ce7c0db6f1" and content_message == "小幫手數量":
                message = "下表為目前有使用服務的小幫手~\n"
                cnt = 1
                for id in self.data:
                    if id == "manager's_id":
                        continue
                    message += f"{cnt}. {user_name}\n"
                    cnt += 1
                self.line.push_message(user_id, TextMessage(text=message))

            if user_id in self.data:
                if content_message == "new子群":
                    new_pwd = self.generate_random_string(20)
                    for key, val in self.data.items():
                        print(key, val)
                        if key == user_id:
                            if len(val) < 10: #子群最多10個
                                val[0][new_pwd] = ''
                            else:
                                self.line.push_message(user_id, TextMessage(text=f'{user_name} 的子群數量已達上限!'))   
                                return
                    self.line.push_message(user_id, TextMessage(text='子群啟用密碼為：' + new_pwd))   
                    self.update_data()
                
                elif content_message[0] == '#' and content_message[1] == '#':
                    #儲存訂單
                    content_message = content_message[3:]
                    # ex:
                    # 7/11
                    # 送機
                    # 0250 4人 板橋區送【假七】-URM999126

                    # 接機
                    # 1745 4人 接桃園觀音區【2.0】-邱昭瑾
                    # 2010 3人 接大同區【假七】-VXH973284
                    # 2320 4人 接新竹竹東鎮【2.0】-24KK295365016

                    # 包套
                    # 1745 4人 接桃園觀音區【2.0】-邱昭瑾
                    tasks = content_message.split('\n')
                    cnt = 1
                    todo = {"type": self.data[user_id][1]['type'],
                            "送機": {"date":tasks[0], "content":[]},
                            "接機": {"date":tasks[0], "content":[]},
                            "包套": {"date":tasks[0], "content":[]}}
                    print(self.data[user_id][1]['type'])
                    todo_msg = f"幫{user_name}派單\n{tasks[0]}\n送機\n"
                    for i in range(tasks.index("送機")+1, len(tasks)):
                        if len(tasks[i]) < 1:
                            break
                        todo['送機']["content"].append(f"{cnt}. {tasks[i]}")
                        todo_msg += f"{todo['type']}{cnt}. {tasks[i]}\n"
                        cnt += 1
                    todo_msg += '\n接機\n'
                    for i in range(tasks.index("接機")+1, len(tasks)):
                        if len(tasks[i]) < 1:
                            break
                        todo['接機']["content"].append(f"{cnt}. {tasks[i]}")
                        todo_msg += f"{todo['type']}{cnt}. {tasks[i]}\n"
                        cnt += 1
                    todo_msg += '\n包套\n'
                    for i in range(tasks.index("包套")+1, len(tasks)):
                        if len(tasks[i]) < 1:
                            break
                        todo['包套']["content"].append(f"{cnt}. {tasks[i]}")
                        todo_msg += f"{todo['type']}{cnt}. {tasks[i]}\n"
                        cnt += 1

                    #群發
                    for pwd, id in self.data[user_id][0].items():
                        self.line.push_message(id, TextMessage(text=todo_msg))

                    self.data[user_id][1] = todo
                    self.update_data()

                elif content_message == "剩餘訂單":
                    message = "剩餘訂單如下: \n"
                    message += self.get_todomsg(self.data[user_id][1]['type'])
                    self.line.push_message(user_id, TextMessage(text=message))
            if event.source.type != 'group':
                return
            #檢查是否為密碼
            group_id = event.source.group_id
            is_pwd = False
            for vals in self.data.values():
                for pwd, id in vals[0].items():
                    if pwd == content_message:
                        if id == '':
                            vals[0][pwd] = group_id
                            self.line.push_message(group_id, TextMessage(text=f'{user_name} 的子群成功啟用~({len(vals[0])}/10)'))
                            is_pwd = True
                        elif id != group_id:
                            self.line.push_message(group_id, TextMessage(text='{user_name}，此密碼已被使用過~'))
                        else:
                            self.line.push_message(group_id, TextMessage(text='{user_name}，群組不需再次啟用~'))
            if is_pwd:
                self.update_data()
                return
                    
            #標單
            match = re.match(r'#([a-zA-Z]+)(\d+)', content_message)
            if match:
                #檢查是否為啟用群組
                is_sub_group = False
                t = ''
                for vals in self.data.values():
                    if group_id in vals[0].values():
                        is_sub_group = True
                if not is_sub_group:
                    return
                
                type_str = match.group(1)
                num = match.group(2)
                owner_data = {}
                owner_id = ""
                fd = False
                #檢查type存不存在
                for id, vals in self.data.items():
                    if vals[1]['type'] == type_str:
                        owner_data = vals
                        owner_id = id
                        fd = True
                        break
                if not fd:
                    self.line.push_message(group_id, TextMessage(text=f"標單編號不存在，標單失敗!"))
                    return
                #檢查num存不存在
                info = ""
                group_summary = self.line.get_group_summary(group_id)
                group_name = group_summary.group_name
                fd = False
                t = ['送機', '接機', '包套']
                for tt in t:
                    for c in owner_data[1][tt]['content']:
                        m = re.match(r'(\d+)\.', c)
                        if m and m.group(1) == num:
                            info = f"日期：{owner_data[1][tt]['date']}，{c}，司機為：'{user_name}，來自：{group_name}"
                            owner_data[1][tt]['content'].pop(owner_data[1][tt]['content'].index(c))
                            fd = True
                if fd:
                    self.data[owner_id] = owner_data
                    self.update_data()

                    #傳訊息給司機與小幫手
                    self.line.push_message(owner_id, TextMessage(text=info))
                    self.line.push_message(user_id, TextMessage(text=info))
                else:
                    self.line.push_message(group_id, TextMessage(text=f"標單編號不存在或已被搶，標單失敗!\n{self.get_todomsg(type_str)}"))
            else:
                self.line.push_message(group_id, TextMessage(text="標單格式錯誤!"))
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

    handler.scheduler.start()

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