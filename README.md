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

## TODO

1. **Make consumer idempotent**

### Idempotency Goal

In the current setup, multiple instances of the **Notification Service** can be connected to the same **Google Pub/Sub subscription**.  
The goal is to ensure that **only one consumer processes a given message**, even if multiple consumers receive or acknowledge it concurrently.

This form of idempotency means:

- Each Pub/Sub message should be **acted upon exactly once**, regardless of how many service instances are running.
- If a message is redelivered or received by multiple subscribers, **only the first successful handler** should perform the side effect (e.g., sending an email).
- Other consumers that receive the same message should detect that it has already been processed and safely **acknowledge and skip it**.

### Possible Approaches

- Use a **message deduplication store** (e.g., Redis, Postgres) to track processed message IDs.  
  Before handling a message, check if its `message_id` or `event_id` has already been recorded.
- Implement an **idempotency key** derived from the event payload or Pub/Sub `message_id`.
- Store and enforce processing status at the **application level**, ensuring that replays or retries do not trigger duplicate actions.

**Goal:**  
Ensure **at-least-once delivery semantics** from Pub/Sub do not result in **duplicate side effects** in the Notification Service.
