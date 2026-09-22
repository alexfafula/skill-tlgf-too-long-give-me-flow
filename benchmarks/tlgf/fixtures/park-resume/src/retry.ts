export class TimeoutError extends Error {}

export type RetryOptions = {
  attempts: number;
  baseDelayMs: number;
};

export async function requestWithRetry<T>(
  operation: () => Promise<T>,
  options: RetryOptions,
): Promise<T> {
  for (let attempt = 1; attempt <= options.attempts; attempt += 1) {
    try {
      return await operation();
    } catch (error) {
      const canRetry = !(error instanceof TimeoutError) && attempt < options.attempts;
      if (!canRetry) throw error;
      await new Promise((resolve) => setTimeout(resolve, options.baseDelayMs * attempt));
    }
  }

  throw new Error("unreachable");
}
