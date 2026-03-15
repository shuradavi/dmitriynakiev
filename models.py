from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    language_code = Column(String(10), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    last_active = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    pets = relationship("Pet", back_populates="user", cascade="all, delete-orphan")


class Pet(Base):
    __tablename__ = 'pets'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    species = Column(String(100), nullable=False)
    name = Column(String(100), nullable=True)
    age = Column(String(20), default="0")  # Количество линек в виде строки
    last_feeding = Column(DateTime, nullable=True)
    last_molt = Column(DateTime, nullable=True)
    last_cleaning = Column(DateTime, nullable=True)
    feeding_interval_hours = Column(Integer, default=8)
    cleaning_interval_days = Column(Integer, default=3)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    user = relationship("User", back_populates="pets")