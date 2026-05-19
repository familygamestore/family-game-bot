import discord
from discord.ext import commands
from datetime import datetime
import asyncio

class Admin(commands.Cog):
    """Administrative commands for server admins"""
    
    def __init__(self, bot):
        self.bot = bot
    
    # ====================================================================================================
    # MODERATION COMMANDS
    # ====================================================================================================
    
    @commands.command(name="clear")
    @commands.has_permissions(manage_messages=True)
    async def clear_messages(self, ctx, amount: int = 10):
        """Clear messages in the channel (Admin only)"""
        if amount > 100:
            amount = 100
            await ctx.send("⚠️ Maximum limit is 100 messages. Clearing 100 messages...")
        
        deleted = await ctx.channel.purge(limit=amount + 1)
        msg = await ctx.send(f"✅ Cleared {len(deleted) - 1} messages!")
        await asyncio.sleep(3)
        await msg.delete()
    
    @commands.command(name="kick")
    @commands.has_permissions(kick_members=True)
    async def kick_member(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Kick a member from the server"""
        if member == ctx.author:
            await ctx.send("❌ You cannot kick yourself!")
            return
        
        if member.guild_permissions.administrator:
            await ctx.send("❌ You cannot kick an administrator!")
            return
        
        embed = discord.Embed(
            title="👢 Member Kicked",
            description=f"{member.mention} has been kicked from the server.",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        
        await member.kick(reason=reason)
        await ctx.send(embed=embed)
        
        # Try to DM the kicked member
        try:
            dm_embed = discord.Embed(
                title=f"You were kicked from {ctx.guild.name}",
                description=f"**Reason:** {reason}",
                color=discord.Color.red()
            )
            await member.send(embed=dm_embed)
        except:
            pass
    
    @commands.command(name="ban")
    @commands.has_permissions(ban_members=True)
    async def ban_member(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Ban a member from the server"""
        if member == ctx.author:
            await ctx.send("❌ You cannot ban yourself!")
            return
        
        if member.guild_permissions.administrator:
            await ctx.send("❌ You cannot ban an administrator!")
            return
        
        embed = discord.Embed(
            title="🔨 Member Banned",
            description=f"{member.mention} has been banned from the server.",
            color=discord.Color.dark_red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        
        await member.ban(reason=reason)
        await ctx.send(embed=embed)
        
        # Try to DM the banned member
        try:
            dm_embed = discord.Embed(
                title=f"You were banned from {ctx.guild.name}",
                description=f"**Reason:** {reason}",
                color=discord.Color.red()
            )
            await member.send(embed=dm_embed)
        except:
            pass
    
    @commands.command(name="unban")
    @commands.has_permissions(ban_members=True)
    async def unban_member(self, ctx, *, username: str):
        """Unban a member from the server"""
        banned_users = [entry async for entry in ctx.guild.bans()]
        
        for ban_entry in banned_users:
            user = ban_entry.user
            if user.name.lower() == username.lower() or str(user.id) == username:
                await ctx.guild.unban(user)
                
                embed = discord.Embed(
                    title="✅ Member Unbanned",
                    description=f"{user.mention} has been unbanned.",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
                await ctx.send(embed=embed)
                return
        
        await ctx.send(f"❌ Could not find banned user named `{username}`")
    
    @commands.command(name="timeout")
    @commands.has_permissions(moderate_members=True)
    async def timeout_member(self, ctx, member: discord.Member, duration: str, *, reason: str = "No reason provided"):
        """Timeout a member (mute them temporarily)
        Duration format: 1m, 1h, 1d, 1w
        """
        # Parse duration
        units = {
            'm': 60,
            'h': 3600,
            'd': 86400,
            'w': 604800
        }
        
        unit = duration[-1].lower()
        if unit not in units:
            await ctx.send("❌ Invalid duration format! Use: `1m`, `1h`, `1d`, or `1w`")
            return
        
        try:
            value = int(duration[:-1])
        except ValueError:
            await ctx.send("❌ Invalid duration value!")
            return
        
        seconds = value * units[unit]
        if seconds > 2419200:  # 28 days max
            await ctx.send("❌ Timeout cannot exceed 28 days!")
            return
        
        until = datetime.now() + timedelta(seconds=seconds)
        
        await member.timeout(until, reason=reason)
        
        embed = discord.Embed(
            title="⏰ Member Timed Out",
            description=f"{member.mention} has been timed out for **{duration}**.",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Duration", value=duration, inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="untimeout")
    @commands.has_permissions(moderate_members=True)
    async def untimeout_member(self, ctx, member: discord.Member):
        """Remove timeout from a member"""
        await member.timeout(None)
        
        embed = discord.Embed(
            title="✅ Timeout Removed",
            description=f"Timeout removed from {member.mention}.",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        await ctx.send(embed=embed)
    
    # ====================================================================================================
    # SERVER CONFIGURATION COMMANDS
    # ====================================================================================================
    
    @commands.command(name="setlogchannel")
    @commands.has_permissions(administrator=True)
    async def set_log_channel(self, ctx, channel: discord.TextChannel = None):
        """Set the channel for bot logs"""
        if channel is None:
            channel = ctx.channel
        
        # Store in database or bot config
        if not hasattr(self.bot, 'log_channels'):
            self.bot.log_channels = {}
        
        self.bot.log_channels[ctx.guild.id] = channel.id
        
        embed = discord.Embed(
            title="📝 Log Channel Set",
            description=f"Bot logs will be sent to {channel.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="setmuterole")
    @commands.has_permissions(administrator=True)
    async def set_mute_role(self, ctx, role: discord.Role = None):
        """Set the mute role for the server"""
        if role is None:
            # Create a mute role if not provided
            role = discord.utils.get(ctx.guild.roles, name="Muted")
            if not role:
                role = await ctx.guild.create_role(
                    name="Muted",
                    reason="Auto-created mute role"
                )
                
                # Set permissions for the mute role
                for channel in ctx.guild.channels:
                    await channel.set_permissions(
                        role,
                        send_messages=False,
                        add_reactions=False,
                        speak=False
                    )
        
        # Store in database or bot config
        if not hasattr(self.bot, 'mute_roles'):
            self.bot.mute_roles = {}
        
        self.bot.mute_roles[ctx.guild.id] = role.id
        
        embed = discord.Embed(
            title="🔇 Mute Role Set",
            description=f"Mute role set to {role.mention}",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="mute")
    @commands.has_permissions(moderate_members=True)
    async def mute_member(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Mute a member using mute role"""
        if not hasattr(self.bot, 'mute_roles') or ctx.guild.id not in self.bot.mute_roles:
            await ctx.send("❌ Mute role not set! Use `!setmuterole` first.")
            return
        
        mute_role_id = self.bot.mute_roles[ctx.guild.id]
        mute_role = ctx.guild.get_role(mute_role_id)
        
        if not mute_role:
            await ctx.send("❌ Mute role not found!")
            return
        
        if mute_role in member.roles:
            await ctx.send(f"❌ {member.mention} is already muted!")
            return
        
        await member.add_roles(mute_role, reason=reason)
        
        embed = discord.Embed(
            title="🔇 Member Muted",
            description=f"{member.mention} has been muted.",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        await ctx.send(embed=embed)
    
    @commands.command(name="unmute")
    @commands.has_permissions(moderate_members=True)
    async def unmute_member(self, ctx, member: discord.Member):
        """Unmute a member"""
        if not hasattr(self.bot, 'mute_roles') or ctx.guild.id not in self.bot.mute_roles:
            await ctx.send("❌ Mute role not set!")
            return
        
        mute_role_id = self.bot.mute_roles[ctx.guild.id]
        mute_role = ctx.guild.get_role(mute_role_id)
        
        if not mute_role:
            await ctx.send("❌ Mute role not found!")
            return
        
        if mute_role not in member.roles:
            await ctx.send(f"❌ {member.mention} is not muted!")
            return
        
        await member.remove_roles(mute_role)
        
        embed = discord.Embed(
            title="🔊 Member Unmuted",
            description=f"{member.mention} has been unmuted.",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        await ctx.send(embed=embed)
    
    # ====================================================================================================
    # WARNING SYSTEM
    # ====================================================================================================
    
    @commands.command(name="warn")
    @commands.has_permissions(kick_members=True)
    async def warn_member(self, ctx, member: discord.Member, *, reason: str = "No reason provided"):
        """Warn a member"""
        # Initialize warnings storage
        if not hasattr(self.bot, 'warnings'):
            self.bot.warnings = {}
        
        if ctx.guild.id not in self.bot.warnings:
            self.bot.warnings[ctx.guild.id] = {}
        
        if member.id not in self.bot.warnings[ctx.guild.id]:
            self.bot.warnings[ctx.guild.id][member.id] = []
        
        # Add warning
        warning = {
            'id': len(self.bot.warnings[ctx.guild.id][member.id]) + 1,
            'moderator': ctx.author.id,
            'reason': reason,
            'timestamp': datetime.now().isoformat()
        }
        self.bot.warnings[ctx.guild.id][member.id].append(warning)
        
        embed = discord.Embed(
            title="⚠️ Member Warned",
            description=f"{member.mention} has been warned.",
            color=discord.Color.yellow(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=True)
        embed.add_field(name="Total Warnings", value=len(self.bot.warnings[ctx.guild.id][member.id]), inline=True)
        
        await ctx.send(embed=embed)
        
        # Try to DM the warned member
        try:
            dm_embed = discord.Embed(
                title=f"⚠️ You have been warned in {ctx.guild.name}",
                description=f"**Reason:** {reason}\n**Warnings:** {len(self.bot.warnings[ctx.guild.id][member.id])}",
                color=discord.Color.yellow()
            )
            await member.send(embed=dm_embed)
        except:
            pass
    
    @commands.command(name="warnings")
    @commands.has_permissions(kick_members=True)
    async def show_warnings(self, ctx, member: discord.Member):
        """Show warnings for a member"""
        if not hasattr(self.bot, 'warnings') or ctx.guild.id not in self.bot.warnings:
            await ctx.send(f"⚠️ {member.mention} has no warnings.")
            return
        
        if member.id not in self.bot.warnings[ctx.guild.id]:
            await ctx.send(f"⚠️ {member.mention} has no warnings.")
            return
        
        warnings = self.bot.warnings[ctx.guild.id][member.id]
        
        embed = discord.Embed(
            title=f"⚠️ Warnings for {member.name}",
            description=f"Total warnings: **{len(warnings)}**",
            color=discord.Color.orange()
        )
        
        for warning in warnings[-5:]:  # Show last 5 warnings
            moderator = ctx.guild.get_member(warning['moderator'])
            mod_name = moderator.name if moderator else "Unknown"
            embed.add_field(
                name=f"Warning #{warning['id']}",
                value=f"**Moderator:** {mod_name}\n**Reason:** {warning['reason']}\n**Date:** {warning['timestamp'][:10]}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="clearwarnings")
    @commands.has_permissions(administrator=True)
    async def clear_warnings(self, ctx, member: discord.Member):
        """Clear all warnings for a member"""
        if not hasattr(self.bot, 'warnings') or ctx.guild.id not in self.bot.warnings:
            await ctx.send(f"⚠️ {member.mention} has no warnings to clear.")
            return
        
        if member.id not in self.bot.warnings[ctx.guild.id]:
            await ctx.send(f"⚠️ {member.mention} has no warnings to clear.")
            return
        
        del self.bot.warnings[ctx.guild.id][member.id]
        
        embed = discord.Embed(
            title="✅ Warnings Cleared",
            description=f"All warnings for {member.mention} have been cleared.",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        await ctx.send(embed=embed)
    
    # ====================================================================================================
    # SLOWMODE COMMANDS
    # ====================================================================================================
    
    @commands.command(name="slowmode")
    @commands.has_permissions(manage_channels=True)
    async def set_slowmode(self, ctx, seconds: int = 0):
        """Set slowmode for the current channel"""
        if seconds > 21600:
            await ctx.send("❌ Slowmode cannot exceed 6 hours (21600 seconds)!")
            return
        
        await ctx.channel.edit(slowmode_delay=seconds)
        
        if seconds == 0:
            await ctx.send("✅ Slowmode disabled!")
        else:
            await ctx.send(f"✅ Slowmode set to {seconds} seconds!")
    
    @commands.command(name="lock")
    @commands.has_permissions(manage_channels=True)
    async def lock_channel(self, ctx, channel: discord.TextChannel = None):
        """Lock the channel (prevent sending messages)"""
        if channel is None:
            channel = ctx.channel
        
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = False
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        
        embed = discord.Embed(
            title="🔒 Channel Locked",
            description=f"{channel.mention} has been locked. Only moderators can send messages.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name="unlock")
    @commands.has_permissions(manage_channels=True)
    async def unlock_channel(self, ctx, channel: discord.TextChannel = None):
        """Unlock the channel"""
        if channel is None:
            channel = ctx.channel
        
        overwrite = channel.overwrites_for(ctx.guild.default_role)
        overwrite.send_messages = None
        await channel.set_permissions(ctx.guild.default_role, overwrite=overwrite)
        
        embed = discord.Embed(
            title="🔓 Channel Unlocked",
            description=f"{channel.mention} has been unlocked. Members can now send messages.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    # ====================================================================================================
    # SERVER INFO COMMANDS
    # ====================================================================================================
    
    @commands.command(name="serverinfo")
    async def server_info(self, ctx):
        """Display server information"""
        guild = ctx.guild
        
        embed = discord.Embed(
            title=f"📊 {guild.name}",
            description=guild.description or "No description",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Server stats
        embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="Created", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Verification Level", value=str(guild.verification_level).title(), inline=True)
        
        embed.add_field(name="Members", value=guild.member_count, inline=True)
        embed.add_field(name="Channels", value=len(guild.channels), inline=True)
        embed.add_field(name="Roles", value=len(guild.roles), inline=True)
        
        embed.add_field(name="Boost Level", value=guild.premium_tier, inline=True)
        embed.add_field(name="Boosts", value=guild.premium_subscription_count, inline=True)
        embed.add_field(name="Emojis", value=len(guild.emojis), inline=True)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="userinfo")
    async def user_info(self, ctx, member: discord.Member = None):
        """Display user information"""
        if member is None:
            member = ctx.author
        
        embed = discord.Embed(
            title=f"👤 {member.name}",
            color=member.color or discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        embed.add_field(name="ID", value=member.id, inline=True)
        embed.add_field(name="Nickname", value=member.nickname or "None", inline=True)
        embed.add_field(name="Joined Discord", value=member.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="Top Role", value=member.top_role.mention, inline=True)
        embed.add_field(name="Is Bot", value="Yes" if member.bot else "No", inline=True)
        
        # Roles
        roles = [role.mention for role in member.roles[1:]][:5]  # Exclude @everyone
        if roles:
            embed.add_field(name=f"Roles ({len(member.roles)-1})", value=" ".join(roles), inline=False)
        
        await ctx.send(embed=embed)
    
    # ====================================================================================================
    # ERROR HANDLING
    # ====================================================================================================
    
    @clear_messages.error
    @kick_member.error
    @ban_member.error
    @timeout_member.error
    async def admin_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ You don't have permission to use this command!")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Missing required argument: {error.param.name}")
        elif isinstance(error, commands.BadArgument):
            await ctx.send(f"❌ Invalid argument: {error}")
        else:
            await ctx.send(f"❌ An error occurred: {error}")


async def setup(bot):
    await bot.add_cog(Admin(bot))
