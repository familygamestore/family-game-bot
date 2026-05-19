import discord
from discord.ext import commands
import random
import time
from datetime import datetime

class Leveling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voice_tracker = {}
        self.xp_data = {}
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        if isinstance(message.channel, discord.DMChannel):
            return
        
        # Add XP
        xp_gain = random.randint(10, 20)
        await self.add_xp(message.author.id, xp_gain, message.guild.id)
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot:
            return
        
        # Joined voice
        if before.channel is None and after.channel is not None:
            self.voice_tracker[member.id] = time.time()
        
        # Left voice
        elif before.channel is not None and after.channel is None:
            if member.id in self.voice_tracker:
                duration = time.time() - self.voice_tracker[member.id]
                minutes = int(duration // 60)
                xp_gain = minutes * 5  # 5 XP per minute
                
                if xp_gain > 0:
                    await self.add_xp(member.id, xp_gain, member.guild.id)
                
                del self.voice_tracker[member.id]
    
    async def add_xp(self, user_id, xp, guild_id):
        """Add XP to user"""
        if user_id not in self.xp_data:
            self.xp_data[user_id] = {'xp': 0, 'level': 0}
        
        self.xp_data[user_id]['xp'] += xp
        
        # Calculate level (formula: level = sqrt(xp/100))
        new_level = int((self.xp_data[user_id]['xp'] / 100) ** 0.5)
        
        if new_level > self.xp_data[user_id]['level']:
            self.xp_data[user_id]['level'] = new_level
            await self.on_level_up(user_id, new_level, guild_id)
    
    async def on_level_up(self, user_id, new_level, guild_id):
        """Handle level up events"""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        
        member = guild.get_member(user_id)
        if not member:
            return
        
        # Send level up message
        channel = discord.utils.get(guild.text_channels, name="general")
        if channel:
            await channel.send(f"🎉 {member.mention} just reached **Level {new_level}**!")
    
    @commands.command(name="rank")
    async def check_rank(self, ctx, member: discord.Member = None):
        """Check your rank or someone else's"""
        target = member or ctx.author
        
        if target.id not in self.xp_data:
            await ctx.send(f"{target.mention} has 0 XP (Level 0)")
            return
        
        data = self.xp_data[target.id]
        await ctx.send(f"{target.mention} - Level {data['level']} ({data['xp']} XP)")
    
    @commands.command(name="leaderboard")
    async def level_leaderboard(self, ctx, limit: int = 10):
        """Show level leaderboard"""
        sorted_users = sorted(self.xp_data.items(), key=lambda x: x[1]['level'], reverse=True)[:limit]
        
        embed = discord.Embed(
            title="🏆 Level Leaderboard",
            color=discord.Color.gold()
        )
        
        description = ""
        for i, (user_id, data) in enumerate(sorted_users, 1):
            user = self.bot.get_user(user_id)
            name = user.name if user else f"User {user_id}"
            medal = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            description += f"{medal} **{name}** - Level {data['level']}\n"
        
        embed.description = description
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Leveling(bot))