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

---

這是一個通知系統，不是聊天機器人。

# 股東會紀念品通知系統

這是一個穩健的、時間驅動的通知系統，透過 LINE Bot 每週廣播「股東會紀念品報告」。

## 概覽
- **類型**：通知系統（無對話式 AI）
- **時程**：每週廣播（亞洲/台北時間 週一 08:30）
- **技術棧**：Python, Flask, APScheduler, SQLAlchemy (PostgreSQL)
- **部署**：Render + Neon

## 核心限制
1. **系統識別**：嚴格用於通知。忽略聊天訊息。
2. **無狀態**：處理 Render 的暫存檔案系統。
3. **資料庫**：PostgreSQL 搭配連線池。
4. **時區**：Asia/Taipei。

## 錯過執行寬限時間 (Misfire Grace Time)
排程器包含 3600 秒（1 小時）的 `misfire_grace_time`，以因應 Render 可能的冷啟動延遲。
