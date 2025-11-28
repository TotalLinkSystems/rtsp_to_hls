import uvicorn
import logging
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi import WebSocket
from fastapi.responses import HTMLResponse
from typing import List
import subprocess, os, traceback
import asyncio
import folder_utils as fu
import watchdog_manager as wd
import db_utils as db

# -----------------------
# Logging Configuration
# -----------------------
LOG_FILE = "app.log"

logger = logging.getLogger("stream_api")
logger.setLevel(logging.INFO)
file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# -----------------------
# FastAPI App
# -----------------------
app = FastAPI(title="Stream Control API")

# Define the allowed origins as a wildcard to allow all
origins = ["*", "http://192.168.55.106:8080", "http://127.0.0.1:8080"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,  # Set to True if your frontend sends cookies or authorization headers
    allow_methods=["*"],     # Allows all HTTP methods
    allow_headers=["*"],     # Allows all request headers
)

def start_stream_process(record, db_session):
    # command = [
    #     "ffmpeg", "-i", record.url, "-c:v", "copy", "-c:a", "aac", "-ac", "1",
    #     "-ar", "44100", "-b:a", "128k", "-f", "hls",
    #     "-hls_time", "2", "-hls_list_size", "5", "-hls_flags", "delete_segments",
    #     f"/var/www/html/bsghelp/streams/{record.name}/{record.name}.m3u8"
    # ]
    command = [
        "ffmpeg", "-rtsp_transport", "tcp", "-fflags", "+genpts", "-timeout", "50000000",
        # "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "2",
        "-i", record.url, "-c:v", "copy", "-c:a", "aac", "-ac", "1",
        "-ar", "44100", "-b:a", "128k", "-f", "hls",
        "-hls_time", "4", "-hls_list_size", "10", "-hls_flags", "delete_segments+append_list+program_date_time",
        "-hls_allow_cache", "0", "-hls_segment_filename", f"/var/www/html/bsghelp/streams/{record.name}/segment_%03d.ts",
        f"/var/www/html/bsghelp/streams/{record.name}/{record.name}.m3u8"
    ]
    process = subprocess.Popen(command)
    record.pid = process.pid
    db_session.commit()
    db_session.refresh(record)
    folder_path = f"/var/www/html/bsghelp/streams/{record.name}"
    wd.start_watchdog(process.pid, folder_path, restart_stream_by_pid)
    logger.info(f"Started stream for record {record.id} (PID: {process.pid})")
    return process.pid


def stop_stream_process(pid, db_session):
    wd.stop_watchdog(pid)
    try:
        os.kill(pid, 9)
        delete_files_in_directory(pid)
    except ProcessLookupError:
        logger.warning(f"PID {pid} not found (already stopped)")
    record = db_session.query(db.Record).filter(db.Record.pid == pid).first()
    if record:
        record.pid = None
        db_session.commit()
        db_session.refresh(record)
    logger.info(f"Stopped stream PID {pid}")
    return

def restart_stream_process(record, db_session):
    try:
        if record.pid:
            stop_stream_process(record.pid, db_session)
            logger.info("Stream stopped successfully.")
            delete_files_in_directory(record.pid)
        pid = start_stream_process(record, db_session)
        logger.info(f"Restarted stream for record ID {record.id}")
        return {"message": f"Restarted stream for record ID {record.id}", "pid": record.pid}
    except Exception as e:
        logger.error(f"Error restarting stream for record ID {record.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to restart stream")

def restart_stream_by_pid(pid: int):
    """Restart stream given a PID (for watchdog use)."""
    db_session = next(db.get_db())
    record = db_session.query(db.Record).filter(db.Record.pid == pid).first()
    if not record:
        logger.warning(f"No record found for PID {pid}, skipping restart")
        return

    try:
        logger.info(f"Restarting stream for record {record.id} (PID {pid})")
        restart_stream_process(record, db_session)
    except Exception as e:
        logger.error(f"Failed to restart stream for PID {pid}: {e}")
    finally:
        db_session.close()


