from datetime import datetime,timezone
from uuid import UUID,uuid4

from sqlalchemy import DateTime,String,Uuid
from sqlalchemy.orm import Mapped,mapped_column,relationship

from app.db.base import Base

def utcnow()->datetime:
    return datetime.now(timezone.utc)

class Conversation(Base):
    __tablename__="conversations"

    id:Mapped[UUID]=mapped_column(Uuid,primary_key=True,default=uuid4)
    owner_id:Mapped[UUID]=mapped_column(Uuid,index=True)
    title:Mapped[str]=mapped_column(String(120),default="新对话")
    created_at:Mapped[datetime]=mapped_column(
        DateTime(timezone=True),default=utcnow
    )
    updated_at:Mapped[datetime]=mapped_column(
        DateTime(timezone=True),default=utcnow    
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation",
        cascade="all,delete-orphan",
        passive_deletes=True
    )