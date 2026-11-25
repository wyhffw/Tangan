import { ref } from "vue";
import { defineStore } from "pinia";

export type PetTab = "chat" | "graph" | "llm";

export const useAssistantStore = defineStore("assistant", () => {
  const visible = ref(false);
  const hidden = ref(false);
  const tab = ref<PetTab>("chat");

  function open() {
    visible.value = true;
    hidden.value = false;
  }

  function close() {
    visible.value = false;
    hidden.value = true;
  }

  function toggle() {
    if (visible.value) {
      minimize();
    } else {
      open();
    }
  }

  function minimize() {
    visible.value = false;
    hidden.value = false;
  }

  function setTab(next: PetTab) {
    tab.value = next;
    open();
  }

  return { visible, hidden, tab, open, close, toggle, minimize, setTab };
});

