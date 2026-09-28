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
 * B-08 (seeded flaw, SPEC.md B-08, still unfixed as of this commit): on
 * `checkout.session.completed`, credits are still granted with no replay
 * protection - see the next commit for the idempotent version of this
 * same block.
 */
export async function POST(request: Request) {
  const rawBody = await request.text();
  const signature = request.headers.get("stripe-signature");

  let event;
  try {
    event = stripe.webhooks.constructEvent(rawBody, signature ?? "", webhookSecret!);
  } catch {
    return NextResponse.json({ error: "invalid signature" }, { status: 400 });
  }

  if (event.type === "checkout.session.completed") {
    const session = event.data.object as Stripe.Checkout.Session;
    const metadata = (session.metadata ?? {}) as { userId?: string; credits?: string };
    const userId = metadata.userId;
    // Stripe metadata values are always strings on a real event payload
    // (session.metadata.credits is "10", not 10) - coerce so the demo
    // matches the real shape instead of relying on JS's `+` on a string.
    const credits = Number(metadata.credits);

    if (!userId || !Number.isFinite(credits)) {
      return NextResponse.json({ error: "malformed metadata" }, { status: 400 });
    }

    const supabaseAdmin = createAdminClient();
    const { data: profile } = await supabaseAdmin.from("profiles").select("credit_balance").eq("id", userId).single();
    if (profile) {
      await supabaseAdmin
        .from("profiles")
        .update({ credit_balance: profile.credit_balance + credits })
        .eq("id", userId);
    }
  }

  return NextResponse.json({ received: true });
}
