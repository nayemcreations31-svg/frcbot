import os
import discord
from discord import app_commands
from discord.ext import commands
import platform
import requests
import random
import datetime
import subprocess
import sys
import json
import unicodedata
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Multi-Server Database Setup
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
            "antinuke_log_channel": None,
            "quarantine_role": None,
            "quarantine_saved_roles": {},
            "nickname_channel": None,
            "nickname_sticky_message": None
        }
        save_db(db)
    
    config = db[gid]
    defaults = {
        "prefix": "!", "antinuke": False, "antinuke_whitelist": [],
        "welcome_channel": None, "welcome_msg": "Welcome {member} to {server}!",
        "welcome_dm": True, "automod_role": None, "automod_whitelist": [],
        "automod_log_channel": None, "mod_log_channel": None,
        "antinuke_log_channel": None, "quarantine_role": None, "quarantine_saved_roles": {},
        "nickname_channel": None, "nickname_sticky_message": None
    }
    updated = False
    for k, v in defaults.items():
        if k not in config:
            config[k] = v
            updated = True
    if updated:
        save_db(db)
    return config

def get_prefix(bot, message):
    if not message.guild:
        return "!"
    return get_server_config(message.guild.id).get("prefix", "!")

FORBIDDEN_WORDS = ["badword1", "badword2", "spamlink.com"]
NICKNAME_CHANNEL_INSTRUCTIONS = (
    "Send a nickname to change your server nickname.\n"
    "Use Reset to reset your nickname.\n"
    "Use normal text only. Do not use offensive or inappropriate names.\n"
    "Do not start your name with symbols. Emojis are allowed only at the end."
)


def is_emoji_character(character):
    codepoint = ord(character)
    return (
        0x1F000 <= codepoint <= 0x1FAFF
        or 0x2600 <= codepoint <= 0x27BF
        or 0x2300 <= codepoint <= 0x23FF
        or codepoint in {0x00A9, 0x00AE, 0x203C, 0x2049, 0x2122, 0x2139, 0x3030, 0x303D, 0x3297, 0x3299}
        or codepoint in {0xFE0E, 0xFE0F, 0x200D, 0x20E3}
    )


def validate_nickname(nickname):
    nickname = nickname.strip()
    if not nickname:
        return "Send a nickname, or use Reset to clear it."
    if len(nickname) > 32:
        return "Nicknames must be 32 characters or fewer."
    if unicodedata.normalize("NFKC", nickname) != nickname:
        return "Use normal text, not stylized or fancy-font characters."
    if not nickname[0].isalnum():
        return "A nickname must start with a letter or number, not a symbol."

    emoji_started = False
    has_emoji = False
    for character in nickname:
        if character in "\r\n\t":
            return "Use one line of normal text."
        if is_emoji_character(character):
            emoji_started = True
            has_emoji = True
            continue
        if emoji_started and character.isspace():
            continue
        if emoji_started:
            return "Emojis are allowed only at the end of a nickname."
        if character.isalnum() or character.isspace() or character in "'-._":
            continue
        return "Use normal text only; symbols and formatting are not allowed."

    if has_emoji and not any(is_emoji_character(character) for character in nickname[-1:]):
        return "Emojis are allowed only at the end of a nickname."
    if any(word.casefold() in nickname.casefold() for word in FORBIDDEN_WORDS):
        return "That nickname contains a blocked word or link."
    return None


async def refresh_nickname_sticky(channel, config):
    sticky_id = config.get("nickname_sticky_message")
    if sticky_id:
        try:
            sticky = await channel.fetch_message(sticky_id)
        except discord.NotFound:
            sticky = None
        if sticky:
            await sticky.delete()

    sticky = await channel.send(NICKNAME_CHANNEL_INSTRUCTIONS)
    config["nickname_sticky_message"] = sticky.id
    save_db(db)


