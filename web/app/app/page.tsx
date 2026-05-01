import Link from "next/link"
import { redirect } from "next/navigation"
import {
  BarChart3,
  Building2,
  ChevronRight,
  LayoutGrid,
  LogOut,
  Settings,
} from "lucide-react"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { getLogoutUrl, getServerSession } from "@/lib/server/auth"
import { ApiError, getTenants, type Tenant } from "@/lib/server/api"

export const dynamic = "force-dynamic"

function initials(name: string | null, fallback: string): string {
  const source = name ?? fallback
  return source
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("")
}

export default async function AppHubPage() {
  const session = await getServerSession()

  if (!session) {
    redirect("/")
  }

  const displayName = session.name ?? session.preferredUsername ?? "Usuario"
  const logoutUrl = getLogoutUrl("/")
  let tenants: Tenant[] = []
  let tenantsError: string | null = null

  try {
    tenants = await getTenants()
  } catch (error) {
    tenantsError =
      error instanceof ApiError ? error.message : "Nao foi possivel carregar os ambientes."
  }

  return (
    <main className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/95">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <Link href="/app" className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary">
              <LayoutGrid className="h-5 w-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-semibold text-foreground">Ctrl Contábil</span>
          </Link>

          <div className="flex items-center gap-3">
            <Avatar className="h-9 w-9">
              <AvatarFallback className="bg-primary/10 text-sm font-medium text-primary">
                {initials(session.name, session.preferredUsername ?? session.sub)}
              </AvatarFallback>
            </Avatar>
            <div className="hidden text-right sm:block">
              <p className="text-sm font-medium text-foreground">{displayName}</p>
              <p className="text-xs text-muted-foreground">Sessão ativa</p>
            </div>
            <Button asChild variant="ghost" size="icon" aria-label="Sair">
              <a href={logoutUrl}>
                <LogOut className="h-4 w-4" />
              </a>
            </Button>
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="mb-2 text-sm font-medium text-primary">Hub do sistema</p>
            <h1 className="text-2xl font-semibold text-foreground sm:text-3xl">
              Olá, {displayName.split(" ")[0]}.
            </h1>
            <p className="mt-2 max-w-2xl text-muted-foreground">
              Escolha o ambiente de trabalho e acesse os módulos disponíveis.
            </p>
          </div>

          <Button asChild variant="outline">
            <Link href="/app/dashboard">
              <BarChart3 className="h-4 w-4" />
              Dashboard geral
            </Link>
          </Button>
        </div>

        {tenantsError ? (
          <Card className="border-destructive/40">
            <CardContent className="p-6">
              <p className="font-medium text-foreground">Nao foi possivel carregar os ambientes.</p>
              <p className="mt-1 text-sm text-muted-foreground">{tenantsError}</p>
            </CardContent>
          </Card>
        ) : tenants.length === 0 ? (
          <Card>
            <CardContent className="p-6">
              <p className="font-medium text-foreground">Nenhum ambiente disponivel.</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Solicite ao administrador a criação ou liberação de acesso ao seu escritório.
              </p>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
            {tenants.map((tenant) => (
              <Card key={tenant.id} className="border-border">
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <CardTitle className="text-lg">{tenant.display_name}</CardTitle>
                      <CardDescription>{tenant.slug}</CardDescription>
                    </div>
                    <Badge variant="secondary">Ativo</Badge>
                  </div>
                </CardHeader>
                <CardContent className="grid gap-3 sm:grid-cols-2">
                  <Button asChild className="justify-between">
                    <Link href={`/app/tenants/${tenant.id}/empresas`}>
                      <span className="flex items-center gap-2">
                        <Building2 className="h-4 w-4" />
                        Empresas
                      </span>
                      <ChevronRight className="h-4 w-4" />
                    </Link>
                  </Button>
                  <Button asChild variant="outline" className="justify-between">
                    <Link href="/app/dashboard">
                      <span className="flex items-center gap-2">
                        <Settings className="h-4 w-4" />
                        Painel geral
                      </span>
                      <ChevronRight className="h-4 w-4" />
                    </Link>
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </section>
    </main>
  )
}
