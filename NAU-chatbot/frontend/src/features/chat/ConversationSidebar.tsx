import { useEffect, useMemo, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import { Brand } from "../../components/Brand";
import { Icon } from "../../components/Icon";
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

interface ConversationGroup {
  label: string;
  items: ConversationSummary[];
}

export function ConversationSidebar(props: Props) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [menuId, setMenuId] = useState<string | null>(null);
  const [title, setTitle] = useState("");

  // Close dropdown on outside click or Escape
  useEffect(() => {
    if (!menuId) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMenuId(null);
    };
    const handleClick = () => setMenuId(null);
    document.addEventListener("keydown", handleKey);
    document.addEventListener("click", handleClick);
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.removeEventListener("click", handleClick);
    };
  }, [menuId]);

  // Close drawer on Escape
  useEffect(() => {
    if (!props.open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") props.onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [props.open, props.onClose]);

  const saveTitle = async (id: string) => {
    const value = title.trim();
    if (value) await props.onRename(id, value);
    setEditingId(null);
  };

  const groups = useMemo(() => {
    if (props.conversations.length === 0) return [];
    const now = new Date();
    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
    const sevenDaysAgo = startOfToday - 6 * 24 * 60 * 60 * 1000;

    const todayItems: ConversationSummary[] = [];
    const weekItems: ConversationSummary[] = [];
    const olderItems: ConversationSummary[] = [];

    for (const conv of props.conversations) {
      const time = new Date(conv.updated_at || conv.created_at).getTime();
      if (isNaN(time) || time >= startOfToday) {
        todayItems.push(conv);
      } else if (time >= sevenDaysAgo) {
        weekItems.push(conv);
      } else {
        olderItems.push(conv);
      }
    }

    const result: ConversationGroup[] = [];
    if (todayItems.length > 0) result.push({ label: "Aujourd’hui", items: todayItems });
    if (weekItems.length > 0) result.push({ label: "7 derniers jours", items: weekItems });
    if (olderItems.length > 0) result.push({ label: "Plus ancien", items: olderItems });
    return result;
  }, [props.conversations]);

  return (
    <>
      <aside
        className={`admin-sidebar conversation-sidebar ${props.open ? "admin-sidebar--open conversation-sidebar--open" : ""}`}
        aria-label="Historique des conversations"
      >
        <div className="admin-sidebar__brand">
          <Brand link="/chat" />
          <button
            className="icon-button admin-sidebar__close"
            type="button"
            onClick={props.onClose}
            aria-label="Fermer l’historique"
          >
            <Icon name="close" />
          </button>
        </div>

        <nav className="admin-nav conversation-nav" aria-label="Conversations">
          <span className="admin-nav__label">Conversations</span>

          <button
            className="conversation-new-action"
            type="button"
            onClick={props.onNew}
          >
            <Icon name="plus" />
            <span>Nouvelle conversation</span>
          </button>

          {props.conversations.length === 0 && !props.loading && (
            <div className="conversation-empty">
              <strong>Aucune conversation pour le moment.</strong>
              <span>Commencez une discussion pour la retrouver ici.</span>
            </div>
          )}

          {groups.map((group) => (
            <div key={group.label} className="conversation-group">
              <span className="conversation-group__label">{group.label}</span>
              {group.items.map((conversation) => {
                const isActive = conversation.id === props.activeId;
                return (
                  <div
                    className={`conversation-item ${isActive ? "active" : ""}`}
                    key={conversation.id}
                  >
                    {editingId === conversation.id ? (
                      <form
                        className="conversation-item__edit-form"
                        onSubmit={(event) => {
                          event.preventDefault();
                          void saveTitle(conversation.id);
                        }}
                      >
                        <input
                          autoFocus
                          maxLength={160}
                          value={title}
                          onChange={(event) => setTitle(event.target.value)}
                          onBlur={() => void saveTitle(conversation.id)}
                          aria-label="Nouveau titre"
                        />
                      </form>
                    ) : (
                      <NavLink
                        to={`/chat/${conversation.id}`}
                        className={({ isActive: navActive }) => (isActive || navActive ? "active" : undefined)}
                        onClick={() => {
                          setMenuId(null);
                          props.onClose();
                        }}
                      >
                        <span className="conversation-item__title">{conversation.title}</span>
                      </NavLink>
                    )}

                    <div className="conversation-item__actions">
                      <button
                        className="conversation-item__menu-button"
                        type="button"
                        aria-label={`Actions pour ${conversation.title}`}
                        aria-expanded={menuId === conversation.id}
                        onClick={(e) => {
                          e.stopPropagation();
                          setMenuId((current) => (current === conversation.id ? null : conversation.id));
                        }}
                      >
                        •••
                      </button>
                      {menuId === conversation.id && (
                        <div
                          className="conversation-item__menu"
                          role="menu"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <button
                            type="button"
                            role="menuitem"
                            onClick={() => {
                              setMenuId(null);
                              setEditingId(conversation.id);
                              setTitle(conversation.title);
                            }}
                          >
                            <Icon name="edit" /> Renommer
                          </button>
                          <button
                            type="button"
                            role="menuitem"
                            onClick={() => {
                              setMenuId(null);
                              props.onDelete(conversation);
                            }}
                          >
                            <Icon name="trash" /> Supprimer
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          ))}

          {props.hasMore && (
            <button
              className="conversation-load-more"
              disabled={props.loading}
              type="button"
              onClick={props.onLoadMore}
            >
              {props.loading ? "Chargement…" : "Charger plus"}
            </button>
          )}
        </nav>

        <div className="admin-sidebar__footer">
          <div className="admin-user admin-user--sidebar" aria-label="Session utilisateur">
            <span className="admin-user__avatar" aria-hidden="true">
              {props.user.name.slice(0, 1).toUpperCase()}
            </span>
            <span>
              <strong>{props.user.name}</strong>
              <small>{props.user.role === "ADMIN" ? "Administrateur" : "Utilisateur"}</small>
            </span>
          </div>
          {props.user.role === "ADMIN" && (
            <Link className="sidebar-public-link" to="/admin">
              <Icon name="dashboard" /> Tableau de bord
            </Link>
          )}
          <button type="button" onClick={props.onLogout}>
            <Icon name="logout" /> Se déconnecter
          </button>
        </div>
      </aside>
      {props.open && (
        <button
          className="sidebar-scrim"
          type="button"
          aria-label="Fermer le menu"
          onClick={props.onClose}
        />
      )}
    </>
  );
}
