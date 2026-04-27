import "server-only"

import { cookies } from "next/headers"

export type SessionUser = {
  sub: string
  email: string | null
  groups: string[]
  name: string | null
  preferredUsername: string | null
  roles: string[]
}

type SessionResponse = {
  authenticated: true
  user: SessionUser
}

export function getApiBaseUrl(): string {
  return (
    process.env.API_BASE_URL ??
    process.env.NEXT_PUBLIC_API_BASE_URL ??
    "http://localhost:8000"
  ).replace(/\/+$/, "")
}

export function getInternalApiBaseUrl(): string {
  return (process.env.API_INTERNAL_BASE_URL ?? getApiBaseUrl()).replace(/\/+$/, "")
}

export function getLoginUrl(returnTo = "/dashboard"): string {
  const loginUrl = new URL("/auth/login", getApiBaseUrl())
  loginUrl.searchParams.set("return_to", returnTo)
  return loginUrl.toString()
}

export function getLogoutUrl(returnTo = "/"): string {
  const logoutUrl = new URL("/auth/logout", getApiBaseUrl())
  logoutUrl.searchParams.set("return_to", returnTo)
  return logoutUrl.toString()
}

export async function getServerSession(): Promise<SessionUser | null> {
  const cookieStore = await cookies()
  const cookieHeader = cookieStore.toString()

  if (!cookieHeader) {
    return null
  }

  try {
    const response = await fetch(`${getInternalApiBaseUrl()}/auth/session`, {
      cache: "no-store",
      headers: {
        cookie: cookieHeader
      }
    })

    if (!response.ok) {
      return null
    }

    const payload = (await response.json()) as SessionResponse
    return payload.user
  } catch {
    return null
  }
}
