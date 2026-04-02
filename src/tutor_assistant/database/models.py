"""SQLAlchemy ORM models."""

from __future__ import annotations

import datetime

from sqlalchemy import BigInteger, ForeignKey, SmallInteger, Time, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(nullable=False)
    tutor_chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(server_default=func.now())

    slots: Mapped[list[ScheduleSlot]] = relationship(
        "ScheduleSlot",
        back_populates="student",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ScheduleSlot(Base):
    __tablename__ = "schedule_slots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True
    )
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # 0=Mon … 6=Sun
    time_start: Mapped[datetime.time] = mapped_column(Time, nullable=False)

    student: Mapped[Student] = relationship("Student", back_populates="slots")
