Install Python Virutal env:
```
python3.10 -m venv ozbargin_pyvenv
source ozbargin_pyvenv/bin/activate
pip install --upgrade pip
```

Then install requirements:
```
pip3.10 install -r requirements.txt
```

Update your `.env` file accordingly (see: `.env.example`)

To launch:

```
./ozbargin.py
```

--

Quick mockup for Ubuntu:


```
adduser discordbots
cd /home/discordbots/
git clone git@github.com:mty22/ozbargain-discord-bot.git
cp .env.example .env
```

Update .env file with discord webhook!

```
python3.10 -m venv ozbargin_pyvenv
source ozbargin_pyvenv/bin/activate
pip3.10 install --upgrade pip
pip3.10 install -r requirements.txt
```

as root:
```
echo '[Unit]
Description=ozbargin
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=3
User=discordbots
Group=discordbots
SyslogIdentifier=ozbargin
WorkingDirectory=/home/discordbots/
ExecStart=/home/discordbots/ozbargain-discord-bot/ozbargin_pyvenv/bin/python /home/discordbots/ozbargain-discord-bot/ozbargin.py

[Install]
WantedBy=multi-user.target' > /etc/systemd/system/ozbargin.service

systemctl daemon-reload
systemctl enable ozbargin --now
```