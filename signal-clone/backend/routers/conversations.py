from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, and_, desc
from database import get_db
import models, schemas
from auth import get_current_user
from typing import List
from websocket_manager import manager

router = APIRouter(prefix="/api/conversations", tags=["conversations"])


def get_conversation_out(conv: models.Conversation, current_user_id: int, db: Session):
    participants = []
    if conv.is_group:
        members = db.query(models.GroupMember).filter(
            models.GroupMember.conversation_id == conv.id
        ).all()
        for m in members:
            user = db.query(models.User).filter(models.User.id == m.user_id).first()
            if user:
                participants.append(user)
    else:
        for p in conv.participants:
            participants.append(p.user)

    last_msg = (
        db.query(models.Message)
        .filter(
            models.Message.conversation_id == conv.id,
            models.Message.is_deleted == False,
        )
        .order_by(desc(models.Message.created_at))
        .first()
    )

    unread_count = (
        db.query(models.Message)
        .outerjoin(
            models.MessageReadReceipt,
            and_(
                models.MessageReadReceipt.message_id == models.Message.id,
                models.MessageReadReceipt.user_id == current_user_id,
            ),
        )
        .filter(
            models.Message.conversation_id == conv.id,
            models.Message.sender_id != current_user_id,
            models.Message.is_deleted == False,
            models.MessageReadReceipt.id == None,
        )
        .count()
    )

    result = {
        "id": conv.id,
        "is_group": conv.is_group,
        "group_name": conv.group_name,
        "group_avatar_url": conv.group_avatar_url,
        "group_description": conv.group_description,
        "created_at": conv.created_at,
        "updated_at": conv.updated_at,
        "participants": participants,
        "last_message": last_msg,
        "unread_count": unread_count,
    }
    return result


