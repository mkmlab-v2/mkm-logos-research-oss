/** Geumsan pilot operator UI — aligns with smartfarm_geumsan_6channel_valve_mapping_v1.json */

export const SMARTFARM_PILOT_FARM_ID = "geumsan_farm_01";

export type SmartfarmSensorZone = {
  zone_id: string;
  label_ko: string;
  device_nm: string;
};

export type SmartfarmValveChannel = {
  channel_id: string;
  relay_index: number;
  label_ko: string;
  role: "fresh_water" | "nutrient" | "zone_crop" | "demo_experience";
  tier?: "primary_revenue" | "showroom_demo";
};

export const SMARTFARM_SENSOR_ZONES: SmartfarmSensorZone[] = [
  { zone_id: "zone_01", label_ko: "구역 1 (D301)", device_nm: "D301" },
  { zone_id: "zone_02", label_ko: "구역 2 (D302)", device_nm: "D302" },
];

export const SMARTFARM_VALVE_CHANNELS: SmartfarmValveChannel[] = [
  { channel_id: "ch1", relay_index: 1, label_ko: "맹물 (5톤)", role: "fresh_water" },
  { channel_id: "ch2", relay_index: 2, label_ko: "배양액 (200L)", role: "nutrient" },
  { channel_id: "ch3", relay_index: 3, label_ko: "노지 두릅", role: "zone_crop", tier: "primary_revenue" },
  {
    channel_id: "ch4",
    relay_index: 4,
    label_ko: "화분 커피 체험·데모 (50주·~20평)",
    role: "demo_experience",
    tier: "showroom_demo",
  },
  { channel_id: "ch5", relay_index: 5, label_ko: "잎들깨", role: "zone_crop", tier: "primary_revenue" },
  {
    channel_id: "ch6",
    relay_index: 6,
    label_ko: "체험 작물",
    role: "demo_experience",
    tier: "showroom_demo",
  },
];

/** Primary zone for farm-level valve commands in API stub. */
export const SMARTFARM_CONTROL_ZONE_ID = "zone_01";

export const SMARTFARM_INTERLOCK_PAIRS: [string, string][] = [["ch1", "ch2"]];

export function apiBasePath(): string {
  return "/api/smartfarm";
}
