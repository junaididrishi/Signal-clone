from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class UserBase(BaseModel):
    phone: str
    username: str
    display_name: str


class UserCreate(UserBase):
    password: str
    otp: str = "123456"


class UserLogin(BaseModel):
    phone: str
    password: str


class UserUpdate(BaseModel):
    display_name: Optional[str] = None
    about: Optional[str] = None
    avatar_url: Optional[str] = None


class UserOut(UserBase):
    id: int
    avatar_url: Optional[str]
    about: Optional[str]
    is_online: bool
    last_seen: Optional[datetime]

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


class ContactCreate(BaseModel):
    phone: str
    nickname: Optional[str] = None


class ContactOut(BaseModel):
    id: int
    contact_user: UserOut
    nickname: Optional[str]

    class Config:
        from_attributes = True


class MessageCreate(BaseModel):
    content: str
    message_type: str = "text"
    reply_to_id: Optional[int] = None


class MessageOut(BaseModel):
    id: int
    conversation_id: int
    sender_id: int
    content: str
    message_type: str
    status: str
    reply_to_id: Optional[int]
    is_deleted: bool
    created_at: datetime
    sender: UserOut
    reactions: List[dict] = []

    class Config:
        from_attributes = True


class ConversationCreate(BaseModel):
    participant_id: int


class GroupCreate(BaseModel):
    name: str
    member_ids: List[int]
    description: Optional[str] = None


class ConversationOut(BaseModel):
    id: int
    is_group: bool
    group_name: Optional[str]
    group_avatar_url: Optional[str]
    group_description: Optional[str]
    created_at: datetime
    updated_at: datetime
    participants: List[UserOut] = []
    last_message: Optional[MessageOut] = None
    unread_count: int = 0

    class Config:
        from_attributes = True


class GroupMemberOut(BaseModel):
    user: UserOut
    is_admin: bool
    joined_at: datetime

    class Config:
        from_attributes = True


class ReactionCreate(BaseModel):
    emoji: str


class TypingEvent(BaseModel):
    conversation_id: int
    is_typing: bool
