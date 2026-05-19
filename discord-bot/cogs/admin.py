import discord
from discord.ext import commands
import sys
import os
from datetime import datetime  # ← TAMBAHKAN IMPORT INI

class Admin(commands.Cog):
    """Administrative commands"""
    
    def __init__(self, bot):
        self.bot = bot

    async def cog_check(self, ctx):
        return ctx.author.id in [123456789012345678]
    
    @commands.command(name="reload")
    @commands.is_owner()
    async def reload_cogs(self, ctx, cog: str = None):
        """Reload all or specific cogs (Owner only)"""
        if cog:
            try:
                await self.bot.reload_extension(f'cogs.{cog}')
                await ctx.send(f"✅ Reloaded cog: {cog}")
            except Exception as e:
                await ctx.send(f"❌ Failed to reload {cog}: {e}")
        else:
            cogs = ['invite_tracker', 'leveling', 'giveaway', 'premium', 'admin']  # Hapus 'license'
            for cog_name in cogs:
                try:
                    await self.bot.reload_extension(f'cogs.{cog_name}')
                    await ctx.send(f"✅ Reloaded: {cog_name}")
                except Exception as e:
                    await ctx.send(f"❌ Failed to reload {cog_name}: {e}")
    
    @commands.command(name="sync")
    @commands.is_owner()
    async def sync_commands(self, ctx):
        """Sync slash commands (Owner only)"""
        await self.bot.tree.sync()
        await ctx.send("✅ Slash commands synced!")
    
    @commands.command(name="status")
    @commands.is_owner()
    async def status(self, ctx):
        """Show bot status (Owner only)"""
        embed = discord.Embed(
            title="🤖 Bot Status",
            color=discord.Color.blue(),
            timestamp=datetime.now()  # ← GANTI dari utcnow() ke now()
        )
        embed.add_field(name="Guilds", value=len(self.bot.guilds), inline=True)
        embed.add_field(name="Latency", value=f"{round(self.bot.latency * 1000)}ms", inline=True)
        embed.add_field(name="Python", value=sys.version.split()[0], inline=True)
        
        # Memory usage (opsional - install psutil dulu jika ingin)
        try:
            import psutil
            process = psutil.Process()
            memory = process.memory_info().rss / 1024 / 1024
            embed.add_field(name="Memory", value=f"{memory:.1f} MB", inline=True)
        except ImportError:
            embed.add_field(name="Memory", value="psutil not installed", inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="shutdown")
    @commands.is_owner()
    async def shutdown_bot(self, ctx):
        """Shutdown the bot (Owner only)"""
        await ctx.send("🔄 Shutting down...")
        await self.bot.close()
    
    @commands.command(name="servers")
    @commands.is_owner()
    async def list_servers(self, ctx):
        """List all servers the bot is in (Owner only)"""
        servers = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)
        
        embed = discord.Embed(
            title="📊 Server List",
            description=f"Total: {len(servers)} servers",
            color=discord.Color.blue()
        )
        
        for guild in servers[:25]:  # Limit to 25
            embed.add_field(
                name=guild.name,
                value=f"ID: {guild.id}\nMembers: {guild.member_count}",
                inline=True
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="leave")
    @commands.is_owner()
    async def leave_server(self, ctx, guild_id: int):
        """Leave a specific server (Owner only)"""
        guild = self.bot.get_guild(guild_id)
        if guild:
            await guild.leave()
            await ctx.send(f"✅ Left server: {guild.name}")
        else:
            await ctx.send("❌ Server not found")

async def setup(bot):
    await bot.add_cog(Admin(bot))
