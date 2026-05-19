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

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

TOKEN = os.getenv('DISCORD_TOKEN')
API_URL = os.getenv('API_URL', 'http://localhost:8000')
PREFIX = os.getenv('BOT_PREFIX', '!')

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.invites = True
intents.voice_states = True

bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# Store license info
server_licenses = {}
voice_tracker = {}

# ====================================================================================================
# LICENSE CHECKER
# ====================================================================================================

async def check_license(server_id, license_key):
    """Verify license with API"""
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(f'{API_URL}/verify-license', json={
                'license_key': license_key,
                'server_id': str(server_id)
            }) as resp:
                return await resp.json()
        except Exception as e:
            print(f"License check error: {e}")
            return {'valid': False}

async def get_server_license(guild_id):
    """Get license info for a server"""
    # Check if license already loaded
    if guild_id in server_licenses:
        return server_licenses[guild_id]
    
    # Check database or config
    # For now, return None (free tier)
    return None

def has_premium(guild_id):
    """Check if server has premium features"""
    license_info = server_licenses.get(guild_id)
    return license_info and license_info.get('valid', False)

# ====================================================================================================
# BOT EVENTS
# ====================================================================================================

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guilds')
    
    await bot.change_presence(activity=discord.Game(name=f"{PREFIX}help | Premium Bot"))
    
    # Load cogs
    await load_cogs()

async def load_cogs():
    """Load all cogs"""
    cogs = [
        'cogs.invite_tracker',
        'cogs.leveling',
        'cogs.giveaway',
        'cogs.premium',
        'cogs.admin'
    ]
    
    for cog in cogs:
        try:
            await bot.load_extension(cog)
            print(f'✅ Loaded cog: {cog}')
        except Exception as e:
            print(f'❌ Failed to load cog {cog}: {e}')

# ====================================================================================================
# COMMANDS
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
        value="`!myinvites` - Check your invites\n`!inviteleaderboard` - Top inviters",
        inline=False
    )
    
    embed.add_field(
        name="📊 Leveling System",
        value="`!rank [@user]` - Check level\n`!leaderboard` - Top levels",
        inline=False
    )
    
    embed.add_field(
        name="🎁 Giveaway",
        value="`!joingiveaway` - Join active giveaway",
        inline=False
    )
    
    if is_premium:
        embed.add_field(
            name="✨ Premium Commands",
            value="`!creategiveaway` - Create giveaway\n`!setwelcomemessage` - Welcome message\n`!setlevelrole` - Level roles\n`!customcommand` - Custom commands",
            inline=False
        )
    
    embed.add_field(
        name="🔑 License",
        value="`!license` - Check status\n`!activate <key>` - Activate premium",
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
        embed.add_field(name="Premium Benefits", value="• Unlimited giveaways\n• Voice XP\n• Custom commands\n• Level roles\n• Priority support", inline=False)
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
        
        # Log to channel if configured
        log_channel = discord.utils.get(ctx.guild.text_channels, name="bot-logs")
        if log_channel:
            await log_channel.send(f"🔑 Premium license activated by {ctx.author.mention}")
    else:
        await ctx.send("❌ Invalid license key! Please check your key and try again.")

# ====================================================================================================
# RUN BOT
# ====================================================================================================

if __name__ == "__main__":
    if not TOKEN:
        print("No token found! Please set DISCORD_TOKEN in .env file")
        exit(1)
    
    bot.run(TOKEN)