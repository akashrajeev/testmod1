import csv
import hashlib
import io
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.db.base import Category, Expense, User
from app.schemas.expense import ExpenseCreate, ExpenseUpdate

CENT = Decimal("0.01")
DEFAULT_CATEGORIES = ["Food", "Transport", "Housing", "Shopping", "Health", "Entertainment", "Bills", "Other"]


def cents_from_amount(amount: Decimal) -> int:
    if amount.as_tuple().exponent < -2:
        raise ValueError("amount must have at most 2 decimal places")
    return int(amount.quantize(CENT, rounding=ROUND_HALF_UP) * 100)


def amount_from_cents(cents: int) -> Decimal:
    return (Decimal(cents) / Decimal("100")).quantize(CENT)


def get_or_create_category(db: Session, name: str) -> Category:
    normalized = name.strip()
    category = db.scalar(select(Category).where(func.lower(Category.name) == normalized.lower()))
    if category:
        return category
    category = Category(name=normalized)
    db.add(category)
    db.flush()
    return category


def create_expense(db: Session, user: User, payload: ExpenseCreate) -> Expense:
    category = get_or_create_category(db, payload.category)
    expense = Expense(
        user_id=user.id,
        category_id=category.id,
        amount_cents=cents_from_amount(payload.amount),
        description=payload.description,
        expense_date=payload.date,
        notes=payload.notes,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return db.scalar(select(Expense).options(joinedload(Expense.category)).where(Expense.id == expense.id))


def update_expense(db: Session, user: User, expense: Expense, payload: ExpenseUpdate) -> Expense:
    data = payload.model_dump(exclude_unset=True)
    if "amount" in data and data["amount"] is not None:
        expense.amount_cents = cents_from_amount(data["amount"])
    if "description" in data and data["description"] is not None:
        expense.description = data["description"].strip()
    if "category" in data and data["category"] is not None:
        expense.category = get_or_create_category(db, data["category"])
    if "date" in data:
        expense.expense_date = data["date"]
    if "notes" in data:
        expense.notes = data["notes"]
    db.commit()
    db.refresh(expense)
    return db.scalar(select(Expense).options(joinedload(Expense.category)).where(Expense.id == expense.id))


def list_expenses(
    db: Session,
    user: User,
    *,
    page: int,
    page_size: int,
    search: str | None,
    category: str | None,
    date_from: date | None,
    date_to: date | None,
    sort: str,
    direction: str,
):
    base: Select = select(Expense).join(Expense.category).where(Expense.user_id == user.id)
    count_q = select(func.count(Expense.id)).join(Expense.category).where(Expense.user_id == user.id)
    filters = []
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(Expense.description.ilike(term), Expense.notes.ilike(term), Category.name.ilike(term)))
    if category:
        filters.append(func.lower(Category.name) == category.strip().lower())
    if date_from:
        filters.append(Expense.expense_date >= date_from)
    if date_to:
        filters.append(Expense.expense_date <= date_to)
    if filters:
        base = base.where(*filters)
        count_q = count_q.where(*filters)

    sort_columns = {
        "date": Expense.expense_date,
        "amount": Expense.amount_cents,
        "description": Expense.description,
        "created": Expense.created_at,
    }
    sort_column = sort_columns.get(sort, Expense.expense_date)
    order = sort_column.asc() if direction == "asc" else sort_column.desc()
    base = base.options(joinedload(Expense.category)).order_by(order, Expense.id.desc())
    total = db.scalar(count_q) or 0
    items = list(db.scalars(base.offset((page - 1) * page_size).limit(page_size)).unique())
    return items, total


def fingerprint(user_id: int, amount_cents: int, description: str, category: str, expense_date: date, notes: str | None) -> str:
    raw = "|".join([
        str(user_id), str(amount_cents), description.strip(), category.strip().lower(),
        expense_date.isoformat(), (notes or "").strip()
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def import_csv(db: Session, user: User, file: UploadFile) -> dict:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please upload a CSV file")

    imported = skipped = failed = 0
    errors: list[str] = []
    text = io.TextIOWrapper(file.file, encoding="utf-8-sig", newline="")
    reader = csv.DictReader(text)
    required = {"amount", "description", "category", "date"}
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV is missing a header row")

    header_map = {h.strip().lower(): h for h in reader.fieldnames if h}
    if not required.issubset(header_map):
        raise HTTPException(status_code=400, detail="CSV headers must include: amount, description, category, date")

    for row_number, row in enumerate(reader, start=2):
        savepoint = db.begin_nested()
        try:
            amount = Decimal((row.get(header_map["amount"]) or "").strip())
            description = (row.get(header_map["description"]) or "").strip()
            category_name = (row.get(header_map["category"]) or "").strip()
            expense_date = date.fromisoformat((row.get(header_map["date"]) or "").strip())
            notes_key = header_map.get("notes")
            notes = (row.get(notes_key) or "").strip() or None if notes_key else None

            if amount <= 0 or not description or not category_name:
                raise ValueError("amount must be positive and description/category must be present")
            amount_cents = cents_from_amount(amount)
            fp = fingerprint(user.id, amount_cents, description, category_name, expense_date, notes)
            exists = db.scalar(select(Expense.id).where(Expense.user_id == user.id, Expense.import_fingerprint == fp))
            if exists:
                savepoint.rollback()
                skipped += 1
                continue

            category = get_or_create_category(db, category_name)
            db.add(Expense(
                user_id=user.id,
                category_id=category.id,
                amount_cents=amount_cents,
                description=description,
                expense_date=expense_date,
                notes=notes,
                import_fingerprint=fp,
            ))
            db.flush()
            savepoint.commit()
            imported += 1
        except (ValueError, InvalidOperation) as exc:
            savepoint.rollback()
            failed += 1
            errors.append(f"Row {row_number}: {exc}")
        except Exception as exc:
            savepoint.rollback()
            failed += 1
            errors.append(f"Row {row_number}: invalid data ({exc})")

        if len(errors) >= 100:
            errors.append("Additional errors omitted after 100 rows")
            break

    db.commit()
    return {"imported": imported, "skipped_duplicates": skipped, "failed": failed, "errors": errors}


def csv_rows(db: Session, user: User, date_from: date | None, date_to: date | None):
    q = (
        select(Expense)
        .options(joinedload(Expense.category))
        .where(Expense.user_id == user.id)
        .order_by(Expense.expense_date.desc(), Expense.id.desc())
    )
    if date_from:
        q = q.where(Expense.expense_date >= date_from)
    if date_to:
        q = q.where(Expense.expense_date <= date_to)
    return db.scalars(q).unique()
