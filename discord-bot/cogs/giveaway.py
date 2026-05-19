import discord
from discord.ext import commands, tasks
import random
import asyncio
from datetime import datetime, timedelta

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_giveaways = {}
    
    @commands.command(name="joingiveaway")
    async def join_giveaway(self, ctx):
        """Join the active giveaway"""
        if ctx.channel.id not in self.active_giveaways:
            await ctx.send("❌ No active giveaway in this channel!")
            return
        
        giveaway = self.active_giveaways[ctx.channel.id]
        
        if ctx.author.id in giveaway['participants']:
            await ctx.send(f"{ctx.author.mention}, you already joined!")
            return
        
        giveaway['participants'].append(ctx.author.id)
        await ctx.send(f"🎉 {ctx.author.mention} joined the giveaway! Total participants: {len(giveaway['participants'])}")
    
    @commands.command(name="creategiveaway")
    @commands.has_permissions(administrator=True)
    async def create_giveaway(self, ctx, duration: str, prize: str, winners: int = 1):
        """Create a giveaway (Premium feature)"""
        # Parse duration (e.g., "1h", "30m", "1d")
        duration_seconds = self.parse_duration(duration)
        
        embed = discord.Embed(
            title="🎁 Giveaway!",
            description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Duration:** {duration}",
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"Ends at")
        embed.timestamp = datetime.utcnow() + timedelta(seconds=duration_seconds)
        
        message = await ctx.send(embed=embed)
        await message.add_reaction("🎉")
        
        # Store giveaway
        self.active_giveaways[ctx.channel.id] = {
            'message_id': message.id,
            'channel_id': ctx.channel.id,
            'prize': prize,
            'winners': winners,
            'participants': [],
            'end_time': datetime.utcnow() + timedelta(seconds=duration_seconds)
        }
        
        # Schedule end
        await asyncio.sleep(duration_seconds)
        await self.end_giveaway(ctx.channel.id)
    
    async def end_giveaway(self, channel_id):
        """End giveaway and pick winners"""
        if channel_id not in self.active_giveaways:
            return
        
        giveaway = self.active_giveaways[channel_id]
        channel = self.bot.get_channel(channel_id)
        
        if not giveaway['participants']:
            await channel.send("❌ Giveaway ended with no participants!")
            del self.active_giveaways[channel_id]
            return
        
        winners_count = min(giveaway['winners'], len(giveaway['participants']))
        winners = random.sample(giveaway['participants'], winners_count)
        
        winner_mentions = [f"<@{w}>" for w in winners]
        
        embed = discord.Embed(
            title="🎉 Giveaway Ended! 🎉",
            description=f"**Prize:** {giveaway['prize']}\n**Winners:** {', '.join(winner_mentions)}",
            color=discord.Color.green()
        )
        
        await channel.send(embed=embed)
        del self.active_giveaways[channel_id]
    
    def parse_duration(self, duration):
        """Parse duration string to seconds"""
        unit = duration[-1].lower()
        value = int(duration[:-1])
        
        if unit == 's':
            return value
        elif unit == 'm':
            return value * 60
        elif unit == 'h':
            return value * 3600
        elif unit == 'd':
            return value * 86400
        else:
            return 3600  # Default 1 hour

async def setup(bot):
    await bot.add_cog(Giveaway(bot))