# -----------------------
# Exception Handlers
# -----------------------
@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    error_trace = traceback.format_exc()
    logger.error(f"Unhandled exception: {exc}\n{error_trace}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

# -----------------------
# CRUD Endpoints
# -----------------------
@app.get("/records", response_model=list[db.RecordResponse])
def get_records(db_session = Depends(db.get_db)):
    records = db.get_all_records(db_session)
    logger.info("Retrieved all records.")
    return records

@app.post("/records", response_model=db.RecordResponse)
def insert_record(record: db.RecordCreate, db_session = Depends(db.get_db)):
    new_record = db.create_record(record, db_session)
    fu.create_folder_if_not_exists(f"/var/www/html/bsghelp/streams/{new_record.name}")
    logger.info(f"Inserted new record: {new_record}")
    return new_record

@app.put("/records/{id}", response_model=db.RecordResponse)
def update_record(id: int, record: db.RecordUpdate, db_session = Depends(db.get_db)):
    updated = db.update_record_by_id(id, record, db_session)
    fu.update_folder(f"/var/www/html/bsghelp/streams/{updated.name}", updated.name)
    logger.info(f"Updated record ID {id}")
    return updated

@app.delete("/records/{id}")
def delete_record(id: int, db_session = Depends(db.get_db)):
    deleted = db.delete_record_by_id(id, db_session)
    fu.delete_folder_if_exists(f"/var/www/html/bsghelp/streams/{deleted.name}")
    logger.info(f"Deleted record ID {id}")
    return {"message": f"Record {id} deleted successfully"}


# -----------------------
# Stream Control Endpoints
# -----------------------

@app.post("/start_stream/{id}")
def start_stream(id: int, db_session=Depends(db.get_db)):
    record = db_session.query(db.Record).filter(db.Record.id == id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    pid = start_stream_process(record, db_session)
    return {"message": f"Started stream for record {id}", "pid": pid}


@app.post("/stop_stream/{pid}")
def stop_stream(pid: int, db_session=Depends(db.get_db)):
    stop_stream_process(pid, db_session)
    return {"message": f"Stopped stream with PID {pid}"}


@app.post("/restart/{record_id}")
def restart_stream(record_id: int, db_session=Depends(db.get_db)):
    record = db_session.query(db.Record).filter(db.Record.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    restart_stream_process(record, db_session)
    return {"message": f"Restarted stream for record ID {record_id}", "pid": record.pid}

#---------------------------------------
#	Websockets
#---------------------------------------
active_connections: List[WebSocket] = []

@app.websocket("/ws/streams")
async def stream_updates(ws: WebSocket):
    await ws.accept()
    active_connections.append(ws)
    try:
        while True:
            ws.send("Web socket connected in backend")
            await asyncio.sleep(5)
    except Exception:
        pass
    finally:
        active_connections.remove(ws)

#  Call this function whenever records change
async def broadcast_records(records):
    for ws in active_connections:
        try:
            await ws.send_json([r.dict() for r in records])
        except:
            pass

#-------------------------------------------------------
#	Delete all files in directory on stop/restart
#-------------------------------------------------------
def delete_files_in_directory(pid: int):
    """
    Deletes all files inside the stream directory for the given PID.
    Keeps the directory and any subdirectories.
    """
    # --- Get DB session ---
    db_session = next(db.get_db())

    try:
        # --- Get the record from PID ---
        record = db_session.query(db.Record).filter(db.Record.pid == pid).first()
        if not record:
            print(f"No record found for PID {pid}")
            return

        # --- Build path ---
        directory_path = f"/var/www/html/bsghelp/streams/{record.name}"

        if not os.path.isdir(directory_path):
            print(f"Directory not found: {directory_path}")
            return

        # --- Delete files ---
        for filename in os.listdir(directory_path):
            file_path = os.path.join(directory_path, filename)
            if os.path.isfile(file_path):
                try:
                    os.remove(file_path)
                    print(f"Deleted: {file_path}")
                except OSError as e:
                    print(f"Error deleting {file_path}: {e}")

        print(f"All files deleted in: {directory_path}")

    finally:
        db_session.close()


# -----------------------
# Run Server
# -----------------------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
