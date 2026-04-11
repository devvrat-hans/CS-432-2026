# CS-432-2026 — Databases Course Project

Repository for CS-432 (Databases), Semester II 2025-2026, IIT Gandhinagar.

## Project: Blind Drop

A privacy-focused file transfer portal. Upload a file, receive a one-time 6-character download code, and the file is permanently deleted after download. No login, no trace, no account required.

## Repository Structure

```
├── assignment-01/          SQL schema design, DDL, inserts, queries
├── assignment-02/          API layer + B+ tree indexing
│   ├── Module_A/           B+ tree implementation & performance benchmarks
│   └── Module_B/           Flask REST API + Next.js frontend
├── assignment-03/          ACID transactions + stress testing
│   ├── Module_A/           Transaction engine with WAL-based recovery
│   └── Module_B/           Concurrency, durability, failure simulation tests
├── assignment-04/          Sharding implementation (Assignment 4 submission)
│   ├── db_management_system/   Backend with shard-aware query routing
│   ├── frontend/               Next.js frontend
│   ├── tests/                  Sharding + integration tests
│   └── README.md               Sharding documentation
└── blinddrop/              Standalone deployable Blind Drop application
    ├── db_management_system/   Flask backend (Python)
    ├── frontend/               Next.js frontend (TypeScript)
    └── README.md               Full application documentation
```

## Quick Start (Blind Drop)

### Backend

```bash
cd blinddrop/db_management_system
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

### Frontend

```bash
cd blinddrop/frontend
npm install
npm run dev
```

Open `http://localhost:3000` to use the app.

## Tech Stack

- **Backend**: Python, Flask, SQLite (3 shards + 1 main DB)
- **Frontend**: Next.js 16, TypeScript, Tailwind CSS
- **Sharding**: Hash-based (`md5(sessionID) % 3`) across 3 SQLite databases
