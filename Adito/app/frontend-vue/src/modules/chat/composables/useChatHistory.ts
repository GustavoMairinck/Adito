import { call } from "@/common/api/core";
import { buildChart, cancelChatStream, isChatConversationLoading, isScalarResultData } from "@/modules/chat/composables/useChatApi";
import type { ChatMessage, Conversation } from "@/modules/chat/types";
import { isChatChartType } from "@/modules/chat/utils/chartType";
import { computed, ref } from "vue";

const STORAGE_PREFIX = "adito_chat_history";
let localConversationSeq = 0;

function createWelcomeMessage(): ChatMessage {
  return {
    id: "welcome",
    type: "ai",
    text: "Olá! Sou o Adito, seu assistente para consultar os dados de pesquisa e extensão do IFES Campus Serra. Como posso ajudar você hoje?",
    timestamp: new Date().toISOString(),
  };
}

export function createConversation(): Conversation {
  const now = new Date().toISOString();
  localConversationSeq += 1;
  return {
    id: `local-${Date.now()}-${localConversationSeq}`,
    title: "Nova Conversa",
    contextoId: null,
    messages: [createWelcomeMessage()],
    createdAt: now,
    updatedAt: now,
  };
}

function mapBackendMessage(message: any): ChatMessage {
  const metadata = message.metadata || {};
  // O histórico não guarda linhas; loadRows() reexecuta o SQL no dados.db.
  const table: Array<Record<string, any>> = [];
  const isScalarResult = false;

  return {
    id: String(message.id),
    type: message.role === "user" ? "user" : "ai",
    text:
      message.role === "user"
        ? message.content
        : metadata.type === "fallback"
          ? ""
          : message.content,
    timestamp: message.created_at,
    sql: metadata.sql,
    table,
    chart: null,
    isScalarResult,
    needsRows: message.role !== "user" && !!metadata.sql,
    isFallback: metadata.type === "fallback",
    isChat: metadata.type === "chat",
    fallbackScore: metadata.score,
    fallbackMessage: metadata.message,
    explanation: metadata.explanation,
    suggestions: metadata.suggestions,
    related_attributes: metadata.related_attributes,
    fieldFormats: metadata.field_formats,
    suggestedChartType: isChatChartType(metadata.chart_type) ? metadata.chart_type : undefined,
  };
}

function mapBackendConversation(conversation: any): Conversation {
  return {
    id: String(conversation.id),
    title: conversation.title || "Nova Conversa",
    contextoId: conversation.contexto ? String(conversation.contexto) : null,
    messages: [
      createWelcomeMessage(),
      ...(conversation.messages || []).map(mapBackendMessage),
    ],
    createdAt: conversation.createdAt || conversation.created_at,
    updatedAt:
      conversation.updatedAt ||
      conversation.updated_at ||
      conversation.created_at,
  };
}

function clearLegacyChatStorage() {
  for (let index = localStorage.length - 1; index >= 0; index -= 1) {
    const key = localStorage.key(index);
    if (key?.startsWith(`${STORAGE_PREFIX}:`)) {
      localStorage.removeItem(key);
    }
  }
}

// Estado compartilhado no módulo: sobrevive à troca de rota (ex.: Chat → Dashboard → Chat)
// mantendo rascunhos e streams em segundo plano intactos.
const conversations = ref<Conversation[]>([]);
const currentConvId = ref<string | null>(null);
let hasInitialized = false;

function resetToEmptyConversation() {
  const initial = createConversation();
  conversations.value = [initial];
  currentConvId.value = initial.id;
}

export function resetChatHistoryForTests() {
  hasInitialized = false;
  localConversationSeq = 0;
  conversations.value = [];
  currentConvId.value = null;
}

