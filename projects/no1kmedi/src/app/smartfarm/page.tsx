import { redirect } from "next/navigation";

type SmartfarmPageProps = {
  searchParams?: Record<string, string | string[] | undefined>;
};

function pickParam(params: Record<string, string | string[] | undefined>, key: string): string {
  const value = params[key];
  if (Array.isArray(value)) return value[0] ?? "";
  return value ?? "";
}

export default function SmartfarmPage({ searchParams }: SmartfarmPageProps) {
  const params = searchParams ?? {};
  const query = new URLSearchParams({
    stage: pickParam(params, "stage"),
    score: pickParam(params, "score"),
    irrigation: pickParam(params, "irrigation"),
    logging: pickParam(params, "logging"),
    risk: pickParam(params, "risk"),
    budget: pickParam(params, "budget"),
    source: pickParam(params, "source"),
  });

  redirect(`/consumer?${query.toString()}`);
}
