import os
import discord
from discord.ext import commands
import platform
import requests
import random
import datetime
import subprocess
import sys
import json
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ================= CONFIGURATION =================
TOKEN = os.getenv("DISCORD_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Database Files for Multi-Server Settings
DB_FILE = "bot_settings.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

db = load_db()

def get_server_config(guild_id):
    gid = str(guild_id)
    if gid not in db:
        db[gid] = {
            "prefix": "!",
            "antinuke": False,
            "antinuke_whitelist": [],
            "welcome_channel": None,
            "welcome_msg": "Welcome {member} to {server}!",
            "welcome_dm": True,
            "automod_role": None,
            "automod_whitelist": [],
            "automod_log_channel": None,
            "mod_log_channel": None,
            "global_log_channel": None,
            "quarantine_role": None,
            "quarantine_saved_roles": {}
        }
        save_db(db)
    
    config = db[gid]
    if "global_log_channel" not in config:
        config["global_log_channel"] = None
    if "quarantine_role" not in config:
        config["quarantine_role"] = None
    if "quarantine_saved_roles" not in config:
        config["quarantine_saved_roles"] = {}
    save_db(db)
    
    return config

def get_prefix(bot, message):
    if not message.guild:
        return "!"
    config = get_server_config(message.guild.id)
    return config.get("prefix", "!")

# Auto-Mod Settings
FORBIDDEN_WORDS = ["badword1", "badword2", "spamlink.com"]
# =================================================

# Terminal Startup Banner
print("=" * 45)
print("THIS BOT DEVELOPED BY ACID")
print("BUY ME COFFEE binence uid = 1016468667")
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

bot = commands.Bot(command_prefix=get_prefix, intents=intents)

async def send_global_log(guild, title, description, color=discord.Color.blue()):
    """Helper function to log all bot actions into global log channel"""
    config = get_server_config(guild.id)
    log_cid = config.get("global_log_channel") or config.get("mod_log_channel")
    if log_cid:
        log_chan = guild.get_channel(log_cid)
        if log_chan:
            embed = discord.Embed(
                title=title,
                description=description,
                color=color,
                timestamp=datetime.datetime.now(datetime.timezone.utc)
            )
            try:
                await log_chan.send(embed=embed)
            except Exception:
                pass

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (ID: {bot.user.id})")
    send_startup_info()
    
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Failed to sync slash commands: {e}")

# ================= ⚙️ CONFIG & LOG COMMANDS =================

@bot.tree.command(name="setprefix", description="Change bot prefix for this server")
@commands.has_permissions(administrator=True)
async def setprefix(interaction: discord.Interaction, prefix: str):
    config = get_server_config(interaction.guild.id)
    config["prefix"] = prefix
    save_db(db)
    await interaction.response.send_message(f"✅ Server prefix successfully updated to: `{prefix}`", ephemeral=True)
    await send_global_log(interaction.guild, "⚙️ Prefix Changed", f"Prefix updated to `{prefix}` by {interaction.user.mention}")

@bot.tree.command(name="setlogchannel", description="Set main action log channel where all logs will be sent")
@commands.has_permissions(administrator=True)
async def setlogchannel(interaction: discord.Interaction, channel: discord.TextChannel):
    config = get_server_config(interaction.guild.id)
    config["global_log_channel"] = channel.id
    save_db(db)
    await interaction.response.send_message(f"✅ Global log channel set to {channel.mention}", ephemeral=True)
    await send_global_log(interaction.guild, "📜 Log Channel Configured", f"Global action logs will now be sent to {channel.mention} by {interaction.user.mention}")

@bot.tree.command(name="setquarantinerole", description="Set the Quarantine role for Anti-Nuke punishments")
@commands.has_permissions(administrator=True)
async def setquarantinerole(interaction: discord.Interaction, role: discord.Role):
    config = get_server_config(interaction.guild.id)
    config["quarantine_role"] = role.id
    save_db(db)
    await interaction.response.send_message(f"✅ Quarantine role set to {role.mention}", ephemeral=True)
    await send_global_log(interaction.guild, "🛡️ Quarantine Role Configured", f"Quarantine role updated to {role.mention} by {interaction.user.mention}")

# ================= 🛡️ ANTINUKE & QUARANTINE SYSTEM =================

@bot.tree.command(name="antinuke", description="Enable or disable Antinuke feature")
@commands.has_permissions(administrator=True)
async def antinuke(interaction: discord.Interaction, status: bool):
    config = get_server_config(interaction.guild.id)
    config["antinuke"] = status
    save_db(db)
    state = "Enabled 🟢" if status else "Disabled 🔴"
    await interaction.response.send_message(f"🛡️ Antinuke system is now {state}", ephemeral=True)
    await send_global_log(interaction.guild, "🛡️ Anti-Nuke Status Changed", f"Anti-Nuke system was **{state}** by {interaction.user.mention}")

@bot.tree.command(name="antinukewhitelist", description="Add or remove member from Antinuke whitelist")
@commands.has_permissions(administrator=True)
async def antinukewhitelist(interaction: discord.Interaction, action: str, member: discord.Member):
    config = get_server_config(interaction.guild.id)
    w_list = config["antinuke_whitelist"]
    
    if action.lower() == "add":
        if member.id not in w_list:
            w_list.append(member.id)
            save_db(db)
            await interaction.response.send_message(f"✅ {member.mention} added to Antinuke Whitelist.", ephemeral=True)
            await send_global_log(interaction.guild, "🛡️ Whitelist Updated", f"{member.mention} added to Anti-Nuke Whitelist by {interaction.user.mention}")
        else:
            await interaction.response.send_message(f"⚠️ {member.mention} is already in the whitelist.", ephemeral=True)
    elif action.lower() == "remove":
        if member.id in w_list:
            w_list.remove(member.id)
            save_db(db)
            await interaction.response.send_message(f"❌ {member.mention} removed from Antinuke Whitelist.", ephemeral=True)
            await send_global_log(interaction.guild, "🛡️ Whitelist Updated", f"{member.mention} removed from Anti-Nuke Whitelist by {interaction.user.mention}")
        else:
            await interaction.response.send_message(f"⚠️ {member.mention} is not in the whitelist.", ephemeral=True)
    else:
        await interaction.response.send_message("Please use action: `add` or `remove`.", ephemeral=True)

@bot.tree.command(name="unquarantine", description="Restore all roles to a quarantined member")
@commands.has_permissions(administrator=True)
async def unquarantine(interaction: discord.Interaction, member: discord.Member):
    config = get_server_config(interaction.guild.id)
    saved_dict = config.get("quarantine_saved_roles", {})
    mem_id_str = str(member.id)

    q_role_id = config.get("quarantine_role")
    q_role = interaction.guild.get_role(q_role_id) if q_role_id else None

    if q_role and q_role in member.roles:
        try:
            await member.remove_roles(q_role, reason="Unquarantined by Admin")
        except Exception:
            pass

    if mem_id_str in saved_dict:
        role_ids = saved_dict[mem_id_str]
        roles_to_add = [interaction.guild.get_role(rid) for rid in role_ids if interaction.guild.get_role(rid) is not None]
        
        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add, reason="Restoring roles after unquarantine")
            except Exception as e:
                return await interaction.response.send_message(f"⚠️ Roles restore e error hoyeche: {e}", ephemeral=True)

        del saved_dict[mem_id_str]
        config["quarantine_saved_roles"] = saved_dict
        save_db(db)

        await interaction.response.send_message(f"✅ {member.mention} successfully unquarantined ebong shob role fashot dewa hoyeche!", ephemeral=True)
        await send_global_log(interaction.guild, "🔓 Member Unquarantined", f"{member.mention} was unquarantined and all roles restored by {interaction.user.mention}", color=discord.Color.green())
    else:
        await interaction.response.send_message(f"⚠️ {member.mention}-er purano saved role record paowa jayni.", ephemeral=True)

