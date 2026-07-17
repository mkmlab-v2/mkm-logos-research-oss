"use client";

type NavItem = { id: string; label: string };

type ClinicianShallowNavV1Props = {
  items: NavItem[];
  activeId: string;
  onSelect: (id: string) => void;
};

export function ClinicianShallowNavV1({ items, activeId, onSelect }: ClinicianShallowNavV1Props) {
  if (items.length === 0) return null;
  return (
    <nav className="clinician-shallow-nav-v1" aria-label="주요 패널">
      {items.map((item) => (
        <button
          key={item.id}
          type="button"
          className={`clinician-shallow-nav-v1__item${activeId === item.id ? " is-active" : ""}`}
          aria-current={activeId === item.id ? "page" : undefined}
          onClick={() => onSelect(item.id)}
        >
          {item.label}
        </button>
      ))}
    </nav>
  );
}
