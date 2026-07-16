import data from "../../marketing-site/public-copy.json";

export type EnterpriseCopy = {
  seo: { title: string; description: string };
  nav: {
    brand_tagline: string;
    back_home: string;
    jema_os?: string;
    admission_evidence?: string;
    pillars: string;
    proof: string;
    research: string;
    contact: string;
    main_aria_label: string;
    principles_aria_label: string;
  };
  hero: {
    eyebrow: string;
    title: string;
    subtitle: string;
    cta_primary: string;
    cta_secondary: string;
  };
  jema_os?: {
    section_label: string;
    title: string;
    lead: string;
    pipeline: { stage: string; label: string; body: string }[];
    composition: {
      title: string;
      items: { share: string; label: string; detail: string }[];
    };
    bullets: string[];
    not_claims: string[];
    oss_cta: { label: string; href: string; sublabel: string };
    footnote: string;
  };
  principles: { title: string; body: string }[];
  composition: {
    title: string;
    items: { share: string; label: string; detail: string }[];
  };
  pillars: {
    section_label: string;
    title: string;
    lead: string;
    cards: { title: string; body: string }[];
  };
  breadth: { section_label: string; title: string; body: string };
  applications: {
    title: string;
    lead: string;
    items: { title: string; body: string }[];
  };
  research: {
    section_label: string;
    title: string;
    body: string;
    link_label: string;
    link_href: string;
  };
  proof: { title: string; lead: string };
  admission_evidence?: {
    section_label: string;
    title: string;
    lead: string;
    hold_badge: string;
    items: {
      id: string;
      label: string;
      command: string;
      artifact: string;
      note: string;
    }[];
    disclaimer: string;
  };
  wtt_persona_os: {
    section_label: string;
    title: string;
    lead: string;
    cta_label: string;
    mock_caption: string;
    bullets: string[];
  };
  compression_roi: {
    section_label: string;
    title: string;
    lead: string;
    cta_label: string;
    apply_cta_label?: string;
    apply_href?: string;
    artifact_note: string;
  };
  contact: { label: string; email: string };
  footer: {
    legal_entity: string;
    brand_line: string;
    rights: string;
  };
  disclaimer: { title: string; items: string[] };
};

export type LaneGovernanceRow = {
  lane_id: string;
  public_label_ko: string;
  public_label_en: string;
  role_ko: string;
  role_en: string;
  not_do_ko: string;
  not_do_en: string;
  route_label_ko: string;
  route_label_en: string;
  route_href: string;
  route_external: boolean;
};

export type LaneGovernanceCopy = {
  schema: string;
  ring: number;
  constitution_ref: string;
  seo: {
    title: string;
    title_ko?: string;
    description: string;
    description_ko?: string;
  };
  nav: {
    brand_tagline: string;
    back_home: string;
    lanes: string;
    principles: string;
    firewall: string;
    validation: string;
    enterprise: string;
    main_aria_label: string;
  };
  hero: {
    eyebrow: string;
    title: string;
    title_en: string;
    lead: string;
    lead_en: string;
  };
  principles: {
    title: string;
    title_en: string;
    items: {
      title_ko: string;
      title_en: string;
      body_ko: string;
      body_en: string;
    }[];
  };
  lanes_table: {
    title: string;
    title_en: string;
    caption: string;
    caption_en: string;
    columns: {
      lane_ko: string;
      lane_en: string;
      role_ko: string;
      role_en: string;
      not_do_ko: string;
      not_do_en: string;
      route_ko: string;
      route_en: string;
    };
    rows: LaneGovernanceRow[];
  };
  firewall: {
    title: string;
    title_en: string;
    lead: string;
    lead_en: string;
    rules: string[];
    gate_command: string;
  };
  cta: {
    primary: { label: string; href: string };
    secondary: { label: string; href: string };
  };
  disclaimer: {
    title: string;
    title_en: string;
    items: string[];
    items_en: string[];
  };
  legacy_clinical_safety_ref?: string;
};

export type ValidationEngineCopy = {
  schema: string;
  ring: number;
  constitution_ref: string;
  safe_copy_ref: string;
  seo: {
    title: string;
    title_ko?: string;
    description: string;
    description_ko?: string;
  };
  nav: {
    brand_tagline: string;
    back_home: string;
    performance: string;
    governance: string;
    reproduce: string;
    enterprise: string;
    main_aria_label: string;
  };
  hero: {
    eyebrow: string;
    title: string;
    title_en: string;
    metrics: { label: string; value: string; scope: string }[];
  };
  what_it_does: { title: string; body: string; body_en: string };
  performance: {
    title: string;
    lead: string;
    lead_en: string;
    rows: { label: string; value: string }[];
    scope_note: string;
  };
  governance: {
    title: string;
    badges: string[];
    body: string;
    body_en: string;
  };
  reproduce: {
    title: string;
    lead: string;
    lead_en: string;
    evidence: { artifact: string; command: string }[];
    gate_command: string;
  };
  cta: {
    primary: { label: string; href: string };
    secondary: { label: string; href: string };
  };
  disclaimer: { title: string; items: string[] };
};

