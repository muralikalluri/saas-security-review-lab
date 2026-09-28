import { createServerClient, type CookieOptions } from "@supabase/ssr";
import { cookies, headers } from "next/headers";

type CookieToSet = { name: string; value: string; options: CookieOptions };

/**
 * Server client (Server Components / Route Handlers) - runs as the
 * calling user, either via their session cookie (the browser app) or a
 * raw `Authorization: Bearer <access_token>` header (curl / the
 * exploits/ scripts) - both are legitimate, equally-real ways to call
 * these routes, exactly like targets/tenant-api's own /invoices etc.
 * Anon key only; RLS (where it exists - see B-03/B-04) still applies.
 */
export function createClient() {
  const cookieStore = cookies();
  const bearer = getBearerToken();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      global: bearer ? { headers: { Authorization: `Bearer ${bearer}` } } : undefined,
      cookies: {
        getAll() {
          return cookieStore.getAll();
        },
        setAll(cookiesToSet: CookieToSet[]) {
          try {
            cookiesToSet.forEach(({ name, value, options }) => cookieStore.set(name, value, options));
          } catch {
            // called from a Server Component - a middleware refreshing the session handles this instead.
          }
        },
      },
    }
  );
}

function getBearerToken(): string | null {
  const authHeader = headers().get("authorization");
  if (authHeader?.startsWith("Bearer ")) {
    return authHeader.slice("Bearer ".length);
  }
  return null;
}

/** Reads the current user from their session (cookie or bearer token), or null if not logged in. */
export async function getSessionUser() {
  const supabase = createClient();
  const bearer = getBearerToken();
  const {
    data: { user },
  } = bearer ? await supabase.auth.getUser(bearer) : await supabase.auth.getUser();
  return user;
}
