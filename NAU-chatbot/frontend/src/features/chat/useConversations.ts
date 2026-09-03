import { useCallback, useEffect, useState } from "react";
import { conversationApi } from "../../api/conversations";
import type { ConversationSummary } from "../../types/conversation";
import { errorMessage } from "../../utils/errors";

const PAGE_SIZE = 30;

export function useConversations() {
  const [items, setItems] = useState<ConversationSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async (append = false) => {
    setLoading(true);
    setError(null);
    try {
      const offset = append ? items.length : 0;
      const page = await conversationApi.list(PAGE_SIZE, offset);
      setItems((current) => append ? [...current, ...page.items] : page.items);
      setTotal(page.total);
    } catch (reason) {
      setError(errorMessage(reason));
    } finally {
      setLoading(false);
    }
  }, [items.length]);

  useEffect(() => { void load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const rename = useCallback(async (id: string, title: string) => {
    const updated = await conversationApi.rename(id, title);
    setItems((current) => current.map((item) => item.id === id ? updated : item));
  }, []);

  const remove = useCallback(async (id: string) => {
    await conversationApi.delete(id);
    setItems((current) => current.filter((item) => item.id !== id));
    setTotal((current) => Math.max(0, current - 1));
  }, []);

  return { items, total, error, loading, refresh: () => load(false), loadMore: () => load(true), rename, remove };
}
