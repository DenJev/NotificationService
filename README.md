# Notification Service

## Overview

A FastAPI-based web application that integrates a **Google Pub/Sub subscriber** for processing and reacting to published messages in real time.  
This service listens to a specified Pub/Sub subscription, handles message acknowledgment, and sends an email using the Google API. 

The purpose of the **Notification Service** is to act as a **standalone microservice** that integrates with other systems or microservices to send out emails triggered by Pub/Sub events.

Dishka is used to manage dependency injection and we structure the project to aid domain driven design. 

## Architecture
**Direction of Dependencies (DDD)**

This project follows Domain-Driven Design (DDD) principles to maintain a clean and modular architecture.

**Dependency Rule**

All dependencies flow inward, toward the Domain layer, which represents the core business logic of the system.

`Infrastructure  →  Application  →  Domain`


The Domain is at the core (or bottom, depending on visualization).
It contains all business rules and has no knowledge of external systems.

**Layer Responsibilities**

`Domain` — Core business rules, entities, value objects, and domain services.
No external dependencies.

`Application` — Orchestrates use cases and defines ports (interfaces) for external services.
Depends only on the Domain.

`Infrastructure` — Implements the ports defined in the Application layer (e.g., SMTP, Pub/Sub, DB).
Depends on Application and Domain.

`Presentation` — Handles input/output (HTTP, CLI, etc.) and calls into the Application layer.

```
└── src/
    └── app/
        ├── run.py                           # app entry point
        │
        ├── application/...                  # application layer
        │   ├── events/                      # common layer objects
        │   │   ├── event_dispatcher.py      # Handles dispatching of events to interactors that handle notification.
        │   │   └── ...                      # ports, exceptions, etc.
        │   │
        │   ├── commands/                    # write operations, business-critical reads
        │   │   ├── game_digest.py           # interactor to process event and send notification for user.
        │   │   └── ...                      # other interactors
        │   │
        │   └── common/ports                 # ports for infrastructure
        │       ├── event_subscriber.py      # query service
        │       └── ...                      # other query services
        │
        ├── domain/                          # domain layer
        │   ├── entities/...                 # key business logic actors
        │   │   ├── base/...                 # base declarations
        │   │   └── pub_sub/...              # event entities and value objects
        │   │
        │   ├── services/...                 # domain layer services
        │   └── ...                          # ports, exceptions, etc.
        │
        ├── infrastructure/                         # Infrastructure layer
        │   ├── adapters/                           # Technology-specific implementations
        │   │   ├── email/                          # Email-related adapters
        │   │   │   ├── smtp_email_sender.py        # Implements EmailSender port using SMTP
        │   │   │   └── __init__.py
        │   │   │
        │   │   ├── pub_sub/                        # Pub/Sub event system adapters
        │   │   │   ├── pub_sub_event_consumer.py   # Consumes Pub/Sub messages
        │   │   │   ├── pub_sub_event_producer.py   # (optional) Publishes events to Pub/Sub
        │   │   │   └── __init__.py
        │   │   │
        │   │   └── ...                             # Other adapters (e.g., DB, Cache, Keycloak)
        │   │
        │   ├── exceptions/                         # Infra-level exceptions (optional)
        │   ├── logging/                            # Logging setup (optional)
        │   └── __init__.py
        ├── presentation/...                 # presentation layer
        │   ├── common/...                   # common layer objects
        │   │
        │   └── http_controllers/            # controllers (http)
        │       ├──                          # controller
        │       └── ...                      # other controllers
        │
        └── setup/
            ├── app_factory.py               # app builder
            ├── config/...                   # app settings
            └── ioc/...                      # dependency injection setup
```

## Running Tests with Docker
**Create the environment**

```uv sync --python 3.12```

**Set the application environment**

```export APP_ENV=test```

**Make the environment**

```make env```

**Create the dotenv**

```make dotenv``

To run the test suite inside a Docker environment:

1. Navigate to the **test configuration directory**:
   ```bash
   cd ./config/test

   docker compose -f docker-compose.test.yaml up --build
   ```

## Idempotency Goal

The Notification Service consumes messages from Google Pub/Sub.
Since Pub/Sub guarantees at-least-once delivery, the same message may be delivered multiple times or to multiple consumers concurrently.
To prevent duplicate side effects (e.g., multiple emails sent for the same event), this service implements strong idempotency at the application level.

#### Implementation Details

**Idempotency** is enforced through a combination of:

Database-backed event tracking
Each Pub/Sub message is uniquely identified by its message_id and topic.
These are stored in the events table with a lifecycle status:

*PROCESSING* - event is being handled

*PROCESSED* - event successfully handled

*FAILED* - event processing failed (retryable)

PostgreSQL advisory locks
Before handling an event, the interactor acquires a transaction-level advisory lock based on the topic and message IDs:

```SELECT pg_try_advisory_xact_lock(:topic_key, :message_key)```


If the lock cannot be acquired, another consumer is already processing this message.

This ensures only one consumer can process a given message at a time — even across distributed instances.

Event status-based deduplication
When a message is received:

If the event doesn’t exist → create it and mark as *PROCESSING*

If it’s already *PROCESSED* → ack message and skip (idempotent no-op)

If it’s *PROCESSING* → skip (concurrent duplicate) but nack the message so it can be retried in case consumer fails.

If it’s *FAILED* → nack message and retry the event
