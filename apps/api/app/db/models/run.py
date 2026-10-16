from datetime import datetime
from uuid import UUID,uuid4

from sqlalchemy import CheckConstraint,DateTime,ForeignKey,String,Text,Uuid,Integer
from sqlalchemy.orm import Mapped,mapped_column,relationship

from app.db.base import Base
from app.db.models.conversation import utcnow

class AgentRun(Base):
    __tablename__ = "agent_runs"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(32), default="running")
    error_code: Mapped[str | None] = mapped_column(String(80))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))