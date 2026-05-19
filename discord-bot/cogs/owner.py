import discord
from discord.ext import commands
import sys
import os
import psutil
from datetime import datetime

class Owner(commands.Cog):
    """Owner-only commands"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_check(self, ctx):
        owner_ids = [int(id.strip()) for id in os.getenv('OWNER_IDS', '').split(',') if id.strip()]
        return ctx.author.id in owner_ids
    
    @commands.command(name="reload")
    async def reload_cogs(self, ctx, cog: str = None):
        """Reload all or specific cogs (Owner only)"""
        if cog:
            try:
                await self.bot.reload_extension(f'cogs.{cog}')
                await ctx.send(f"✅ Reloaded cog: {cog}")
            except Exception as e:
                await ctx.send(f"❌ Failed to reload {cog}: {e}")
        else:
            cogs = ['admin', 'leveling', 'giveaway', 'invite_tracker', 'premium', 'owner']
            for cog_name in cogs:
                try:
                    await self.bot.reload_extension(f'cogs.{cog_name}')
                    await ctx.send(f"✅ Reloaded: {cog_name}")
                except Exception as e:
                    await ctx.send(f"❌ Failed to reload {cog_name}: {e}")
    
    @commands.command(name="sync")
    async def sync_commands(self, ctx):
        """Sync slash commands (Owner only)"""
        await self.bot.tree.sync()
        await ctx.send("✅ Slash commands synced!")
    
    @commands.command(name="status")
    async def status(self, ctx):
        """Show bot status (Owner only)"""
        embed = discord.Embed(
            title="🤖 Bot Status",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Guilds", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="Python", value=sys.version.split()[0], inline=True)
        
        try:
            process = psutil.Process()
            memory = process.memory_info().rss / 1024 / 1024
            embed.add_field(name="Memory", value=f"{memory:.1f} MB", inline=True)
        except:
            embed.add_field(name="Memory", value="N/A", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="shutdown")
    async def shutdown_bot(self, ctx):
        """Shutdown the bot (Owner only)"""
        await ctx.send("🔄 Shutting down...")
        await self.bot.close()
    
    @commands.command(name="servers")
    async def list_servers(self, ctx):
        """List all servers the bot is in (Owner only)"""
        servers = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)
        
        embed = discord.Embed(
            title="📊 Server List",
            description=f"Total: {len(servers)} servers",
            color=discord.Color.blue()
        )
        
        for guild in servers[:25]:
            embed.add_field(
                name=guild.name,
                value=f"ID: {guild.id}\nMembers: {guild.member_count}",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="leave")
    async def leave_server(self, ctx, guild_id: int):
        """Leave a specific server (Owner only)"""
        guild = self.bot.get_guild(guild_id)
        if guild:
            await guild.leave()
            await ctx.send(f"✅ Left server: {guild.name}")
        else:
            await ctx.send("❌ Server not found")
    
    @commands.command(name="broadcast")
    async def broadcast(self, ctx, *, message: str):
        """Broadcast message to all servers (Owner only)"""
        await ctx.send(f"📡 Broadcasting to {len(self.bot.guilds)} servers...")
        
        success = 0
        failed = 0
        
        for guild in self.bot.guilds:
            try:
                channel = discord.utils.get(guild.text_channels, name="general")
                if not channel:
                    channel = guild.system_channel
                if channel:
                    await channel.send(f"📢 **Announcement from Developer:**\n{message}")
                    success += 1
                else:
                    failed += 1
            except:
                failed += 1
            
            await asyncio.sleep(0.5)
        
        await ctx.send(f"✅ Broadcast complete! Sent to {success} servers, failed: {failed}")

async def setup(bot):
    await bot.add_cog(Owner(bot))
