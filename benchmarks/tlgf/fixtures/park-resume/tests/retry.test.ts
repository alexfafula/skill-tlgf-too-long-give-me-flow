import { requestWithRetry } from "../src/retry";

test("retries a transient connection error", async () => {
  let attempts = 0;
  const operation = async () => {
    attempts += 1;
    if (attempts === 1) throw new Error("connection reset");
    return "ok";
  };

  await expect(requestWithRetry(operation, { attempts: 2, baseDelayMs: 1 })).resolves.toBe("ok");
  expect(attempts).toBe(2);
});
