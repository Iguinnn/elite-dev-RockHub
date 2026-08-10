"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentProps, ReactNode } from "react";

import estilos from "./Masthead.module.css";

type NavLinkProps = {
  href: ComponentProps<typeof Link>["href"];
  children: ReactNode;
};

/**
 * Item da navegação do masthead. Existe como componente de cliente por um
 * motivo só: `usePathname()` para marcar o item ativo. Mantê-lo separado
 * deixa o `Masthead` inteiro no servidor.
 */
export default function NavLink({ href, children }: NavLinkProps) {
  const caminho = usePathname();
  const ativo = caminho === href;

  return (
    <Link
      href={href}
      className={ativo ? `${estilos.navLink} ${estilos.ativo}` : estilos.navLink}
      aria-current={ativo ? "page" : undefined}
    >
      {children}
    </Link>
  );
}
