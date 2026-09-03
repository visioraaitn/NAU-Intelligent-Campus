import { Link } from "react-router-dom";
import { Icon } from "../../components/Icon";

export interface BreadcrumbItem {
  label: string;
  to?: string;
}

export function AdminBreadcrumb({ items }: { items: BreadcrumbItem[] }) {
  return (
    <nav className="admin-breadcrumb" aria-label="Fil d’Ariane">
      <ol>
        {items.map((item, index) => (
          <li key={`${item.label}-${index}`}>
            {index > 0 && <Icon name="chevron-right" />}
            {item.to ? <Link to={item.to}>{item.label}</Link> : <span aria-current="page">{item.label}</span>}
          </li>
        ))}
      </ol>
    </nav>
  );
}
