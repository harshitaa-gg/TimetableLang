import type { CompileResponse } from './types';

// Reads configured base URL, default to current origin or fallback
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

export async function compileSource(
  source: string,
  maxSlots?: number | null
): Promise<CompileResponse> {
  const endpoint = `${API_BASE_URL}/api/compile`;

  const payload: { source: string; max_slots?: number } = { source };
  if (typeof maxSlots === 'number' && !isNaN(maxSlots) && maxSlots > 0) {
    payload.max_slots = maxSlots;
  }

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(
      `Compiler API returned HTTP ${response.status}: ${errorText || response.statusText}`
    );
  }

  const data: CompileResponse = await response.json();
  return data;
}
