"use client";

import { useEffect, useId, useRef, useState } from "react";

type ApexNavLink = { label: string; href: string };
type ApexNavGroup = { id: string; label: string; links: ApexNavLink[] };

export type HubApexNavCopy = {
  solutions_label: string;
  company_label: string;
  main_aria_label: string;
  toggle_label: string;
  toggle_open_aria: string;
  toggle_close_aria: string;
  groups: ApexNavGroup[];
  company_links: ApexNavLink[];
};

type Brand = { brand_name: string; brand_tagline: string };

function isExternal(href: string): boolean {
  return href.startsWith("http://") || href.startsWith("https://");
}

function NavAnchor({
  href,
  label,
  onNavigate,
}: {
  href: string;
  label: string;
  onNavigate?: () => void;
}) {
  const external = isExternal(href);
  return (
    <a
      href={href}
      onClick={() => onNavigate?.()}
      {...(external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
    >
      {label}
    </a>
  );
}

/**
 * Guest apex GNB — grouped Solutions + Company.
 * Classic SiteHeader (#about / flat service row) stays on /home and other marketing pages.
 */
export function HubApexHeader({ nav, brand }: { nav: HubApexNavCopy; brand: Brand }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [openGroup, setOpenGroup] = useState<string | null>(null);
  const rootRef = useRef<HTMLElement | null>(null);
  const solutionsId = useId();

  useEffect(() => {
    if (!openGroup) return;
    const onPointer = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpenGroup(null);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpenGroup(null);
        setMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", onPointer);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onPointer);
      document.removeEventListener("keydown", onKey);
    };
  }, [openGroup]);

  const closeAll = () => {
    setMenuOpen(false);
    setOpenGroup(null);
  };

  return (
    <header className="site-header hub-apex-header" ref={rootRef}>
      <div className="header-inner">
        <a className="brand hub-apex-brand-link" href="/">
          <span className="hub-apex-brand-name">{brand.brand_name}</span>
          <span className="hub-apex-brand-tag">{brand.brand_tagline}</span>
        </a>
        <button
          type="button"
          className="nav-toggle"
          aria-label={menuOpen ? nav.toggle_close_aria : nav.toggle_open_aria}
          aria-expanded={menuOpen}
          aria-controls="hub-apex-nav"
          onClick={() => {
            setMenuOpen((v) => !v);
            setOpenGroup(null);
          }}
        >
          {nav.toggle_label}
        </button>
        <nav
          className={`nav-main hub-apex-nav${menuOpen ? " is-open" : ""}`}
          id="hub-apex-nav"
          aria-label={nav.main_aria_label}
        >
          <div className="hub-apex-nav-cluster">
            <span className="nav-group-label">{nav.solutions_label}</span>
            <ul className="hub-apex-nav-groups">
              {nav.groups.map((group) => {
                const panelId = `${solutionsId}-${group.id}`;
                const expanded = openGroup === group.id;
                return (
                  <li key={group.id} className="hub-apex-nav-item">
                    <button
                      type="button"
                      className="hub-apex-nav-trigger"
                      aria-expanded={expanded || menuOpen}
                      aria-controls={panelId}
                      onClick={() => setOpenGroup((cur) => (cur === group.id ? null : group.id))}
                    >
                      {group.label}
                    </button>
                    <ul
                      id={panelId}
                      className={`hub-apex-nav-panel${expanded ? " is-open" : ""}`}
                    >
                      {group.links.map((link) => (
                        <li key={`${group.id}-${link.href}`}>
                          <NavAnchor href={link.href} label={link.label} onNavigate={closeAll} />
                        </li>
                      ))}
                    </ul>
                  </li>
                );
              })}
            </ul>
          </div>
          <div className="hub-apex-nav-cluster">
            <span className="nav-group-label">{nav.company_label}</span>
            <ul className="hub-apex-nav-flat">
              {nav.company_links.map((link) => (
                <li key={link.href}>
                  <NavAnchor href={link.href} label={link.label} onNavigate={closeAll} />
                </li>
              ))}
            </ul>
          </div>
        </nav>
      </div>
    </header>
  );
}
