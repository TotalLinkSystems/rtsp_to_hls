from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from pydantic import BaseModel
from typing import Optional, List
from fastapi import HTTPException
import logging

# -----------------------
# Logging
# -----------------------
logger = logging.getLogger("stream_api")

# -----------------------
# Database Configuration
# -----------------------
DATABASE_URL = "mysql+mysqlconnector://rtspuser:8dH7*xPY!@localhost:3306/rtsp_to_hls"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()

# -----------------------
# Model Definition
# -----------------------
class Record(Base):
    __tablename__ = "streams"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    url = Column(String(100), nullable=False)
    name = Column(String(50), nullable=False)
    pid = Column(Integer, nullable=True)

Base.metadata.create_all(bind=engine)

# -----------------------
# Pydantic Schemas
# -----------------------
class RecordCreate(BaseModel):
    url: str
    name: str

class RecordUpdate(BaseModel):
    url: Optional[str] = None
    name: Optional[str] = None
    pid: Optional[int] = None

class RecordResponse(BaseModel):
    id: int
    url: str
    name: str
    pid: Optional[int]

    class ConfigDict:
        from_attributes = True

# -----------------------
# Session Dependency
# -----------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------
# CRUD Utility Functions
# -----------------------
def get_all_records(db: Session):
    try:
        return db.query(Record).all()
    except Exception as e:
        logger.error(f"Error retrieving records: {e}")
        raise HTTPException(status_code=500, detail="Database error")

def get_record_by_id(id: int, db: Session):
    try:
        record = db.query(Record).filter(Record.id == id).first()
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        return record
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving record {id}: {e}")
        raise HTTPException(status_code=500, detail="Database error")
        
def get_record_by_pid(pid: int, db: Session):
    try:
        record = db.query(Record).filter(Record.pid == pid).first()
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")
        return record
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving record with PID {pid}: {e}")
        raise HTTPException(status_code=500, detail="Database error")

def create_record(record_data: RecordCreate, db: Session):
    try:
        new_record = Record(url=record_data.url, name=record_data.name)
        db.add(new_record)
        db.commit()
        db.refresh(new_record)
        return new_record
    except Exception as e:
        db.rollback()
        logger.error(f"Error inserting record: {e}")
        raise HTTPException(status_code=500, detail="Failed to insert record")

def update_record_by_id(id: int, record_data: RecordUpdate, db: Session):
    try:
        db_record = db.query(Record).filter(Record.id == id).first()
        if not db_record:
            raise HTTPException(status_code=404, detail="Record not found")

        for field, value in record_data.model_dump(exclude_unset=True).items():
            setattr(db_record, field, value)

        db.commit()
        db.refresh(db_record)
        return db_record
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating record {id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update record")

def update_record_by_pid(pid: int, record_data: RecordUpdate, db: Session):
    try:
        db_record = db.query(Record).filter(Record.pid == pid).first()
        if not db_record:
            raise HTTPException(status_code=404, detail="Record not found")

        for field, value in record_data.model_dump(exclude_unset=True).items():
            setattr(db_record, field, value)

        db.commit()
        db.refresh(db_record)
        return db_record
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating record with PID {pid}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update record")

def delete_record_by_id(id: int, db: Session):
    try:
        db_record = db.query(Record).filter(Record.id == id).first()
        if not db_record:
            raise HTTPException(status_code=404, detail="Record not found")

        db.delete(db_record)
        db.commit()
        return db_record
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting record {id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete record")
