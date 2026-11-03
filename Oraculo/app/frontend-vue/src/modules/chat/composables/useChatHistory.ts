import httpClient from "@/common/api/httpClient";
import { buildChart, isScalarResultData } from "@/modules/chat/composables/useChatApi";
import type { ChatMessage, Conversation } from "@/modules/chat/types";
import { computed, ref } from "vue";

const STORAGE_PREFIX = "oraculo_esx_chat_history";

function createWelcomeMessage(): ChatMessage {
  return {
    id: "welcome",
    type: "ai",
    text: "Olá! Sou o ORACULO-ESX, seu assistente de inteligência estratégica. Como posso ajudar você hoje?",
    timestamp: new Date().toISOString(),
  };
}

export function createConversation(): Conversation {
  const now = new Date().toISOString();
  return {
    id: `local-${Date.now()}`,
    title: "Nova Conversa",
    messages: [createWelcomeMessage()],
    createdAt: now,
    updatedAt: now,
  };
}

function mapBackendMessage(message: any): ChatMessage {
  const metadata = message.metadata || {};
  const table = metadata.data || [];
  const isScalarResult = isScalarResultData(table);

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
    chart: message.role === "user" || isScalarResult ? null : buildChart(table),
    isScalarResult,
    isFallback: metadata.type === "fallback",
    isChat: metadata.type === "chat",
    fallbackScore: metadata.score,
    fallbackMessage: metadata.message,
    explanation: metadata.explanation,
    suggestions: metadata.suggestions,
    related_attributes: metadata.related_attributes,
    fieldFormats: metadata.field_formats,
  };
}

function mapBackendConversation(conversation: any): Conversation {
  return {
    id: String(conversation.id),
    title: conversation.title || "Nova Conversa",
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

export function useChatHistory() {
  const conversations = ref<Conversation[]>([]);
  const currentConvId = ref<string | null>(null);

  const resetToEmptyConversation = () => {
    conversations.value = [createConversation()];
    currentConvId.value = conversations.value[0]?.id || null;
  };

  clearLegacyChatStorage();
  resetToEmptyConversation();

  const syncFromBackend = async () => {
    try {
      const { data } = await httpClient.get("/api/chat/conversations");
      if (!Array.isArray(data)) return;

      if (data.length === 0) {
        resetToEmptyConversation();
        return;
      }

      conversations.value = data.map(mapBackendConversation);
      currentConvId.value = conversations.value[0]?.id || null;
    } catch {
      // Mantem fallback local quando usuario ainda nao autenticou ou backend esta offline.
    }
  };

  syncFromBackend();

  const handleNewConversation = () => {
    const newConversation = createConversation();
    conversations.value = [newConversation, ...conversations.value];
    currentConvId.value = newConversation.id;
  };

  const handleDeleteConversation = async (id: string) => {
    if (!id.startsWith("local-")) {
      await httpClient.delete(`/api/chat/conversations/${id}`);
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

  const updateCurrentConversation = (
    updater: (conversation: Conversation) => Conversation,
  ) => {
    conversations.value = conversations.value.map((conversation) => {
      if (conversation.id !== currentConvId.value) return conversation;
      return updater(conversation);
    });
  };

  const replaceConversationId = (oldId: string, newId: string) => {
    conversations.value = conversations.value.map((conversation) =>
      conversation.id === oldId ? { ...conversation, id: newId } : conversation,
    );
    if (currentConvId.value === oldId) currentConvId.value = newId;
  };

  const setCurrentConvId = (id: string) => {
    currentConvId.value = id;
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
    updateCurrentConversation,
    replaceConversationId,
    currentConversation,
    syncFromBackend,
  };
}
