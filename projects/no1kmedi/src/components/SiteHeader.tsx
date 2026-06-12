"use client";

import { useState } from "react";

type Nav = {
  service_group: string;
  service_hub?: string;
  service_consumer: string;
  service_clinician: string;
  service_reception: string;
  service_enterprise?: string;
  service_developer: string;
  toggle_label: string;
  toggle_open_aria: string;
  toggle_close_aria: string;
  main_aria_label: string;
  about_group: string;
  about: string;
  safety: string;
  workflow: string;
  governance?: string;
  contact: string;
};
type Brand = { brand_name: string; brand_tagline: string };
type Links = {
  hub?: string;
  consumer: string;
  clinician: string;
  reception: string;
  enterprise?: string;
  developer: string;
  contact: string;
};

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
          aria-label={open ? nav.toggle_close_aria : nav.toggle_open_aria}
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
          {nav.toggle_label}
        </button>
        <nav
          className={`nav-main${open ? " is-open" : ""}`}
          id="site-nav"
          aria-label={nav.main_aria_label}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              setOpen(false);
            }
          }}
        >
          <span className="nav-group-label">{nav.service_group}</span>
          {nav.service_hub && links.hub ? (
            <a href={links.hub} onClick={() => setOpen(false)}>
              {nav.service_hub}
            </a>
          ) : null}
          <a href={links.consumer} onClick={() => setOpen(false)}>
            {nav.service_consumer}
          </a>
          <a href={links.clinician} onClick={() => setOpen(false)}>
            {nav.service_clinician}
          </a>
          <a href={links.reception} onClick={() => setOpen(false)}>
            {nav.service_reception}
          </a>
          {nav.service_enterprise && links.enterprise ? (
            <a href={links.enterprise} onClick={() => setOpen(false)}>
              {nav.service_enterprise}
            </a>
          ) : null}
          <a href={links.developer} onClick={() => setOpen(false)}>
            {nav.service_developer}
          </a>
          <span className="nav-group-label">{nav.about_group}</span>
          <a href="#about" onClick={() => setOpen(false)}>
            {nav.about}
          </a>
          <a href="#safety" onClick={() => setOpen(false)}>
            {nav.safety}
          </a>
          {nav.governance ? (
            <a href="#governance-flow" onClick={() => setOpen(false)}>
              {nav.governance}
            </a>
          ) : null}
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
