import Link from "next/link"

import { Button } from "@/components/ui/button"

export default function AuthErrorPage() {
  return (
    <main className="min-h-screen bg-background flex items-center justify-center px-6">
      <div className="w-full max-w-md text-center">
        <h1 className="text-2xl font-semibold text-foreground">Acesso nao autorizado</h1>
        <p className="mt-3 text-sm text-muted-foreground">
          Nao foi possivel validar a sessao. Inicie o acesso novamente pelo provedor corporativo.
        </p>
        <Button asChild className="mt-6">
          <Link href="/">Entrar novamente</Link>
        </Button>
      </div>
    </main>
  )
}
