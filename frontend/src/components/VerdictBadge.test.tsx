import { render, screen } from "@testing-library/react";
import { VerdictBadge } from "./VerdictBadge";

test("renders the consumer-friendly label, not the raw backend label", () => {
  render(<VerdictBadge label="Buy" />);
  expect(screen.getByText("Potential Opportunity")).toBeInTheDocument();
  expect(screen.queryByText("Buy")).not.toBeInTheDocument();
});

test("falls back to the raw label for an unrecognized value", () => {
  render(<VerdictBadge label="Mystery" />);
  expect(screen.getByText("Mystery")).toBeInTheDocument();
});