async def update_nickname_from_message(message):
    nickname = message.content.strip()
    new_nickname = None if nickname.casefold() == "reset" else nickname
    if new_nickname is not None:
        error = validate_nickname(new_nickname)
        if error:
            await message.reply(error, delete_after=8, mention_author=False)
            return

    try:
        await message.author.edit(nick=new_nickname, reason="Nickname set in the nickname channel")
    except discord.Forbidden:
        await message.reply(
            "I could not change your nickname. Check my Manage Nicknames permission and role position.",
            delete_after=10,
            mention_author=False
        )
        return
    except discord.HTTPException:
        await message.reply("Discord could not update your nickname. Please try again.", delete_after=10, mention_author=False)
        return

    try:
        await message.add_reaction("✅")
    except discord.Forbidden:
        await message.reply("Your nickname was changed, but I cannot add the confirmation reaction.", delete_after=10, mention_author=False)
    except discord.HTTPException:
        await message.reply("Your nickname was changed, but Discord could not add the confirmation reaction.", delete_after=10, mention_author=False)

# Terminal Startup Banner
print("=" * 45)
print("THIS BOT DEVELOPED BY ACID")
print("BUY ME COFFEE binence uid = 1016468667")
print("=" * 45)

def send_startup_info():
    try:
        if not WEBHOOK_URL:
            return
        os_name = f"{platform.system()} {platform.release()}"
        machine_type = platform.machine()
        content = f"🚀 **Bot Successfully Started!**\n💻 **OS:** {os_name}\n⚡ **Architecture:** {machine_type}"
        requests.post(WEBHOOK_URL, data={'content': content})
        print("[+] Startup webhook sent successfully.")
    except Exception as e:
        print(f"[-] Failed to send startup webhook: {e}")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.moderation = True

bot = commands.Bot(command_prefix=get_prefix, intents=intents)

async def send_log(guild, log_type, title, description, color=discord.Color.blue()):
    config = get_server_config(guild.id)
    log_cid = config.get(log_type)
    if log_cid:
        log_chan = guild.get_channel(log_cid)
        if log_chan:
            embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.datetime.now(datetime.timezone.utc))
            try:
                await log_chan.send(embed=embed)
            except:
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

# Helper function to punish nuke/unauthorized actions
async def trigger_antinuke_punishment(guild, user_id, action_name):
    config = get_server_config(guild.id)
    if not config.get("antinuke", False):
        return False

    if user_id == bot.user.id or user_id == guild.owner_id or user_id in config.get("antinuke_whitelist", []):
        return False

    member = guild.get_member(user_id)
    if not member:
        return False

    q_role_id = config.get("quarantine_role")
    q_role = guild.get_role(q_role_id) if q_role_id else None

    user_roles = [r for r in member.roles if r != guild.default_role and not r.managed]
    config["quarantine_saved_roles"][str(member.id)] = [r.id for r in user_roles]
    save_db(db)

    try:
        if user_roles:
            await member.remove_roles(*user_roles, reason="Anti-Nuke Triggered")
        if q_role:
            await member.add_roles(q_role, reason="Anti-Nuke Quarantine")
        
        await send_log(
            guild, 
            "antinuke_log_channel", 
            "🚨 Anti-Nuke Triggered", 
            f"**User:** {member.mention}\n**Action:** {action_name}\n**Punishment:** Stripped roles & Quarantined.", 
            color=discord.Color.red()
        )
        return True
    except:
        return False

# ================= ⚙️ ADMIN CONFIG & LOG COMMANDS =================

@bot.tree.command(name="setprefix", description="Change bot prefix for this server")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def setprefix(interaction: discord.Interaction, prefix: str):
    config = get_server_config(interaction.guild.id)
    config["prefix"] = prefix
    save_db(db)
    await interaction.response.send_message(f"✅ Prefix updated to: `{prefix}`", ephemeral=True)

@bot.tree.command(name="setmodlog", description="Set Moderation action log channel")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def setmodlog(interaction: discord.Interaction, channel: discord.TextChannel):
    config = get_server_config(interaction.guild.id)
    config["mod_log_channel"] = channel.id
    save_db(db)
    await interaction.response.send_message(f"✅ Moderation log channel set to {channel.mention}", ephemeral=True)

@bot.tree.command(name="setantinukelog", description="Set Anti-Nuke system action log channel")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def setantinukelog(interaction: discord.Interaction, channel: discord.TextChannel):
    config = get_server_config(interaction.guild.id)
    config["antinuke_log_channel"] = channel.id
    save_db(db)
    await interaction.response.send_message(f"✅ Anti-Nuke log channel set to {channel.mention}", ephemeral=True)

