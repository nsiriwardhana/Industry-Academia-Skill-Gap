import { useSyncExternalStore } from 'react';
import type { ModelSettings } from '@/types/industryConnect';

const STORAGE_KEY = 'industry-connect-model-settings';

const DEFAULT_SETTINGS: ModelSettings = {
  model_provider: 'ollama',
  ollama_model: '',
};

let currentSettings: ModelSettings | null = null;
let storageListenerBound = false;
const listeners = new Set<() => void>();

function loadSettings(): ModelSettings {
  if (typeof window === 'undefined') return DEFAULT_SETTINGS;

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_SETTINGS;
    return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

function getSnapshot(): ModelSettings {
  if (currentSettings === null) {
    currentSettings = loadSettings();
  }
  return currentSettings;
}

function notifyListeners() {
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);

  if (typeof window !== 'undefined' && !storageListenerBound) {
    window.addEventListener('storage', (event) => {
      if (event.key !== STORAGE_KEY) return;
      currentSettings = loadSettings();
      notifyListeners();
    });
    storageListenerBound = true;
  }

  return () => {
    listeners.delete(listener);
  };
}

export function useModelSettings() {
  const settings = useSyncExternalStore(subscribe, getSnapshot, getSnapshot);

  const saveSettings = (next: ModelSettings) => {
    currentSettings = next;

    if (typeof window === 'undefined') {
      notifyListeners();
      return;
    }

    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    } catch {
      // quota exceeded or private browsing — silently ignore
    }

    notifyListeners();
  };

  return { settings, saveSettings };
}