@bot.event
async def on_guild_channel_delete(channel):
    config = get_server_config(channel.guild.id)
    if not config.get("antinuke", False):
        return

    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        user = entry.user
        if user.id == bot.user.id or user.id == channel.guild.owner_id or user.id in config.get("antinuke_whitelist", []):
            return

        member = channel.guild.get_member(user.id)
        if not member:
            return

        q_role_id = config.get("quarantine_role")
        q_role = channel.guild.get_role(q_role_id) if q_role_id else None

        user_roles = [r for r in member.roles if r != channel.guild.default_role and not r.managed]
        user_role_ids = [r.id for r in user_roles]

        mem_id_str = str(member.id)
        config["quarantine_saved_roles"][mem_id_str] = user_role_ids
        save_db(db)

        try:
            if user_roles:
                await member.remove_roles(*user_roles, reason="Anti-Nuke Triggered: Stripping roles for punishment")
            
            if q_role:
                await member.add_roles(q_role, reason="Anti-Nuke Triggered: Added Quarantine Role")
            
            await send_global_log(
                channel.guild,
                "🚨 Anti-Nuke Triggered (Quarantined)",
                f"**User:** {member.mention}\n**Action:** Mass Channel Deletion (`{channel.name}`)\n**Punishment:** Removed all roles & added Quarantine role.",
                color=discord.Color.red()
            )
        except Exception as e:
            await send_global_log(
                channel.guild,
                "⚠️ Anti-Nuke Action Error",
                f"Failed to punish {member.mention} on channel deletion: `{e}`",
                color=discord.Color.gold()
            )

