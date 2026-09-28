import Stripe from "stripe";

// B-02 (seeded flaw, SPEC.md B-02): the Stripe secret key is hardcoded
// directly in this server file and committed to the repo, instead of
// being read from an env var with no fallback. This value is obviously
// fake and deliberately shaped so it can never match Stripe's real
// `sk_live_`/`sk_test_` key format (see CLAUDE.md - a real-looking format
// here would trip GitHub push protection). The fixed branch (M6) reads
// this from STRIPE_SECRET_KEY with no default and fails to start without
// it.
const STRIPE_SECRET_KEY = "FAKE_STRIPE_SECRET_DO_NOT_USE_51NxYzAbCdEfGhIjKlMnOpQrStUv";

export const stripe = new Stripe(STRIPE_SECRET_KEY, {
  apiVersion: "2024-06-20",
});
