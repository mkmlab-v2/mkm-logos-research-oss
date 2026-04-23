"use client";

import { useState } from "react";

type Nav = {
  service_group: string;
  service_consumer: string;
  service_clinician: string;
  service_reception: string;
  about_group: string;
  about: string;
  safety: string;
  workflow: string;
  contact: string;
};
type Brand = { brand_name: string; brand_tagline: string };
type Links = { consumer: string; clinician: string; reception: string; contact: string };

export function SiteHeader({ nav, brand, links }: { nav: Nav; brand: Brand; links: Links }) {
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
          aria-label={open ? "메뉴 닫기" : "메뉴 열기"}
          aria-expanded={open}
          aria-controls="site-nav"
          id="nav-toggle"
          onClick={() => setOpen((v) => !v)}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setOpen(false);
            }
          }}
        >
          메뉴
        </button>
        <nav
          className={`nav-main${open ? " is-open" : ""}`}
          id="site-nav"
          aria-label="주요"
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setOpen(false);
            }
          }}
        >
          <span className="nav-group-label">{nav.service_group}</span>
          <a href={links.consumer} onClick={() => setOpen(false)}>
            {nav.service_consumer}
          </a>
          <a href={links.clinician} onClick={() => setOpen(false)}>
            {nav.service_clinician}
          </a>
          <a href={links.reception} onClick={() => setOpen(false)}>
            {nav.service_reception}
          </a>
          <span className="nav-group-label">{nav.about_group}</span>
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