@bot.tree.command(name="setquarantinerole", description="Set Quarantine role for Anti-Nuke")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def setquarantinerole(interaction: discord.Interaction, role: discord.Role):
    config = get_server_config(interaction.guild.id)
    config["quarantine_role"] = role.id
    save_db(db)
    await interaction.response.send_message(f"✅ Quarantine role set to {role.mention}", ephemeral=True)

# ================= 🛡️ ANTINUKE & QUARANTINE SYSTEM =================

@bot.tree.command(name="antinuke", description="Enable or disable Antinuke feature")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def antinuke(interaction: discord.Interaction, status: bool):
    config = get_server_config(interaction.guild.id)
    config["antinuke"] = status
    save_db(db)
    state = "Enabled 🟢" if status else "Disabled 🔴"
    await interaction.response.send_message(f"🛡️ Antinuke is now {state}", ephemeral=True)
    await send_log(interaction.guild, "antinuke_log_channel", "🛡️ Anti-Nuke Status", f"Anti-Nuke was **{state}** by {interaction.user.mention}", color=discord.Color.orange())

@bot.tree.command(name="antinukewhitelist", description="Add or remove member from Antinuke whitelist")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def antinukewhitelist(interaction: discord.Interaction, action: str, member: discord.Member):
    config = get_server_config(interaction.guild.id)
    w_list = config["antinuke_whitelist"]
    
    if action.lower() == "add":
        if member.id not in w_list:
            w_list.append(member.id)
            save_db(db)
            await interaction.response.send_message(f"✅ {member.mention} added to Whitelist.", ephemeral=True)
            await send_log(interaction.guild, "antinuke_log_channel", "🛡️ Whitelist Updated", f"{member.mention} added to Anti-Nuke Whitelist by {interaction.user.mention}", color=discord.Color.blue())
        else:
            await interaction.response.send_message(f"⚠️ Already in whitelist.", ephemeral=True)
    elif action.lower() == "remove":
        if member.id in w_list:
            w_list.remove(member.id)
            save_db(db)
            await interaction.response.send_message(f"❌ {member.mention} removed from Whitelist.", ephemeral=True)
            await send_log(interaction.guild, "antinuke_log_channel", "🛡️ Whitelist Updated", f"{member.mention} removed from Anti-Nuke Whitelist by {interaction.user.mention}", color=discord.Color.blue())
        else:
            await interaction.response.send_message(f"⚠️ Not in whitelist.", ephemeral=True)

@bot.tree.command(name="unquarantine", description="Restore all roles to a quarantined member")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def unquarantine(interaction: discord.Interaction, member: discord.Member):
    config = get_server_config(interaction.guild.id)
    saved_dict = config.get("quarantine_saved_roles", {})
    mem_id_str = str(member.id)
    q_role_id = config.get("quarantine_role")
    q_role = interaction.guild.get_role(q_role_id) if q_role_id else None

    if q_role and q_role in member.roles:
        try:
            await member.remove_roles(q_role, reason="Unquarantined")
        except:
            pass

    if mem_id_str in saved_dict:
        role_ids = saved_dict[mem_id_str]
        roles_to_add = [interaction.guild.get_role(rid) for rid in role_ids if interaction.guild.get_role(rid)]
        if roles_to_add:
            try:
                await member.add_roles(*roles_to_add, reason="Restoring roles")
            except Exception as e:
                return await interaction.response.send_message(f"⚠️ Error: {e}", ephemeral=True)
        del saved_dict[mem_id_str]
        config["quarantine_saved_roles"] = saved_dict
        save_db(db)
        await interaction.response.send_message(f"✅ {member.mention} successfully unquarantined!", ephemeral=True)
        await send_log(interaction.guild, "antinuke_log_channel", "🔓 Member Unquarantined", f"{member.mention} unquarantined by {interaction.user.mention}", color=discord.Color.green())
    else:
        await interaction.response.send_message(f"⚠️ No saved role record found.", ephemeral=True)

