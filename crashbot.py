import os
import discord
import json
import asyncio
import re
from Flask import Flask
from discord import Intents
from discord.ext import commands
from discord.ext.commands import check
from datetime import datetime
import base64
from app import keep_alive

app.keep_alive()

intents = discord.Intents.default()
app = Flask(__name__)

bot = commands.Bot(command_prefix='/', intents=intents)

# Define your bot command server ID here
bot_command_server_id = 1067822214918983731

# Replace 'YOUR_BOT_OWNER_ID' with your bot owner's user ID
bot_owner_id = int(os.environ["BOT_OWNER_ID"])

# Initialize user levels, message count, active damage, and total damage from 'levels.json' if it exists
user_levels = {}
if os.path.exists('user_data.json'):
    with open('user_data.json', 'r') as file:
        user_levels = json.load(file)

# Initialize the list of eligible moderators from 'eligible_moderators.json' if it exists
eligible_moderators_file = 'eligible_moderators.json'
eligible_moderators = json.load(open(eligible_moderators_file)) if os.path.exists(eligible_moderators_file) else []

# Get the current year using datetime
current_year = datetime.now().year

@bot.event
async def on_ready():
    print('We have logged in as {0.user}'.format(bot))

# Define a decorator for a 2-second cooldown (30 commands per minute)
def rate_limit():
    def decorator(ctx):
        # Check if the user is a moderator or the bot owner
        if ctx.author.id in eligible_moderators or ctx.author.id == YOUR_BOT_OWNER_ID:
            return True  # No cooldown for moderators and the bot owner
        return False
    return commands.check(decorator)

# Define decrypt_message function
def decrypt_message(message):
    # Implement decryption logic here
    return message

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Decrypt the message content
    decrypted_message = decrypt_message(message.content)

    # Check if the message is in the 'general' channel
    if message.channel.name == 'general':
        author_id = str(message.author.id)

        # Check if the user is in the user_levels dictionary
        user_data = user_levels.get(author_id, {
            'level': 0,
            'xp': 0,
            'xp_required': 100,
            'message_count': 0,
            'active_damage': 0,
            'total_damage': 0
        })

        # Check if the user should level up (e.g., every 100 XP)
        user_data['xp'] += 5  # Assuming you give 5 XP for each message
        user_data['message_count'] += 1

        if user_data['xp'] >= user_data['xp_required']:
            user_data['xp'] = 0
            user_data['level'] += 1
            user_data['xp_required'] += 15  # Increase required XP for the next level

            if user_data['message_count'] == 1000:
                eligible_moderators.append(message.author.id)  # Add user to eligible moderators

            # Check if the user has sent their 1000th message
            if user_data['message_count'] % 1000 == 0:
                await message.channel.send(f'{message.author.mention} has sent their {user_data["message_count"]} message and has received the "wild bandicoot" rank!')

        # Save updated user levels to 'levels.json'
        with open('levels.json', 'w') as file:
            json.dump(user_levels, file)

        # Check if the message author is an administrator or higher
        if any(role.permissions.administrator for role in message.author.roles):
            # Check for forms.gle links with the correct form name
            form_pattern = re.compile(r'(https?://forms\.gle/[^/\s]+/[^/\s]+)(?:\s|$)')
            match = form_pattern.search(message.content)

            if match:
                form_url = match.group(1)
                form_name_pattern = re.compile(r'Bandicoot Gang Discord Moderator Application (\d{4})', re.I)
                form_name_match = form_name_pattern.search(form_url)

                if form_name_match:
                    year = int(form_name_match.group(1))
                    if year == current_year:
                        # Check if the user has less than 15 total damage
                        if user_data['total_damage'] < 15:
                            eligible_moderators.clear()  # Reset eligible moderators
                            eligible_moderators.append(message.author.id)  # Add user to eligible moderators

    await bot.process_commands(message)

@bot.command(guild_ids=[bot_command_server_id])
@rate_limit()  # Apply the rate_limit decorator to leaderboard
async def leaderboard(ctx):
    # Sort user_levels dictionary by level in descending order
    sorted_users = sorted(user_levels.items(), key=lambda x: x[1]['level'], reverse=True)

    # Create a rich embed for the leaderboard
    embed = discord.Embed(
        title="Leaderboard",
        color=0x818589  # Gray color
    )

    # Add the top 5 users with the highest levels to the embed
    for index, (user_id, user_data) in enumerate(sorted_users[:5], start=1):
        level = user_data['level']
        user = await bot.fetch_user(int(user_id))

        if user:
            display_name = user.display_name
            avatar_url = user.avatar_url
        else:
            display_name = "Unknown User"
            avatar_url = ""

        embed.add_field(
            name=f"#{index}: {display_name}",
            value=f"Level: {level}",
            inline=False
        )

        # Add the user's profile picture as a thumbnail
        if avatar_url:
            embed.set_thumbnail(url=avatar_url)

    await ctx.send(embed=embed)

@bot.command()
@commands.has_any_role("moderator", "administrator", "BANDICOOT GOD")
async def warn(ctx, user: discord.User, damage: int, reason: str):
    # Check if the user has been warned before
    author_id = str(user.id)
    user_data = user_levels.get(author_id, {})
    warned_before = user_data.get('warned_before', False)

    # Calculate the new active damage and total damage
    active_damage = user_data.get('active_damage', 0)
    total_damage = user_data.get('total_damage', 0)

    if damage >= 25:
        # Ban the user with appeal
        await user.send("You have been banned from the server due to reaching 25 or more active damage.")
        await user.ban(reason="Reached 25 or more active damage.")
        await ctx.send(f"{user.mention} has been banned from the server for reaching 25 or more active damage. They can appeal the ban.")

        # Reset active damage and total damage
        user_data['active_damage'] = 0
        user_data['total_damage'] = 0
    else:
        # Mute the user for (damage/2) hours
        mute_time = damage / 2
        mute_role = discord.utils.get(ctx.guild.roles, name="Muted")  # Change to your server's mute role

        if mute_role:
            await user.add_roles(mute_role, reason=f"Muted for {damage} damage: {reason}")
            await user.send(f"You have been muted for {mute_time} hours due to receiving {damage} damage. Reason: {reason}")
            await ctx.send(f"{user.mention} has been muted for {mute_time} hours due to receiving {damage} damage. Reason: {reason}")

            # Update active damage
            user_data['active_damage'] = active_damage + damage

            # Update total damage
            user_data['total_damage'] = total_damage + damage

    # Save the updated user data to 'user_data.json'
    with open('user_data.json', 'w') as file:
        json.dump(user_levels, file)

    # Send a friend request if the user hasn't been warned before
    if not warned_before:
        try:
            await user.send("You have received a friend request from the server bot.")
            await user.send("Please accept the friend request to receive further warnings and updates.")
            await user.send("If you have any questions or concerns, feel free to message the bot.")

            # Set the 'warned_before' flag to True
            user_data['warned_before'] = True

            # Save the updated user data to 'user_data.json'
            with open('user_data.json', 'w') as file:
                json.dump(user_levels, file)
        except discord.Forbidden:
            await ctx.send("The user has their DMs closed, so a friend request couldn't be sent.")

if __name__ == '__main__':
    @app.route('/')
    def hello():
        return "hello"
    
    # The bot token is now retrieved from GitHub Secrets
    bot_token = os.environ["TOKEN"]
    bot.run(bot_token)
