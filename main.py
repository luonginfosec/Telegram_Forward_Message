import time
import asyncio
from telethon.sync import TelegramClient
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, MessageMediaWebPage
import re
import requests

def read_url_post():
    try:
        with open("url.txt", "r", encoding='utf-8') as file:
            url = file.readline().strip()
            if url:
                return url
            else:
                print("URL not found in the url.txt file.")
                return None
    except FileNotFoundError:
        print("url.txt file not found.")
        return None

def replace_urls_in_text(text):
    url_pattern = r'(https?://[^\s]+)'

    def replace_url(match):
        url = match.group(1)
        try:
            data = {
                "text": url,
                "submit": ""
            }
            response = requests.post(urlPost, data=data).text
            regex = r'<textarea[^>]*class="[^"]*form-control[^"]*"[^>]*>(https?://[^\s<]+)</textarea>'
            matches = re.findall(regex, response)
            return matches[-1] if matches else url
        except Exception as e:
            print(f"Error processing URL {url}: {e}")
            return url

    new_text = re.sub(url_pattern, replace_url, text)
    return new_text

# TelegramForwarder class
class TelegramForwarder:
    def __init__(self, api_id, api_hash, phone_number):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone_number = phone_number
        self.client = TelegramClient('session_' + phone_number, api_id, api_hash)

    async def list_chats(self):
        await self.client.connect()

        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone_number)
            await self.client.sign_in(self.phone_number, input('Enter the code: '))

        dialogs = await self.client.get_dialogs()
        with open(f"chats_of_{self.phone_number}.txt", "w", encoding='utf-8') as chats_file:
            for dialog in dialogs:
                print(f"Chat ID: {dialog.id}, Title: {dialog.title}")
                chats_file.write(f"Chat ID: {dialog.id}, Title: {dialog.title}\n")

        print("List of groups printed successfully!")

    async def forward_messages_to_channel(self, source_chat_id, destination_channel_id, keywords):
        await self.client.connect()

        if not await self.client.is_user_authorized():
            await self.client.send_code_request(self.phone_number)
            await self.client.sign_in(self.phone_number, input('Enter the code: '))

        last_message_id = (await self.client.get_messages(source_chat_id, limit=1))[0].id

        while True:
            try:
                print("Checking for messages and forwarding them...")
                messages = await self.client.get_messages(source_chat_id, min_id=last_message_id, limit=None)
                for message in reversed(messages):
                    should_forward = False
                    modified_text = message.text if message.text else ""
                    if modified_text:
                        modified_text = replace_urls_in_text(modified_text)
                        if keywords:
                            if any(keyword.strip().lower() in modified_text.lower() for keyword in keywords):
                                should_forward = True
                                print(f"Message contains a keyword: {modified_text}")
                        else:
                            should_forward = True
                    elif not keywords and (message.media or message.photo or message.document):
                        should_forward = True

                    if should_forward:
                        try:
                            # Check if there is text and it's modified
                            if modified_text and modified_text != message.text:
                                # Only attach file if media is a valid file type (photo or document)
                                await self.client.send_message(
                                    destination_channel_id,
                                    modified_text,
                                    file=message.media if isinstance(message.media, (MessageMediaPhoto, MessageMediaDocument)) else None
                                )
                            else:
                                # Forward the message with media
                                await self.client.forward_messages(
                                    destination_channel_id,
                                    message.id,
                                    source_chat_id
                                )
                            print("Message forwarded successfully")
                        except Exception as e:
                            print(f"Error forwarding message: {str(e)}")

                    last_message_id = max(last_message_id, message.id)

            except Exception as e:
                print(f"Error occurred: {str(e)}")
                await asyncio.sleep(5)  
                continue
            await asyncio.sleep(5)  


def read_credentials():
    try:
        with open("credentials.txt", "r", encoding='utf-8') as file:
            lines = file.readlines()
            api_id = lines[0].strip()
            api_hash = lines[1].strip()
            phone_number = lines[2].strip()
            return api_id, api_hash, phone_number
    except FileNotFoundError:
        print("Credentials file not found.")
        return None, None, None


def write_credentials(api_id, api_hash, phone_number):
    with open("credentials.txt", "w", encoding='utf-8') as file:
        file.write(api_id + "\n")
        file.write(api_hash + "\n")
        file.write(phone_number + "\n")


async def main():
    global urlPost
    urlPost = read_url_post()  

    if urlPost is None:
        print("Exiting program due to missing or invalid URL in url.txt.")
        return  

    api_id, api_hash, phone_number = read_credentials()

    if api_id is None or api_hash is None or phone_number is None:
        api_id = input("Enter your API ID: ")
        api_hash = input("Enter your API Hash: ")
        phone_number = input("Enter your phone number: ")
        write_credentials(api_id, api_hash, phone_number)

    forwarder = TelegramForwarder(api_id, api_hash, phone_number)
    
    print("Choose an option:")
    print("1. List Chats")
    print("2. Forward Messages")
    
    choice = input("Enter your choice: ")
    
    if choice == "1":
        await forwarder.list_chats()
    elif choice == "2":
        source_chat_id = int(input("Enter the source chat ID: "))
        destination_channel_id = int(input("Enter the destination chat ID: "))
        print("Enter keywords if you want to forward messages with specific keywords, or leave blank to forward every message!")
        keywords_input = input("Put keywords (comma separated if multiple, or leave blank): ")
        keywords = [k.strip() for k in keywords_input.split(",")] if keywords_input.strip() else []
        await forwarder.forward_messages_to_channel(source_chat_id, destination_channel_id, keywords)
    else:
        print("Invalid choice")

if __name__ == "__main__":
    asyncio.run(main())
