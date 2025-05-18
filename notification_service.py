import asyncio
import json
import pika
import smtplib
from typing import List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import enum
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./notifications.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# RabbitMQ setup
RABBITMQ_URL = "amqp://guest:guest@localhost:5672/%2F"
QUEUE_NAME = "notifications"

# Notification types
class NotificationType(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"

# Database model
class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    type = Column(Enum(NotificationType))
    content = Column(String)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    retry_count = Column(Integer, default=0)

Base.metadata.create_all(bind=engine)

# Pydantic models
class NotificationCreate(BaseModel):
    user_id: int
    type: NotificationType
    content: str

class NotificationResponse(BaseModel):
    id: int
    user_id: int
    type: NotificationType
    content: str
    status: str
    created_at: datetime
    retry_count: int

# FastAPI app
app = FastAPI()

# RabbitMQ publisher
def publish_to_queue(notification: dict):
    try:
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.basic_publish(
            exchange='',
            routing_key=QUEUE_NAME,
            body=json.dumps(notification),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
        logger.info(f"Published notification {notification['id']} to queue")
    except Exception as e:
        logger.error(f"Failed to publish to queue: {str(e)}")
        raise

# Notification processors
async def process_email_notification(notification: dict):
    # Simulated email sending (replace with actual SMTP server details)
    try:
        # smtp = smtplib.SMTP("smtp.gmail.com", 587)
        # smtp.starttls()
        # smtp.login("your_email", "your_password")
        # smtp.sendmail("from@example.com", "to@example.com", notification["content"])
        logger.info(f"Sent email notification {notification['id']}")
        return True
    except Exception as e:
        logger.error(f"Email notification {notification['id']} failed: {str(e)}")
        return False

async def process_sms_notification(notification: dict):
    # Simulated SMS sending (replace with actual SMS gateway)
    try:
        logger.info(f"Sent SMS notification {notification['id']}")
        return True
    except Exception as e:
        logger.error(f"SMS notification {notification['id']} failed: {str(e)}")
        return False

async def process_in_app_notification(notification: dict):
    # Simulated in-app notification (could be stored in a separate table or sent via websocket)
    try:
        logger.info(f"Sent in-app notification {notification['id']}")
        return True
    except Exception as e:
        logger.error(f"In-app notification {notification['id']} failed: {str(e)}")
        return False

# Notification processor
async def process_notification(notification: dict):
    db = SessionLocal()
    try:
        notif = db.query(Notification).filter(Notification.id == notification["id"]).first()
        if not notif:
            logger.error(f"Notification {notification['id']} not found")
            return

        max_retries = 3
        if notif.retry_count >= max_retries:
            notif.status = "failed"
            db.commit()
            logger.error(f"Notification {notification['id']} reached max retries")
            return

        success = False
        if notification["type"] == NotificationType.EMAIL:
            success = await process_email_notification(notification)
        elif notification["type"] == NotificationType.SMS:
            success = await process_sms_notification(notification)
        elif notification["type"] == NotificationType.IN_APP:
            success = await process_in_app_notification(notification)

        notif.retry_count += 1
        notif.status = "sent" if success else "pending"
        db.commit()

        if not success and notif.retry_count < max_retries:
            # Re-queue for retry with delay
            await asyncio.sleep(2 ** notif.retry_count)  # Exponential backoff
            publish_to_queue(notification)
            logger.info(f"Re-queued notification {notification['id']} for retry {notif.retry_count}")

    except Exception as e:
        logger.error(f"Error processing notification {notification['id']}: {str(e)}")
    finally:
        db.close()

# RabbitMQ consumer
def start_consumer():
    async def callback(ch, method, properties, body):
        notification = json.loads(body)
        await process_notification(notification)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def consume():
        connection = pika.BlockingConnection(pika.URLParameters(RABBITMQ_URL))
        channel = connection.channel()
        channel.queue_declare(queue=QUEUE_NAME, durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=QUEUE_NAME, on_message_callback=lambda ch, method, properties, body: asyncio.run(callback(ch, method, properties, body)))
        channel.start_consuming()

    import threading
    threading.Thread(target=consume, daemon=True).start()

# Start consumer when app starts
@app.on_event("startup")
def startup_event():
    start_consumer()

# API endpoints
@app.post("/notifications", response_model=NotificationResponse)
async def send_notification(notification: NotificationCreate):
    db = SessionLocal()
    try:
        db_notification = Notification(
            user_id=notification.user_id,
            type=notification.type,
            content=notification.content
        )
        db.add(db_notification)
        db.commit()
        db.refresh(db_notification)

        # Publish to queue
        queue_message = {
            "id": db_notification.id,
            "user_id": db_notification.user_id,
            "type": db_notification.type.value,
            "content": db_notification.content
        }
        publish_to_queue(queue_message)

        return db_notification
    finally:
        db.close()

@app.get("/users/{user_id}/notifications", response_model=List[NotificationResponse])
async def get_user_notifications(user_id: int):
    db = SessionLocal()
    try:
        notifications = db.query(Notification).filter(Notification.user_id == user_id).all()
        if not notifications:
            raise HTTPException(status_code=404, message="No notifications found for user")
        return notifications
    finally:
        db.close()