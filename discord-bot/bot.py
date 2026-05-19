#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import discord
from discord.ext import commands
import aiohttp
import asyncio
import os
import json
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
API_URL = os.getenv('API_URL', 'http://api:8000')
PREFIX = os.getenv('BOT_PREFIX', '!')
OWNER_IDS = [int(id.strip()) for id in os.getenv('OWNER_IDS', '').split(',') if id.strip()]

if not TOKEN:
    print("❌ DISCORD_TOKEN not set!")
    exit(1)

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.invites = True
intents.voice_states = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# Store data
server_licenses = {}
voice_tracker = {}
xp_data = {}
custom_commands = {}
welcome_messages = {}
level_roles = {}

# ====================================================================================================
# LICENSE FUNCTIONS
# ====================================================================================================

async def check_license(server_id, license_key):
    """Verify license with API"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f'{API_URL}/api/verify-license', json={
                'license_key': license_key,
                'server_id': str(server_id)
            }) as resp:
                return await resp.json()
        except Exception as e:
            print(f"License check error: {e}")
            return {'valid': False}

async def get_server_license(guild_id):
    """Get license info for a server"""
    if guild_id in server_licenses:
        return server_licenses[guild_id]
    return None

def has_premium(guild_id):
    """Check if server has premium features"""
    license_info = server_licenses.get(guild_id)
    return license_info and license_info.get('valid', False)

async def add_xp(user_id, xp, guild_id):
    """Add XP to user"""
    if user_id not in xp_data:
        xp_data[user_id] = {'xp': 0, 'level': 0, 'guild_id': guild_id}
    
    xp_data[user_id]['xp'] += xp
    
    # Calculate level (formula: level = sqrt(xp/100))
    new_level = int((xp_data[user_id]['xp'] / 100) ** 0.5)
    
    if new_level > xp_data[user_id]['level']:
        xp_data[user_id]['level'] = new_level
        await on_level_up(user_id, new_level, guild_id)

async def on_level_up(user_id, new_level, guild_id):
    """Handle level up events"""
    guild = bot.get_guild(guild_id)
    if not guild:
        return
    
    member = guild.get_member(user_id)
    if not member:
        return
    
    # Check for level role
    if guild_id in level_roles:
        for level, role_id in level_roles[guild_id].items():
            if new_level >= int(level):
                role = guild.get_role(role_id)
                if role and role not in member.roles:
                    await member.add_roles(role)
                    channel = discord.utils.get(guild.text_channels, name="general")
                    if channel:
                        await channel.send(f"🎉 {member.mention} reached Level {new_level} and got {role.mention}!")
                    return
    
    # Send level up message
    channel = discord.utils.get(guild.text_channels, name="general")
    if channel:
        await channel.send(f"🎉 {member.mention} just reached **Level {new_level}**!")

# ====================================================================================================
# BOT EVENTS
# ====================================================================================================

@bot.event
async def on_ready():
    print(f'✅ {bot.user} has connected to Discord!')
    print(f'📊 Bot is in {len(bot.guilds)} guilds')
    print(f'👑 Owner IDs: {OWNER_IDS}')
    
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help | Premium Bot"))
    
    # Load cogs
    await load_cogs()

async def load_cogs():
    """Load all cogs"""
    cogs = [
        'cogs.admin',
        'cogs.leveling', 
        'cogs.giveaway',
        'cogs.invite_tracker',
        'cogs.premium',
        'cogs.owner'
    ]
    
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            print(f'✅ Loaded cog: {cog}')
        except Exception as e:
            print(f'❌ Failed to load cog {cog}: {e}')

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if isinstance(message.channel, discord.DMChannel):
        return
    
    # Add XP for messages (non-premium also gets XP)
    xp_gain = random.randint(10, 20)
    await add_xp(message.author.id, xp_gain, message.guild.id)
    
    # Check for custom commands
    if message.guild and message.guild.id in custom_commands:
        content = message.content.lower()
        if content.startswith(PREFIX):
            cmd_name = content[len(PREFIX):].split()[0] if ' ' in content else content[len(PREFIX):]
            if cmd_name in custom_commands[message.guild.id]:
                response = custom_commands[message.guild.id][cmd_name]
                await message.channel.send(response)
                return
    
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return
    
    # Only premium servers get voice XP
    if not has_premium(member.guild.id):
        return
    
    # Joined voice
    if before.channel is None and after.channel is not None:
        voice_tracker[member.id] = time.time()
    
    # Left voice
    elif before.channel is not None and after.channel is None:
        if member.id in voice_tracker:
            duration = time.time() - voice_tracker[member.id]
            minutes = int(duration // 60)
            xp_gain = minutes * 5  # 5 XP per minute
            
            if xp_gain > 0:
                await add_xp(member.id, xp_gain, member.guild.id)
            
            del voice_tracker[member.id]

@bot.event
async def on_member_join(member):
    if member.bot:
        return
    
    # Welcome message for premium servers
    if member.guild.id in welcome_messages:
        data = welcome_messages[member.guild.id]
        channel = member.guild.get_channel(data['channel_id'])
        if channel:
            welcome_msg = data['message'].replace('{user}', member.mention).replace('{server}', member.guild.name)
            await channel.send(welcome_msg)

# ====================================================================================================
# BASIC COMMANDS
# ====================================================================================================

@bot.command(name="help")
async def help_command(ctx):
    """Show all commands"""
    is_premium = has_premium(ctx.guild.id)
    
    embed = discord.Embed(
        title="🎮 Family Game Store Bot",
        description="Complete Discord Bot for Giveaways & Community",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="📨 Invite Tracker",
        value=f"`{PREFIX}myinvites` - Check your invites\n`{PREFIX}inviteleaderboard` - Top inviters",
        inline=False
    )
    
    embed.add_field(
        name="📊 Leveling System",
        value=f"`{PREFIX}rank [@user]` - Check level\n`{PREFIX}leaderboard` - Top levels",
        inline=False
    )
    
    embed.add_field(
        name="🎁 Giveaway",
        value=f"`{PREFIX}joingiveaway` - Join active giveaway",
        inline=False
    )
    
    if is_premium:
        embed.add_field(
            name="✨ Premium Commands",
            value=f"`{PREFIX}creategiveaway` - Create giveaway\n`{PREFIX}setwelcomemessage` - Welcome message\n`{PREFIX}setlevelrole` - Level roles\n`{PREFIX}customcommand` - Custom commands\n`{PREFIX}exportstats` - Export stats",
            inline=False
        )
    
    embed.add_field(
        name="🔑 License",
        value=f"`{PREFIX}license` - Check status\n`{PREFIX}activate <key>` - Activate premium",
        inline=False
    )
    
    if ctx.author.id in OWNER_IDS:
        embed.add_field(
            name="👑 Owner Commands",
            value=f"`{PREFIX}reload` - Reload cogs\n`{PREFIX}status` - Bot status\n`{PREFIX}servers` - List servers\n`{PREFIX}shutdown` - Shutdown bot",
            inline=False
        )
    
    embed.set_footer(text=f"Plan: {'Premium' if is_premium else 'Free'} | {len(bot.guilds)} servers")
    
    await ctx.send(embed=embed)

@bot.command(name="license")
async def check_license_status(ctx):
    """Check current license status"""
    license_info = await get_server_license(ctx.guild.id)
    
    if license_info and license_info.get('valid'):
        embed = discord.Embed(
            title="🔑 Premium License Active",
            description=f"Plan: **{license_info.get('plan', 'Premium').upper()}**",
            color=discord.Color.green()
        )
        embed.add_field(name="Expires", value=license_info.get('expires', 'Never'), inline=True)
        embed.add_field(name="Features", value="All premium features unlocked!", inline=True)
    else:
        embed = discord.Embed(
            title="🔓 Free Plan",
            description="Upgrade to Premium for more features!",
            color=discord.Color.yellow()
        )
        embed.add_field(name="Premium Benefits", 
                       value="• Unlimited giveaways\n• Voice XP\n• Custom commands\n• Level roles\n• Welcome messages\n• Export stats\n• Priority support", 
                       inline=False)
        embed.add_field(name="Get Premium", value="Visit https://yourdomain.com/pricing", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name="activate")
@commands.has_permissions(administrator=True)
async def activate_license(ctx, license_key: str):
    """Activate premium license"""
    result = await check_license(ctx.guild.id, license_key)
    
    if result.get('valid'):
        server_licenses[ctx.guild.id] = result
        
        embed = discord.Embed(
            title="✅ License Activated!",
            description=f"Plan: **{result.get('plan', 'Premium').upper()}**",
            color=discord.Color.green()
        )
        embed.add_field(name="Expires", value=result.get('expires', 'Never'), inline=True)
        embed.add_field(name="Features", value="All premium features are now unlocked!", inline=False)
        
        await ctx.send(embed=embed)
        
        # Log to channel
        log_channel = discord.utils.get(ctx.guild.text_channels, name="bot-logs")
        if log_channel:
            await log_channel.send(f"🔑 Premium license activated by {ctx.author.mention}")
    else:
        await ctx.send("❌ Invalid license key! Please check your key and try again.")

@bot.command(name="rank")
async def check_rank(ctx, member: discord.Member = None):
    """Check your rank or someone else's"""
    target = member or ctx.author
    
    if target.id not in xp_data:
        await ctx.send(f"{target.mention} has 0 XP (Level 0)")
        return
    
    data = xp_data[target.id]
    
    # Calculate XP to next level
    current_level_xp = 100 * (data['level'] ** 2)
    next_level_xp = 100 * ((data['level'] + 1) ** 2)
    xp_needed = next_level_xp - data['xp']
    
    embed = discord.Embed(
        title=f"📊 {target.name}'s Rank",
        color=discord.Color.blue()
    )
    embed.add_field(name="Level", value=data['level'], inline=True)
    embed.add_field(name="Total XP", value=data['xp'], inline=True)
    embed.add_field(name="XP to Next Level", value=xp_needed, inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="leaderboard")
async def level_leaderboard(ctx, limit: int = 10):
    """Show level leaderboard"""
    # Filter users in this guild
    guild_users = {uid: data for uid, data in xp_data.items() 
                   if data.get('guild_id') == ctx.guild.id}
    
    sorted_users = sorted(guild_users.items(), key=lambda x: x[1]['level'], reverse=True)[:limit]
    
    embed = discord.Embed(
        title="🏆 Level Leaderboard",
        color=discord.Color.gold()
    )
    
    description = ""
    for i, (user_id, data) in enumerate(sorted_users, 1):
        user = bot.get_user(user_id)
        name = user.name if user else f"User {user_id}"
        medal = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        description += f"{medal} **{name}** - Level {data['level']} ({data['xp']} XP)\n"
    
    embed.description = description
    await ctx.send(embed=embed)

# ====================================================================================================
# RUN BOT
# ====================================================================================================

if __name__ == "__main__":
    import random
    import time
    
    bot.run(TOKEN)
