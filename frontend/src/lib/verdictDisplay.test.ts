import { expect, test } from "vitest";
import { toDisplayLabel } from "./verdictDisplay";

test("maps each backend verdict label to consumer-friendly text", () => {
  expect(toDisplayLabel("Strong Buy")).toBe("Strong Opportunity");
  expect(toDisplayLabel("Buy")).toBe("Potential Opportunity");
  expect(toDisplayLabel("Hold")).toBe("Worth Watching");
  expect(toDisplayLabel("Avoid")).toBe("No Clear Opportunity");
});

test("falls back to the raw label for an unrecognized value", () => {
  expect(toDisplayLabel("Mystery")).toBe("Mystery");
});
