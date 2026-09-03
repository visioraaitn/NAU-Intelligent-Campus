import { useState } from "react";
import { NavLink } from "react-router-dom";
import { Icon } from "../../components/Icon";
import { IITLogo } from "../../components/IITLogo";
import type { AuthUser } from "../../types/auth";
import type { ConversationSummary } from "../../types/conversation";

interface Props {
  conversations: ConversationSummary[];
  activeId?: string;
  user: AuthUser;
  open: boolean;
  hasMore: boolean;
  loading: boolean;
  onClose: () => void;
  onNew: () => void;
  onRename: (id: string, title: string) => Promise<void>;
  onDelete: (conversation: ConversationSummary) => void;
  onLoadMore: () => void;
  onLogout: () => void;
}

export function ConversationSidebar(props: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [menuId, setMenuId] = useState<string | null>(null);
  const [title, setTitle] = useState("");

  const saveTitle = async (id: string) => {
    const value = title.trim();
    if (value) await props.onRename(id, value);
    setEditingId(null);
  };

  return (
    <>
      <aside className={`conversation-sidebar ${props.open ? "conversation-sidebar--open" : ""}`} aria-label="Historique des conversations">
        <div className="conversation-sidebar__header">
          <IITLogo className="conversation-sidebar__logo" link="/chat" />
          <button className="icon-button conversation-sidebar__close" type="button" onClick={props.onClose} aria-label="Fermer l’historique"><Icon name="close" /></button>
        </div>
        <button className="conversation-new" type="button" onClick={props.onNew}><Icon name="plus" /> Nouvelle conversation</button>
        <div className="conversation-history">
          <span className="conversation-history__label">Conversations récentes</span>
          {props.conversations.length === 0 && !props.loading && <p className="conversation-history__empty"><strong>Aucune conversation pour le moment.</strong><span>Commencez une discussion pour la retrouver ici.</span></p>}
          {props.conversations.map((conversation) => (
            <div className={`conversation-history__item ${conversation.id === props.activeId ? "active" : ""}`} key={conversation.id}>
              {editingId === conversation.id ? (
                <form onSubmit={(event) => { event.preventDefault(); void saveTitle(conversation.id); }}>
                  <input autoFocus maxLength={160} value={title} onChange={(event) => setTitle(event.target.value)} onBlur={() => void saveTitle(conversation.id)} aria-label="Nouveau titre" />
                </form>
              ) : (
                <NavLink to={`/chat/${conversation.id}`} onClick={() => { setMenuId(null); props.onClose(); }}>{conversation.title}</NavLink>
              )}
              <div className="conversation-history__actions">
                <button className="conversation-history__menu-button" type="button" aria-label={`Actions pour ${conversation.title}`} aria-expanded={menuId === conversation.id} onClick={() => setMenuId((current) => current === conversation.id ? null : conversation.id)}>•••</button>
                {menuId === conversation.id && <div className="conversation-history__menu" role="menu">
                  <button type="button" role="menuitem" onClick={() => { setMenuId(null); setEditingId(conversation.id); setTitle(conversation.title); }}><Icon name="edit" /> Renommer</button>
                  <button type="button" role="menuitem" onClick={() => { setMenuId(null); props.onDelete(conversation); }}><Icon name="trash" /> Supprimer</button>
                </div>}
              </div>
            </div>
          ))}
          {props.hasMore && <button className="conversation-load-more" disabled={props.loading} type="button" onClick={props.onLoadMore}>{props.loading ? "Chargement…" : "Charger plus"}</button>}
        </div>
        <div className="conversation-sidebar__footer">
          <div className="conversation-user"><span>{props.user.name.slice(0, 1).toUpperCase()}</span><div><strong>{props.user.name}</strong><small>{props.user.role === "ADMIN" ? "Administrateur" : "Utilisateur"}</small></div></div>
          <button type="button" onClick={props.onLogout}><Icon name="logout" /> Déconnexion</button>
          <small className="powered-by">Powered by <strong>Visiora AI</strong></small>
        </div>
      </aside>
      {props.open && <button className="conversation-sidebar__scrim" type="button" aria-label="Fermer l’historique" onClick={props.onClose} />}
    </>
  );
}
