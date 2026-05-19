import discord
from discord.ext import commands
import json
from datetime import datetime

class InviteTracker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites = {}
    
    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            self.invites[guild.id] = await guild.invites()
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            return
        
        guild = member.guild
        new_invites = await guild.invites()
        
        for invite in new_invites:
            if invite.code not in [inv.code for inv in self.invites.get(guild.id, [])]:
                # Track invite
                await self.track_invite(member, invite)
                break
        
        self.invites[guild.id] = new_invites
    
    async def track_invite(self, member, invite):
        """Track who invited the member"""
        # Store in database
        print(f"{member.name} joined using invite from {invite.inviter.name}")
        
        # Add XP to inviter
        if hasattr(self.bot, 'add_xp'):
            await self.bot.add_xp(invite.inviter.id, 25)
    
    @commands.command(name="myinvites")
    async def my_invites(self, ctx):
        """Check your invite count"""
        invites = await ctx.guild.invites()
        user_invites = sum(1 for inv in invites if inv.inviter == ctx.author)
        
        embed = discord.Embed(
            title=f"{ctx.author.name}'s Invites",
            description=f"You have invited **{user_invites}** users!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="inviteleaderboard")
    async def invite_leaderboard(self, ctx, limit: int = 10):
        """Show top inviters"""
        invites = await ctx.guild.invites()
        inviter_counts = {}
        
        for inv in invites:
            if inv.inviter:
                inviter_counts[inv.inviter] = inviter_counts.get(inv.inviter, 0) + inv.uses
        
        sorted_inviters = sorted(inviter_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        embed = discord.Embed(
            title="🎯 Invite Leaderboard",
            color=discord.Color.gold()
        )
        
        description = ""
        for i, (inviter, count) in enumerate(sorted_inviters, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            description += f"{medal} **{inviter.name}** - {count} invites\n"
        
        embed.description = description
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(InviteTracker(bot))