# ================= 👋 WELCOME SYSTEM =================

@bot.tree.command(name="setwelcomechannel", description="Set the welcome channel")
@commands.has_permissions(administrator=True)
async def setwelcomechannel(interaction: discord.Interaction, channel: discord.TextChannel):
    config = get_server_config(interaction.guild.id)
    config["welcome_channel"] = channel.id
    save_db(db)
    await interaction.response.send_message(f"✅ Welcome channel set to {channel.mention}", ephemeral=True)
    await send_global_log(interaction.guild, "👋 Welcome Config", f"Welcome channel updated to {channel.mention} by {interaction.user.mention}")

@bot.tree.command(name="setwelcomemessage", description="Set welcome message (Use {member} and {server})")
@commands.has_permissions(administrator=True)
async def setwelcomemessage(interaction: discord.Interaction, message: str):
    config = get_server_config(interaction.guild.id)
    config["welcome_msg"] = message
    save_db(db)
    await interaction.response.send_message(f"✅ Welcome message updated to:\n`{message}`", ephemeral=True)

@bot.tree.command(name="togglewelcomedm", description="Toggle whether to send welcome message in DM")
@commands.has_permissions(administrator=True)
async def togglewelcomedm(interaction: discord.Interaction, status: bool):
    config = get_server_config(interaction.guild.id)
    config["welcome_dm"] = status
    save_db(db)
    await interaction.response.send_message(f"📬 Welcome DM status set to: {status}", ephemeral=True)

@bot.event
async def on_member_join(member):
    config = get_server_config(member.guild.id)
    raw_msg = config.get("welcome_msg", "Welcome {member} to {server}!")
    formatted_msg = raw_msg.replace("{member}", member.mention).replace("{server}", member.guild.name)

    channel_id = config.get("welcome_channel")
    if channel_id:
        channel = member.guild.get_channel(channel_id) or discord.utils.get(member.guild.text_channels, name="welcome")
        if channel:
            embed = discord.Embed(
                title="👋 Welcome to the Server!",
                description=formatted_msg,
                color=discord.Color.green()
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)

    if config.get("welcome_dm", True):
        try:
            dm_embed = discord.Embed(
                title=f"Welcome to {member.guild.name}!",
                description=formatted_msg,
                color=discord.Color.green()
            )
            await member.send(embed=dm_embed)
        except:
            pass