export type HubLink = { href: string; label: string; sublabel: string; label_en?: string; sublabel_en?: string };

export type PatientWellnessCta = {
  label: string;
  href: string;
  external: boolean;
};

export type PatientWellnessCard =
  | { variant: "provide"; title: string; items: string[] }
  | { variant: "forbid"; title: string; items: string[] }
  | {
      variant: "rhythm";
      title: string;
      body: string;
      cta_primary: PatientWellnessCta;
      cta_secondary: PatientWellnessCta;
      cta_ghost: PatientWellnessCta;
    };

export type PatientWellnessEntryCopy = {
  seo: { title: string; description: string };
  badge_non_medical: string;
  hero: { eyebrow: string; title: string; lead: string };
  cards: PatientWellnessCard[];
  kakao_blocks: { intro: string; links: string };
  disclaimer: { title: string; body: string; items: string[] };
};

export type PositioningV1Copy = {
  schema: string;
  snippets_doc: string;
  tagline_ko: string;
  tagline_en: string;
  footer_strip_ko: string;
  footer_strip_en: string;
  deck_kicker_ko: string;
  deck_kicker_en: string;
};

export type HubDiscoverReviewerBlockV1 = {
  title: string;
  body: string;
  href: string;
  cta: string;
  external?: boolean;
};

export type HubAudienceTrifurcationCardV1 = {
  id: string;
  title: string;
  body: string;
  href: string;
  cta: string;
};

export type HubAudienceTrifurcationLocaleCopy = {
  section_label: string;
  section_lead?: string;
  cards: HubAudienceTrifurcationCardV1[];
};

export type HubDiscoverLocaleCopy = {
  title: string;
  tagline: string;
  trust_wedge?: string;
  lead: string;
  placeholder: string;
  focus_badge: string;
  attach_hint: string;
  attach_hint_title: string;
  submit: string;
  routing_note: string;
  b2b_prefix: string;
  b2b_link: string;
  jema_os_prefix?: string;
  jema_os_link?: string;
  read_depth_skim?: string;
  read_depth_deep?: string;
  coordinate_envelope_note?: string;
  coordinate_envelope_disclaimer?: string;
  locale_toggle: string;
  validation_missing: string;
  reviewer_section_label?: string;
  reviewer_blocks?: HubDiscoverReviewerBlockV1[];
  reviewer_enterprise_cta?: { label: string; href: string; body: string };
};

export type ClinicianSurfaceCopy = {
  schema: string;
  ssot_ref: string;
  methodology_footnote_ko: string;
  methodology_footnote_en: string;
};

