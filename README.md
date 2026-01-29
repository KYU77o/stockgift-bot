This is a notification system, not a chat bot.

# Stock Gift Notification System

A robust, time-driven notification system that broadcasts weekly "Shareholder Meeting Souvenir Reports" via LINE Bot.

## Overview
- **Type**: Notification System (No Conversational AI)
- **Schedule**: Weekly broadcasts (Monday 08:30 Asia/Taipei)
- **Stack**: Python, Flask, APScheduler, SQLAlchemy (PostgreSQL)
- **Deployment**: Render + Neon

## Core Constraints
1. **System Identity**: Strictly for notifications. Ignores chat messages.
2. **Stateless**: Handles Render's ephemeral filesystem.
3. **Database**: PostgreSQL with connection pooling.
4. **Timezone**: Asia/Taipei.

## Misfire Grace Time
The scheduler includes a `misfire_grace_time` of 3600 seconds (1 hour) to accommodate Render's potential cold-start delays.
