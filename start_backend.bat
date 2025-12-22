@echo off
cd backend
..\venv\Scripts\python.exe -m uvicorn app.main:app --reload
