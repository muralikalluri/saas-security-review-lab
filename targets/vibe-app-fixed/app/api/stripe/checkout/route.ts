import { NextResponse } from "next/server";
import { stripe } from "@/lib/stripe";
import { getSessionUser } from "@/lib/supabase/server";

/**
 * Creates a real Stripe Checkout Session for a credit pack. Since
 * lib/stripe.ts's key is a fake placeholder (B-02), this call fails
 * against the real Stripe API in this lab - it's included for structural
 * completeness only. The seeded findings this module exists to
 * demonstrate (B-07, B-08) are proven against /api/stripe/webhook
 * directly with a forged event body, which needs no real Stripe account.
 */
export async function POST(request: Request) {
  const user = await getSessionUser();
  if (!user) {
    return NextResponse.json({ error: "not authenticated" }, { status: 401 });
  }

  const origin = new URL(request.url).origin;

  try {
    const session = await stripe.checkout.sessions.create({
      mode: "payment",
      line_items: [{ price_data: { currency: "usd", unit_amount: 2500, product_data: { name: "10 class credits (fictional)" } }, quantity: 1 }],
      success_url: `${origin}/bookings?purchase=success`,
      cancel_url: `${origin}/bookings?purchase=cancelled`,
      metadata: { userId: user.id, credits: "10" },
    });
    return NextResponse.json({ url: session.url });
  } catch (err) {
    return NextResponse.json({ error: "Stripe checkout is not functional in this lab (fake key, see lib/stripe.ts)." }, { status: 502 });
  }
}
