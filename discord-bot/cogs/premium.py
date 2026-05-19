import discord
from discord.ext import commands
import json
import os

class Premium(commands.Cog):
    """Premium exclusive features"""
    
    def __init__(self, bot):
        self.bot = bot
        self.custom_commands = {}
        self.welcome_messages = {}
        self.level_roles = {}
    
    async def is_premium(self, guild_id):
        """Check if server has premium"""
        # Import here to avoid circular import
        from bot import get_server_license
        license_info = await get_server_license(guild_id)
        return license_info and license_info.get('plan') in ['premium', 'enterprise']
    
    @commands.command(name="customcommand")
    @commands.has_permissions(administrator=True)
    async def create_custom_command(self, ctx, name: str, *, response: str):
        """Create a custom command (Premium feature)"""
        if not await self.is_premium(ctx.guild.id):
            embed = discord.Embed(
                title="✨ Premium Feature",
                description="Custom commands are only available for Premium users!\nVisit https://yourdomain.com/pricing to upgrade.",
                color=discord.Color.gold()
            )
            await ctx.send(embed=embed)
            return
        
        # Store custom command
        if ctx.guild.id not in self.custom_commands:
            self.custom_commands[ctx.guild.id] = {}
        
        self.custom_commands[ctx.guild.id][name.lower()] = response
        
        embed = discord.Embed(
            title="✅ Custom Command Created",
            description=f"Command `!{name}` has been created!",
            color=discord.Color.green()
        )
        embed.add_field(name="Response", value=response[:200], inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        # Check for custom commands
        if message.guild and message.guild.id in self.custom_commands:
            content = message.content.lower()
            if content.startswith('!'):
                cmd_name = content[1:].split()[0] if ' ' in content else content[1:]
                if cmd_name in self.custom_commands[message.guild.id]:
                    response = self.custom_commands[message.guild.id][cmd_name]
                    await message.channel.send(response)
    
    @commands.command(name="setwelcomemessage")
    @commands.has_permissions(administrator=True)
    async def set_welcome_message(self, ctx, channel: discord.TextChannel, *, message: str):
        """Set welcome message for new members (Premium feature)"""
        if not await self.is_premium(ctx.guild.id):
            await ctx.send("✨ This is a Premium feature! Upgrade to use it.")
            return
        
        self.welcome_messages[ctx.guild.id] = {
            'channel_id': channel.id,
            'message': message
        }
        
        await ctx.send(f"✅ Welcome message set in {channel.mention}")
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        if member.bot:
            return
        
        if member.guild.id in self.welcome_messages:
            data = self.welcome_messages[member.guild.id]
            channel = member.guild.get_channel(data['channel_id'])
            if channel:
                welcome_msg = data['message'].replace('{user}', member.mention).replace('{server}', member.guild.name)
                await channel.send(welcome_msg)
    
    @commands.command(name="setlevelrole")
    @commands.has_permissions(administrator=True)
    async def set_level_role(self, ctx, level: int, role: discord.Role):
        """Set role reward for reaching a level (Premium feature)"""
        if not await self.is_premium(ctx.guild.id):
            await ctx.send("✨ This is a Premium feature! Upgrade to use it.")
            return
        
        if ctx.guild.id not in self.level_roles:
            self.level_roles[ctx.guild.id] = {}
        
        self.level_roles[ctx.guild.id][level] = role.id
        
        await ctx.send(f"✅ Users will get {role.mention} at level {level}!")
    
    @commands.command(name="exportstats")
    @commands.has_permissions(administrator=True)
    async def export_stats(self, ctx):
        """Export server statistics (Premium feature)"""
        if not await self.is_premium(ctx.guild.id):
            await ctx.send("✨ This is a Premium feature! Upgrade to use it.")
            return
        
        # Collect stats
        stats = {
            'server_name': ctx.guild.name,
            'member_count': ctx.guild.member_count,
            'channel_count': len(ctx.guild.channels),
            'role_count': len(ctx.guild.roles),
            'emojis': len(ctx.guild.emojis),
            'boost_count': ctx.guild.premium_subscription_count
        }
        
        # Create file
        import json
        from io import BytesIO
        
        data = json.dumps(stats, indent=2)
        file = discord.File(BytesIO(data.encode()), filename=f"stats_{ctx.guild.id}.json")
        
        await ctx.send("📊 Server statistics exported:", file=file)

async def setup(bot):
    await bot.add_cog(Premium(bot))