"use client";

import { useState } from "react";

type Nav = { about: string; safety: string; workflow: string; contact: string };
type Brand = { brand_name: string; brand_tagline: string };

export function SiteHeader({ nav, brand }: { nav: Nav; brand: Brand }) {
  const [open, setOpen] = useState(false);

  return (
    <header className="site-header">
      <div className="header-inner">
        <a className="brand" href="/">
          {brand.brand_name} <span>{brand.brand_tagline}</span>
        </a>
        <button
          type="button"
          className="nav-toggle"
          aria-expanded={open}
          aria-controls="site-nav"
          id="nav-toggle"
          onClick={() => setOpen((v) => !v)}
        >
          메뉴
        </button>
        <nav className={`nav-main${open ? " is-open" : ""}`} id="site-nav" aria-label="주요">
          <a href="#about" onClick={() => setOpen(false)}>
            {nav.about}
          </a>
          <a href="#safety" onClick={() => setOpen(false)}>
            {nav.safety}
          </a>
          <a href="#workflow" onClick={() => setOpen(false)}>
            {nav.workflow}
          </a>
          <a href="#contact" onClick={() => setOpen(false)}>
            {nav.contact}
          </a>
        </nav>
      </div>
    </header>
  );
}