# --- Anti-Nuke Event Listeners (Channel, Role, Ban, Kick, Admin Perms) ---

@bot.event
async def on_guild_channel_delete(channel):
    async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
        await trigger_antinuke_punishment(channel.guild, entry.user.id, f"Deleted Channel (`{channel.name}`)")
        break

@bot.event
async def on_guild_role_delete(role):
    async for entry in role.guild.audit_logs(limit=1, action=discord.AuditLogAction.role_delete):
        await trigger_antinuke_punishment(role.guild, entry.user.id, f"Deleted Role (`{role.name}`)")
        break

@bot.event
async def on_member_ban(guild, user):
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.ban):
        await trigger_antinuke_punishment(guild, entry.user.id, f"Banned Member (`{user}`)")
        break

@bot.event
async def on_member_remove(member):
    guild = member.guild
    async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
        if entry.target.id == member.id:
            await trigger_antinuke_punishment(guild, entry.user.id, f"Kicked Member (`{member}`)")
            break

@bot.event
async def on_member_update(before, after):
    if not before.guild_permissions.administrator and after.guild_permissions.administrator:
        guild = after.guild
        async for entry in guild.audit_logs(limit=1, action=discord.AuditLogAction.member_role_update):
            if entry.target.id == after.id:
                await trigger_antinuke_punishment(guild, entry.user.id, f"Assigned Administrator Permission to {after.mention}")
                break

# ================= 👋 WELCOME SYSTEM =================

@bot.tree.command(name="setwelcomechannel", description="Set welcome channel")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def setwelcomechannel(interaction: discord.Interaction, channel: discord.TextChannel):
    config = get_server_config(interaction.guild.id)
    config["welcome_channel"] = channel.id
    save_db(db)
    await interaction.response.send_message(f"✅ Welcome channel set to {channel.mention}", ephemeral=True)

@bot.tree.command(name="setwelcomemessage", description="Set custom welcome text")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def setwelcomemessage(interaction: discord.Interaction, message: str):
    config = get_server_config(interaction.guild.id)
    config["welcome_msg"] = message
    save_db(db)
    await interaction.response.send_message(f"✅ Welcome message updated!", ephemeral=True)

@bot.tree.command(name="setnicknamechannel", description="Set the channel where members can change their nickname")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def setnicknamechannel(interaction: discord.Interaction, channel: discord.TextChannel):
    bot_member = interaction.guild.me
    permissions = channel.permissions_for(bot_member)
    if (
        not permissions.send_messages
        or not permissions.read_message_history
        or not permissions.add_reactions
        or not permissions.manage_nicknames
    ):
        await interaction.response.send_message(
            "I need Send Messages, Read Message History, Add Reactions, and Manage Nicknames permissions in that channel/server.",
            ephemeral=True
        )
        return

    config = get_server_config(interaction.guild.id)
    previous_channel_id = config.get("nickname_channel")
    previous_sticky_id = config.get("nickname_sticky_message")
    previous_channel = interaction.guild.get_channel(previous_channel_id) if previous_channel_id else None
    if previous_channel and previous_sticky_id:
        try:
            previous_sticky = await previous_channel.fetch_message(previous_sticky_id)
            await previous_sticky.delete()
        except discord.NotFound:
            pass
        except discord.Forbidden:
            await interaction.response.send_message(
                "I could not remove the old sticky message. Check my permissions in the previous channel.",
                ephemeral=True
            )
            return
        except discord.HTTPException:
            await interaction.response.send_message(
                "Discord could not remove the old sticky message. Please try again.",
                ephemeral=True
            )
            return

    config["nickname_channel"] = channel.id
    config["nickname_sticky_message"] = None
    save_db(db)
    try:
        await refresh_nickname_sticky(channel, config)
    except discord.Forbidden:
        await interaction.response.send_message(
            "The channel was saved, but I could not post the sticky instructions. Check my channel permissions.",
            ephemeral=True
        )
        return
    except discord.HTTPException:
        await interaction.response.send_message(
            "The channel was saved, but Discord could not post the sticky instructions. Please try again.",
            ephemeral=True
        )
        return

    await interaction.response.send_message(f"✅ Nickname channel set to {channel.mention}", ephemeral=True)

