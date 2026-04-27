"use client"

import Link from "next/link"

import { Button } from "@/components/ui/button"

export default function GlobalError() {
  return (
    <main className="min-h-screen bg-background flex items-center justify-center px-6">
      <div className="w-full max-w-md text-center">
        <h1 className="text-2xl font-semibold text-foreground">Nao foi possivel continuar</h1>
        <p className="mt-3 text-sm text-muted-foreground">
          A requisicao foi interrompida por seguranca. Tente novamente em instantes.
        </p>
        <Button asChild className="mt-6">
          <Link href="/">Voltar ao login</Link>
        </Button>
      </div>
    </main>
  )
}
