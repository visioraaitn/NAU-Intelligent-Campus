import { Modal } from "./Modal";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel: string;
  busy?: boolean;
  destructive?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel,
  busy = false,
  destructive = false,
  onCancel,
  onConfirm,
}: ConfirmDialogProps) {
  return (
    <Modal open={open} title={title} description={message} onClose={onCancel} size="small">
      <div className="modal__actions">
        <button className="button button--ghost" type="button" onClick={onCancel} disabled={busy}>
          Annuler
        </button>
        <button
          className={`button ${destructive ? "button--danger" : "button--primary"}`}
          type="button"
          onClick={onConfirm}
          disabled={busy}
        >
          {busy && <span className="spinner spinner--small" aria-hidden="true" />}
          {busy ? "Traitement…" : confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
