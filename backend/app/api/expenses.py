import csv
import io
from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.db.base import Expense, User
from app.db.session import get_db
from app.schemas.expense import ExpenseCreate, ExpenseListOut, ExpenseOut, ExpenseUpdate, ImportResult
from app.services.expenses import amount_from_cents, create_expense, csv_rows, import_csv, list_expenses, update_expense

router = APIRouter(prefix="/expenses", tags=["expenses"])


@router.get("", response_model=ExpenseListOut)
def get_expenses(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), search: str | None = Query(None, max_length=100),
    category: str | None = Query(None, max_length=64), date_from: date | None = None, date_to: date | None = None,
    sort: str = Query("date", pattern="^(date|amount|description|created)$"), direction: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must be before date_to")
    items, total = list_expenses(db, user, page=page, page_size=page_size, search=search, category=category, date_from=date_from, date_to=date_to, sort=sort, direction=direction)
    return {"items": items, "page": page, "page_size": page_size, "total": total, "pages": (total + page_size - 1) // page_size}


@router.post("", response_model=ExpenseOut, status_code=201)
def add_expense(payload: ExpenseCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return create_expense(db, user, payload)


@router.get("/export/csv")
def export_expenses(date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must be before date_to")

    def generate():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["amount", "description", "category", "date", "notes"])
        yield buffer.getvalue()
        buffer.seek(0); buffer.truncate(0)
        for expense in csv_rows(db, user, date_from, date_to):
            writer.writerow([f"{amount_from_cents(expense.amount_cents):.2f}", expense.description, expense.category.name, expense.expense_date.isoformat(), expense.notes or ""])
            yield buffer.getvalue()
            buffer.seek(0); buffer.truncate(0)

    return StreamingResponse(generate(), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=ledgerly-expenses.csv"})


@router.post("/import", response_model=ImportResult)
async def import_expenses(file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return await import_csv(db, user, file)


@router.get("/{expense_id}", response_model=ExpenseOut)
def get_expense(expense_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    expense = db.scalar(select(Expense).options(joinedload(Expense.category)).where(Expense.id == expense_id, Expense.user_id == user.id))
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@router.patch("/{expense_id}", response_model=ExpenseOut)
def edit_expense(expense_id: str, payload: ExpenseUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    expense = db.scalar(select(Expense).where(Expense.id == expense_id, Expense.user_id == user.id))
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return update_expense(db, user, expense, payload)


@router.delete("/{expense_id}", status_code=204)
def remove_expense(expense_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    expense = db.scalar(select(Expense).where(Expense.id == expense_id, Expense.user_id == user.id))
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    db.delete(expense)
    db.commit()
