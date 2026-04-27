import { NextRequest, NextResponse } from "next/server"

const apiBaseUrl =
  process.env.API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
const apiInternalBaseUrl = process.env.API_INTERNAL_BASE_URL ?? apiBaseUrl
const sessionCookieName = process.env.SESSION_COOKIE_NAME ?? "__Host-ctrl_session"

function buildLoginRedirect(request: NextRequest): NextResponse {
  const loginUrl = new URL("/auth/login", apiBaseUrl)
  loginUrl.searchParams.set("return_to", request.nextUrl.href)
  return NextResponse.redirect(loginUrl)
}

export async function middleware(request: NextRequest) {
  const sessionCookie = request.cookies.get(sessionCookieName)

  if (!sessionCookie?.value) {
    return buildLoginRedirect(request)
  }

  try {
    const sessionUrl = new URL("/auth/session", apiInternalBaseUrl)
    const response = await fetch(sessionUrl, {
      cache: "no-store",
      headers: {
        cookie: request.headers.get("cookie") ?? ""
      }
    })

    if (response.ok) {
      return NextResponse.next()
    }
  } catch {
    // Fail closed: protected UI must not render when the auth boundary is unavailable.
  }

  const response = buildLoginRedirect(request)
  response.cookies.delete(sessionCookieName)
  return response
}

export const config = {
  matcher: ["/dashboard/:path*"]
}