export type SiteCopy = {
  positioning_v1?: PositioningV1Copy;
  hub_audience_trifurcation?: {
    ko: HubAudienceTrifurcationLocaleCopy;
    en: HubAudienceTrifurcationLocaleCopy;
  };
  hub_discover?: { ko: HubDiscoverLocaleCopy; en: HubDiscoverLocaleCopy };
  hub_shell?: { ko: Record<string, string>; en: Record<string, string> };
  hub_links: {
    showroom_jemaai: HubLink;
    premium_mkmlife: HubLink;
    b2b_acodeai: HubLink;
    jema_os_enterprise?: HubLink;
    farm_b2b_smartfarm?: HubLink;
    research_logos?: HubLink;
    logos_beta_ask?: HubLink;
    research_mkmlab?: HubLink;
    personadiary_preview?: HubLink;
    memory_continuity_preview?: HubLink;
    gyeokmul_preview?: HubLink;
    wtt_persona_os_demo?: HubLink;
    compression_roi_dashboard?: HubLink;
    evidence_pack_v0?: HubLink;
    showroom_topology_radar?: HubLink;
    showroom_meaning_graph?: HubLink;
    showroom_meaning_qa_v2?: HubLink;
    clinician_support?: HubLink;
    clinician_no1kmedi_portal?: HubLink;
    validation_engine?: HubLink;
    lane_governance?: HubLink;
    mai_profile_card?: HubLink;
    patient_wellness_entry?: HubLink;
  };
  header: { brand_name: string; brand_tagline: string };
  seo: { title: string; description: string };
  nav: {
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
  links: {
    hub?: string;
    classic_home?: string;
    consumer: string;
    wellness?: string;
    clinician: string;
    reception: string;
    enterprise?: string;
    developer: string;
    contact: string;
    validation?: string;
    safety?: string;
  };
  validation_engine?: ValidationEngineCopy;
  lane_governance?: LaneGovernanceCopy;
  enterprise?: EnterpriseCopy;
  clinician_surface?: ClinicianSurfaceCopy;
  homepage_a11y: {
    skip_to_main: string;
    trust_section_label: string;
    feature_triad_heading: string;
    brand_motion_proof_label: string;
  };
  hero: {
    eyebrow: string;
    title: string;
    subtitle: string;
    cta_primary: string;
    cta_secondary: string;
    cta_tertiary: string;
    cta_quaternary: string;
    proof_aria_label: string;
    proof_items: string[];
    role_cards: {
      title: string;
      body: string;
      cta: string;
      href: string;
      variant: "primary" | "ghost";
    }[];
  };
  app_entry: {
    title: string;
    lead: string;
    consumer: { title: string; body: string; cta: string; href: string };
    clinician: { title: string; body: string; cta: string; href: string };
    wellness?: { title: string; body: string; cta: string; href: string };
  };
  why_mkm_ai: {
    title: string;
    section_lead: string;
    cards: { title: string; body: string; code_terms?: string[] }[];
    disclaimer: string;
  };
  quick_start: {
    title: string;
    section_lead: string;
    cards: { title: string; body: string }[];
    ctas: { label: string; href: string; variant: "primary" | "ghost" }[];
  };
  home_clinic_flow: {
    steps: { step: string; title: string; body: string }[];
  };
  basic_health_chat: {
    title: string;
    section_lead: string;
    intake_hint: string;
    assistant_greeting: string;
    labels: {
      pain_area: string;
      pain_scale: string;
      digestion: string;
      sleep: string;
    };
    placeholders: {
      pain_area: string;
      digestion: string;
      sleep: string;
      message: string;
    };
    chat: {
      assistant_role: string;
      user_role: string;
      busy_message: string;
      send_busy: string;
      send_idle: string;
      error_message: string;
    };
    survey_defaults: {
      pain_area_empty: string;
      digestion_empty: string;
      sleep_empty: string;
    };
    ctas: {
      marketing: { primary: { label: string; href: string }; secondary: { label: string; href: string } };
      workspace: { primary: { label: string; href: string }; secondary: { label: string; href: string } };
    };
  };
  governance_flow: {
    title: string;
    section_lead: string;
    field_label: string;
    lens_label: string;
    resolve_label: string;
    field_items: { title: string; body: string }[];
    lens_items: { title: string; body: string; non_gating?: boolean }[];
    resolver: { title: string; body: string };
    final_action_label: string;
    final_actions: string[];
    footnote_prefix: string;
    figjam_label: string;
    figjam_url: string;
    svg_preview_note: string;
  };
  trust: { items: { label: string; value: string }[]; note: string };
  public_solution: {
    title: string;
    section_lead: string;
    cards: { title: string; body: string }[];
    cta_primary: string;
    cta_secondary: string;
  };
  feature_triad: {
    cards: { variant: "copilot" | "heritage" | "sovereign"; title: string; subtitle: string; body: string }[];
  };
  concept_block: {
    label: string;
    title: string;
    lead: string;
    proof_items: string[];
    stage_label: string;
  };
  about: { title: string; section_lead: string };
  value_props: { title: string; body: string }[];
  safety: {
    title: string;
    section_lead?: string;
    lane_governance_cta?: {
      label: string;
      label_en?: string;
      href: string;
      note?: string;
    };
    items: string[];
  };
  workflow: { title: string; section_lead: string; steps: string[] };
  clinic_o2o: {
    title: string;
    section_lead: string;
    cards: { title: string; body: string }[];
    ctas: { label: string; href: string; variant: "primary" | "ghost" }[];
  };
  landing_flow: {
    title: string;
    lead: string;
    cards: { label: string; title: string; body: string }[];
    cta_primary: string;
    cta_secondary: string;
  };
  contact: { title: string; section_lead: string; email_label: string };
  paddle_checkout: {
    button_loading: string;
    button_idle: string;
    hint: string;
    errors: { missing_env: string; init_failed: string; checkout_prefix: string };
  };
  free_validation_lead: {
    title: string;
    section_lead: string;
    labels: { name: string; email: string; company: string; use_case: string };
    placeholders: { use_case: string };
    submit_busy: string;
    submit_idle: string;
    errors: { required_fields: string; save_failed: string; network: string };
    success: string;
  };
  footer: {
    company_line: string;
    brand_subline: string;
    address_label: string;
    address: string;
    biz_reg_label: string;
    email: string;
    biz_reg: string;
    rights: string;
  };
  compression_pilot_audit_apply?: CompressionPilotAuditApplyCopy;
  patient_wellness_entry?: PatientWellnessEntryCopy;
};

export type CompressionPilotAuditApplyCopy = {
  seo: { title: string; description: string };
  nav: { back_enterprise: string; back_hub: string };
  hero: {
    eyebrow: string;
    title: string;
    subtitle: string;
    steps_label: string;
    steps: string[];
  };
  sections: {
    organization: string;
    contact: string;
    use_case: string;
    data: string;
    ack: string;
  };
  labels: Record<string, string>;
  options: Record<string, { value: string; label: string }[]>;
  placeholders: Record<string, string>;
  submit_idle: string;
  submit_busy: string;
  success: string;
  errors: {
    required_fields: string;
    ack_required: string;
    save_failed: string;
    network: string;
  };
  disclaimer: { title: string; items: string[] };
};

export const siteCopy = data as SiteCopy;
