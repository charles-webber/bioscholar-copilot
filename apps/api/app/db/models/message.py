from datetime import datetime
from uuid import UUID,uuid4

from sqlalchemy import CheckConstraint,DateTime,ForeignKey,String,Text,Uuid
from sqlalchemy.orm import Mapped,mapped_column,relationship

from app.db.base import Base
from app.db.models.conversation import utcnow

class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint("role IN('user','assistant')",name="ck_message_role"),
    )

    id:Mapped[UUID] = mapped_column(Uuid,primary_key=True,default=uuid4)
    conversation_id:Mapped[UUID]=mapped_column(
        ForeignKey("conversations.id",ondelete="CASCADE"),index=True
    )
    role:Mapped[str]=mapped_column(String(20))
    content:Mapped[str]=mapped_column(Text)
    status:Mapped[str]=mapped_column(String(20),default="completed")
    created_at:Mapped[datetime]=mapped_column(
        DateTime(timezone=True),default=utcnow
    )

    conversation:Mapped["Conversation"]=relationship(back_populates="messages")

