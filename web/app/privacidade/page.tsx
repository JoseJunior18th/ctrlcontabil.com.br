import Link from "next/link"
import { ArrowLeft, ShieldCheck } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

const sections = [
  {
    title: "Dados tratados",
    text: "A plataforma pode tratar dados cadastrais, dados de autenticação, informações contábeis e registros técnicos necessários para operar o serviço.",
  },
  {
    title: "Finalidade",
    text: "Os dados são usados para autenticação, execução das funcionalidades contratadas, suporte técnico, segurança da aplicação e cumprimento de obrigações legais.",
  },
  {
    title: "Segurança",
    text: "São adotados controles de acesso, cookies de sessão protegidos e medidas técnicas para reduzir riscos de acesso indevido, perda ou alteração não autorizada.",
  },
  {
    title: "Contato",
    text: "Dúvidas sobre privacidade ou solicitações relacionadas a dados pessoais podem ser encaminhadas para suporte@josejunior.eng.br.",
  },
]

export default function PrivacidadePage() {
  const currentYear = new Date().getFullYear()

  return (
    <main className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/95">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link href="/dashboard" className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center">
              <ShieldCheck className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-semibold text-foreground">Ctrl Contábil</span>
          </Link>
          <Button asChild variant="ghost" size="sm">
            <Link href="/dashboard">
              <ArrowLeft className="w-4 h-4" />
              Voltar
            </Link>
          </Button>
        </div>
      </header>

      <section className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="mb-8">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground mb-2">Política de Privacidade</h1>
          <p className="text-muted-foreground">
            Informações sobre o tratamento de dados no ambiente Ctrl Contábil.
          </p>
        </div>

        <Card className="border-border">
          <CardHeader>
            <CardTitle>Privacidade e proteção de dados</CardTitle>
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
            <Link href="/termos-de-uso" className="text-sm text-muted-foreground hover:text-primary transition-colors">
              Termos de Uso
            </Link>
          </div>
        </div>
      </footer>
    </main>
  )
}
