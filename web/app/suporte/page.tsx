import Link from "next/link"
import { ArrowLeft, Mail, MessageCircle } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

const whatsappUrl = "https://wa.me/5537996652670"
const supportEmail = "suporte@josejunior.eng.br"

export default function SuportePage() {
  const currentYear = new Date().getFullYear()

  return (
    <main className="min-h-screen bg-background">
      <header className="border-b border-border bg-card/95">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <Link href="/app" className="flex items-center gap-3">
            <div className="w-10 h-10 bg-primary rounded-xl flex items-center justify-center">
              <MessageCircle className="w-5 h-5 text-primary-foreground" />
            </div>
            <span className="text-xl font-semibold text-foreground">Ctrl Contábil</span>
          </Link>
          <Button asChild variant="ghost" size="sm">
            <Link href="/app">
              <ArrowLeft className="w-4 h-4" />
              Voltar
            </Link>
          </Button>
        </div>
      </header>

      <section className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
        <div className="mb-8">
          <h1 className="text-2xl sm:text-3xl font-semibold text-foreground mb-2">Suporte</h1>
          <p className="text-muted-foreground">
            Escolha o canal mais adequado para falar com a equipe de atendimento.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <Card className="border-border">
            <CardHeader>
              <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center text-primary mb-3">
                <Mail className="w-6 h-6" />
              </div>
              <CardTitle>E-mail</CardTitle>
              <CardDescription>
                Envie sua solicitação com o máximo de detalhes para análise.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild className="w-full">
                <a href={`mailto:${supportEmail}`}>{supportEmail}</a>
              </Button>
            </CardContent>
          </Card>

          <Card className="border-border">
            <CardHeader>
              <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center text-primary mb-3">
                <MessageCircle className="w-6 h-6" />
              </div>
              <CardTitle>WhatsApp</CardTitle>
              <CardDescription>
                Use o contato atual para conversas rápidas e acompanhamento.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild variant="outline" className="w-full">
                <a href={whatsappUrl} target="_blank" rel="noopener noreferrer">
                  Abrir WhatsApp
                </a>
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>

      <footer className="border-t border-border mt-12">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-6 flex flex-col sm:flex-row items-center justify-between gap-4">
          <p className="text-sm text-muted-foreground">
            {currentYear} Ctrl Contábil. Todos os direitos reservados.
          </p>
          <div className="flex items-center gap-6">
            <Link href="/termos-de-uso?return_to=/suporte" className="text-sm text-muted-foreground hover:text-primary transition-colors">
              Termos de Uso
            </Link>
            <Link href="/privacidade?return_to=/suporte" className="text-sm text-muted-foreground hover:text-primary transition-colors">
              Privacidade
            </Link>
          </div>
        </div>
      </footer>
    </main>
  )
}
