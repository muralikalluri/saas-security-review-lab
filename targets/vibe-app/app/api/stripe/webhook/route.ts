import { NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";

/**
 * B-07 (seeded flaw, SPEC.md B-07): parses the request body directly with
 * no signature verification at all - a real handler would call
 * `stripe.webhooks.constructEvent(rawBody, signatureHeader, webhookSecret)`
 * and reject anything that doesn't verify. Anyone who knows this URL can
 * POST an arbitrary fake event and have it processed as if Stripe sent it.
 *
 * B-08 (seeded flaw, SPEC.md B-08): on `checkout.session.completed`,
 * credits are granted with no check that this specific Stripe event id
 * has already been processed - POSTing the identical body twice grants
 * credits twice. A real fix (M6) records processed event ids (or uses a
 * unique constraint) before granting anything.
 */
export async function POST(request: Request) {
  const event = await request.json();

  if (event.type === "checkout.session.completed") {
    const session = event.data.object;
    const userId: string = session.metadata.userId;
    // Stripe metadata values are always strings on a real event payload
    // (session.metadata.credits is "10", not 10) - coerce so the demo
    // matches the real shape instead of relying on JS's `+` on a string.
    const credits: number = Number(session.metadata.credits);

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
