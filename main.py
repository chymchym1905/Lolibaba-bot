import discord
from discord.message import Message
from ollama import AsyncClient
import json
import os
import dotenv

dotenv.load_dotenv()

ACC_TOKEN = os.getenv("TOKEN")

# Define your target channel IDs
TARGET_CHANNELS = [
    1330237721557471232, #hideout count
    1334351579058405447 #testing
]

BLOCK_LIST =  [
    159985870458322944,
    510016054391734273
]

import re

def remove_think_content(text):
    return re.sub(r'<think>.*?</think>\n?', '', text, flags=re.DOTALL)

def is_positive_number(s):
    try:
        # Try to convert the string to a float
        num = float(s)
        # Check if the number is positive
        if num > 0:
            return True
        else:
            return False
    except ValueError:
        # If conversion fails, it's not a number
        return False

class MyClient(discord.Client):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.messagehistory = {}
        for item in os.listdir():
            if item.endswith('.txt'):
                self.messagehistory[item.split('.')[0]] = self._load_messages_from_file(item)
        for channel in TARGET_CHANNELS: 
            if channel not in self.messagehistory:
                self.messagehistory[channel] = [
                    {
                        "role": "system", 
                        "content": """My most important trait is I only make simple response to simple question, and  my user id is 793266426349748235. 
                        When someone <@793266426349748235>, that means they are calling me out, and I just respond naturally 
                        without mentioning that i was being mentioned. 
                        In the context of messagging, <@number> means mentioning or @ating a user by their userid. When there's
                        a message that include <@number>, I will implicitly understand that a user is being mentioned."""
                    }
                ]# Initialize conversation context
        self.ollama_client = AsyncClient()  # Initialize Ollama client

    def _load_messages_from_file(self, file_path: str) -> list:
        """Load messages from a file. Return an empty list if the file is empty or doesn't exist."""
        try:
            with open(file_path, 'r') as file:
                content = file.read()
                if not content:
                    return []
                return json.loads(content)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _save_messages_to_file(self, file_path: str, messages: list):
        """Save messages to a file."""
        with open(file_path, 'w') as file:
            json.dump(messages, file)

    async def on_ready(self):
        print(f'Logged on as {self.user}')

    async def generate_response(self, user_message: dict, author: str, channelid) -> str:
        """Generate a response using the Ollama model."""
        author = author.replace("#0","")
        print(fr"Replying to {author}: {user_message['content']}")
        # Append user message to the conversation history
        self.messagehistory[channelid].append( {'role': 'user', "content": fr'{author} says: {user_message["content"]}'})
        print(self.messagehistory[channelid])
        # Generate response using Ollama
        response = await self.ollama_client.chat(model='gemma2:2b', messages=self.messagehistory[channelid])
        ret: str = remove_think_content(response['message']['content'])

        # Append the tool's response to the conversation history
        self.messagehistory[channelid].append({"role": "system", "content": ret})

        # Save updated messages to file
        self._save_messages_to_file(f'{channelid}.txt', self.messagehistory[channelid])

        # Limit the conversation history to 100 messages
        if len(self.messagehistory[channelid]) > 100:
            self.messagehistory[channelid].pop(1)

        print(ret)
        if is_positive_number(ret) or is_positive_number(ret[0]) or ret.lower().startswith("pi") or ret.lower().startswith("π"):
            ret = "Hah, don't think you got me this time: " + ret
        return ret.strip()

    async def on_message(self, message: Message):
        if message.author == self.user:
            return  # Ignore bot's own messages

        # Check if the message is from a specific channel and bot is mentioned
        if message.guild and message.channel.id in TARGET_CHANNELS:
            if is_positive_number(message.content): # Counting
                await message.channel.typing()
                await message.channel.send(int(round(float(message.content)) + 1))
            if self.user.mentioned_in(message): # Generative response
                if message.author.id in BLOCK_LIST:
                    return
                await message.channel.typing()
                response = await self.generate_response({'role': 'user', 'content': message.content}, str(message.author), message.channel.id)
                await message.reply(response)



client = MyClient()
client.run(ACC_TOKEN) 