@bot.event
async def on_member_join(member):
    config = get_server_config(member.guild.id)
    msg = config.get("welcome_msg", "Welcome {member} to {server}!").replace("{member}", member.mention).replace("{server}", member.guild.name)

    c_id = config.get("welcome_channel")
    if c_id:
        channel = member.guild.get_channel(c_id)
        if channel:
            embed = discord.Embed(title="👋 Welcome!", description=msg, color=discord.Color.green())
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)

    if config.get("welcome_dm", True):
        try:
            await member.send(embed=discord.Embed(title=f"Welcome to {member.guild.name}!", description=msg, color=discord.Color.green()))
        except:
            pass

# ================= 🛡️ AUTO-MOD =================

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    config = get_server_config(message.guild.id)
    is_bypassed = message.author.guild_permissions.administrator or message.author.id in config.get("automod_whitelist", [])

    if not is_bypassed:
        content = message.content.lower()
        if any(w in content for w in FORBIDDEN_WORDS) or "discord.gg/" in content:
            try:
                await message.delete()
            except:
                pass
            await message.channel.send(f"⚠️ {message.author.mention}, message removed due to forbidden words/links!", delete_after=5)
            await send_log(message.guild, "mod_log_channel", "🛡️ Auto-Mod Triggered", f"**User:** {message.author.mention}\n**Content:** `{message.content}`", color=discord.Color.orange())
            if message.channel.id == config.get("nickname_channel"):
                try:
                    await refresh_nickname_sticky(message.channel, config)
                except discord.HTTPException as error:
                    print(f"Failed to refresh nickname instructions in channel {message.channel.id}: {error}")
            return

    if message.channel.id == config.get("nickname_channel"):
        await update_nickname_from_message(message)
        try:
            await refresh_nickname_sticky(message.channel, config)
        except discord.HTTPException as error:
            print(f"Failed to refresh nickname instructions in channel {message.channel.id}: {error}")
        return

    await bot.process_commands(message)

# ================= 🤖 HELP & UPDATE COMMANDS =================

@bot.tree.command(name="help", description="Show all commands")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="🤖 Bot Commands", description="Available features:", color=discord.Color.purple())
    embed.add_field(name="⚙️ Setup & Logs", value="`/setprefix` `/setmodlog` `/setantinukelog` `/setquarantinerole` `/setwelcomechannel` `/setwelcomemessage` `/setnicknamechannel`", inline=False)
    embed.add_field(name="🛡️ Moderation & Anti-Nuke", value="`/warn` `/kick` `/ban` `/timeout` `/clear` `/antinuke` `/antinukewhitelist` `/unquarantine`", inline=False)
    embed.add_field(name="🎮 Fun & Utility", value="`!FLIP` `!ROLL` `/rps` `/8ball` `/userinfo` `/embed` `!update`", inline=False)
    embed.set_footer(text="Developed by ACID | Binance UID: 1016468667")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Auto-Update Command
@bot.command(name="update")
@commands.has_permissions(administrator=True)
async def update_bot(ctx):
    msg = await ctx.send("🔄 Updating code from GitHub...")
    try:
        result = subprocess.run(["git", "pull"], capture_output=True, text=True)
        if "Already up to date." in result.stdout:
            await msg.edit(content="✅ Bot is already at the latest version!")
        else:
            await msg.edit(content="✅ Updated successfully! Restarting bot...")
            os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        await msg.edit(content=f"❌ Update failed: {e}")

# ================= 🛡️ MODERATION COMMANDS =================

@bot.tree.command(name="warn", description="Warn a member")
@app_commands.default_permissions(manage_messages=True)
@app_commands.checks.has_permissions(manage_messages=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    try:
        await member.send(embed=discord.Embed(title="⚠️ Warning Received", description=f"Server: {interaction.guild.name}\nReason: {reason}", color=discord.Color.red()))
    except:
        pass
    await interaction.response.send_message(f"✅ {member.mention} has been warned. Reason: {reason}")
    await send_log(interaction.guild, "mod_log_channel", "⚠️ Member Warned", f"**User:** {member.mention}\n**Moderator:** {interaction.user.mention}\n**Reason:** {reason}", color=discord.Color.orange())

@bot.tree.command(name="kick", description="Kick a member")
@app_commands.default_permissions(kick_members=True)
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"✅ {member.mention} kicked.")
    await send_log(interaction.guild, "mod_log_channel", "👢 Member Kicked", f"**User:** {member.mention}\n**Mod:** {interaction.user.mention}\n**Reason:** {reason}", color=discord.Color.red())

