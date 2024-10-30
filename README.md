# *Telegram bot saving photos to Yandex Disk*

When sending or forwarding photos (including uncompressed) in chat with bot, it will save all photos to [Yandex Disk](https://360.yandex.ru/disk/) in a folder
(by default bot_uploads, you can choose any other). The bot accepts photos from specific users by checking their Telegram ids.
For users whose ids are not specified, the bot will not show any activity.

# Environment variables 🦠 
|     Name     |                                                    Description                                                     |
|:------------:|:------------------------------------------------------------------------------------------------------------------:|
|  BOT_TOKEN   |              Telegram bot API token. You can get it from [@BotFather](https://telegram.me/BotFather)               |
| YANDEX_TOKEN |  Yandex Disk API token. Get it from this [link](https://yandex.ru/dev/disk-api/doc/ru/concepts/quickstart#oauth)   |
| ALLOWED_IDS  | This is the telegram id of users from whom the bot will successfully accept photos. Example in `.env.example` file |


# How to Use ☄️ 
## Running in Docker 🐳 

- configure environment variables in `.env` file

- start services
```commandline
docker compose up -d --build
```
## Running on Local Machine 💻 
- install dependencies 
```commandline
pip install -r requirements.txt
```
- configure environment variables in `.env` file
- start `main.py` in `app` directory

# License ⚖️
Distributed under MIT license. See [LICENSE](https://github.com/nsat1/photo-saving-bot/blob/main/LICENSE) for more information.

# Contact 🌍
<a href="mailto:artnas379@gmail.com">artnas379@gmail.com</a>
