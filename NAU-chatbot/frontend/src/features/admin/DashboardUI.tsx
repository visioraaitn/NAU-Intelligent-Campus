import { Link } from "react-router-dom";
import { Icon, type IconName } from "../../components/Icon";

interface DashboardStatProps {
  label: string;
  value: number | null | undefined;
  loading?: boolean;
  to: string;
}

export function DashboardStat({ label, value, loading = false, to }: DashboardStatProps) {
  const displayedValue = value === null ? "—" : value ?? 0;
  return (
    <Link className="dashboard-stat" to={to} aria-label={`${label} : ${value === null ? "indisponible" : displayedValue}`}>
      <span>{label}</span>
      {loading ? <span className="skeleton skeleton--number" /> : <strong>{displayedValue}</strong>}
    </Link>
  );
}

interface DashboardActionProps {
  title: string;
  description: string;
  to: string;
  icon: IconName;
}

export function DashboardAction({ title, description, to, icon }: DashboardActionProps) {
  return (
    <Link className="dashboard-action" to={to}>
      <span className="dashboard-action__icon" aria-hidden="true"><Icon name={icon} /></span>
      <span>
        <strong>{title}</strong>
        <small>{description}</small>
      </span>
      <Icon name="chevron-right" />
    </Link>
  );
}

interface DashboardResourceLinkProps {
  title: string;
  count: number | null | undefined;
  loading: boolean;
  to: string;
}

export function DashboardResourceLink({ title, count, loading, to }: DashboardResourceLinkProps) {
  return (
    <Link className="dashboard-resource" to={to}>
      <span>{title}</span>
      {loading ? (
        <span className="skeleton dashboard-resource__skeleton" />
      ) : (
        <strong aria-label={count === null ? "Indisponible" : `${count ?? 0} entrées`}>
          {count === null ? "—" : count ?? 0}
        </strong>
      )}
      <Icon name="chevron-right" />
    </Link>
  );
}
