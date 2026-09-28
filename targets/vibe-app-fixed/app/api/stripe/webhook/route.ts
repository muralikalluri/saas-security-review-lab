import { NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";
import { stripe } from "@/lib/stripe";
import type Stripe from "stripe";

const webhookSecret = process.env.STRIPE_WEBHOOK_SECRET;
if (!webhookSecret) {
  throw new Error("STRIPE_WEBHOOK_SECRET is not set - copy .env.example to .env and fill it in.");
}

/**
 * B-07 (fixed, SPEC.md B-07): reads the RAW body (request.text(), not
 * .json() - constructEvent needs the exact bytes Stripe signed) and
 * verifies it against the `stripe-signature` header before touching
 * anything. Any failure - missing header, wrong secret, tampered body,
 * expired timestamp - returns 400 without ever parsing the payload as an
 * event. Fails closed at import time if STRIPE_WEBHOOK_SECRET is unset,
 * rather than silently skipping verification.
 *
 * B-08 (fixed, SPEC.md B-08): the actual credit grant now happens inside
 * apply_checkout_credits() (see the migration), a single atomic SQL
 * statement that records the event id (unique constraint) and grants
 * credits together - replaying the identical event, or a different event
 * for the same checkout session, is a no-op the second time. The
 * baseline's select-balance-then-write-balance was also a lost-update race
 * even ignoring replay; this RPC fixes both with one change.
 */
export async function POST(request: Request) {
  const rawBody = await request.text();
  const signature = request.headers.get("stripe-signature");

  let event: Stripe.Event;
  try {
    event = stripe.webhooks.constructEvent(rawBody, signature ?? "", webhookSecret!);
  } catch {
    return NextResponse.json({ error: "invalid signature" }, { status: 400 });
  }

  if (event.type === "checkout.session.completed") {
    const session = event.data.object as Stripe.Checkout.Session;

    if (session.payment_status !== "paid") {
      return NextResponse.json({ received: true, skipped: "not paid" });
    }

    const metadata = (session.metadata ?? {}) as { userId?: string; credits?: string };
    const userId = metadata.userId;
    // Stripe metadata values are always strings on a real event payload
    // (session.metadata.credits is "10", not 10) - coerce so the demo
    // matches the real shape instead of relying on JS's `+` on a string.
    const credits = Number(metadata.credits);

    if (!userId || !Number.isInteger(credits) || credits <= 0) {
      return NextResponse.json({ error: "malformed metadata" }, { status: 400 });
    }

    const supabaseAdmin = createAdminClient();
    const { data: outcome, error } = await supabaseAdmin.rpc("apply_checkout_credits", {
      p_event_id: event.id,
      p_session_id: session.id,
      p_user_id: userId,
      p_credits: credits,
    });

    if (error) {
      // Non-2xx tells Stripe to retry - a transient DB error should not be
      // silently swallowed as a permanent "duplicate".
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json({ received: true, outcome });
  }

  return NextResponse.json({ received: true });
}
