"""
routes/goals.py — Goals & Habits endpoints:
  POST   /goals/add
  GET    /goals
  POST   /goals/update
  DELETE /goals/{goal_id}
"""

from datetime import datetime

from bson import ObjectId
from fastapi import APIRouter, HTTPException

from config import goals_col

router = APIRouter()


@router.post("/goals/add")
async def add_goal(data: dict):
    user_id  = data.get("user_id")
    goal     = data.get("goal", "").strip()
    category = data.get("category", "General")
    if not user_id or not goal:
        raise HTTPException(status_code=400, detail="user_id and goal required")
    doc = {
        "user_id": user_id, "goal": goal, "category": category,
        "progress": 0, "completed": False,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "notes": []
    }
    result = await goals_col.insert_one(doc)
    return {"status": "added", "id": str(result.inserted_id)}


@router.get("/goals")
async def get_goals(user_id: str):
    cursor = goals_col.find({"user_id": user_id}).sort("created_at", -1)
    goals  = await cursor.to_list(length=100)
    for g in goals:
        g["_id"] = str(g["_id"])
    return {"goals": goals}


@router.post("/goals/update")
async def update_goal(data: dict):
    goal_id   = data.get("goal_id")
    progress  = data.get("progress")
    completed = data.get("completed")
    note      = data.get("note", "")
    update    = {"updated_at": datetime.utcnow().isoformat()}
    if progress is not None:
        update["progress"] = int(progress)
        if int(progress) >= 100:
            update["completed"] = True
    if completed is not None:
        update["completed"] = completed
    push = {}
    if note:
        push["notes"] = {"text": note, "at": datetime.utcnow().isoformat()}
    op = {"$set": update}
    if push:
        op["$push"] = push
    await goals_col.update_one({"_id": ObjectId(goal_id)}, op)
    return {"status": "updated"}


@router.delete("/goals/{goal_id}")
async def delete_goal(goal_id: str, user_id: str):
    await goals_col.delete_one({"_id": ObjectId(goal_id), "user_id": user_id})
    return {"status": "deleted"}