# ================= 🛡️ AUTO-MOD & LOGS =================

@bot.tree.command(name="automodrole", description="Set a role to bypass Auto-Mod")
@commands.has_permissions(administrator=True)
async def automodrole(interaction: discord.Interaction, role: discord.Role):
    config = get_server_config(interaction.guild.id)
    config["automod_role"] = role.id
    save_db(db)
    await interaction.response.send_message(f"✅ Auto-Mod bypass role set to {role.mention}", ephemeral=True)

@bot.tree.command(name="automodwhitelist", description="Add or remove user from Auto-Mod whitelist")
@commands.has_permissions(administrator=True)
async def automodwhitelist(interaction: discord.Interaction, action: str, member: discord.Member):
    config = get_server_config(interaction.guild.id)
    w_list = config["automod_whitelist"]
    
    if action.lower() == "add":
        if member.id not in w_list:
            w_list.append(member.id)
            save_db(db)
            await interaction.response.send_message(f"✅ {member.mention} added to Auto-Mod Whitelist.", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ {member.mention} is already in Auto-Mod whitelist.", ephemeral=True)
    elif action.lower() == "remove":
        if member.id in w_list:
            w_list.remove(member.id)
            save_db(db)
            await interaction.response.send_message(f"❌ {member.mention} removed from Auto-Mod Whitelist.", ephemeral=True)
        else:
            await interaction.response.send_message(f"⚠️ {member.mention} is not in Auto-Mod whitelist.", ephemeral=True)
    else:
        await interaction.response.send_message("Please use action: `add` or `remove`.", ephemeral=True)

@bot.tree.command(name="setautomodlog", description="Set Auto-Mod log channel")
@commands.has_permissions(administrator=True)
async def setautomodlog(interaction: discord.Interaction, channel: discord.TextChannel):
    config = get_server_config(interaction.guild.id)
    config["automod_log_channel"] = channel.id
    save_db(db)
    await interaction.response.send_message(f"✅ Auto-Mod log channel set to {channel.mention}", ephemeral=True)

@bot.tree.command(name="setmodlog", description="Set Moderation action log channel")
@commands.has_permissions(administrator=True)
async def setmodlog(interaction: discord.Interaction, channel: discord.TextChannel):
    config = get_server_config(interaction.guild.id)
    config["mod_log_channel"] = channel.id
    save_db(db)
    await interaction.response.send_message(f"✅ Moderation log channel set to {channel.mention}", ephemeral=True)

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    config = get_server_config(message.guild.id)
    
    bypass_role_id = config.get("automod_role")
    is_bypassed = False
    if bypass_role_id and discord.utils.get(message.author.roles, id=bypass_role_id):
        is_bypassed = True
    if message.author.id in config.get("automod_whitelist", []):
        is_bypassed = True
    if message.author.guild_permissions.administrator:
        is_bypassed = True

    if not is_bypassed:
        content = message.content.lower()
        if any(word in content for word in FORBIDDEN_WORDS) or "discord.gg/" in content:
            try:
                await message.delete()
            except:
                pass
            
            await message.channel.send(f"⚠️ {message.author.mention}, your message contained forbidden words/links and was removed!", delete_after=5)
            
            await send_global_log(
                message.guild,
                "🛡️ Auto-Mod Triggered",
                f"**User:** {message.author.mention}\n**Channel:** {message.channel.mention}\n**Content:** `{message.content}`",
                color=discord.Color.orange()
            )
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
        name="⚙️ Config & Setup",
        value="`/setprefix` - Set custom prefix\n`/setlogchannel` - Set global log channel\n`/setquarantinerole` - Set quarantine role\n`/unquarantine` - Restore member roles\n`/setwelcomechannel` - Set welcome channel",
        inline=False
    )
    
    embed.add_field(
        name="🛡️ Moderation & Security",
        value="`/warn` - Warn member & DM\n`/kick` - Kick member\n`/ban` - Ban member\n`/timeout` - Mute member\n`/clear` - Delete chats\n`/antinuke` - Toggle anti-nuke\n`/antinukewhitelist` - Manage nuke whitelist",
        inline=False
    )

    embed.add_field(
        name="🤖 Auto-Mod & Logs",
        value="`/automodrole` - Set bypass role\n`/automodwhitelist` - Manage automod whitelist\n`/setautomodlog` - Set automod log channel",
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

# Auto-Update Command
@bot.command(name="update")
async def update_bot(ctx):
    msg = await ctx.send("🔄 GitHub theke latest code update kora hocche...")
    try:
        result = subprocess.run(["git", "pull"], capture_output=True, text=True)
        
        if "Already up to date." in result.stdout:
            await msg.edit(content="✅ Bot already latest version-e ache! Kono notun update nei.")
        else:
            await msg.edit(content="✅ Code successfully updated! Bot restart hochhe...")
            os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        await msg.edit(content=f"❌ Update fail koreche: {e}")

# ================= 🛡️ MODERATION COMMANDS =================

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
    await send_global_log(interaction.guild, "⚠️ Member Warned", f"**User:** {member.mention}\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}", color=discord.Color.orange())

@bot.tree.command(name="kick", description="Kick a member from the server")
@commands.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"✅ {member.mention} has been kicked. Reason: {reason}")
    await send_global_log(interaction.guild, "👢 Member Kicked", f"**User:** {member.mention}\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}", color=discord.Color.red())

