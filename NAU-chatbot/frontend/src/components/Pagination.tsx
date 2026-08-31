import { Icon } from "./Icon";

interface PaginationProps {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

export function Pagination({ page, pageSize, total, onPageChange }: PaginationProps) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const first = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const last = Math.min(total, page * pageSize);

  return (
    <nav className="pagination" aria-label="Pagination">
      <span className="pagination__summary">
        {first}–{last} sur {total}
      </span>
      <div className="pagination__buttons">
        <button
          className="icon-button"
          type="button"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          aria-label="Page précédente"
        >
          <Icon name="chevron-left" />
        </button>
        <span aria-current="page">Page {page} / {pageCount}</span>
        <button
          className="icon-button"
          type="button"
          disabled={page >= pageCount}
          onClick={() => onPageChange(page + 1)}
          aria-label="Page suivante"
        >
          <Icon name="chevron-right" />
        </button>
      </div>
    </nav>
  );
}
