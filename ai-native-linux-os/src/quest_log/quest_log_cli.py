#!/usr/bin/env python3
"""
Quest Log CLI - Command line interface for viewing quest logs
"""

import os
import sqlite3
import click
import json
from datetime import datetime, timedelta
from pathlib import Path


class QuestLogCLI:
    def __init__(self, db_path=None):
        self.db_path = db_path or Path.home() / ".quest_log.db"
        
    def get_connection(self):
        """Get database connection"""
        if not os.path.exists(self.db_path):
            raise click.ClickException(f"Quest log database not found at {self.db_path}")
        return sqlite3.connect(self.db_path)
    
    def format_timestamp(self, timestamp_str):
        """Format timestamp for display"""
        try:
            dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            return timestamp_str
    
    def get_events(self, limit=None, event_type=None, source=None, since=None):
        """Get events from the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM events WHERE 1=1"
        params = []
        
        if event_type:
            query += " AND event_type = ?"
            params.append(event_type)
        
        if source:
            query += " AND source = ?"
            params.append(source)
        
        if since:
            query += " AND timestamp >= ?"
            params.append(since)
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        events = cursor.fetchall()
        conn.close()
        
        return events
    
    def get_commands(self, limit=None, user=None, since=None):
        """Get commands from the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM commands WHERE 1=1"
        params = []
        
        if user:
            query += " AND user = ?"
            params.append(user)
        
        if since:
            query += " AND timestamp >= ?"
            params.append(since)
        
        query += " ORDER BY timestamp DESC"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        commands = cursor.fetchall()
        conn.close()
        
        return commands
    
    def get_stats(self):
        """Get statistics from the database"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Get event counts
        cursor.execute("SELECT COUNT(*) FROM events")
        total_events = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM commands")
        total_commands = cursor.fetchone()[0]
        
        # Get event types
        cursor.execute("SELECT event_type, COUNT(*) FROM events GROUP BY event_type")
        event_types = cursor.fetchall()
        
        # Get most active users
        cursor.execute("SELECT user, COUNT(*) FROM commands GROUP BY user ORDER BY COUNT(*) DESC LIMIT 5")
        active_users = cursor.fetchall()
        
        conn.close()
        
        return {
            "total_events": total_events,
            "total_commands": total_commands,
            "event_types": event_types,
            "active_users": active_users
        }


@click.group()
@click.option('--db', help='Path to quest log database')
@click.pass_context
def cli(ctx, db):
    """Quest Log CLI - View and analyze system activity logs"""
    ctx.ensure_object(dict)
    ctx.obj['cli'] = QuestLogCLI(db)


@cli.command()
@click.option('--limit', '-l', default=20, help='Limit number of results')
@click.option('--type', '-t', help='Filter by event type')
@click.option('--source', '-s', help='Filter by source')
@click.option('--since', help='Show events since (e.g., "1 hour ago", "2023-01-01")')
@click.pass_context
def events(ctx, limit, type, source, since):
    """Show system events"""
    quest_cli = ctx.obj['cli']
    
    # Parse since parameter
    since_timestamp = None
    if since:
        if "hour" in since:
            hours = int(since.split()[0])
            since_timestamp = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        elif "day" in since:
            days = int(since.split()[0])
            since_timestamp = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        else:
            since_timestamp = since
    
    try:
        events = quest_cli.get_events(limit, type, source, since_timestamp)
        
        if not events:
            click.echo("No events found.")
            return
        
        click.echo(f"{'ID':<5} {'Timestamp':<20} {'Type':<15} {'Source':<10} {'Data'}")
        click.echo("-" * 80)
        
        for event in events:
            event_id, timestamp, event_type, event_source, data, metadata = event
            data_preview = (data[:50] + "...") if data and len(data) > 50 else (data or "")
            click.echo(f"{event_id:<5} {quest_cli.format_timestamp(timestamp):<20} {event_type:<15} {event_source:<10} {data_preview}")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.option('--limit', '-l', default=20, help='Limit number of results')
@click.option('--user', '-u', help='Filter by user')
@click.option('--since', help='Show commands since (e.g., "1 hour ago", "2023-01-01")')
@click.pass_context
def commands(ctx, limit, user, since):
    """Show shell commands"""
    quest_cli = ctx.obj['cli']
    
    # Parse since parameter
    since_timestamp = None
    if since:
        if "hour" in since:
            hours = int(since.split()[0])
            since_timestamp = (datetime.now() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")
        elif "day" in since:
            days = int(since.split()[0])
            since_timestamp = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
        else:
            since_timestamp = since
    
    try:
        commands = quest_cli.get_commands(limit, user, since_timestamp)
        
        if not commands:
            click.echo("No commands found.")
            return
        
        click.echo(f"{'ID':<5} {'Timestamp':<20} {'User':<10} {'Command'}")
        click.echo("-" * 80)
        
        for command in commands:
            cmd_id, timestamp, user, cmd, working_dir, exit_code, output, duration = command
            cmd_preview = (cmd[:50] + "...") if len(cmd) > 50 else cmd
            click.echo(f"{cmd_id:<5} {quest_cli.format_timestamp(timestamp):<20} {user:<10} {cmd_preview}")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.pass_context
def stats(ctx):
    """Show quest log statistics"""
    quest_cli = ctx.obj['cli']
    
    try:
        stats = quest_cli.get_stats()
        
        click.echo("Quest Log Statistics")
        click.echo("=" * 40)
        click.echo(f"Total Events: {stats['total_events']}")
        click.echo(f"Total Commands: {stats['total_commands']}")
        click.echo()
        
        if stats['event_types']:
            click.echo("Event Types:")
            for event_type, count in stats['event_types']:
                click.echo(f"  {event_type}: {count}")
            click.echo()
        
        if stats['active_users']:
            click.echo("Most Active Users:")
            for user, count in stats['active_users']:
                click.echo(f"  {user}: {count} commands")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


@cli.command()
@click.argument('query')
@click.pass_context
def search(ctx, query):
    """Search commands and events"""
    quest_cli = ctx.obj['cli']
    
    try:
        conn = quest_cli.get_connection()
        cursor = conn.cursor()
        
        # Search commands
        cursor.execute("""
            SELECT * FROM commands 
            WHERE command LIKE ? 
            ORDER BY timestamp DESC 
            LIMIT 20
        """, (f"%{query}%",))
        
        commands = cursor.fetchall()
        
        if commands:
            click.echo("Matching Commands:")
            click.echo("-" * 40)
            for command in commands:
                cmd_id, timestamp, user, cmd, working_dir, exit_code, output, duration = command
                click.echo(f"[{quest_cli.format_timestamp(timestamp)}] {user}: {cmd}")
        
        # Search events
        cursor.execute("""
            SELECT * FROM events 
            WHERE data LIKE ? OR event_type LIKE ?
            ORDER BY timestamp DESC 
            LIMIT 20
        """, (f"%{query}%", f"%{query}%"))
        
        events = cursor.fetchall()
        
        if events:
            click.echo("\nMatching Events:")
            click.echo("-" * 40)
            for event in events:
                event_id, timestamp, event_type, event_source, data, metadata = event
                click.echo(f"[{quest_cli.format_timestamp(timestamp)}] {event_type} from {event_source}")
        
        conn.close()
        
        if not commands and not events:
            click.echo("No matching results found.")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)


if __name__ == '__main__':
    cli()