export function useChatHistory() {
  clearLegacyChatStorage();

  const updateMessage = (convId: string, messageId: string, patch: Partial<ChatMessage>) => {
    conversations.value = conversations.value.map((conversation) =>
      conversation.id !== convId
        ? conversation
        : {
            ...conversation,
            messages: conversation.messages.map((message) =>
              message.id === messageId ? { ...message, ...patch } : message,
            ),
          },
    );
  };

  /** Recarrega as linhas das respostas da conversa aberta (o histórico só guarda o SQL). */
  const loadRows = async (convId: string | null) => {
    const conversation = conversations.value.find((c) => c.id === convId);
    if (!conversation || convId?.startsWith("local-")) return;

    const pending = conversation.messages.filter((m) => m.needsRows);
    await Promise.all(
      pending.map(async (message) => {
        try {
          const data = await call("chat.message_rows", { id: message.id });
          const rows = data.data || [];
          const isScalarResult = isScalarResultData(rows);
          updateMessage(convId!, message.id, {
            needsRows: false,
            table: rows,
            isScalarResult,
            chart: isScalarResult ? null : buildChart(rows),
          });
        } catch (error: any) {
          const detail = error?.response?.data?.message || "os dados mudaram; refaça a pergunta";
          updateMessage(convId!, message.id, {
            needsRows: false,
            text: `${message.text}\n\n_Não foi possível recarregar os dados: ${detail}._`,
          });
        }
      }),
    );
  };

  const syncFromBackend = async () => {
    try {
      const data = await call("chat.conversations.list");
      if (!Array.isArray(data)) return;

      // Preserva conversas com stream ativo, locais já interagidas ou com aviso efêmero de interrupção.
      const preserved = conversations.value.filter(
        (c) =>
          isChatConversationLoading(c.id)
          || (c.id.startsWith("local-") && c.messages.length > 1)
          || c.messages.some((m) => m.interrupted),
      );

      if (data.length === 0) {
        if (preserved.length > 0) {
          conversations.value = preserved;
          if (!currentConvId.value || !preserved.some((c) => c.id === currentConvId.value)) {
            currentConvId.value = preserved[0].id;
          }
          return;
        }
        resetToEmptyConversation();
        return;
      }

      const remote = data.map(mapBackendConversation);
      const preservedIds = new Set(preserved.map((c) => c.id));
      const merged = [...preserved, ...remote.filter((c) => !preservedIds.has(c.id))];
      conversations.value = merged;

      const keepCurrent = currentConvId.value && preservedIds.has(currentConvId.value);
      if (!keepCurrent) {
        currentConvId.value = merged[0]?.id || null;
      }
      loadRows(currentConvId.value);
    } catch {
      // Mantem fallback local quando o backend esta offline.
    }
  };

  if (!hasInitialized) {
    hasInitialized = true;
    resetToEmptyConversation();
    syncFromBackend();
  } else if (conversations.value.length === 0) {
    resetToEmptyConversation();
  }

  const handleNewConversation = () => {
    const newConversation = createConversation();
    conversations.value = [newConversation, ...conversations.value];
    currentConvId.value = newConversation.id;
  };

  const handleDeleteConversation = async (id: string) => {
    // Cancela qualquer stream em andamento dessa conversa antes de removê-la.
    cancelChatStream(id);
    if (!id.startsWith("local-")) {
      await call("chat.conversations.delete", { id });
    }
    const updated = conversations.value.filter((c) => c.id !== id);
    if (updated.length === 0) {
      const next = createConversation();
      conversations.value = [next];
      currentConvId.value = next.id;
      return;
    }

    conversations.value = updated;
    if (currentConvId.value === id) {
      currentConvId.value = updated[0].id;
    }
  };

  const updateConversationById = (
    convId: string,
    updater: (conversation: Conversation) => Conversation,
  ) => {
    conversations.value = conversations.value.map((conversation) => {
      if (conversation.id !== convId) return conversation;
      return updater(conversation);
    });
  };

  const updateCurrentConversation = (
    updater: (conversation: Conversation) => Conversation,
  ) => {
    if (!currentConvId.value) return;
    updateConversationById(currentConvId.value, updater);
  };

  const replaceConversationId = (oldId: string, newId: string) => {
    if (!oldId || !newId || oldId === newId) return;
    // Remove eventual cópia já vinda de syncFromBackend() com id === newId para evitar chaves duplicadas.
    conversations.value = conversations.value
      .filter((conversation) => conversation.id !== newId)
      .map((conversation) =>
        conversation.id === oldId ? { ...conversation, id: newId } : conversation,
      );
    if (currentConvId.value === oldId) currentConvId.value = newId;
  };

  const setCurrentConvId = (id: string) => {
    currentConvId.value = id;
    loadRows(id);
  };

  const setConversationContexto = (convId: string, contextoId: string | null) => {
    conversations.value = conversations.value.map((conversation) =>
      conversation.id === convId ? { ...conversation, contextoId } : conversation,
    );
  };

  const currentConversation = computed(
    () =>
      conversations.value.find((c) => c.id === currentConvId.value) ||
      conversations.value[0],
  );

  return {
    conversations,
    currentConvId,
    setCurrentConvId,
    handleNewConversation,
    handleDeleteConversation,
    updateConversationById,
    updateCurrentConversation,
    replaceConversationId,
    setConversationContexto,
    currentConversation,
    syncFromBackend,
  };
}
