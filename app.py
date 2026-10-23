"""FastAPI: RAG, задачи и оптимизация. Учебный локальный сервис."""
import json
from pathlib import Path
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel,Field
from rag import build_index,retrieve,generate
from scheduler import schedule
ROOT=Path(__file__).parent
DATA=json.loads((ROOT/"data.json").read_text(encoding="utf-8"))
ARTICLES=DATA["articles"];TASKS=DATA["tasks"];WORKERS=DATA["workers"]
VECTORIZER,MATRIX=build_index(ARTICLES)
app=FastAPI(title=DATA["title"],version="7.0")
class Ask(BaseModel):
    query:str=Field(min_length=1,max_length=2000)
    k:int=Field(default=3,ge=1,le=10)
class TaskIn(BaseModel):
    title:str=Field(min_length=1,max_length=200)
    priority:str=Field(default="medium")
    duration:int=Field(default=1,ge=1,le=4)
@app.get("/health")
def health():return {"status":"ok","articles":len(ARTICLES),"tasks":len(TASKS)}
@app.post("/search")
def search(req:Ask):return {"sources":retrieve(req.query,ARTICLES,VECTORIZER,MATRIX,req.k)}
@app.post("/ask")
def ask(req:Ask):
    sources=retrieve(req.query,ARTICLES,VECTORIZER,MATRIX,req.k)
    return {**generate(req.query,sources),"sources":sources}
@app.get("/tasks")
def tasks():return TASKS
@app.post("/tasks")
def add_task(req:TaskIn):
    if req.priority not in ("critical","high","medium","low"):raise HTTPException(422,"Некорректный приоритет")
    task={"id":"NEW-"+str(len(TASKS)+1),"title":req.title,"priority":req.priority,"duration":req.duration}
    TASKS.append(task);return task
@app.get("/schedule")
def get_schedule(horizon:int=8):return schedule(TASKS,WORKERS,horizon)
