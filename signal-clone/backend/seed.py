"""Seed the database with sample data."""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import engine, SessionLocal
import models
from auth import get_password_hash
from datetime import datetime, timedelta

models.Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Clear existing data
db.query(models.MessageReadReceipt).delete()
db.query(models.MessageReaction).delete()
db.query(models.Message).delete()
db.query(models.GroupMember).delete()
db.query(models.ConversationParticipant).delete()
db.query(models.Conversation).delete()
db.query(models.Contact).delete()
db.query(models.User).delete()
db.commit()

# Create users
users_data = [
    {"phone": "+1234567890", "username": "alice", "display_name": "Alice Johnson", "about": "Hey there! I am using Signal."},
    {"phone": "+1234567891", "username": "bob", "display_name": "Bob Smith", "about": "Available"},
    {"phone": "+1234567892", "username": "charlie", "display_name": "Charlie Brown", "about": "Busy"},
    {"phone": "+1234567893", "username": "diana", "display_name": "Diana Prince", "about": "At work"},
    {"phone": "+1234567894", "username": "eve", "display_name": "Eve Williams", "about": "In a meeting"},
    {"phone": "+1234567895", "username": "frank", "display_name": "Frank Miller", "about": "🏖️ On vacation"},
    {"phone": "+1234567896", "username": "grace", "display_name": "Grace Lee", "about": "Coding..."},
    {"phone": "+1234567897", "username": "henry", "display_name": "Henry Davis", "about": "Do not disturb"},
]

users = []
for i, u in enumerate(users_data):
    user = models.User(
        phone=u["phone"],
        username=u["username"],
        display_name=u["display_name"],
        about=u["about"],
        hashed_password=get_password_hash("password123"),
        avatar_url=f"https://api.dicebear.com/7.x/thumbs/svg?seed={u['username']}",
        is_online=(i < 3),
        last_seen=datetime.utcnow() - timedelta(minutes=i * 15),
    )
    db.add(user)
    users.append(user)

db.flush()

# Add contacts for Alice
for i in range(1, len(users)):
    db.add(models.Contact(user_id=users[0].id, contact_user_id=users[i].id))

# Alice-Bob conversation
conv1 = models.Conversation(is_group=False)
db.add(conv1)
db.flush()
db.add(models.ConversationParticipant(conversation_id=conv1.id, user_id=users[0].id))
db.add(models.ConversationParticipant(conversation_id=conv1.id, user_id=users[1].id))

# Messages Alice-Bob
messages_ab = [
    (users[1].id, "Hey Alice! How are you doing?"),
    (users[0].id, "Hi Bob! I'm great, thanks. Working on a new project 🚀"),
    (users[1].id, "Sounds exciting! What's it about?"),
    (users[0].id, "Building a Signal clone for an assignment. It's pretty fun!"),
    (users[1].id, "Oh wow, that's cool. Signal-like real-time messaging?"),
    (users[0].id, "Yes! WebSockets, FastAPI backend, Next.js frontend"),
    (users[1].id, "Nice stack! Let me know if you need help testing it"),
    (users[0].id, "Will do! Thanks Bob 😊"),
    (users[1].id, "Any plans for the weekend?"),
    (users[0].id, "Finishing this project first, then maybe hiking"),
]
for i, (sender_id, content) in enumerate(messages_ab):
    db.add(models.Message(
        conversation_id=conv1.id,
        sender_id=sender_id,
        content=content,
        status="read",
        created_at=datetime.utcnow() - timedelta(hours=2, minutes=len(messages_ab) - i),
    ))

# Alice-Charlie conversation
conv2 = models.Conversation(is_group=False)
db.add(conv2)
db.flush()
db.add(models.ConversationParticipant(conversation_id=conv2.id, user_id=users[0].id))
db.add(models.ConversationParticipant(conversation_id=conv2.id, user_id=users[2].id))

messages_ac = [
    (users[2].id, "Alice, did you see the game last night?"),
    (users[0].id, "No I missed it! Who won?"),
    (users[2].id, "It was incredible, last minute goal! 🎉"),
    (users[0].id, "Nooo I need to catch the replay"),
    (users[2].id, "Definitely do, it's worth it!"),
    (users[0].id, "Thanks for the heads up Charlie"),
]
for i, (sender_id, content) in enumerate(messages_ac):
    db.add(models.Message(
        conversation_id=conv2.id,
        sender_id=sender_id,
        content=content,
        status="read",
        created_at=datetime.utcnow() - timedelta(hours=5, minutes=len(messages_ac) - i),
    ))

