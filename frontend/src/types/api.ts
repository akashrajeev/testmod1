export type User = { id: number; email: string; created_at: string };
export type Category = { id: number; name: string };
export type Expense = { id: string; amount: string; description: string; category: Category; date: string; notes: string | null; created_at: string; updated_at: string };
export type ExpenseList = { items: Expense[]; page: number; page_size: number; total: number; pages: number };
export type Dashboard = { total_spending: string; current_month_spending: string; by_category: { category: string; amount: string }[]; recent_expenses: Expense[]; monthly_trends: { month: string; amount: string }[] };
export type ImportResult = { imported: number; skipped_duplicates: number; failed: number; errors: string[] };
