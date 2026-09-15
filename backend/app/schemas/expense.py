from datetime import date as date_type, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


class ExpenseCreate(BaseModel):
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    description: str = Field(min_length=1, max_length=200)
    category: str = Field(min_length=1, max_length=64)
    date: date_type
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("description", "category")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class ExpenseUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    description: str | None = Field(default=None, min_length=1, max_length=200)
    category: str | None = Field(default=None, min_length=1, max_length=64)
    date: date_type | None = None
    notes: str | None = Field(default=None, max_length=2000)

    @field_validator("description", "category")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class ExpenseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    amount: Decimal
    description: str
    category: CategoryOut
    date: date_type
    notes: str | None
    created_at: datetime
    updated_at: datetime


class ExpenseListOut(BaseModel):
    items: list[ExpenseOut]
    page: int
    page_size: int
    total: int
    pages: int


class CategoryTotal(BaseModel):
    category: str
    amount: Decimal


class MonthlyTotal(BaseModel):
    month: str
    amount: Decimal


class DashboardOut(BaseModel):
    total_spending: Decimal
    current_month_spending: Decimal
    by_category: list[CategoryTotal]
    recent_expenses: list[ExpenseOut]
    monthly_trends: list[MonthlyTotal]


class ImportResult(BaseModel):
    imported: int
    skipped_duplicates: int
    failed: int
    errors: list[str]
