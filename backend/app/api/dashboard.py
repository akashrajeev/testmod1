from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import String, cast, func, select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.db.base import Category, Expense, User
from app.db.session import get_db
from app.schemas.expense import DashboardOut
from app.services.expenses import amount_from_cents

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardOut)
def summary(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    today = date.today()
    month_start = today.replace(day=1)
    total_cents = db.scalar(select(func.coalesce(func.sum(Expense.amount_cents), 0)).where(Expense.user_id == user.id)) or 0
    month_cents = db.scalar(select(func.coalesce(func.sum(Expense.amount_cents), 0)).where(Expense.user_id == user.id, Expense.expense_date >= month_start, Expense.expense_date <= today)) or 0

    category_rows = db.execute(
        select(Category.name, func.sum(Expense.amount_cents))
        .join(Expense, Expense.category_id == Category.id)
        .where(Expense.user_id == user.id)
        .group_by(Category.id, Category.name)
        .order_by(func.sum(Expense.amount_cents).desc())
    ).all()

    if db.bind and db.bind.dialect.name == "postgresql":
        month_key = func.to_char(Expense.expense_date, "YYYY-MM")
    else:
        month_key = func.strftime("%Y-%m", Expense.expense_date)
    trend_rows = db.execute(
        select(month_key.label("month"), func.sum(Expense.amount_cents))
        .where(Expense.user_id == user.id)
        .group_by(month_key)
        .order_by(month_key.desc())
        .limit(12)
    ).all()

    recent = list(db.scalars(
        select(Expense).options(joinedload(Expense.category))
        .where(Expense.user_id == user.id)
        .order_by(Expense.expense_date.desc(), Expense.created_at.desc())
        .limit(8)
    ).unique())

    return {
        "total_spending": amount_from_cents(total_cents),
        "current_month_spending": amount_from_cents(month_cents),
        "by_category": [{"category": name, "amount": amount_from_cents(cents or 0)} for name, cents in category_rows],
        "recent_expenses": recent,
        "monthly_trends": [{"month": month, "amount": amount_from_cents(cents or 0)} for month, cents in reversed(trend_rows)],
    }
