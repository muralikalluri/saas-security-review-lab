// Deliberately insecure for demonstration. Do not deploy.
// semgrep --test fixtures for b01-nextpublic-service-role-key.

function badServiceRole() {
  // ruleid: b01-nextpublic-service-role-key
  const key = process.env.NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY!;
  return key;
}

function badGenericSecret() {
  // ruleid: b01-nextpublic-service-role-key
  const secret = process.env.NEXT_PUBLIC_STRIPE_SECRET_KEY!;
  return secret;
}

function okPublicAnonKey() {
  // ok: b01-nextpublic-service-role-key
  const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!;
  return key;
}

function okServerOnlyServiceRole() {
  // ok: b01-nextpublic-service-role-key
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY!;
  return key;
}

function okUnrelatedPublicVar() {
  // ok: b01-nextpublic-service-role-key
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL!;
  return url;
}
