import Stripe from "stripe";

// B-02 (fixed, SPEC.md B-02): no hardcoded fallback - read from the
// environment only, and fail at import time (so the app refuses to start,
// rather than silently running with no key) if it's unset.
const STRIPE_SECRET_KEY = process.env.STRIPE_SECRET_KEY;
if (!STRIPE_SECRET_KEY) {
  throw new Error("STRIPE_SECRET_KEY is not set - copy .env.example to .env and fill it in.");
}

export const stripe = new Stripe(STRIPE_SECRET_KEY, {
  apiVersion: "2024-06-20",
});
