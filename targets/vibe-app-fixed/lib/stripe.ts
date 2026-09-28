import Stripe from "stripe";

// B-02 (fixed, SPEC.md B-02): no hardcoded fallback - read from the
// environment only. Lazy (checked on first use, not at module import): a
// module-level throw here would fail `next build`'s page-data collection
// for every route that imports this file, even in a build environment
// that legitimately doesn't need a real Stripe key yet (e.g. CI). The
// check still fires - and still fails closed - the first time anything
// actually tries to call Stripe.
let cached: Stripe | null = null;

export function getStripe(): Stripe {
  if (cached) return cached;
  const key = process.env.STRIPE_SECRET_KEY;
  if (!key) {
    throw new Error("STRIPE_SECRET_KEY is not set - copy .env.example to .env and fill it in.");
  }
  cached = new Stripe(key, { apiVersion: "2024-06-20" });
  return cached;
}
