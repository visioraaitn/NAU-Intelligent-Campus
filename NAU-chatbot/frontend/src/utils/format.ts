const dateTimeFormatter = new Intl.DateTimeFormat("fr-TN", {
  dateStyle: "medium",
  timeStyle: "short",
});

const dateFormatter = new Intl.DateTimeFormat("fr-TN", {
  dateStyle: "medium",
});

export function formatDateTime(value: unknown): string {
  if (typeof value !== "string" || !value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "—" : dateTimeFormatter.format(date);
}

export function formatDate(value: unknown): string {
  if (typeof value !== "string" || !value) return "—";
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? "—" : dateFormatter.format(date);
}

export function formatCurrency(value: unknown, currency = "TND"): string {
  if (value === null || value === undefined || value === "") return "—";
  const amount = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(amount)) return "—";
  return new Intl.NumberFormat("fr-TN", { style: "currency", currency }).format(amount);
}

export function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Oui" : "Non";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

export function humanizeEnum(value: unknown): string {
  if (typeof value !== "string") return formatValue(value);
  return value.toLocaleLowerCase("fr").replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
}

const languageLabels: Record<string, string> = {
  FRANCAIS: "Français",
  ANGLAIS: "Anglais",
};

export function formatLanguage(value: unknown): string {
  return languageLabels[String(value)] ?? humanizeEnum(value);
}

const criteriaLabels: Record<string, string> = {
  diplome: "Diplôme requis",
  type_bac: "Sections de bac acceptées",
  diplome_origine: "Diplômes d'origine acceptés",
  interet: "Centres d'intérêt",
  profile: "Profil académique",
};

const criteriaValueLabels: Record<string, string> = {
  BAC: "Baccalauréat",
  PREPA: "Prépa validée",
  LICENCE: "Licence",
  MASTER: "Mastère",
  MATH: "Mathématiques",
  SCIENCES: "Sciences expérimentales",
  SCIENTIFIQUE: "Section scientifique",
  SCIENCES_EXPERIMENTALES: "Sciences expérimentales",
  INFORMATIQUE: "Informatique",
  TECHNIQUE: "Sciences techniques",
  ECONOMIQUE: "Économie et Gestion",
  ECONOMIE_GESTION: "Économie et Gestion",
  SPORT: "Sport",
  EQUIVALENT: "Équivalent",
};

export function formatCriteria(value: unknown): string {
  if (!value || typeof value !== "object" || Array.isArray(value)) return "Aucun critère";
  return Object.entries(value as Record<string, unknown>)
    .map(([key, raw]) => {
      const nested = raw && typeof raw === "object" && !Array.isArray(raw)
        ? (raw as Record<string, unknown>).in
        : raw;
      const values = Array.isArray(nested) ? nested : [nested];
      const readable = values
        .filter((item) => item !== undefined && item !== null)
        .map((item) => criteriaValueLabels[String(item)] ?? humanizeEnum(item))
        .join(", ");
      return `${criteriaLabels[key] ?? humanizeEnum(key)} : ${readable || "non renseigné"}`;
    })
    .join(" · ");
}