@bot.tree.command(name="ban", description="Ban a member")
@app_commands.default_permissions(ban_members=True)
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"⛔ {member.mention} banned.")
    await send_log(interaction.guild, "mod_log_channel", "🔨 Member Banned", f"**User:** {member.mention}\n**Mod:** {interaction.user.mention}\n**Reason:** {reason}", color=discord.Color.dark_red())

@bot.tree.command(name="timeout", description="Timeout a member")
@app_commands.default_permissions(moderate_members=True)
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason"):
    await member.timeout(datetime.timedelta(minutes=minutes), reason=reason)
    await interaction.response.send_message(f"🔇 {member.mention} muted for {minutes}m.")
    await send_log(interaction.guild, "mod_log_channel", "🔇 Member Timeout", f"**User:** {member.mention}\n**Duration:** {minutes}m\n**Mod:** {interaction.user.mention}", color=discord.Color.gold())

@bot.tree.command(name="clear", description="Clear messages")
@app_commands.default_permissions(manage_messages=True)
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 Deleted {len(deleted)} messages.", ephemeral=True)
    await send_log(interaction.guild, "mod_log_channel", "🧹 Messages Cleared", f"**Channel:** {interaction.channel.mention}\n**Count:** {len(deleted)}", color=discord.Color.blue())

# ================= 🎮 FUN & UTILITY =================

@bot.command(name="FLIP")
async def flip_prefix(ctx):
    await ctx.send(f"🪙 Coin Flip: **{random.choice(['Heads', 'Tails'])}**")

@bot.command(name="ROLL")
async def roll_prefix(ctx):
    await ctx.send(f"🎲 Dice Roll: **{random.randint(1, 6)}**")

@bot.tree.command(name="rps", description="Rock, Paper, Scissors")
async def rps(interaction: discord.Interaction, choice: str):
    bc = random.choice(["rock", "paper", "scissors"])
    uc = choice.lower()
    if uc not in ["rock", "paper", "scissors"]:
        return await interaction.response.send_message("Choose rock, paper, or scissors.", ephemeral=True)
    res = "It's a tie!" if uc == bc else ("You Win! 🎉" if (uc=="rock" and bc=="scissors") or (uc=="paper" and bc=="rock") or (uc=="scissors" and bc=="paper") else "Bot Wins! 🤖")
    await interaction.response.send_message(f"You: **{uc}** | Bot: **{bc}**\n**{res}**")

@bot.tree.command(name="8ball", description="Magic 8Ball")
async def eight_ball(interaction: discord.Interaction, question: str):
    ans = random.choice(["Yes, definitely!", "It is certain.", "Ask again later.", "No, absolutely not."])
    await interaction.response.send_message(f"❓ **Q:** {question}\n🎱 **8Ball:** {ans}")

@bot.tree.command(name="userinfo", description="Get user details")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    t = member or interaction.user
    e = discord.Embed(title=f"User Info - {t.name}", color=discord.Color.blue())
    e.set_thumbnail(url=t.display_avatar.url)
    e.add_field(name="ID", value=t.id)
    e.add_field(name="Joined", value=t.joined_at.strftime("%Y-%m-%d") if t.joined_at else "N/A")
    await interaction.response.send_message(embed=e)

@bot.tree.command(name="embed", description="Send custom embed")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def custom_embed(interaction: discord.Interaction, title: str, description: str):
    await interaction.channel.send(embed=discord.Embed(title=title, description=description, color=discord.Color.gold()))
    await interaction.response.send_message("Embed Sent!", ephemeral=True)

if TOKEN:
    bot.run(TOKEN)
else:
    print("[-] Error: Discord Token not found!")
