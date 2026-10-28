import os
import discord
from discord.ext import commands
import platform
import requests
import random
import datetime
import subprocess
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ================= CONFIGURATION =================
TOKEN = os.getenv("DISCORD_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Auto-Mod Settings
FORBIDDEN_WORDS = ["badword1", "badword2", "spamlink.com"]
# =================================================

# Terminal Startup Banner
print("=" * 45)
print("THIS BOT DEVOLOP BY ACID")
print("BUY ME COFFE binence uid = 1016468667")
print("=" * 45)

def send_startup_info():
    """Mobile/PC Compatible Startup Info Webhook"""
    try:
        if not WEBHOOK_URL:
            print("[-] Webhook URL not found in environment variables.")
            return
            
        os_name = f"{platform.system()} {platform.release()}"
        machine_type = platform.machine()
        
        content = (
            f"🚀 **Bot Successfully Started!**\n"
            f"💻 **OS:** {os_name}\n"
            f"⚡ **Architecture:** {machine_type}"
        )
        
        requests.post(WEBHOOK_URL, data={'content': content})
        print("[+] Startup bot activated successfully.")
    except Exception as e:
        print(f"[-] Failed to send startup webhook: {e}")

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    send_startup_info()
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

# ================= ⚙️ AUTO-MOD & WELCOME EVENTS =================

@bot.event
async def on_member_join(member):
    channel = discord.utils.get(member.guild.text_channels, name="welcome") or member.guild.system_channel
    if channel:
        embed = discord.Embed(
            title="👋 Welcome to the Server!",
            description=f"Welcome {member.mention}! We are glad to have you here.",
            color=discord.Color.green()
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        await channel.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower()
    if any(word in content for word in FORBIDDEN_WORDS) or "discord.gg/" in content:
        await message.delete()
        await message.channel.send(f"⚠️ {message.author.mention}, your message contained forbidden words/links and was removed!", delete_after=5)
        return

    await bot.process_commands(message)


# ================= 🤖 HELP & UPDATE COMMANDS =================

@bot.tree.command(name="help", description="Shows all available bot features and commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Bot Feature & Command List",
        description="Ekhane bot-er shobgulo command-er talika dewa holo:",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="🛡️ Moderation Commands",
        value="`/warn` - Warn a member & send DM\n`/kick` - Kick a member\n`/ban` - Ban a member\n`/timeout` - Mute a member\n`/clear` - Delete messages",
        inline=False
    )
    
    embed.add_field(
        name="🎮 Fun & Games",
        value="`!FLIP` - Coin Flip game\n`!ROLL` - Roll a dice (1-6)\n`/rps` - Rock, Paper, Scissors\n`/8ball` - Magic 8Ball",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Utility Commands",
        value="`/userinfo` - Get user details\n`/embed` - Send custom embed\n`!update` - Update bot from GitHub\n`/help` - Show this menu",
        inline=False
    )
    
    embed.set_footer(text="Developed by ACID | Binance UID: 1016468667")
    await interaction.response.send_message(embed=embed, ephemeral=True)


# Auto-Update Command (Discord theke update korar jonno)
@bot.command(name="update")
async def update_bot(ctx):
    msg = await ctx.send("🔄 GitHub theke latest code update kora hocche...")
    try:
        # Git pull run korbe
        result = subprocess.run(["git", "pull"], capture_output=True, text=True)
        
        if "Already up to date." in result.stdout:
            await msg.edit(content="✅ Bot already latest version-e ache! Kono notun update nei.")
        else:
            await msg.edit(content="✅ Code successfully updated! Bot restart hochhe...")
            # Bot ke automatic restart korbe
            os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        await msg.edit(content=f"❌ Update fail koreche: {e}")


# ================= 🛡️ 1. MODERATION COMMANDS =================

@bot.tree.command(name="warn", description="Warn a member and send them a DM")
@commands.has_permissions(manage_messages=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    try:
        dm_embed = discord.Embed(
            title="⚠️ You received a Warning!",
            description=f"**Server:** {interaction.guild.name}\n**Reason:** {reason}",
            color=discord.Color.red()
        )
        await member.send(embed=dm_embed)
        dm_status = "DM sent successfully."
    except Exception:
        dm_status = "Could not send DM (User DMs closed)."

    embed = discord.Embed(
        title="Member Warned",
        description=f"{member.mention} has been warned.\n**Reason:** {reason}\n*{dm_status}*",
        color=discord.Color.orange()
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="kick", description="Kick a member from the server")
@commands.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"✅ {member.mention} has been kicked. Reason: {reason}")

@bot.tree.command(name="ban", description="Ban a member from the server")
@commands.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"⛔ {member.mention} has been banned. Reason: {reason}")

@bot.tree.command(name="timeout", description="Timeout (mute) a member in minutes")
@commands.has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
    duration = datetime.timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await interaction.response.send_message(f"🔇 {member.mention} has been muted for {minutes} minutes.")

@bot.tree.command(name="clear", description="Clear a specified amount of messages")
@commands.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 Deleted {len(deleted)} messages.", ephemeral=True)


# ================= 🎮 2. MINI-GAMES & FUN COMMANDS =================

@bot.command(name="FLIP")
async def flip_prefix(ctx):
    result = random.choice(["Heads", "Tails"])
    await ctx.send(f"🪙 Coin Flip Result: **{result}**!")

@bot.command(name="ROLL")
async def roll_prefix(ctx):
    dice = random.randint(1, 6)
    await ctx.send(f"🎲 You rolled a **{dice}**!")

@bot.tree.command(name="rps", description="Play Rock, Paper, Scissors")
async def rps(interaction: discord.Interaction, choice: str):
    options = ["rock", "paper", "scissors"]
    bot_choice = random.choice(options)
    user_choice = choice.lower()

    if user_choice not in options:
        return await interaction.response.send_message("Please choose: `rock`, `paper`, or `scissors`.", ephemeral=True)

    if user_choice == bot_choice:
        res = "It's a tie!"
    elif (user_choice == "rock" and bot_choice == "scissors") or \
         (user_choice == "paper" and bot_choice == "rock") or \
         (user_choice == "scissors" and bot_choice == "paper"):
        res = "You Win! 🎉"
    else:
        res = "Bot Wins! 🤖"

    await interaction.response.send_message(f"You chose **{user_choice}**, Bot chose **{bot_choice}**.\n**{res}**")

@bot.tree.command(name="8ball", description="Ask the Magic 8Ball a question")
async def eight_ball(interaction: discord.Instruction if "Instruction" in globals() else discord.Interaction, question: str):
    responses = ["Yes, definitely!", "It is certain.", "Ask again later.", "Cannot predict now.", "No, absolutely not.", "My sources say no."]
    answer = random.choice(responses)
    await interaction.response.send_message(f"❓ **Question:** {question}\n🎱 **8Ball:** {answer}")


# ================= ⚙️ 3. UTILITY COMMANDS =================

@bot.tree.command(name="userinfo", description="Get details of a user")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    embed = discord.Embed(title=f"User Info - {target.name}", color=discord.Color.blue())
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="User ID", value=target.id, inline=True)
    embed.add_field(name="Joined Server", value=target.joined_at.strftime("%Y-%m-%d"), inline=True)
    embed.add_field(name="Account Created", value=target.created_at.strftime("%Y-%m-%d"), inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="embed", description="Send a custom embed")
async def custom_embed(interaction: discord.Interaction, title: str, description: str):
    emb = discord.Embed(title=title, description=description, color=discord.Color.gold())
    await interaction.channel.send(embed=emb)
    await interaction.response.send_message("Embed Sent!", ephemeral=True)

# Run the Bot Safely
if TOKEN:
    bot.run(TOKEN)
else:
    print("[-] Error: Discord Token not found! Please check your .env file.")