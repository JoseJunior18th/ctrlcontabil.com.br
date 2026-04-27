import Link from "next/link"

import { Button } from "@/components/ui/button"

const messages: Record<string, string> = {
  invalid_state_cookie: "O acesso expirou ou foi iniciado em outra aba. Tente entrar novamente.",
  missing_callback_params: "O provedor nao retornou os dados esperados para concluir o acesso.",
  missing_state_cookie: "O cookie temporario de autenticacao nao foi encontrado. Tente entrar novamente.",
  provider_denied: "O Authentik recusou o acesso para este usuario ou aplicacao.",
  provider_error: "O Authentik retornou um erro durante a autenticacao.",
  state_mismatch: "A validacao de seguranca do login nao conferiu. Tente entrar novamente.",
  token_validation_failed: "Nao foi possivel validar o token retornado pelo Authentik."
}

type AuthErrorPageProps = {
  searchParams: Promise<{ reason?: string }>
}

export default async function AuthErrorPage({ searchParams }: AuthErrorPageProps) {
  const { reason } = await searchParams
  const message =
    reason && messages[reason]
      ? messages[reason]
      : "Nao foi possivel validar a sessao. Inicie o acesso novamente pelo provedor corporativo."

  return (
    <main className="min-h-screen bg-background flex items-center justify-center px-6">
      <div className="w-full max-w-md text-center">
        <h1 className="text-2xl font-semibold text-foreground">Acesso nao autorizado</h1>
        <p className="mt-3 text-sm text-muted-foreground">
          {message}
        </p>
        <Button asChild className="mt-6">
          <Link href="/">Entrar novamente</Link>
        </Button>
      </div>
    </main>
  )
}
