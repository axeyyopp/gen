
import nextcord as discord
from nextcord.ext import commands, tasks
import asyncio
import json
import os
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix='+', intents=intents, help_command=None)

GEN_CHANNEL_ID = 123456789012345678  # replace with your gen channel ID
GEN_ROLE_ID = 987654321098765432     # replace with your gen role ID
ACCESS_FILE = "access.json"

def load_access_data():
    if os.path.exists(ACCESS_FILE):
        with open(ACCESS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_access_data(data):
    with open(ACCESS_FILE, "w") as f:
        json.dump(data, f)

access_data = load_access_data()

@tasks.loop(seconds=60)
async def check_access_expiry():
    now = datetime.utcnow()
    expired = []
    for user_id, end_time in access_data.items():
        end = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        if now >= end:
            expired.append(int(user_id))

    for user_id in expired:
        guild = discord.utils.get(bot.guilds)
        member = guild.get_member(user_id)
        role = guild.get_role(GEN_ROLE_ID)
        if member and role in member.roles:
            await member.remove_roles(role)
        access_data.pop(str(user_id))
    if expired:
        save_access_data(access_data)

@bot.event
async def on_ready():
    print(f"Bot is online as {bot.user}")
    check_access_expiry.start()

@bot.command()
async def help(ctx):
    embed = discord.Embed(title="Help Menu", color=discord.Color.blurple())
    embed.add_field(name="+help", value="Shows this message", inline=False)
    embed.add_field(name="+info", value="Shows info", inline=False)
    embed.add_field(name="+stock", value="Displays current stock", inline=False)
    embed.add_field(name="+gen {item}", value="Generates an item", inline=False)
    embed.add_field(name="+access {user} {time}", value="Gives gen access", inline=False)
    embed.add_field(name="+remove-access", value="Removes gen access", inline=False)
    embed.add_field(name="+check-access", value="Shows who has gen access", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def info(ctx):
    embed = discord.Embed(title="Bot Info", description="Simple Gen Bot", color=discord.Color.green())
    await ctx.send(embed=embed)

@bot.command()
async def stock(ctx):
    stock_list = ["ev.txt"]
    embed = discord.Embed(title="Stock", color=discord.Color.gold())
    for file in stock_list:
        try:
            with open(file, "r") as f:
                lines = f.readlines()
                embed.add_field(name=file.replace(".txt", ""), value=f"{len(lines)} in stock", inline=False)
        except FileNotFoundError:
            embed.add_field(name=file.replace(".txt", ""), value="File not found", inline=False)
    await ctx.send(embed=embed)

@bot.command()
async def gen(ctx, item: str):
    if ctx.channel.id != GEN_CHANNEL_ID:
        await ctx.send(f"This command can only be used in <#{GEN_CHANNEL_ID}>.")
        return

    role = ctx.guild.get_role(GEN_ROLE_ID)
    if role not in ctx.author.roles:
        await ctx.send("You do not have access!")
        return

    filename = f"{item}.txt"
    if not os.path.exists(filename):
        await ctx.send("This item does not exist or has no stock file.")
        return

    try:
        with open(filename, "r") as f:
            lines = f.readlines()
        if not lines:
            await ctx.send("Out of stock!")
            return

        gen_item = lines[0].strip()
        with open(filename, "w") as f:
            f.writelines(lines[1:])

        embed = discord.Embed(title=f"✅ SENT {item.upper()} IN YOUR DMS!", color=discord.Color.green())
        await ctx.send(embed=embed)
        dm_embed = discord.Embed(title="Your Gen Item", description=gen_item, color=discord.Color.blurple())
        await ctx.author.send(embed=dm_embed)
    except discord.Forbidden:
        await ctx.send("I couldn't DM you. Please enable DMs.")

@commands.has_permissions(administrator=True)
@bot.command()
async def access(ctx, member: discord.Member, duration: str):
    role = ctx.guild.get_role(GEN_ROLE_ID)
    if not role:
        await ctx.send("Gen Access role not found.")
        return

    time_map = {"d": 1, "h": 1/24}
    try:
        num = int(duration[:-1])
        unit = duration[-1]
        days = num * time_map[unit]
        expires_at = datetime.utcnow() + timedelta(days=days)

        access_data[str(member.id)] = expires_at.strftime("%Y-%m-%d %H:%M:%S")
        save_access_data(access_data)

        ist_time = expires_at + timedelta(hours=5, minutes=30)
        await member.add_roles(role)
        await ctx.send(f"Gave {member.mention} access until `{ist_time.strftime('%Y-%m-%d %H:%M:%S')}` IST.")
    except Exception:
        await ctx.send("Invalid format. Use `1d`, `2h`, etc.")

@bot.command()
async def remove_access(ctx, member: discord.Member = None):
    member = member or ctx.author
    role = ctx.guild.get_role(GEN_ROLE_ID)
    if role in member.roles:
        await member.remove_roles(role)
        access_data.pop(str(member.id), None)
        save_access_data(access_data)
        await ctx.send(f"Removed access from {member.mention}")
    else:
        await ctx.send("User doesn't have gen access.")

@commands.has_permissions(administrator=True)
@bot.command(name="check-access")
async def check_access(ctx):
    role = ctx.guild.get_role(GEN_ROLE_ID)
    valid_users = []

    for user_id, end_time in access_data.items():
        member = ctx.guild.get_member(int(user_id))
        if member and role in member.roles:
            valid_users.append((member, end_time))

    if not valid_users:
        await ctx.send("No users currently have access.")
        return

    embed = discord.Embed(title="Current Gen Access", color=discord.Color.teal())
    for member, end_time in valid_users:
        end = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
        ist_time = end + timedelta(hours=5, minutes=30)
        embed.add_field(name=member.mention, value=f"Expires at: `{ist_time.strftime('%Y-%m-%d %H:%M:%S')}` IST", inline=False)

    await ctx.send(embed=embed)

bot.run("YOUR_BOT_TOKEN")
