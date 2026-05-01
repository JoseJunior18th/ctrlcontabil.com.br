import Link from "next/link"
import { redirect } from "next/navigation"
import { revalidatePath } from "next/cache"
import {
  ArrowLeft,
  Building2,
  CheckCircle2,
  Pencil,
  Plus,
  RotateCcw,
  Search,
  XCircle,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Separator } from "@/components/ui/separator"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { getServerSession } from "@/lib/server/auth"
import {
  ApiError,
  apiRequest,
  getTenants,
  type Company,
  type CompanyListResponse,
  type CompanyStatus,
  type TaxRegime,
} from "@/lib/server/api"

export const dynamic = "force-dynamic"

const taxRegimeLabels: Record<TaxRegime, string> = {
  simples_nacional: "Simples Nacional",
  lucro_presumido: "Lucro Presumido",
  lucro_real: "Lucro Real",
  mei: "MEI",
  isento: "Isento",
  outro: "Outro",
}

const statusLabels: Record<CompanyStatus, string> = {
  active: "Ativa",
  inactive: "Inativa",
}

type CompaniesPageProps = {
  params: Promise<{ tenantId: string }>
  searchParams?: Promise<{
    page?: string | string[]
    q?: string | string[]
    status?: string | string[]
  }>
}

type CompanyPayload = {
  legal_name: string
  trade_name: string | null
  tax_id: string
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
}

function single(value: string | string[] | undefined): string | undefined {
  return Array.isArray(value) ? value[0] : value
}

function textValue(formData: FormData, key: keyof CompanyPayload): string | null {
  const value = formData.get(key)
  if (typeof value !== "string") {
    return null
  }
  const trimmed = value.trim()
  return trimmed ? trimmed : null
}

function companyPayloadFromForm(formData: FormData): CompanyPayload {
  const taxRegime = textValue(formData, "tax_regime")
  return {
    legal_name: textValue(formData, "legal_name") ?? "",
    trade_name: textValue(formData, "trade_name"),
    tax_id: textValue(formData, "tax_id") ?? "",
    tax_regime: taxRegime as TaxRegime | null,
    state_registration: textValue(formData, "state_registration"),
    municipal_registration: textValue(formData, "municipal_registration"),
    email: textValue(formData, "email"),
    phone: textValue(formData, "phone"),
    postal_code: textValue(formData, "postal_code"),
    street: textValue(formData, "street"),
    number: textValue(formData, "number"),
    complement: textValue(formData, "complement"),
    district: textValue(formData, "district"),
    city: textValue(formData, "city"),
    state: textValue(formData, "state")?.toUpperCase() ?? null,
    country: textValue(formData, "country")?.toUpperCase() ?? "BR",
  }
}

function requiredFormValue(formData: FormData, key: string): string {
  const value = formData.get(key)
  if (typeof value !== "string" || !value.trim()) {
    throw new Error(`Campo obrigatorio ausente: ${key}`)
  }
  return value.trim()
}

async function createCompanyAction(formData: FormData) {
  "use server"
  const tenantId = requiredFormValue(formData, "tenant_id")
  await apiRequest<Company>(`/api/tenants/${tenantId}/companies`, {
    method: "POST",
    body: companyPayloadFromForm(formData),
  })
  revalidatePath(`/app/tenants/${tenantId}/empresas`)
  redirect(`/app/tenants/${tenantId}/empresas`)
}

async function updateCompanyAction(formData: FormData) {
  "use server"
  const tenantId = requiredFormValue(formData, "tenant_id")
  const companyId = requiredFormValue(formData, "company_id")
  await apiRequest<Company>(`/api/tenants/${tenantId}/companies/${companyId}`, {
    method: "PATCH",
    body: companyPayloadFromForm(formData),
  })
  revalidatePath(`/app/tenants/${tenantId}/empresas`)
  redirect(`/app/tenants/${tenantId}/empresas`)
}

