# PrizmBet v2 - Deployment Guide

## 1. Create GitHub Repository

Done! Repo: https://github.com/MinorTermite/prizmbet-v2

## 2. Setup GitHub Secrets

Go to: Settings > Secrets and variables > Actions

Add these secrets:
- SUPABASE_URL
- SUPABASE_KEY
- UPSTASH_REDIS_URL
- UPSTASH_REDIS_TOKEN
- TELEGRAM_BOT_TOKEN
- TELEGRAM_CHAT_ID

## 3. Setup Supabase

1. https://supabase.com - New Project
2. SQL Editor - run config/supabase_schema.sql
3. Settings > API - copy URL and Key to Secrets

## 4. Setup Upstash Redis

1. https://upstash.com - Create Database
2. Copy REST API URL and Token to Secrets

## 5. Enable GitHub Actions

1. Go to Actions tab
2. Enable GitHub Actions
3. Workflow runs every 2 hours automatically

## 6. Setup GitHub Pages

Settings > Pages > Source: GitHub Actions

Site will be at: https://MinorTermite.github.io/prizmbet-v2/
