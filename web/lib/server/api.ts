import "server-only"

import { cookies } from "next/headers"
import { getInternalApiBaseUrl } from "@/lib/server/auth"

export type Tenant = {
  id: string
  slug: string
  display_name: string
  status: string
  created_at: string
  updated_at: string
}

export type CompanyStatus = "active" | "inactive"

export type TaxRegime =
  | "simples_nacional"
  | "lucro_presumido"
  | "lucro_real"
  | "mei"
  | "isento"
  | "outro"

export type Company = {
  id: string
  legal_name: string
  trade_name: string | null
  tax_id: string
  status: CompanyStatus
  tax_regime: TaxRegime | null
  state_registration: string | null
  municipal_registration: string | null
  email: string | null
  phone: string | null
  postal_code: string | null
  street: string | null
  number: string | null
  complement: string | null
  district: string | null
  city: string | null
  state: string | null
  country: string
  created_at: string
  updated_at: string
}

export type CompanyListResponse = {
  items: Company[]
  page: number
  page_size: number
  total: number
}

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

type ApiRequestInit = Omit<RequestInit, "body"> & {
  body?: unknown
}

export async function apiRequest<T>(path: string, init: ApiRequestInit = {}): Promise<T> {
  const cookieStore = await cookies()
  const cookieHeader = cookieStore.toString()
  const headers = new Headers(init.headers)

  if (cookieHeader) {
    headers.set("cookie", cookieHeader)
  }
  headers.set("x-forwarded-proto", "https")

  let body: BodyInit | undefined
  if (init.body !== undefined) {
    headers.set("content-type", "application/json")
    body = JSON.stringify(init.body)
  }

  const response = await fetch(`${getInternalApiBaseUrl()}${path}`, {
    ...init,
    body,
    cache: init.cache ?? "no-store",
    headers,
  })

  if (!response.ok) {
    let message = "Nao foi possivel processar a solicitacao."
    try {
      const payload = (await response.json()) as { detail?: string }
      if (payload.detail) {
        message = payload.detail
      }
    } catch {
      // Keep the generic message when the API does not return JSON.
    }
    throw new ApiError(message, response.status)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

export async function getTenants(): Promise<Tenant[]> {
  return apiRequest<Tenant[]>("/api/tenants")
}
