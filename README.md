This is a fork of the AdiosBot project I made for a friend. Primarily, this fork
updates the commands for the bot to use slash commands, fixes some bugs, and
uses a development environment that should work on any platform. Below is the
original README:

---

# AdiosBot

Adios, inactive members.

![5871-adios-card-chihuahua](https://github.com/user-attachments/assets/a2630b75-7b36-41ed-9ed6-b16e44467fbc)

A bot that monitors member inactivity in your Discord server and lets you kick members that haven't posted any messages in x days.

Once you run the bot, it will download the last 10000 messages in every channel, and store the timestamp of the last message for every server member.

On subsequent runs, only new messages will be downloaded.

Due to Discord's limitations, only the last 10000 messages from every channel can be downloaded.

Depending on how active your server is, you might want to leave the bot running for some time before kicking any members.

For example, if you want to kick members that haven't sent any messages in 30 days, it might be necessary to run the bot for 30 days.

When in doubt, examine the respective channel logs (located in WORKING_DIR/message_logs) and check the earliest recorded timestamp.

## Usage
```
source .envrc
export DISCORD_BOT_TOKEN="token"
export WORKING_DIR=$(pwd)
python3 main.py
```

## Commands
* `!inactive n` – Show users who haven't posted any messages in the past n days
* `!kick_inactive n` – Kick users who haven't posted any messages in the past n days
* `!whitelist add name` – Add user `name` to the whitelist (will not get kicked even if inactive)
* `!whitelist remove name` – Remove user `name` from the whitelist
* `!whitelist show` – Show the current whitelist