@router.get("", response_model=List[schemas.ConversationOut])
def get_conversations(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Direct conversations
    direct_conv_ids = (
        db.query(models.ConversationParticipant.conversation_id)
        .filter(models.ConversationParticipant.user_id == current_user.id)
        .all()
    )
    direct_ids = [r[0] for r in direct_conv_ids]

    # Group conversations
    group_conv_ids = (
        db.query(models.GroupMember.conversation_id)
        .filter(models.GroupMember.user_id == current_user.id)
        .all()
    )
    group_ids = [r[0] for r in group_conv_ids]

    all_ids = list(set(direct_ids + group_ids))
    if not all_ids:
        return []

    convs = (
        db.query(models.Conversation)
        .filter(models.Conversation.id.in_(all_ids))
        .order_by(desc(models.Conversation.updated_at))
        .all()
    )

    result = []
    for conv in convs:
        result.append(get_conversation_out(conv, current_user.id, db))

    return result


@router.post("", response_model=schemas.ConversationOut)
def create_or_get_conversation(
    data: schemas.ConversationCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Check if conversation already exists between these two users
    my_convs = (
        db.query(models.ConversationParticipant.conversation_id)
        .filter(models.ConversationParticipant.user_id == current_user.id)
        .all()
    )
    my_conv_ids = [r[0] for r in my_convs]

    their_convs = (
        db.query(models.ConversationParticipant.conversation_id)
        .filter(models.ConversationParticipant.user_id == data.participant_id)
        .all()
    )
    their_conv_ids = [r[0] for r in their_convs]

    shared = set(my_conv_ids) & set(their_conv_ids)
    for conv_id in shared:
        conv = db.query(models.Conversation).filter(
            models.Conversation.id == conv_id,
            models.Conversation.is_group == False,
        ).first()
        if conv:
            return get_conversation_out(conv, current_user.id, db)

    # Create new conversation
    other_user = db.query(models.User).filter(models.User.id == data.participant_id).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="User not found")

    conv = models.Conversation(is_group=False)
    db.add(conv)
    db.flush()

    db.add(models.ConversationParticipant(conversation_id=conv.id, user_id=current_user.id))
    db.add(models.ConversationParticipant(conversation_id=conv.id, user_id=data.participant_id))
    db.commit()
    db.refresh(conv)

    return get_conversation_out(conv, current_user.id, db)


@router.post("/groups", response_model=schemas.ConversationOut)
def create_group(
    data: schemas.GroupCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = models.Conversation(
        is_group=True,
        group_name=data.name,
        group_description=data.description,
        group_avatar_url=f"https://api.dicebear.com/7.x/initials/svg?seed={data.name}",
        created_by=current_user.id,
    )
    db.add(conv)
    db.flush()

    # Add creator as admin
    db.add(models.GroupMember(
        conversation_id=conv.id,
        user_id=current_user.id,
        is_admin=True,
    ))

    # Add members
    for member_id in data.member_ids:
        if member_id != current_user.id:
            user = db.query(models.User).filter(models.User.id == member_id).first()
            if user:
                db.add(models.GroupMember(
                    conversation_id=conv.id,
                    user_id=member_id,
                    is_admin=False,
                ))

    db.commit()
    db.refresh(conv)
    return get_conversation_out(conv, current_user.id, db)


@router.get("/{conv_id}/messages", response_model=List[schemas.MessageOut])
def get_messages(
    conv_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify participant
    is_participant = _check_participant(conv_id, current_user.id, db)
    if not is_participant:
        raise HTTPException(status_code=403, detail="Not a participant")

    messages = (
        db.query(models.Message)
        .filter(
            models.Message.conversation_id == conv_id,
            models.Message.is_deleted == False,
        )
        .order_by(models.Message.created_at)
        .all()
    )

    # Mark as read
    for msg in messages:
        if msg.sender_id != current_user.id:
            existing = db.query(models.MessageReadReceipt).filter(
                models.MessageReadReceipt.message_id == msg.id,
                models.MessageReadReceipt.user_id == current_user.id,
            ).first()
            if not existing:
                db.add(models.MessageReadReceipt(
                    message_id=msg.id,
                    user_id=current_user.id,
                ))
                msg.status = "read"
    db.commit()

    result = []
    for msg in messages:
        reactions = [
            {"emoji": r.emoji, "user_id": r.user_id}
            for r in msg.reactions
        ]
        result.append({
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "sender_id": msg.sender_id,
            "content": msg.content,
            "message_type": msg.message_type,
            "status": msg.status,
            "reply_to_id": msg.reply_to_id,
            "is_deleted": msg.is_deleted,
            "created_at": msg.created_at,
            "sender": msg.sender,
            "reactions": reactions,
        })
    return result


@router.post("/{conv_id}/messages", response_model=schemas.MessageOut)
async def send_message(
    conv_id: int,
    data: schemas.MessageCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    is_participant = _check_participant(conv_id, current_user.id, db)
    if not is_participant:
        raise HTTPException(status_code=403, detail="Not a participant")

    msg = models.Message(
        conversation_id=conv_id,
        sender_id=current_user.id,
        content=data.content,
        message_type=data.message_type,
        reply_to_id=data.reply_to_id,
        status="sent",
    )
    db.add(msg)

    # Update conversation updated_at
    conv = db.query(models.Conversation).filter(models.Conversation.id == conv_id).first()
    from sqlalchemy.sql import func
    conv.updated_at = func.now()

    db.commit()
    db.refresh(msg)

    # Get participant ids for WebSocket broadcast
    participant_ids = _get_participant_ids(conv_id, db)

    msg_data = {
        "type": "new_message",
        "message": {
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "sender_id": msg.sender_id,
            "content": msg.content,
            "message_type": msg.message_type,
            "status": msg.status,
            "reply_to_id": msg.reply_to_id,
            "is_deleted": msg.is_deleted,
            "created_at": msg.created_at.isoformat(),
            "sender": {
                "id": current_user.id,
                "phone": current_user.phone,
                "username": current_user.username,
                "display_name": current_user.display_name,
                "avatar_url": current_user.avatar_url,
                "about": current_user.about,
                "is_online": True,
                "last_seen": current_user.last_seen.isoformat() if current_user.last_seen else None,
            },
            "reactions": [],
        },
    }

    await manager.broadcast_to_conversation(conv_id, msg_data, participant_ids)

    return {
        "id": msg.id,
        "conversation_id": msg.conversation_id,
        "sender_id": msg.sender_id,
        "content": msg.content,
        "message_type": msg.message_type,
        "status": msg.status,
        "reply_to_id": msg.reply_to_id,
        "is_deleted": msg.is_deleted,
        "created_at": msg.created_at,
        "sender": current_user,
        "reactions": [],
    }


@router.delete("/{conv_id}/messages/{msg_id}")
async def delete_message(
    conv_id: int,
    msg_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    msg = db.query(models.Message).filter(
        models.Message.id == msg_id,
        models.Message.conversation_id == conv_id,
        models.Message.sender_id == current_user.id,
    ).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")

    msg.is_deleted = True
    msg.content = "This message was deleted"
    db.commit()

    participant_ids = _get_participant_ids(conv_id, db)
    await manager.broadcast_to_conversation(conv_id, {
        "type": "message_deleted",
        "message_id": msg_id,
        "conversation_id": conv_id,
    }, participant_ids)

    return {"detail": "Message deleted"}


@router.post("/{conv_id}/messages/{msg_id}/react")
async def react_to_message(
    conv_id: int,
    msg_id: int,
    data: schemas.ReactionCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(models.MessageReaction).filter(
        models.MessageReaction.message_id == msg_id,
        models.MessageReaction.user_id == current_user.id,
    ).first()

    if existing:
        if existing.emoji == data.emoji:
            db.delete(existing)
        else:
            existing.emoji = data.emoji
    else:
        db.add(models.MessageReaction(
            message_id=msg_id,
            user_id=current_user.id,
            emoji=data.emoji,
        ))

    db.commit()

    participant_ids = _get_participant_ids(conv_id, db)
    await manager.broadcast_to_conversation(conv_id, {
        "type": "reaction_update",
        "message_id": msg_id,
        "conversation_id": conv_id,
        "user_id": current_user.id,
        "emoji": data.emoji,
    }, participant_ids)

    return {"detail": "Reaction updated"}


@router.get("/{conv_id}/members", response_model=List[schemas.GroupMemberOut])
def get_group_members(
    conv_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    members = db.query(models.GroupMember).filter(
        models.GroupMember.conversation_id == conv_id
    ).all()
    return members


@router.post("/{conv_id}/members/{user_id}")
def add_group_member(
    conv_id: int,
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    admin = db.query(models.GroupMember).filter(
        models.GroupMember.conversation_id == conv_id,
        models.GroupMember.user_id == current_user.id,
        models.GroupMember.is_admin == True,
    ).first()
    if not admin:
        raise HTTPException(status_code=403, detail="Only admins can add members")

    existing = db.query(models.GroupMember).filter(
        models.GroupMember.conversation_id == conv_id,
        models.GroupMember.user_id == user_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already in group")

    db.add(models.GroupMember(conversation_id=conv_id, user_id=user_id))
    db.commit()
    return {"detail": "Member added"}


@router.delete("/{conv_id}/members/{user_id}")
def remove_group_member(
    conv_id: int,
    user_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    admin = db.query(models.GroupMember).filter(
        models.GroupMember.conversation_id == conv_id,
        models.GroupMember.user_id == current_user.id,
        models.GroupMember.is_admin == True,
    ).first()
    if not admin and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Only admins can remove members")

    member = db.query(models.GroupMember).filter(
        models.GroupMember.conversation_id == conv_id,
        models.GroupMember.user_id == user_id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    db.delete(member)
    db.commit()
    return {"detail": "Member removed"}


def _check_participant(conv_id: int, user_id: int, db: Session) -> bool:
    conv = db.query(models.Conversation).filter(models.Conversation.id == conv_id).first()
    if not conv:
        return False
    if conv.is_group:
        return db.query(models.GroupMember).filter(
            models.GroupMember.conversation_id == conv_id,
            models.GroupMember.user_id == user_id,
        ).first() is not None
    else:
        return db.query(models.ConversationParticipant).filter(
            models.ConversationParticipant.conversation_id == conv_id,
            models.ConversationParticipant.user_id == user_id,
        ).first() is not None


def _get_participant_ids(conv_id: int, db: Session):
    conv = db.query(models.Conversation).filter(models.Conversation.id == conv_id).first()
    if not conv:
        return []
    if conv.is_group:
        members = db.query(models.GroupMember).filter(
            models.GroupMember.conversation_id == conv_id
        ).all()
        return [m.user_id for m in members]
    else:
        parts = db.query(models.ConversationParticipant).filter(
            models.ConversationParticipant.conversation_id == conv_id
        ).all()
        return [p.user_id for p in parts]
