# Signal Clone — SDE Fullstack Assignment

A functional Signal Messenger clone built with Next.js 16 + FastAPI + SQLite + WebSockets + Redis pub/sub.

---

## Quick Start

### Option A — Docker (recommended)

```bash
cp .env.example .env      # edit SECRET_KEY
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Redis: localhost:6379

### Option B — Local (manual)

**1. Start Redis**

```bash
redis-server
```

**2. Backend**

```bash
cd backend
pip install -r requirements.txt
python seed.py          # seed sample data
uvicorn main:app --reload --port 8000
```

**3. Frontend**

```bash
cd frontend
npm install
npm run dev             # http://localhost:3000
```

---

## Demo Accounts

All accounts use password: **`password123`**

| Phone | Username | Display Name |
|-------|----------|--------------|
| +1234567890 | alice | Alice Johnson |
| +1234567891 | bob | Bob Smith |
| +1234567892 | charlie | Charlie Brown |
| +1234567893 | diana | Diana Prince |
| +1234567894 | eve | Eve Williams |
| +1234567895 | frank | Frank Miller |
| +1234567896 | grace | Grace Lee |
| +1234567897 | henry | Henry Davis |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16 (TypeScript, Turbopack) |
| UI | Tailwind CSS v4, Lucide icons |
| State | Zustand |
| Backend | Python 3 + FastAPI |
| Database | SQLite via SQLAlchemy ORM |
| Real-time | WebSockets (FastAPI native) + Redis pub/sub |
| Auth | JWT (python-jose) |
| Deployment | Docker + docker-compose |

---

## Architecture Overview

```
signal-clone/
├── docker-compose.yml         # redis + backend + frontend services
├── .env.example               # all configurable env vars
│
├── frontend/
│   ├── Dockerfile
│   ├── app/
│   │   ├── layout.tsx         # Root layout
│   │   ├── page.tsx           # Entry → AppShell
│   │   └── auth/page.tsx      # Register / Login
│   ├── components/
│   │   ├── AppShell.tsx       # Main authenticated wrapper, WS init
│   │   ├── Sidebar.tsx        # Conversation list + search
│   │   ├── ChatPane.tsx       # Message view + input
│   │   ├── Avatar.tsx         # Reusable avatar with online dot
│   │   ├── NewChatModal.tsx   # Start DM / add contact
│   │   ├── NewGroupModal.tsx  # Create group chat
│   │   └── SettingsPanel.tsx  # Profile edit + settings
│   └── lib/
│       ├── api.ts             # All REST API calls
│       ├── store.ts           # Zustand global state
│       └── websocket.ts       # WS connect / event dispatch
│
└── backend/
    ├── Dockerfile
    ├── main.py                # FastAPI app, WS endpoint, lifespan
    ├── database.py            # SQLAlchemy engine + session
    ├── models.py              # ORM models
    ├── schemas.py             # Pydantic request/response schemas
    ├── auth.py                # JWT + password hashing
    ├── websocket_manager.py   # Redis pub/sub + WS connection registry
    ├── seed.py                # Sample data seeder
    └── routers/
        ├── auth.py            # /api/auth/*
        ├── contacts.py        # /api/contacts/*
        └── conversations.py   # /api/conversations/*
```

---

## Real-time Flow (Redis pub/sub)

```
Client A sends message (REST POST)
        │
        ▼
  FastAPI publishes to Redis channel: chat:user:{recipient_id}
        │
        ▼
  Redis broadcasts to all subscribed server instances
        │
        ▼
  Each server delivers to its locally-connected WebSocket(s)
        │
        ▼
  Client B receives new_message event → Zustand store updates UI
```

Each connected user gets their own Redis channel (`chat:user:{id}`). When a user connects, a background asyncio task subscribes to their channel and forwards any published JSON to their WebSocket. This means the backend scales horizontally — multiple uvicorn workers or containers all share the same Redis and messages are delivered regardless of which instance a user is connected to.

Typing indicators are sent directly over WebSocket (not published to Redis, not persisted).

---

## Environment Variables

Copy `.env.example` to `.env` and adjust as needed:

```env
# Backend
SECRET_KEY=change-me-to-a-long-random-string
REDIS_URL=redis://redis:6379
CORS_ORIGINS=http://localhost:3000

# Frontend (must be set at build time — Next.js NEXT_PUBLIC_ vars)
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

---

## Database Schema

```
users
  id, phone, username, display_name, avatar_url, about,
  is_online, last_seen, hashed_password, created_at

contacts
  id, user_id → users, contact_user_id → users, nickname

conversations
  id, is_group, group_name, group_avatar_url, group_description,
  created_by → users, created_at, updated_at

conversation_participants   -- for 1-on-1 chats
  id, conversation_id → conversations, user_id → users

group_members               -- for group chats
  id, conversation_id → conversations, user_id → users,
  is_admin, joined_at

messages
  id, conversation_id → conversations, sender_id → users,
  content, message_type, status, reply_to_id → messages,
  is_deleted, disappear_at, created_at, updated_at

message_reactions
  id, message_id → messages, user_id → users, emoji

message_read_receipts
  id, message_id → messages, user_id → users, read_at
```

---

## API Reference

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/auth/register | Register (OTP mock: 123456) |
| POST | /api/auth/login | Login with phone + password |
| GET | /api/auth/me | Get current user |
| PUT | /api/auth/me | Update profile |

### Contacts
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/contacts | List contacts |
| POST | /api/contacts | Add contact by phone |
| DELETE | /api/contacts/{id} | Remove contact |
| GET | /api/contacts/search?q= | Search users |

### Conversations & Messages
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/conversations | List all conversations |
| POST | /api/conversations | Create / get DM |
| POST | /api/conversations/groups | Create group |
| GET | /api/conversations/{id}/messages | Get messages |
| POST | /api/conversations/{id}/messages | Send message |
| DELETE | /api/conversations/{id}/messages/{msgId} | Delete message |
| POST | /api/conversations/{id}/messages/{msgId}/react | React with emoji |
| GET | /api/conversations/{id}/members | Group members |
| POST | /api/conversations/{id}/members/{userId} | Add member |
| DELETE | /api/conversations/{id}/members/{userId} | Remove member |

Interactive docs available at http://localhost:8000/docs when the backend is running.

---

## Features

- Auth: register with phone, mocked OTP (123456), login, JWT session
- Contact management: add by phone, search users
- Conversation list: sorted by activity, unread counts, last message preview
- One-on-one and group messaging, real-time via WebSockets + Redis
- Message status: sent / delivered / read (double-tick)
- Typing indicators (real-time, not persisted)
- Message deletion (soft delete)
- Emoji reactions
- Reply-to / quoted messages
- Online/offline presence indicators
- Profile editing (name, about)
- Pre-seeded sample data (8 users, multiple DMs + 2 groups)
- Horizontal scaling ready (Redis pub/sub decouples WS delivery from process)

---

## Assumptions & Limitations

- OTP verification is mocked: any registration accepts `123456` as the valid OTP
- Passwords are hashed with SHA-256 + server secret (production would use bcrypt/argon2)
- Database is SQLite by default; set `DATABASE_URL` to a PostgreSQL URL for production
- File/image attachment upload endpoints are stubbed (schema ready, upload handler not wired)
- Voice/video calls, Stories, and Linked devices are not implemented
- Disappearing messages: schema has `disappear_at` column but the cleanup timer is not wired
