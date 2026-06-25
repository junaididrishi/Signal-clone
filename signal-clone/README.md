# Signal Clone — SDE Fullstack Assignment

A functional Signal Messenger clone built with Next.js 16 + FastAPI + SQLite + WebSockets.

## Quick Start

### 1. Backend

```bash
cd backend
pip3 install -r requirements.txt
python3 seed.py          # Seed sample data
uvicorn main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev              # Starts on http://localhost:3000 (or 3001 if in use)
```

Open [http://localhost:3000](http://localhost:3000) and log in with any seeded account.

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
| Real-time | WebSockets (FastAPI native) |
| Auth | JWT (python-jose) |

---

## Architecture Overview

```
signal-clone/
├── frontend/                  # Next.js app
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
    ├── main.py                # FastAPI app, WS endpoint
    ├── database.py            # SQLAlchemy engine + session
    ├── models.py              # ORM models
    ├── schemas.py             # Pydantic request/response schemas
    ├── auth.py                # JWT + password hashing
    ├── websocket_manager.py   # WS connection registry + broadcast
    ├── seed.py                # Sample data seeder
    └── routers/
        ├── auth.py            # /api/auth/*
        ├── contacts.py        # /api/contacts/*
        └── conversations.py   # /api/conversations/*
```

### Real-time flow

1. On login, client opens `ws://localhost:8000/ws/{user_id}?token=...`
2. Server validates JWT and registers the socket in `ConnectionManager`
3. When a message is sent via REST `POST /api/conversations/{id}/messages`, the server broadcasts it over WS to all participants
4. Client Zustand store receives the event and updates the UI reactively
5. Typing indicators are sent over WS directly (not persisted)

---

## Database Schema

```sql
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

## API Overview

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

---

## Features Implemented

### Core
- ✅ Auth: register with phone, mocked OTP (123456), login, JWT session
- ✅ Contact management: add by phone, search users
- ✅ Conversation list: sorted by activity, unread counts, last message preview
- ✅ One-on-one messaging: real-time via WebSockets
- ✅ Group messaging: create, add/remove members, admin controls
- ✅ Message status: sent / delivered / read (double-tick ✓✓)
- ✅ Typing indicators (real-time over WS)
- ✅ Message deletion (soft delete with "This message was deleted")
- ✅ Emoji reactions (6 quick-react emojis)
- ✅ Reply-to / quoted messages
- ✅ Online/offline presence indicators
- ✅ Profile editing (name, about)
- ✅ Signal-accurate UI (green header, chat bubble colors, layout)
- ✅ Pre-seeded sample data (8 users, multiple DMs + 2 groups)

### Mocked / Coming Soon
- Voice / Video calls (button present, "Coming Soon")
- Stories
- Linked devices
- Actual E2E encryption (mocked via JWT)
- Disappearing messages (schema ready, timer not yet wired)

---

## Assumptions

- OTP verification is mocked: any registration accepts `123456` as the valid OTP
- Passwords are hashed with SHA-256 + server secret (production would use bcrypt/argon2)
- The app is single-server; for horizontal scaling, the WebSocket manager would need Redis pub/sub
- File/image attachment upload endpoints are stubbed (schema ready, upload handler not wired)
