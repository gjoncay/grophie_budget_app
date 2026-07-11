from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Category, CategoryRule

router = APIRouter(tags=["categories"])


@router.get("/api/categories")
def list_categories(db: Session = Depends(get_db)):
    return [
        {
            "id": c.id,
            "name": c.name,
            "group": c.group,
            "parent_category_id": c.parent_category_id,
            "is_custom": c.is_custom,
        }
        for c in db.query(Category).order_by(Category.parent_category_id.is_(None).desc(), Category.name).all()
    ]


@router.get("/api/category-rules")
def list_category_rules(db: Session = Depends(get_db)):
    return [
        {
            "id": r.id,
            "match_type": r.match_type,
            "match_value": r.match_value,
            "category_id": r.category_id,
            "category_name": r.category.name,
            "priority": r.priority,
        }
        for r in db.query(CategoryRule).order_by(CategoryRule.priority.desc()).all()
    ]


@router.delete("/api/category-rules/{rule_id}")
def delete_category_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.get(CategoryRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    db.delete(rule)
    db.commit()
    return {"ok": True}
