import discord
from discord import app_commands
from discord.ext import commands
import requests
import uuid
import re

# 🔎 Regex to extract Uber Eats group links, including optional query params and www prefix
GROUP_LINK_PATTERN = r"https:\/\/(?:www\.)?eats\.uber\.com\/group-orders\/[a-zA-Z0-9-]+\/join(?:\?[^ ]*)?"

# 🧼 Function to extract the first valid Uber Eats group link from messy input
def extract_group_link(text):
    match = re.search(GROUP_LINK_PATTERN, text)
    return match.group(0) if match else None

# 🤖 Bot setup 
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"❌ Sync failed: {e}")

# 🚚 Slash command to copy group order items from one link to another
@bot.tree.command(name="copygroup", description="Copy Uber Eats group order items from one group link to another.")
@app_commands.describe(
    to_link="Target group order link (where the items will go)",
    from_link="Source group order link (where the items come from)"
)
async def copygroup(interaction: discord.Interaction, to_link: str, from_link: str):
    await interaction.response.defer()

    # 🧹 Clean the inputs using regex
    to_link_clean = extract_group_link(to_link)
    from_link_clean = extract_group_link(from_link)

    if not to_link_clean or not from_link_clean:
        await interaction.followup.send("❌ One or both of the inputs didn't contain a valid Uber Eats group order link.")
        return

    session = requests.Session()
    headers = {
        "x-csrf-token": "x",
        "accept": "application/json",
        "content-type": "application/json"
    }

    try:
        # 🧩 Extract UUIDs
        orderuuidto = to_link_clean.split("/")[4]
        orderuuidfrom = from_link_clean.split("/")[4]

        # 🔄 Join the source group order to get items
        res_from = session.post("https://www.ubereats.com/_p/api/addMemberToDraftOrderV1", headers=headers, json={
            "draftOrderUuid": orderuuidfrom,
            "nickname": "DrewEats"
        })
        res_from.raise_for_status()
        data_from = res_from.json()

        source_items = data_from["data"]["shoppingCart"]["items"]

        # 🔄 Join the target group order to get its cart UUID
        res_to = session.post("https://www.ubereats.com/_p/api/addMemberToDraftOrderV1", headers=headers, json={
            "draftOrderUuid": orderuuidto,
            "nickname": "DrewEats"
        })
        res_to.raise_for_status()
        data_to = res_to.json()

        target_cart_uuid = data_to["data"]["shoppingCart"]["cartUuid"]

        # 🔁 Copy and modify item UUIDs
        copied_items = []
        for item in source_items:
            new_item = item.copy()
            new_item["shoppingCartItemUuid"] = str(uuid.uuid4())
            copied_items.append(new_item)

        # 📦 Send items to the target cart
        payload = {
            "draftOrderUUID": orderuuidto,
            "cartUUID": target_cart_uuid,
            "items": copied_items
        }

        res_add = session.post("https://www.ubereats.com/_p/api/addItemsToGroupDraftOrderV2", headers=headers, json=payload)

        if res_add.status_code == 200:
            await interaction.followup.send("✅ Items successfully copied to the target group order.")
        else:
            await interaction.followup.send(f"❌ Failed to add items: {res_add.status_code} - {res_add.text}")

    except Exception as e:
        await interaction.followup.send(f"❌ An error occurred: `{e}`")

# 🔐 Replace with your regenerated Discord bot token (never share it publicly!)

import os
token = os.environ['token']

bot.run(token)
