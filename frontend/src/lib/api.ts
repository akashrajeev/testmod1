import type { Dashboard, Expense, ExpenseList, ImportResult, User } from "../types/api";

const TOKEN_KEY = "ledgerly_token";
let token: string | null = sessionStorage.getItem(TOKEN_KEY);

export function getToken() { return token; }
export function setToken(value: string | null) { token = value; if (value) sessionStorage.setItem(TOKEN_KEY, value); else sessionStorage.removeItem(TOKEN_KEY); }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  const response = await fetch(path, { ...init, headers });
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => null);
  if (!response.ok) throw new Error(data?.detail ?? "Something went wrong");
  return data as T;
}

export const api = {
  register: (email: string, password: string) => request<{ access_token: string }>("/api/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),
  login: (email: string, password: string) => request<{ access_token: string }>("/api/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  me: () => request<User>("/api/auth/me"),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),
  expenses: (params: URLSearchParams) => request<ExpenseList>(`/api/expenses?${params.toString()}`),
  expense: (id: string) => request<Expense>(`/api/expenses/${id}`),
  createExpense: (body: object) => request<Expense>("/api/expenses", { method: "POST", body: JSON.stringify(body) }),
  updateExpense: (id: string, body: object) => request<Expense>(`/api/expenses/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  deleteExpense: (id: string) => request<void>(`/api/expenses/${id}`, { method: "DELETE" }),
  dashboard: () => request<Dashboard>("/api/dashboard/summary"),
  importCsv: (file: File) => { const form = new FormData(); form.append("file", file); return request<ImportResult>("/api/expenses/import", { method: "POST", body: form }); },
};
