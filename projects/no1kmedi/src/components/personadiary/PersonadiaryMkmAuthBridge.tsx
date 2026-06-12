"use client";

import { useEffect } from "react";

/** Reads MKM Family handoff result from sessionStorage (personadiary.com / jema-ai.com shared app). */
export function PersonadiaryMkmAuthBridge() {
  useEffect(() => {
    const accountId = sessionStorage.getItem("mkm_family_account_id");
    const profileId = sessionStorage.getItem("mkm_family_product_profile_id");
    if (!accountId) return;
    window.dispatchEvent(
      new CustomEvent("personadiary_mkm_family_linked", {
        detail: { mkm_account_id: accountId, product_profile_id: profileId },
      }),
    );
  }, []);

  return null;
}
