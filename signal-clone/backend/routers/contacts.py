from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from auth import get_current_user
from typing import List

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


@router.get("", response_model=List[schemas.ContactOut])
def get_contacts(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contacts = (
        db.query(models.Contact)
        .filter(models.Contact.user_id == current_user.id)
        .all()
    )
    return contacts


@router.post("", response_model=schemas.ContactOut)
def add_contact(
    contact_data: schemas.ContactCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    target = db.query(models.User).filter(models.User.phone == contact_data.phone).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found with that phone number")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot add yourself as a contact")

    existing = (
        db.query(models.Contact)
        .filter(
            models.Contact.user_id == current_user.id,
            models.Contact.contact_user_id == target.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Contact already added")

    contact = models.Contact(
        user_id=current_user.id,
        contact_user_id=target.id,
        nickname=contact_data.nickname,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{contact_id}")
def remove_contact(
    contact_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    contact = (
        db.query(models.Contact)
        .filter(
            models.Contact.id == contact_id,
            models.Contact.user_id == current_user.id,
        )
        .first()
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    db.delete(contact)
    db.commit()
    return {"detail": "Contact removed"}


@router.get("/search")
def search_users(
    q: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    users = (
        db.query(models.User)
        .filter(
            models.User.id != current_user.id,
            (
                models.User.phone.contains(q)
                | models.User.username.contains(q)
                | models.User.display_name.contains(q)
            ),
        )
        .limit(20)
        .all()
    )
    return users
