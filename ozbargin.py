#!/usr/bin/env python3
"""
    Simple script which checks for new deals on ozbargain.com.au
    Then posts to a Discord webhook.
    Author: github.com/mty22
    Git repo: https://github.com/mty22/ozbargain-discord-bot
"""

import os
import sys
import datetime
import time
import dotenv
import requests
import re
import random
import sqlite3
from sqlite3 import Error
from discord_webhook import DiscordWebhook, DiscordEmbed


def discord_notify(url, text):
    """Send a notification to Discord"""
    unix_timestamp = int(datetime.datetime.now().timestamp())
    webhook = DiscordWebhook(url=os.getenv("DISCORD_WEBHOOK"))
    # Randomise the colour of the embed.
    colors = [
        0xFFE4E1,
        0x00FF7F,
        0xD8BFD8,
        0xDC143C,
        0xFF4500,
        0xDEB887,
        0xADFF2F,
        0x800000,
        0x4682B4,
        0x006400,
        0x808080,
        0xA0522D,
        0xF08080,
        0xC71585,
        0xFFB6C1,
        0x00CED1,
    ]
    embed = DiscordEmbed(title=f"{url}", description=text, color=random.choice(colors))
    embed.set_author(
        name="",
        url=url,
        icon_url="https://pbs.twimg.com/profile_images/450879240657850368/g0VNhtll_400x400.png",
    )
    embed.add_embed_field(
        name="Seen", value=f"<t:{unix_timestamp}:F> (<t:{unix_timestamp}:R>)"
    )

    webhook.add_embed(embed)
    response = webhook.execute()

    if response.status_code == 200 or response.status_code == 204:
        return True
    else:
        return False


def tprint(text):
    """Log to stdout"""
    current_timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{current_timestamp}] {text}")


def sqlite_db_initialise():
    """If the SQLite DB doesn't exist, create it"""
    # Check if the SQLite DB file exists.
    sqlite_file = os.path.join(os.path.dirname(__file__), os.getenv("SQLITE_DB_FILE"))

    if os.path.exists(sqlite_file):
        return

    conn = sqlite_create_connection(sqlite_file)
    if conn is not None:
        sql_create_deals_table = """ CREATE TABLE IF NOT EXISTS deals (
                                        id integer PRIMARY KEY,
                                        url text NOT NULL,
                                        timestamp text NOT NULL
                                    ); """
        try:
            c = conn.cursor()
            c.execute(sql_create_deals_table)
        except Error as e:
            tprint(f"Error: Unable to initialise database: {e}")
    else:
        tprint("Error: Unable to connet to SQLite DB")


def sqlite_create_connection(SQLITE_DB_FILE):
    """Connect to the SQLite DB"""
    conn = None
    try:
        conn = sqlite3.connect(SQLITE_DB_FILE)
    except Error as e:
        tprint(f"Error: Unable to connect to the database: {e}")
    return conn


def sqlite_seen_deal(url):
    """Check if we've already seen this deal in the SQLite DB"""
    sqlite_file = os.path.join(os.path.dirname(__file__), os.getenv("SQLITE_DB_FILE"))
    conn = sqlite_create_connection(sqlite_file)
    if conn is not None:
        sql_check_deal = f"SELECT * FROM deals WHERE url = (?);"
        try:
            c = conn.cursor()
            c.execute(sql_check_deal, (url,))
            if c.fetchone() is None:
                return False
            else:
                return True
        except Error as e:
            tprint(f"Error: Unable to query database for deal: {e}")


def sqlite_insert_deal(url):
    """Update the SQLite DB once we've seen the deal"""
    sqlite_file = os.path.join(os.path.dirname(__file__), os.getenv("SQLITE_DB_FILE"))
    conn = sqlite_create_connection(sqlite_file)
    if conn is not None:
        sql_insert_data = (url, int(datetime.datetime.now().timestamp()))
        try:
            c = conn.cursor()
            c.execute(
                "INSERT INTO deals (url, timestamp) VALUES (?,?);", sql_insert_data
            )
            conn.commit()
            conn.close()
        except Error as e:
            tprint(f"Error: Unable to insert deal into database: {e}")


def sqlite_purge_old_deals():
    """Purge deals older than 30 days from the database"""
    sqlite_file = os.path.join(os.path.dirname(__file__), os.getenv("SQLITE_DB_FILE"))
    conn = sqlite_create_connection(sqlite_file)
    if conn is not None:
        sql_purge_deals = "DELETE FROM deals WHERE timestamp < strftime('%s', date('now', '-30 days'));"
        try:
            c = conn.cursor()
            c.execute(sql_purge_deals)
        except Error as e:
            tprint(f"Error: Unable to purge old deals from the database: {e}")


def ozbargin_site_check():
    """Check the ozbargain site for new deals"""
    rss_url = os.getenv("OZBARGIN_RSS_FEED")
    initial_run = True

    # Endless loop.
    while True:
        # Purge old deals from the SQLite DB
        sqlite_purge_old_deals()

        # Get the RSS feed.
        tprint("Fetching RSS feed...")
        try:
            rss_request = requests.get(rss_url, timeout=10)
        except Error as e:
            tprint(f"Error: Unable to fetch RSS feed: {e}")
        finally:
            if rss_request.status_code == 200:
                rss_feed = rss_request.text
                # Find all the deals in the RSS feed, read line by line.
                for line in rss_feed.splitlines():
                    # Only print line if string is matched: <description><![CDATA[
                    if re.search(r"<description><!\[CDATA\[", line):
                        node_id = re.search(r'href="/node/(.*?)"', line).group(1)
                        deal_url = f"https://www.ozbargain.com.au/node/{node_id}"
                        deal_details = re.search(r'alt="(.*?)"', line).group(1)

                        # Check if we've seen the deal or not.
                        if sqlite_seen_deal(deal_url):
                            continue
                        else:
                            tprint(f"New deal found: {deal_url}")

                            if initial_run == True:
                                tprint(
                                    f"Initial run, skipping Discord webhook for deal: {deal_url}"
                                )
                            else:
                                # Send the deal to Discord via webhook.
                                # Sleep for 60 seconds if the webhook fails (then try again).
                                while discord_notify(deal_url, deal_details) == False:
                                    time.sleep(60)

                            # Update the SQLite DB with the new deal.
                            sqlite_insert_deal(deal_url)
                            time.sleep(1)

                # Sleep for 5 minutes before checking again.
                initial_run = False
                tprint("Sleeping for 5 minutes...")
                time.sleep(300)
            else:
                tprint(
                    f"Error: Unable to get RSS feed: {rss_request.status_code}, sleeping for 5 minutes..."
                )
                time.sleep(300)


def check_envs():
    """Load environment variables from .env file"""
    dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(dotenv_path):
        dotenv.load_dotenv(dotenv_path)

        # Check for required environment variables.
        if os.getenv("SQLITE_DB_FILE") is None:
            tprint("Error: SQLITE_DB_FILE not set")
            sys.exit(1)

        if os.getenv("DISCORD_WEBHOOK") is None:
            tprint("Error: DISCORD_WEBHOOK not set")
            sys.exit(1)

        if os.getenv("OZBARGIN_RSS_FEED") is None:
            tprint("Error: OZBARGIN_RSS_FEED not set")
            sys.exit(1)
    else:
        tprint("Error: .env file not found, please check README.md")
        sys.exit(1)


def main():
    """Main function"""

    # Check environment variables
    check_envs()

    # Initialise SQLite DB
    sqlite_db_initialise()

    # Check ozbargain.com.au for new deals
    tprint("Starting ozbargin site check...")
    ozbargin_site_check()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
