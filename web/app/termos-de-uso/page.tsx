import Link from "next/link"
import { ArrowLeft, FileText } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const sections = [
  {
    title: "Uso da plataforma",
    text: "O Ctrl Contábil deve ser usado apenas por usuários autorizados e para fins relacionados à gestão contábil, fiscal e administrativa do cliente.",
  },
  {
    title: "Responsabilidades do usuário",
    text: "Cada usuário é responsável por manter suas credenciais protegidas, revisar as informações enviadas e comunicar qualquer uso indevido ou inconsistência identificada.",
  },
  {
    title: "Disponibilidade",
    text: "A plataforma pode passar por manutenções, atualizações ou indisponibilidades pontuais necessárias para segurança, estabilidade e evolução do serviço.",
  },
  {
    title: "Suporte",
    text: "As solicitações de suporte devem ser encaminhadas pelos canais oficiais informados na página de suporte.",
  },
]

type LegalPageProps = {
  searchParams?: Promise<{
    return_to?: string | string[]
  }>
}

function resolveReturnHref(returnTo: string | string[] | undefined): string {
  const value = Array.isArray(returnTo) ? returnTo[0] : returnTo
  return value === "/app" || value === "/app/dashboard" || value === "/suporte" ? value : "/"
}

export default async function TermosDeUsoPage({ searchParams }: LegalPageProps) {
  const params = await searchParams
  const returnHref = resolveReturnHref(params?.return_to)
  const currentYear = new Date().getFullYear()

  return (
    <main className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/95">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link href="/app" className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center">
              <FileText className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-semibold text-foreground">Ctrl Contábil</span>
          </Link>
          <Button asChild variant="ghost" size="sm">
            <Link href={returnHref}>
              <ArrowLeft className="w-4 h-4" />
              Voltar
            </Link>
          </Button>
        </div>
      </header>

      <section className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="mb-8">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground mb-2">Termos de Uso</h1>
          <p className="text-muted-foreground">
            Condições gerais para acesso e utilização do ambiente Ctrl Contábil.
          </p>
        </div>

        <Card className="border-border">
          <CardHeader>
            <CardTitle>Condições de utilização</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {sections.map((section) => (
              <div key={section.title}>
                <h2 className="text-base font-semibold text-foreground mb-2">{section.title}</h2>
                <p className="text-sm leading-6 text-muted-foreground">{section.text}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </section>

      <footer className="border-t border-border mt-12">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            {currentYear} Ctrl Contábil. Todos os direitos reservados.
          </p>
          <div className="flex items-center gap-6">
            <Link href="/suporte" className="text-sm text-muted-foreground hover:text-primary transition-colors">
              Suporte
            </Link>
            <Link href="/privacidade" className="text-sm text-muted-foreground hover:text-primary transition-colors">
              Privacidade
            </Link>
          </div>
        </div>
      </footer>
    </main>
  )
}
