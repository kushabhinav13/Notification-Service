
# Notification Service

A FastAPI-based microservice for sending user notifications via Email, SMS, and In-App methods. It integrates with RabbitMQ for asynchronous task processing and uses SQLite for persistent storage.

## Features

* REST API to send and retrieve notifications.
* Asynchronous processing using RabbitMQ.
* Retry logic with exponential backoff.
* Logging for monitoring and debugging.

## Tech Stack

* **FastAPI** – Web framework
* **SQLite** – Lightweight database
* **SQLAlchemy** – ORM
* **RabbitMQ** – Message broker
* **Pika** – Python RabbitMQ client
* **SMTP (Mocked)** – Email simulation
* **Threading and AsyncIO** – Background task execution

## Setup Instructions

### Prerequisites

* Python 3.8+
* RabbitMQ running locally (on `localhost:5672` with guest\:guest)

### 1. Clone the Repository


git clone https://github.com/kushabhinav13/Notification-Service.git
cd Notification-Service


### 2. Create a Virtual Environment


python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

### 3. Install Dependencies

Create a `requirements.txt` with the following content:


fastapi
uvicorn
sqlalchemy
pika
pydantic

Then run:


pip install -r requirements.txt


### 4. Start RabbitMQ

Make sure RabbitMQ is running on your local machine:


docker run -d --hostname my-rabbit --name some-rabbit -p 5672:5672 rabbitmq:3


### 5. Run the Service


uvicorn notification_service:app --reload

The service will be available at: [http://localhost:8000](http://localhost:8000)

### 6. Test the Endpoints

* `POST /notifications`: Send a notification
* `GET /users/{user_id}/notifications`: Retrieve all notifications for a user

Example request body for sending a notification:

```json
{
  "user_id": 1,
  "type": "email",
  "content": "Hello from Notification Service!"
}
```

## Assumptions Made

* Email, SMS, and In-App notification sending is currently mocked/simulated.
* RabbitMQ runs locally with default credentials (`guest:guest`).
* Notifications are stored in an SQLite database named `notifications.db`.
* SMTP and SMS sending functionalities should be configured in production using proper credentials and APIs.

## To Do

* Add Dockerfile and docker-compose for simplified deployment.
* Add authentication/authorization to APIs.
* Replace simulated notification logic with real services.
* Implement unit tests.

## License

MIT – see the [LICENSE](LICENSE) file for details
