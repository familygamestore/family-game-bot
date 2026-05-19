import aiosqlite
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'bot.db')

class BotDatabase:
    """SQLite database for bot local storage"""
    
    def __init__(self):
        self.conn = None
    
    async def connect(self):
        """Connect to database"""
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        self.conn = await aiosqlite.connect(DB_PATH)
        await self.init_tables()
    
    async def init_tables(self):
        """Initialize database tables"""
        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS xp_data (
                user_id INTEGER PRIMARY KEY,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                messages INTEGER DEFAULT 0,
                voice_minutes INTEGER DEFAULT 0,
                last_active TIMESTAMP
            )
        ''')
        
        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS custom_commands (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                command_name TEXT NOT NULL,
                response TEXT NOT NULL,
                created_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(guild_id, command_name)
            )
        ''')
        
        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS welcome_messages (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                enabled BOOLEAN DEFAULT 1
            )
        ''')
        
        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS level_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                level INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                UNIQUE(guild_id, level)
            )
        ''')
        
        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS giveaways (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                prize TEXT NOT NULL,
                winners INTEGER NOT NULL,
                end_time TIMESTAMP NOT NULL,
                ended BOOLEAN DEFAULT 0
            )
        ''')
        
        await self.conn.commit()
    
    async def close(self):
        """Close database connection"""
        if self.conn:
            await self.conn.close()
    
    # ========== XP METHODS ==========
    async def add_xp(self, user_id: int, xp: int):
        """Add XP to user"""
        await self.conn.execute('''
            INSERT INTO xp_data (user_id, xp, last_active)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                xp = xp + ?,
                last_active = ?
        ''', (user_id, xp, datetime.now().isoformat(), xp, datetime.now().isoformat()))
        await self.conn.commit()
    
    async def get_xp(self, user_id: int):
        """Get user XP and level"""
        cursor = await self.conn.execute('SELECT xp, level FROM xp_data WHERE user_id = ?', (user_id,))
        row = await cursor.fetchone()
        if row:
            return {'xp': row[0], 'level': row[1]}
        return {'xp': 0, 'level': 0}
    
    async def update_level(self, user_id: int, level: int):
        """Update user level"""
        await self.conn.execute('UPDATE xp_data SET level = ? WHERE user_id = ?', (level, user_id))
        await self.conn.commit()
    
    # ========== CUSTOM COMMANDS ==========
    async def add_custom_command(self, guild_id: int, command_name: str, response: str, created_by: int):
        """Add custom command"""
        await self.conn.execute('''
            INSERT OR REPLACE INTO custom_commands (guild_id, command_name, response, created_by)
            VALUES (?, ?, ?, ?)
        ''', (guild_id, command_name.lower(), response, created_by))
        await self.conn.commit()
    
    async def get_custom_command(self, guild_id: int, command_name: str):
        """Get custom command response"""
        cursor = await self.conn.execute(
            'SELECT response FROM custom_commands WHERE guild_id = ? AND command_name = ?',
            (guild_id, command_name.lower())
        )
        row = await cursor.fetchone()
        return row[0] if row else None
    
    async def get_all_custom_commands(self, guild_id: int):
        """Get all custom commands for a guild"""
        cursor = await self.conn.execute(
            'SELECT command_name, response FROM custom_commands WHERE guild_id = ?',
            (guild_id,)
        )
        return await cursor.fetchall()
    
    async def delete_custom_command(self, guild_id: int, command_name: str):
        """Delete custom command"""
        await self.conn.execute(
            'DELETE FROM custom_commands WHERE guild_id = ? AND command_name = ?',
            (guild_id, command_name.lower())
        )
        await self.conn.commit()
    
    # ========== WELCOME MESSAGES ==========
    async def set_welcome_message(self, guild_id: int, channel_id: int, message: str):
        """Set welcome message for guild"""
        await self.conn.execute('''
            INSERT OR REPLACE INTO welcome_messages (guild_id, channel_id, message, enabled)
            VALUES (?, ?, ?, 1)
        ''', (guild_id, channel_id, message))
        await self.conn.commit()
    
    async def get_welcome_message(self, guild_id: int):
        """Get welcome message for guild"""
        cursor = await self.conn.execute(
            'SELECT channel_id, message FROM welcome_messages WHERE guild_id = ? AND enabled = 1',
            (guild_id,)
        )
        return await cursor.fetchone()
    
    # ========== LEVEL ROLES ==========
    async def add_level_role(self, guild_id: int, level: int, role_id: int):
        """Add level role reward"""
        await self.conn.execute('''
            INSERT OR REPLACE INTO level_roles (guild_id, level, role_id)
            VALUES (?, ?, ?)
        ''', (guild_id, level, role_id))
        await self.conn.commit()
    
    async def get_level_role(self, guild_id: int, level: int):
        """Get role for a specific level"""
        cursor = await self.conn.execute(
            'SELECT role_id FROM level_roles WHERE guild_id = ? AND level <= ? ORDER BY level DESC LIMIT 1',
            (guild_id, level)
        )
        row = await cursor.fetchone()
        return row[0] if row else None

bot_db = BotDatabase()