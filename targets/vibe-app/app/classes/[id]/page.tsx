import { createClient } from "@/lib/supabase/server";
import BookingForm from "@/components/BookingForm";

export default async function ClassDetailPage({ params }: { params: { id: string } }) {
  const supabase = createClient();
  const { data: classRow } = await supabase.from("classes").select("*").eq("id", params.id).single();

  if (!classRow) {
    return <main>Class not found.</main>;
  }

  return (
    <main>
      <h1>{classRow.title}</h1>
      <p>
        {classRow.instructor} - {classRow.studio_name}
      </p>
      <p>{new Date(classRow.starts_at).toLocaleString()}</p>
      <BookingForm classId={classRow.id} creditCostPerSeat={classRow.credit_cost} />
    </main>
  );
}
