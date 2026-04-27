import Image from "next/image"
import Link from "next/link"
import { Button } from "@/components/ui/button"
import { getLoginUrl } from "@/lib/server/auth"

export const dynamic = "force-dynamic"

export default function LoginPage() {
  const loginUrl = getLoginUrl("/dashboard")

  return (
    <main className="min-h-screen flex">
      {/* Lado Esquerdo - Imagem */}
      <div className="hidden lg:flex lg:w-1/2 xl:w-3/5 relative bg-accent">
        <Image
          src="/accounting-hero.jpg"
          alt="Ambiente de trabalho contábil profissional"
          fill
          className="object-cover"
          priority
        />
        {/* Overlay com gradiente */}
        <div className="absolute inset-0 bg-gradient-to-r from-primary/20 to-transparent" />
        
        {/* Conteúdo sobre a imagem */}
        <div className="absolute inset-0 flex flex-col justify-between p-12">
          {/* Logo no topo */}
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 bg-card/95 backdrop-blur-sm rounded-xl flex items-center justify-center shadow-lg">
              <svg
                className="w-6 h-6 text-primary"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                />
              </svg>
            </div>
            <span className="text-xl font-semibold text-card drop-shadow-lg">
              Ctrl Contábil
            </span>
          </div>

          {/* Texto promocional */}
          <div className="max-w-md">
            <div className="bg-card/95 backdrop-blur-sm rounded-2xl p-8 shadow-xl">
              <h2 className="text-2xl font-semibold text-foreground mb-3 text-balance">
                Gestão contábil simplificada para o seu negócio
              </h2>
              <p className="text-muted-foreground leading-relaxed">
                Tenha controle total das suas finanças com relatórios precisos, 
                gestão fiscal automatizada e suporte especializado.
              </p>
              <div className="flex items-center gap-6 mt-6 pt-6 border-t border-border">
                <div>
                  <p className="text-2xl font-bold text-primary">500+</p>
                  <p className="text-sm text-muted-foreground">Empresas ativas</p>
                </div>
                <div className="w-px h-10 bg-border" />
                <div>
                  <p className="text-2xl font-bold text-primary">99.9%</p>
                  <p className="text-sm text-muted-foreground">Uptime garantido</p>
                </div>
                <div className="w-px h-10 bg-border" />
                <div>
                  <p className="text-2xl font-bold text-primary">24/7</p>
                  <p className="text-sm text-muted-foreground">Suporte técnico</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Lado Direito - Formulário */}
      <div className="w-full lg:w-1/2 xl:w-2/5 flex items-center justify-center p-6 sm:p-8 lg:p-12 bg-background">
        <div className="w-full max-w-md">
          {/* Logo mobile */}
          <div className="lg:hidden flex items-center justify-center gap-3 mb-10">
            <div className="w-11 h-11 bg-primary rounded-xl flex items-center justify-center">
              <svg
                className="w-6 h-6 text-primary-foreground"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
                strokeWidth={2}
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 7h6m0 10v-3m-3 3h.01M9 17h.01M9 14h.01M12 14h.01M15 11h.01M12 11h.01M9 11h.01M7 21h10a2 2 0 002-2V5a2 2 0 00-2-2H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                />
              </svg>
            </div>
            <span className="text-2xl font-semibold text-foreground">
              Ctrl Contábil
            </span>
          </div>

          {/* Título */}
          <div className="mb-8">
            <h1 className="text-2xl sm:text-3xl font-semibold text-foreground mb-2">
              Bem-vindo de volta
            </h1>
            <p className="text-muted-foreground">
              Acesse com sua identidade corporativa
            </p>
          </div>

          {/* Autenticacao */}
          <div className="bg-card rounded-2xl border border-border p-6 sm:p-8 shadow-sm">
            <Button asChild className="w-full h-12 font-medium text-base">
              <Link href={loginUrl}>Entrar com Authentik</Link>
            </Button>

            <div className="mt-6 pt-6 border-t border-border">
              <p className="text-center text-sm text-muted-foreground">
                Ainda não tem uma conta?{" "}
                <a
                  href="https://wa.me/5537996652670"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary hover:text-primary/80 font-semibold transition-colors"
                >
                  Solicite acesso
                </a>
              </p>
            </div>
          </div>

          {/* Footer */}
          <div className="mt-8 text-center">
            <p className="text-xs text-muted-foreground">
              Ao entrar, você concorda com nossos{" "}
              <button type="button" className="text-primary hover:underline font-medium">
                Termos de Uso
              </button>{" "}
              e{" "}
              <button type="button" className="text-primary hover:underline font-medium">
                Política de Privacidade
              </button>
            </p>
          </div>
        </div>
      </div>
    </main>
  )
}