async function setCompanyStatusAction(formData: FormData) {
  "use server"
  const tenantId = requiredFormValue(formData, "tenant_id")
  const companyId = requiredFormValue(formData, "company_id")
  const action = requiredFormValue(formData, "status_action")
  const endpoint = action === "reactivate" ? "reactivate" : "deactivate"

  await apiRequest<Company>(`/api/tenants/${tenantId}/companies/${companyId}/${endpoint}`, {
    method: "POST",
  })
  revalidatePath(`/app/tenants/${tenantId}/empresas`)
  redirect(`/app/tenants/${tenantId}/empresas`)
}

function dateLabel(value: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(new Date(value))
}

function Field({
  defaultValue,
  label,
  name,
  required = false,
}: {
  defaultValue?: string | null
  label: string
  name: keyof CompanyPayload
  required?: boolean
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={name}>{label}</Label>
      <Input id={name} name={name} defaultValue={defaultValue ?? ""} required={required} />
    </div>
  )
}

function CompanyForm({
  action,
  company,
  submitLabel,
  tenantId,
}: {
  action: (formData: FormData) => Promise<void>
  company?: Company
  submitLabel: string
  tenantId: string
}) {
  return (
    <form action={action} className="space-y-6">
      <input type="hidden" name="tenant_id" value={tenantId} />
      {company ? <input type="hidden" name="company_id" value={company.id} /> : null}

      <div>
        <h3 className="mb-3 text-sm font-medium text-foreground">Identificacao</h3>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <Field
            name="legal_name"
            label="Razao social"
            defaultValue={company?.legal_name}
            required
          />
          <Field name="trade_name" label="Nome fantasia" defaultValue={company?.trade_name} />
          <Field name="tax_id" label="CNPJ/CPF" defaultValue={company?.tax_id} required />
        </div>
      </div>

      <Separator />

      <div>
        <h3 className="mb-3 text-sm font-medium text-foreground">Fiscal</h3>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="space-y-2">
            <Label htmlFor={`tax_regime_${company?.id ?? "new"}`}>Regime tributario</Label>
            <select
              id={`tax_regime_${company?.id ?? "new"}`}
              name="tax_regime"
              defaultValue={company?.tax_regime ?? ""}
              className="h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
            >
              <option value="">Nao informado</option>
              {Object.entries(taxRegimeLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <Field
            name="state_registration"
            label="Inscricao estadual"
            defaultValue={company?.state_registration}
          />
          <Field
            name="municipal_registration"
            label="Inscricao municipal"
            defaultValue={company?.municipal_registration}
          />
        </div>
      </div>

      <Separator />

      <div>
        <h3 className="mb-3 text-sm font-medium text-foreground">Contato</h3>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <Field name="email" label="E-mail" defaultValue={company?.email} />
          <Field name="phone" label="Telefone" defaultValue={company?.phone} />
        </div>
      </div>

      <Separator />

      <div>
        <h3 className="mb-3 text-sm font-medium text-foreground">Endereco</h3>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-6">
          <Field name="postal_code" label="CEP" defaultValue={company?.postal_code} />
          <div className="md:col-span-3">
            <Field name="street" label="Logradouro" defaultValue={company?.street} />
          </div>
          <Field name="number" label="Numero" defaultValue={company?.number} />
          <Field name="complement" label="Complemento" defaultValue={company?.complement} />
          <Field name="district" label="Bairro" defaultValue={company?.district} />
          <Field name="city" label="Cidade" defaultValue={company?.city} />
          <Field name="state" label="UF" defaultValue={company?.state} />
          <Field name="country" label="Pais" defaultValue={company?.country ?? "BR"} />
        </div>
      </div>

      <div className="flex justify-end">
        <Button type="submit">
          <CheckCircle2 className="h-4 w-4" />
          {submitLabel}
        </Button>
      </div>
    </form>
  )
}

export default async function EmpresasPage({ params, searchParams }: CompaniesPageProps) {
  const session = await getServerSession()
  if (!session) {
    redirect("/")
  }

  const { tenantId } = await params
  const filters = (await searchParams) ?? {}
  const q = single(filters.q) ?? ""
  const status = single(filters.status) ?? "active"
  const page = Number(single(filters.page) ?? "1")
  const query = new URLSearchParams({
    page: Number.isFinite(page) && page > 0 ? String(page) : "1",
    page_size: "20",
    status,
  })
  if (q) {
    query.set("q", q)
  }

  const tenants = await getTenants()
  const tenant = tenants.find((item) => item.id === tenantId)
  if (!tenant) {
    redirect("/app")
  }

  let companies: CompanyListResponse = { items: [], page: 1, page_size: 20, total: 0 }
  let errorMessage: string | null = null
  try {
    companies = await apiRequest<CompanyListResponse>(
      `/api/tenants/${tenantId}/companies?${query.toString()}`,
    )
  } catch (error) {
    errorMessage =
      error instanceof ApiError ? error.message : "Nao foi possivel carregar as empresas."
  }

  const totalPages = Math.max(1, Math.ceil(companies.total / companies.page_size))
  const basePath = `/app/tenants/${tenantId}/empresas`

  return (
    <main className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/95">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <Button asChild variant="ghost" size="icon" aria-label="Voltar ao hub">
              <Link href="/app">
                <ArrowLeft className="h-4 w-4" />
              </Link>
            </Button>
            <div>
              <div className="text-xs text-muted-foreground">Hub / {tenant.display_name}</div>
              <h1 className="text-lg font-semibold text-foreground">Empresas</h1>
            </div>
          </div>
          <Button asChild variant="outline">
            <Link href="/app/dashboard">Dashboard geral</Link>
          </Button>
        </div>
      </header>

      <section className="mx-auto max-w-7xl space-y-6 px-4 py-8 sm:px-6 lg:px-8">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm font-medium text-primary">{tenant.slug}</p>
            <h2 className="mt-1 text-2xl font-semibold text-foreground">
              Cadastro fiscal de empresas
            </h2>
            <p className="mt-2 max-w-2xl text-muted-foreground">
              Consulte, cadastre e mantenha os dados fiscais essenciais das empresas deste
              ambiente.
            </p>
          </div>
          <Badge variant="secondary">{companies.total} registros</Badge>
        </div>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Plus className="h-5 w-5 text-primary" />
              <div>
                <CardTitle>Nova empresa</CardTitle>
                <CardDescription>Preencha os dados principais para iniciar o cadastro.</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <CompanyForm
              action={createCompanyAction}
              tenantId={tenantId}
              submitLabel="Cadastrar empresa"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <CardTitle>Empresas cadastradas</CardTitle>
                <CardDescription>Use busca e status para refinar a listagem.</CardDescription>
              </div>
              <form className="flex flex-col gap-2 sm:flex-row" action={basePath}>
                <div className="relative">
                  <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    name="q"
                    defaultValue={q}
                    placeholder="Buscar por nome, CNPJ ou e-mail"
                    className="pl-9 sm:w-72"
                  />
                </div>
                <select
                  name="status"
                  defaultValue={status}
                  className="h-10 rounded-md border border-input bg-background px-3 text-sm"
                >
                  <option value="active">Ativas</option>
                  <option value="inactive">Inativas</option>
                  <option value="all">Todas</option>
                </select>
                <Button type="submit">Filtrar</Button>
              </form>
            </div>
          </CardHeader>
          <CardContent>
            {errorMessage ? (
              <div className="rounded-md border border-destructive/40 p-4">
                <p className="font-medium text-foreground">Erro ao carregar empresas.</p>
                <p className="mt-1 text-sm text-muted-foreground">{errorMessage}</p>
              </div>
            ) : companies.items.length === 0 ? (
              <div className="rounded-md border border-dashed p-8 text-center">
                <Building2 className="mx-auto h-8 w-8 text-muted-foreground" />
                <p className="mt-3 font-medium text-foreground">Nenhuma empresa encontrada.</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Cadastre a primeira empresa ou ajuste os filtros da busca.
                </p>
              </div>
            ) : (
              <div className="space-y-4">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Empresa</TableHead>
                      <TableHead>CNPJ/CPF</TableHead>
                      <TableHead>Regime</TableHead>
                      <TableHead>Contato</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Atualizada</TableHead>
                      <TableHead className="text-right">Acoes</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {companies.items.map((company) => (
                      <TableRow key={company.id}>
                        <TableCell>
                          <div className="font-medium text-foreground">{company.legal_name}</div>
                          <div className="text-xs text-muted-foreground">
                            {company.trade_name ?? "Sem nome fantasia"}
                          </div>
                        </TableCell>
                        <TableCell>{company.tax_id}</TableCell>
                        <TableCell>
                          {company.tax_regime ? taxRegimeLabels[company.tax_regime] : "Nao informado"}
                        </TableCell>
                        <TableCell>{company.email ?? company.phone ?? "Nao informado"}</TableCell>
                        <TableCell>
                          <Badge variant={company.status === "active" ? "default" : "secondary"}>
                            {statusLabels[company.status]}
                          </Badge>
                        </TableCell>
                        <TableCell>{dateLabel(company.updated_at)}</TableCell>
                        <TableCell className="text-right">
                          <div className="flex justify-end gap-2">
                            <details className="group text-left">
                              <summary className="inline-flex h-9 cursor-pointer items-center gap-2 rounded-md border border-input px-3 text-sm font-medium">
                                <Pencil className="h-4 w-4" />
                                Editar
                              </summary>
                              <div className="mt-2 w-[min(86vw,920px)] rounded-md border bg-card p-4 shadow-lg">
                                <CompanyForm
                                  action={updateCompanyAction}
                                  tenantId={tenantId}
                                  company={company}
                                  submitLabel="Salvar alteracoes"
                                />
                              </div>
                            </details>
                            <form action={setCompanyStatusAction}>
                              <input type="hidden" name="tenant_id" value={tenantId} />
                              <input type="hidden" name="company_id" value={company.id} />
                              <input
                                type="hidden"
                                name="status_action"
                                value={company.status === "active" ? "deactivate" : "reactivate"}
                              />
                              <Button
                                type="submit"
                                variant="outline"
                                size="sm"
                                className={
                                  company.status === "active"
                                    ? "text-destructive"
                                    : "text-primary"
                                }
                              >
                                {company.status === "active" ? (
                                  <XCircle className="h-4 w-4" />
                                ) : (
                                  <RotateCcw className="h-4 w-4" />
                                )}
                                {company.status === "active" ? "Inativar" : "Reativar"}
                              </Button>
                            </form>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                <div className="flex items-center justify-between text-sm text-muted-foreground">
                  <span>
                    Pagina {companies.page} de {totalPages}
                  </span>
                  <div className="flex gap-2">
                    {companies.page <= 1 ? (
                      <Button variant="outline" size="sm" disabled>
                        Anterior
                      </Button>
                    ) : (
                      <Button asChild variant="outline" size="sm">
                        <Link
                          href={`${basePath}?${new URLSearchParams({
                            q,
                            status,
                            page: String(companies.page - 1),
                          }).toString()}`}
                        >
                          Anterior
                        </Link>
                      </Button>
                    )}
                    {companies.page >= totalPages ? (
                      <Button variant="outline" size="sm" disabled>
                        Proxima
                      </Button>
                    ) : (
                      <Button asChild variant="outline" size="sm">
                        <Link
                          href={`${basePath}?${new URLSearchParams({
                            q,
                            status,
                            page: String(companies.page + 1),
                          }).toString()}`}
                        >
                          Proxima
                        </Link>
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </section>
    </main>
  )
}
