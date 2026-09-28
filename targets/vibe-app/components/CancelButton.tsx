"use client";

import { useRouter } from "next/navigation";

export default function CancelButton({ bookingId }: { bookingId: string }) {
  const router = useRouter();

  async function handleCancel() {
    const res = await fetch(`/api/bookings/${bookingId}/cancel`, { method: "POST" });
    if (res.ok) {
      router.refresh();
    } else {
      const body = await res.json();
      alert(`Could not cancel: ${body.error}`);
    }
  }

  return <button onClick={handleCancel}>Cancel</button>;
}