@bot.tree.command(name="ban", description="Ban a member from the server")
@commands.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"⛔ {member.mention} has been banned. Reason: {reason}")
    await send_global_log(interaction.guild, "🔨 Member Banned", f"**User:** {member.mention}\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}", color=discord.Color.dark_red())

@bot.tree.command(name="timeout", description="Timeout (mute) a member in minutes")
@commands.has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
    duration = datetime.timedelta(minutes=minutes)
    await member.timeout(duration, reason=reason)
    await interaction.response.send_message(f"🔇 {member.mention} has been muted for {minutes} minutes.")
    await send_global_log(interaction.guild, "🔇 Member Timeout", f"**User:** {member.mention}\n**Duration:** {minutes} minutes\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}", color=discord.Color.gold())

@bot.tree.command(name="clear", description="Clear a specified amount of messages")
@commands.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 Deleted {len(deleted)} messages.", ephemeral=True)
    await send_global_log(interaction.guild, "🧹 Messages Cleared", f"**Channel:** {interaction.channel.mention}\n**Amount:** {len(deleted)}\n**Moderator:** {interaction.user.mention}", color=discord.Color.blue())

# ================= 🎮 MINI-GAMES & FUN COMMANDS =================

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
async def eight_ball(interaction: discord.Interaction, question: str):
    responses = ["Yes, definitely!", "It is certain.", "Ask again later.", "Cannot predict now.", "No, absolutely not.", "My sources say no."]
    answer = random.choice(responses)
    await interaction.response.send_message(f"❓ **Question:** {question}\n🎱 **8Ball:** {answer}")

# ================= ⚙️ UTILITY COMMANDS =================

@bot.tree.command(name="userinfo", description="Get details of a user")
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    embed = discord.Embed(title=f"User Info - {target.name}", color=discord.Color.blue())
    embed.set_thumbnail(url=target.display_avatar.url)
    embed.add_field(name="User ID", value=target.id, inline=True)
    embed.add_field(name="Joined Server", value=target.joined_at.strftime("%Y-%m-%d") if target.joined_at else "N/A", inline=True)
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