# Alice-Diana conversation
conv3 = models.Conversation(is_group=False)
db.add(conv3)
db.flush()
db.add(models.ConversationParticipant(conversation_id=conv3.id, user_id=users[0].id))
db.add(models.ConversationParticipant(conversation_id=conv3.id, user_id=users[3].id))

messages_ad = [
    (users[3].id, "Can you review my PR when you get a chance?"),
    (users[0].id, "Sure! Sending it to me now?"),
    (users[3].id, "Yes, just pushed. It's the auth refactoring"),
    (users[0].id, "On it! Will take a look in the afternoon"),
    (users[3].id, "Thanks! No rush, whenever you have time"),
]
for i, (sender_id, content) in enumerate(messages_ad):
    db.add(models.Message(
        conversation_id=conv3.id,
        sender_id=sender_id,
        content=content,
        status="delivered",
        created_at=datetime.utcnow() - timedelta(hours=1, minutes=len(messages_ad) - i),
    ))

# Group: Project Team
group1 = models.Conversation(
    is_group=True,
    group_name="Project Team 🚀",
    group_description="Main project coordination group",
    group_avatar_url="https://api.dicebear.com/7.x/initials/svg?seed=PT",
    created_by=users[0].id,
)
db.add(group1)
db.flush()

for i, user in enumerate(users[:5]):
    db.add(models.GroupMember(
        conversation_id=group1.id,
        user_id=user.id,
        is_admin=(i == 0),
    ))

group1_msgs = [
    (users[0].id, "Welcome everyone to the project team! 🎉"),
    (users[1].id, "Excited to be here!"),
    (users[2].id, "Let's do this! 💪"),
    (users[3].id, "Great team we have here"),
    (users[4].id, "Ready to ship something amazing"),
    (users[0].id, "First standup is tomorrow at 9am"),
    (users[1].id, "I'll be there"),
    (users[2].id, "Same, putting it in the calendar"),
    (users[3].id, "See you all then!"),
    (users[0].id, "Remember to update your tickets before the meeting"),
    (users[4].id, "Will do boss 😄"),
    (users[1].id, "Quick question - are we using Jira or Linear?"),
    (users[0].id, "Linear for now, I'll send the invite"),
]
for i, (sender_id, content) in enumerate(group1_msgs):
    db.add(models.Message(
        conversation_id=group1.id,
        sender_id=sender_id,
        content=content,
        status="read",
        created_at=datetime.utcnow() - timedelta(days=1, minutes=len(group1_msgs) - i),
    ))

# Group: Family Chat
group2 = models.Conversation(
    is_group=True,
    group_name="Family ❤️",
    group_description="Family group chat",
    group_avatar_url="https://api.dicebear.com/7.x/initials/svg?seed=Fam",
    created_by=users[0].id,
)
db.add(group2)
db.flush()

for i, user in enumerate([users[0], users[5], users[6], users[7]]):
    db.add(models.GroupMember(
        conversation_id=group2.id,
        user_id=user.id,
        is_admin=(i == 0),
    ))

group2_msgs = [
    (users[5].id, "Family dinner this Sunday? 🍝"),
    (users[6].id, "Absolutely! I'll bring dessert"),
    (users[7].id, "Count me in! What time?"),
    (users[5].id, "Let's say 6pm at my place"),
    (users[0].id, "Perfect! I'll bring salad"),
    (users[6].id, "Can't wait to see everyone 😍"),
    (users[7].id, "Same! It's been too long"),
    (users[5].id, "Agreed! Sunday it is"),
]
for i, (sender_id, content) in enumerate(group2_msgs):
    db.add(models.Message(
        conversation_id=group2.id,
        sender_id=sender_id,
        content=content,
        status="delivered",
        created_at=datetime.utcnow() - timedelta(hours=3, minutes=len(group2_msgs) - i),
    ))

db.commit()
print("✅ Database seeded successfully!")
print("\nTest accounts (all use password: password123):")
for u in users_data:
    print(f"  Phone: {u['phone']} | Username: {u['username']} | Name: {u['display_name']}")
